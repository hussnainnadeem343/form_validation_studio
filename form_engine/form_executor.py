"""Form executor that drives Playwright through dynamically generated validation test cases."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.sync_api import Page
from config.config_loader import FrameworkConfig
from form_engine.models import (
    ExpectedBehavior,
    FieldDefinition,
    FormDefinition,
    SemanticType,
    TestCase,
    TestResult,
    TestStatus,
)
from reporting.logger import logger
from test_data.data_generator import DataGenerator
from validators.field_state_validator import FieldStateValidator
from validators.validation_message_validator import ValidationMessageValidator

try:
    import allure
    HAS_ALLURE = True
except ImportError:
    HAS_ALLURE = False


class FormExecutor:
    """Executes validation test cases against web forms and verifies outcomes."""

    def __init__(
        self,
        config: FrameworkConfig,
        event_listener: Optional[Any] = None,
        form_detector: Optional[Any] = None,
        rule_registry: Optional[Any] = None,
    ):
        self.config = config
        self.data_generator = DataGenerator(config.raw_config)
        self.screenshots_dir = Path(config.execution.screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.event_listener = event_listener

        if form_detector is None:
            from form_engine.form_detector import FormDetector
            from form_engine.field_detector import FieldDetector
            from form_engine.field_classifier import FieldClassifier
            classifier = FieldClassifier(overrides=config.field_overrides)
            detector = FieldDetector(classifier=classifier, config=config.raw_config)
            self.form_detector = FormDetector(field_detector=detector)
        else:
            self.form_detector = form_detector

        if rule_registry is None:
            from rules.rule_registry import RuleRegistry
            self.rule_registry = RuleRegistry()
        else:
            self.rule_registry = rule_registry

    def execute_suite(
        self,
        page: Page,
        form: FormDefinition,
        test_cases: List[TestCase],
    ) -> List[TestResult]:
        """Executes a suite of TestCases sequentially against the form, supporting multi-step wizards."""
        is_wizard = form.is_wizard or bool(form.next_element) or self.form_detector.is_multi_step_wizard(page)
        if is_wizard:
            return self._execute_wizard_suite(page, form, test_cases)
        return self._execute_single_form_suite(page, form, test_cases)

    def _execute_single_form_suite(
        self,
        page: Page,
        form: FormDefinition,
        test_cases: List[TestCase],
    ) -> List[TestResult]:
        """Standard single-step form validation suite execution."""
        results: List[TestResult] = []
        logger.info(f"Beginning execution of {len(test_cases)} validation test cases...")

        if self.event_listener:
            try:
                self.event_listener({"type": "suite_started", "total": len(test_cases), "form": form.selector})
            except Exception:
                pass

        fields_by_name = {f.name: f for f in form.fields}
        self._suite_context: Dict[str, Any] = {}
        self._baseline_dataset = self.data_generator.generate_baseline_dataset(form.fields, self._suite_context)

        for idx, tc in enumerate(test_cases, start=1):
            start_time = time.time()
            logger.info(f"[{idx}/{len(test_cases)}] Testing '{tc.field_name}' | Rule: {tc.rule_name} | Input: '{tc.input_value}'")

            if self.event_listener:
                try:
                    self.event_listener({
                        "type": "test_started",
                        "index": idx,
                        "total": len(test_cases),
                        "field": tc.field_name,
                        "semantic_type": tc.semantic_type.value,
                        "rule": tc.rule_name,
                        "input": str(tc.input_value),
                    })
                except Exception:
                    pass

            result = self._execute_single_test(page, form, fields_by_name, tc, idx)
            result.duration_ms = round((time.time() - start_time) * 1000, 2)
            results.append(result)

            logger.info(f"   -> Result: {result.status.value} | {result.actual_behavior}")

            if self.event_listener:
                try:
                    self.event_listener({
                        "type": "test_completed",
                        "index": idx,
                        "total": len(test_cases),
                        "field": tc.field_name,
                        "semantic_type": tc.semantic_type.value,
                        "rule": tc.rule_name,
                        "input": str(tc.input_value),
                        "status": result.status.value,
                        "actual": result.actual_behavior,
                        "validation_message": result.validation_message,
                        "screenshot": f"screenshots/{Path(result.screenshot_path).name}" if result.screenshot_path else None,
                        "duration_ms": result.duration_ms,
                    })
                except Exception:
                    pass

            if result.status == TestStatus.FAIL and self.config.execution.stop_on_failure:
                logger.warning("Stopping test suite early due to 'stop_on_failure: true' setting.")
                break

        if self.event_listener:
            try:
                self.event_listener({
                    "type": "suite_completed",
                    "total": len(results),
                    "passed": sum(1 for r in results if r.status == TestStatus.PASS),
                    "failed": sum(1 for r in results if r.status == TestStatus.FAIL),
                    "observation": sum(1 for r in results if r.status == TestStatus.OBSERVATION),
                    "skipped": sum(1 for r in results if r.status == TestStatus.SKIPPED),
                })
            except Exception:
                pass

        return results

    def _execute_wizard_suite(
        self,
        page: Page,
        form: FormDefinition,
        test_cases: List[TestCase],
    ) -> List[TestResult]:
        """Orchestrates validation execution across all sequential steps of a multi-step wizard."""
        results: List[TestResult] = []
        current_step = 1
        max_steps = 10
        completed_field_names = set()
        self._suite_context: Dict[str, Any] = {}
        self._cumulative_baseline: Dict[str, Any] = {}

        current_form = form
        current_cases = test_cases

        logger.info("Multi-step wizard detected. Initiating step-by-step validation progression...")

        while current_step <= max_steps:
            logger.info(f"=== Beginning Validation for Wizard Step {current_step} ({len(current_form.fields)} fields) ===")

            for tc in current_cases:
                tc.step_number = current_step

            step_field_names = {f.name for f in current_form.fields}
            completed_field_names.update(step_field_names)

            step_baseline = self.data_generator.generate_baseline_dataset(
                current_form.fields, self._suite_context
            )
            self._cumulative_baseline.update(step_baseline)
            self._baseline_dataset = dict(self._cumulative_baseline)

            if self.event_listener:
                try:
                    self.event_listener({
                        "type": "suite_started" if current_step == 1 else "step_started",
                        "step": current_step,
                        "fields_count": len(current_form.fields),
                        "total": len(results) + len(current_cases),
                    })
                except Exception:
                    pass

            def case_sort_order(tc: TestCase) -> int:
                if tc.expected_behavior == ExpectedBehavior.VALIDATION_TRIGGERED:
                    return 0
                elif tc.expected_behavior == ExpectedBehavior.OBSERVE:
                    return 1
                return 2

            sorted_cases = sorted(current_cases, key=case_sort_order)
            fields_by_name = {f.name: f for f in current_form.fields}

            for idx, tc in enumerate(sorted_cases, start=len(results) + 1):
                start_time = time.time()
                logger.info(
                    f"[Step {current_step} | #{idx}] Testing '{tc.field_name}' | "
                    f"Rule: {tc.rule_name} | Input: '{tc.input_value}'"
                )

                if self.event_listener:
                    try:
                        self.event_listener({
                            "type": "test_started",
                            "index": idx,
                            "step_number": current_step,
                            "total": len(results) + len(sorted_cases),
                            "field": tc.field_name,
                            "semantic_type": tc.semantic_type.value,
                            "rule": tc.rule_name,
                            "input": str(tc.input_value),
                        })
                    except Exception:
                        pass

                self._ensure_on_wizard_step(page, current_form, current_step)

                result = self._execute_single_test(page, current_form, fields_by_name, tc, idx)
                result.step_number = current_step
                result.duration_ms = round((time.time() - start_time) * 1000, 2)
                results.append(result)

                logger.info(f"   -> Result: {result.status.value} | {result.actual_behavior}")

                if self.event_listener:
                    try:
                        self.event_listener({
                            "type": "test_completed",
                            "index": idx,
                            "step_number": current_step,
                            "total": len(results),
                            "field": tc.field_name,
                            "semantic_type": tc.semantic_type.value,
                            "rule": tc.rule_name,
                            "input": str(tc.input_value),
                            "status": result.status.value,
                            "actual": result.actual_behavior,
                            "validation_message": result.validation_message,
                            "screenshot": f"screenshots/{Path(result.screenshot_path).name}" if result.screenshot_path else None,
                            "duration_ms": result.duration_ms,
                        })
                    except Exception:
                        pass

                if result.status == TestStatus.FAIL and self.config.execution.stop_on_failure:
                    logger.warning("Stopping test suite early due to 'stop_on_failure: true' setting.")
                    return results

            # All tests for current step completed:
            # 1. Fill current step with verified valid baseline data
            self._fill_all_step_fields(page, current_form.fields, self._cumulative_baseline)

            # 2. Find progression button ("Next" / "Continue")
            next_btn_sel = current_form.next_element or self.form_detector.detect_next_button(page)
            if not next_btn_sel:
                logger.info(f"No Next button found at Step {current_step}. Wizard validation completed.")
                break

            # 3. Click Next button to advance
            try:
                next_loc = page.locator(next_btn_sel).first
                if next_loc.count() > 0 and next_loc.is_visible():
                    logger.info(f"Advancing wizard from Step {current_step} via '{next_btn_sel}'...")
                    next_loc.click()
                    page.wait_for_timeout(800)
                else:
                    logger.info(f"Next button '{next_btn_sel}' not visible. Wizard validation finished.")
                    break
            except Exception as e:
                logger.warning(f"Failed to click Next button '{next_btn_sel}': {e}")
                break

            # 4. Detect new fields visible on the next step
            all_page_fields = self.form_detector.field_detector.detect_fields(page, container_selector="body")
            new_step_fields = [f for f in all_page_fields if f.name not in completed_field_names]

            if not new_step_fields:
                logger.info(f"No newly visible interactive fields found after Step {current_step}. Final review or submission reached.")
                break

            current_step += 1
            next_next_btn = self.form_detector.detect_next_button(page)
            next_prev_btn = self.form_detector.detect_prev_button(page)
            step_submit = next_next_btn or self.form_detector._detect_form_submit(page.locator("body").first, "body", page=page)

            current_form = FormDefinition(
                selector=current_form.selector,
                fields=new_step_fields,
                submit_element=step_submit,
                is_wizard=True,
                next_element=next_next_btn or "",
                prev_element=next_prev_btn or "",
                step_number=current_step,
            )

            current_cases = self.rule_registry.generate_all(new_step_fields, self.config.raw_config)
            logger.info(f"Discovered {len(new_step_fields)} fields on Step {current_step}; generated {len(current_cases)} test cases.")

        if self.event_listener:
            try:
                self.event_listener({
                    "type": "suite_completed",
                    "total": len(results),
                    "passed": sum(1 for r in results if r.status == TestStatus.PASS),
                    "failed": sum(1 for r in results if r.status == TestStatus.FAIL),
                    "observation": sum(1 for r in results if r.status == TestStatus.OBSERVATION),
                    "skipped": sum(1 for r in results if r.status == TestStatus.SKIPPED),
                })
            except Exception:
                pass

        return results

    def _fill_all_step_fields(
        self,
        page: Page,
        fields: List[FieldDefinition],
        baseline_dataset: Dict[str, Any],
    ) -> None:
        """Fills all fields on the current step with clean, valid baseline data."""
        for f in fields:
            val = baseline_dataset.get(f.name, "")
            loc = page.locator(f.selector).first
            if loc.count() > 0 and loc.is_visible():
                self._fill_field(loc, f, val)
                try:
                    loc.evaluate("el => el.dispatchEvent(new Event('input', { bubbles: true }))")
                    loc.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                    loc.evaluate("el => el.dispatchEvent(new Event('blur', { bubbles: true }))")
                except Exception:
                    pass

    def _ensure_on_wizard_step(
        self,
        page: Page,
        form: FormDefinition,
        step_number: int,
    ) -> None:
        """Ensures the browser is on the step containing the active step fields."""
        any_visible = False
        for f in form.fields:
            loc = page.locator(f.selector).first
            if loc.count() > 0 and loc.is_visible():
                any_visible = True
                break

        if not any_visible:
            prev_btn = form.prev_element or self.form_detector.detect_prev_button(page)
            if prev_btn:
                try:
                    p_loc = page.locator(prev_btn).first
                    if p_loc.count() > 0 and p_loc.is_visible():
                        logger.info(f"Target fields not visible; clicking Previous button '{prev_btn}' to return to Step {step_number}.")
                        p_loc.click()
                        page.wait_for_timeout(500)
                except Exception as e:
                    logger.debug(f"Failed to click previous button: {e}")

    def _execute_single_test(
        self,
        page: Page,
        form: FormDefinition,
        fields_by_name: Dict[str, FieldDefinition],
        test_case: TestCase,
        test_index: int,
    ) -> TestResult:
        """Executes one validation test case."""
        target_field = fields_by_name.get(test_case.field_name)
        if not target_field:
            return TestResult(
                test_case=test_case,
                status=TestStatus.SKIPPED,
                actual_behavior=f"Field '{test_case.field_name}' not found in form fields.",
                step_number=test_case.step_number,
            )

        # 1. Reset / Refresh form to a clean baseline state if needed
        self._reset_and_fill_baseline(page, form, target_field, test_case)

        # 2. Inject target test input into target field
        target_loc = page.locator(target_field.selector).first
        self._fill_field(target_loc, target_field, test_case.input_value)

        # 3. Trigger validation via blur and/or form submission
        target_loc.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
        target_loc.evaluate("el => el.dispatchEvent(new Event('blur', { bubbles: true }))")

        if form.submit_element:
            try:
                sub_loc = page.locator(form.submit_element).first
                if sub_loc.count() > 0 and sub_loc.is_visible():
                    is_next_btn = (
                        form.is_wizard
                        and bool(form.next_element)
                        and (form.submit_element == form.next_element or "next" in form.submit_element.lower())
                    )
                    if is_next_btn and test_case.expected_behavior == ExpectedBehavior.ACCEPTED:
                        logger.debug("Skipping Next click for ACCEPTED test case on wizard step to avoid premature advancement.")
                    elif sub_loc.is_enabled():
                        sub_loc.click(timeout=1000)
                    else:
                        logger.debug("Submit button is currently disabled by application logic.")
            except Exception as e:
                logger.debug(f"Click submit failed: {e}")
        else:
            try:
                target_loc.press("Enter")
            except Exception:
                pass

        page.wait_for_timeout(400)

        # 4. Capture validation state and messages
        form_loc = page.locator(form.selector).first if form.selector else None
        is_invalid_state, state_reason = FieldStateValidator.is_field_invalid(target_loc)
        has_msg, msg_text, msg_source = ValidationMessageValidator.find_validation_message(page, target_loc, form_loc, target_field)

        has_validation = is_invalid_state or has_msg
        validation_detail = msg_text or state_reason

        if not has_validation and test_case.rule_name == "alphabetic_value_in_number":
            html_type = (target_loc.get_attribute("type") or "").lower()
            if html_type == "number":
                has_validation = True
                validation_detail = "Browser native HTML5 number control strictly rejects alphabetic characters."

        if not has_validation and test_case.rule_name in ("invalid_date_format", "impossible_calendar_date"):
            html_type = (target_loc.get_attribute("type") or "").lower()
            if html_type in ("date", "datetime-local"):
                is_bad_input = target_loc.evaluate("el => (el.validity && (el.validity.badInput || !el.validity.valid)) || (el.value === '')")
                if is_bad_input:
                    has_validation = True
                    validation_detail = "Browser native HTML5 date control rejected invalid calendar date format."

        # 5. Evaluate status: PASS / FAIL / OBSERVATION
        status, actual_behavior = self._evaluate_outcome(test_case, has_validation, validation_detail)

        # 6. Capture screenshot if configured
        screenshot_path = self._handle_screenshot(page, test_case, status, test_index)

        # 7. Record Allure report steps and attachments
        self._report_to_allure(test_case, status, actual_behavior, validation_detail, screenshot_path)

        return TestResult(
            test_case=test_case,
            status=status,
            actual_behavior=actual_behavior,
            validation_message=validation_detail if has_validation else None,
            screenshot_path=screenshot_path,
            step_number=test_case.step_number,
        )

    def _reset_and_fill_baseline(
        self,
        page: Page,
        form: FormDefinition,
        target_field: FieldDefinition,
        test_case: TestCase,
    ) -> None:
        """Fills supporting required fields with valid baseline data to isolate target field validation."""
        paired_pass = test_case.metadata.get("paired_password")
        baseline_data = dict(getattr(self, "_baseline_dataset", {}))
        if not baseline_data:
            baseline_data = self.data_generator.generate_baseline_dataset(form.fields, {})
            self._baseline_dataset = baseline_data

        if paired_pass:
            for f in form.fields:
                if f.semantic_type in (SemanticType.PASSWORD, SemanticType.CONFIRM_PASSWORD):
                    baseline_data[f.name] = paired_pass

        for f in form.fields:
            if f.name == target_field.name:
                continue

            val = baseline_data.get(f.name, "")
            loc = page.locator(f.selector).first
            if loc.count() > 0 and loc.is_visible():
                self._fill_field(loc, f, val)

    def _fill_field(self, locator, field_def: FieldDefinition, value: Any) -> None:
        """Sets value on element according to its HTML tag and type with zero timeout stalls."""
        try:
            val_str = "" if value is None else str(value)
            tag = (field_def.tag or "").lower()
            html_type = (field_def.html_type or "").lower()
            is_dropdown = tag == "select" or field_def.semantic_type == SemanticType.DROPDOWN

            if is_dropdown:
                locator.evaluate("""(el, targetVal) => {
                    if (!el) return;
                    if (el.tagName !== 'SELECT') {
                        el.value = targetVal;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return;
                    }
                    const valStr = String(targetVal || '').trim();
                    const valLower = valStr.toLowerCase();

                    // 1. Exact value match
                    for (let i = 0; i < el.options.length; i++) {
                        if (el.options[i].value === valStr) {
                            el.selectedIndex = i;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return;
                        }
                    }
                    // 2. Case-insensitive value match
                    for (let i = 0; i < el.options.length; i++) {
                        if (el.options[i].value.toLowerCase() === valLower) {
                            el.selectedIndex = i;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return;
                        }
                    }
                    // 3. Label/Text match
                    for (let i = 0; i < el.options.length; i++) {
                        const optText = el.options[i].text.trim().toLowerCase();
                        if (optText === valLower || (valLower && optText.includes(valLower))) {
                            el.selectedIndex = i;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return;
                        }
                    }
                    // 4. First non-empty option
                    for (let i = 0; i < el.options.length; i++) {
                        if (el.options[i].value.trim() !== '') {
                            el.selectedIndex = i;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return;
                        }
                    }
                    // 5. Fallback to index 1 or 0
                    if (el.options.length > 1) {
                        el.selectedIndex = 1;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""", val_str)
            elif html_type in ("radio", "checkbox"):
                locator.evaluate("""(el) => {
                    if (el && !el.checked) {
                        el.checked = true;
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""")
            elif html_type == "file" or field_def.semantic_type == SemanticType.FILE_UPLOAD:
                try:
                    current_files = locator.evaluate("el => el.files ? el.files.length : 0") or 0
                    if current_files == 0:
                        import tempfile
                        from pathlib import Path
                        dummy_file = Path(tempfile.gettempdir()) / "qa_dummy_upload.jpg"
                        if not dummy_file.exists():
                            dummy_file.write_bytes(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9')
                        locator.set_input_files(str(dummy_file))
                        locator.evaluate("el => { el.dispatchEvent(new Event('change', { bubbles: true })); }")
                except Exception as e:
                    logger.debug(f"File upload handling skipped: {e}")
                return
            else:
                is_date = html_type in ("date", "datetime-local") or field_def.semantic_type == SemanticType.DATE
                if is_date and html_type in ("date", "datetime-local"):
                    locator.evaluate("""(el, v) => {
                        try {
                            el.value = v;
                        } catch(e) {}
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""", val_str)
                else:
                    try:
                        locator.fill(val_str, timeout=1500)
                    except Exception:
                        locator.evaluate("""(el, v) => {
                            el.value = v;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }""", val_str)

                    actual_val = locator.evaluate("el => el.value") or ""
                    if len(val_str) > len(actual_val) and html_type not in ("number", "date", "datetime-local"):
                        locator.evaluate("""(el, v) => {
                            el.value = v;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }""", val_str)

                if is_date:
                    locator.evaluate("""(el) => {
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                        const popups = document.querySelectorAll('.daterangepicker, .ui-datepicker, .datepicker-dropdown, .flatpickr-calendar, .pika-single, .bootstrap-datetimepicker-widget');
                        popups.forEach(p => {
                            p.style.display = 'none';
                            p.classList.remove('show', 'show-calendar', 'open');
                        });
                    }""")
        except Exception as e:
            logger.debug(f"Error setting field {field_def.name}: {e}")

    def _evaluate_outcome(
        self,
        test_case: TestCase,
        has_validation: bool,
        validation_detail: str,
    ) -> tuple[TestStatus, str]:
        """Maps expected vs actual outcomes to PASS, FAIL, or OBSERVATION."""
        exp = test_case.expected_behavior

        if exp == ExpectedBehavior.OBSERVE:
            if has_validation:
                return TestStatus.OBSERVATION, f"Application rejected input: '{validation_detail}'"
            return TestStatus.OBSERVATION, "Application accepted input without validation error."

        elif exp == ExpectedBehavior.VALIDATION_TRIGGERED:
            if has_validation:
                return TestStatus.PASS, f"Validation triggered as expected: '{validation_detail}'"
            return TestStatus.FAIL, "Expected validation error, but application accepted the input."

        elif exp == ExpectedBehavior.ACCEPTED:
            if not has_validation:
                return TestStatus.PASS, "Input was accepted with no validation error as expected."
            return TestStatus.FAIL, f"Expected input to be accepted, but validation error triggered: '{validation_detail}'"

        return TestStatus.SKIPPED, "Unknown expected behavior"

    def _handle_screenshot(
        self,
        page: Page,
        test_case: TestCase,
        status: TestStatus,
        test_index: int,
    ) -> Optional[str]:
        """Captures screenshot according to execution settings."""
        should_snap = False
        if status == TestStatus.FAIL and self.config.execution.screenshot_on_failure:
            should_snap = True
        elif status == TestStatus.OBSERVATION and self.config.execution.screenshot_on_observation:
            should_snap = True

        if not should_snap:
            return None

        clean_field = re.sub(r"\W+", "_", test_case.field_name.lower())
        clean_rule = re.sub(r"\W+", "_", test_case.rule_name.lower())
        filename = f"{clean_field}_{clean_rule}_{test_index:03d}.png"
        file_path = self.screenshots_dir / filename

        try:
            page.screenshot(path=str(file_path), full_page=True)
            return str(file_path)
        except Exception as e:
            logger.warning(f"Failed to capture screenshot: {e}")
            return None

    def _report_to_allure(
        self,
        test_case: TestCase,
        status: TestStatus,
        actual: str,
        validation_detail: str,
        screenshot_path: Optional[str],
    ) -> None:
        """Attaches execution details to Allure if running under an Allure test lifecycle."""
        if not HAS_ALLURE:
            return
        try:
            step_name = f"{test_case.field_name} - {test_case.rule_name} [{status.value}]"
            with allure.step(step_name):
                allure.attach(
                    f"Field: {test_case.field_name}\n"
                    f"Step: {test_case.step_number}\n"
                    f"Semantic Type: {test_case.semantic_type.value}\n"
                    f"Rule: {test_case.rule_name}\n"
                    f"Input: {test_case.input_value}\n"
                    f"Expected: {test_case.expected_behavior.value}\n"
                    f"Actual: {actual}\n"
                    f"Validation Detail: {validation_detail}\n"
                    f"Status: {status.value}\n",
                    name="Test Case Summary",
                    attachment_type=allure.attachment_type.TEXT,
                )
                if screenshot_path and os.path.exists(screenshot_path):
                    with open(screenshot_path, "rb") as f:
                        allure.attach(
                            f.read(),
                            name=f"Screenshot_{status.value}",
                            attachment_type=allure.attachment_type.PNG,
                        )
        except Exception:
            pass
