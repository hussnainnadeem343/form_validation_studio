"""End-to-end integration test verifying the generic form validation framework against a multi-step wizard."""
import pytest
from config.config_loader import ApplicationConfig, BrowserConfig, ExecutionConfig, FrameworkConfig, LoginConfig
from core.browser.browser_manager import BrowserManager
from core.navigation.navigator import Navigator
from form_engine.field_classifier import FieldClassifier
from form_engine.field_detector import FieldDetector
from form_engine.form_detector import FormDetector
from form_engine.form_executor import FormExecutor
from form_engine.models import SemanticType, TestStatus
from reporting.report_manager import ReportManager
from rules.rule_registry import RuleRegistry


@pytest.fixture
def wizard_config(tmp_path):
    """Configuration targeting the 3-step wizard registration demo."""
    return FrameworkConfig(
        project_name="Multi-Step Wizard Registration",
        application=ApplicationConfig(
            base_url="http://127.0.0.1:8080/wizard_registration.html",
            target_url="http://127.0.0.1:8080/wizard_registration.html",
        ),
        login=LoginConfig(),
        browser=BrowserConfig(browser="chromium", headless=True, timeout=15000),
        execution=ExecutionConfig(
            output_dir=str(tmp_path / "reports"),
            screenshots_dir=str(tmp_path / "screenshots"),
        ),
    )


def test_complete_wizard_form_validation_flow(demo_server, wizard_config):
    """Executes full automated validation progression through all steps of the 3-step registration wizard."""
    browser_manager = BrowserManager(wizard_config, headless_override=True)

    try:
        page = browser_manager.start()

        # 1. Navigate to target wizard
        navigator = Navigator(wizard_config)
        page = navigator.navigate_to_target(page)
        assert "wizard_registration.html" in page.url

        # 2. Detect Form & Wizard Elements
        classifier = FieldClassifier()
        field_detector = FieldDetector(classifier=classifier, config=wizard_config.raw_config)
        form_detector = FormDetector(field_detector=field_detector)

        forms = form_detector.detect_forms(page)
        assert len(forms) > 0, "Expected at least one form to be detected."
        target_form = max([f for f in forms if len(f.fields) > 0], key=lambda f: len(f.fields))

        # Verify wizard detection and Step 1 initial fields
        assert target_form.is_wizard is True, "Target form should be recognized as a multi-step wizard."
        assert bool(target_form.next_element), "Next progression button should be detected."

        step1_fields = {f.name: f.semantic_type for f in target_form.fields}
        assert "category" in step1_fields
        assert "cnic" in step1_fields
        assert "cnic_expiry" in step1_fields
        assert step1_fields["cnic_expiry"] == SemanticType.DATE
        assert "password" in step1_fields
        assert "confirm_password" in step1_fields

        # 3. Generate Step 1 Validation Test Cases
        rule_registry = RuleRegistry()
        test_cases = rule_registry.generate_all(target_form.fields, wizard_config.raw_config)
        assert len(test_cases) > 10, f"Expected comprehensive Step 1 tests, got {len(test_cases)}"

        # 4. Execute Multi-Step Wizard Validation
        executor = FormExecutor(
            wizard_config,
            form_detector=form_detector,
            rule_registry=rule_registry,
        )
        results = executor.execute_suite(page, target_form, test_cases)

        # 5. Verify Results Across All Steps
        assert len(results) > len(test_cases), "Wizard execution should discover and test subsequent steps."

        step1_results = [r for r in results if r.step_number == 1]
        step2_results = [r for r in results if r.step_number == 2]

        assert len(step1_results) > 0, "Expected Step 1 validation test results."
        assert len(step2_results) > 0, "Expected Step 2 validation test results."

        # Verify Step 2 fields were tested
        step2_fields_tested = {r.test_case.field_name for r in step2_results}
        assert "recovery_email" in step2_fields_tested
        assert "phone" in step2_fields_tested

        # Check outcomes
        passed = [r for r in results if r.status == TestStatus.PASS]
        failed = [r for r in results if r.status == TestStatus.FAIL]

        assert len(passed) > 0, "Expected passing validation tests."
        assert len(failed) == 0, f"Expected 0 failures in wizard demo, got {len(failed)}: {[f.test_case.rule_name for f in failed]}"

        # 6. Verify Reporting output
        json_path = ReportManager.save_json_summary(results, wizard_config.execution.output_dir)
        html_path = ReportManager.save_html_summary(results, wizard_config.execution.output_dir, wizard_config.project_name)

        assert json_path.exists()
        assert html_path.exists()

    finally:
        browser_manager.stop()
