"""End-to-end integration test verifying the generic form validation framework pipeline."""
import pytest
from core.browser.browser_manager import BrowserManager
from core.login.login_manager import LoginManager
from core.navigation.navigator import Navigator
from form_engine.field_classifier import FieldClassifier
from form_engine.field_detector import FieldDetector
from form_engine.form_detector import FormDetector
from form_engine.form_executor import FormExecutor
from form_engine.models import SemanticType, TestStatus
from reporting.report_manager import ReportManager
from rules.rule_registry import RuleRegistry


def test_complete_form_validation_flow(demo_server, example_config):
    """Executes the complete end-to-end form validation lifecycle against the local demo application."""
    browser_manager = BrowserManager(example_config, headless_override=True)

    try:
        page = browser_manager.start()

        # 1. Login
        login_manager = LoginManager(example_config)
        page = login_manager.authenticate(page)

        # 2. Target Form Navigation
        navigator = Navigator(example_config)
        page = navigator.navigate_to_target(page)
        assert "create_user.html" in page.url

        # 3. Detect Form & Fields
        classifier = FieldClassifier(overrides=example_config.field_overrides)
        field_detector = FieldDetector(classifier=classifier, config=example_config.raw_config)
        form_detector = FormDetector(field_detector=field_detector)

        forms = form_detector.detect_forms(page)
        assert len(forms) > 0, "Expected at least one form to be detected."
        forms_with_fields = [f for f in forms if len(f.fields) > 0]
        assert len(forms_with_fields) > 0, "Expected at least one form with interactive fields."
        target_form = max(forms_with_fields, key=lambda f: len(f.fields))

        # Verify all 8 fields in create_user.html are detected & classified
        field_types = {f.name: f.semantic_type for f in target_form.fields}
        assert field_types.get("username") == SemanticType.USERNAME
        assert field_types.get("full_name") == SemanticType.FULL_NAME
        assert field_types.get("email") == SemanticType.EMAIL
        assert field_types.get("password") == SemanticType.PASSWORD
        assert field_types.get("confirm_password") == SemanticType.CONFIRM_PASSWORD
        assert field_types.get("phone") == SemanticType.PHONE
        assert field_types.get("role") == SemanticType.DROPDOWN
        assert field_types.get("age") == SemanticType.NUMBER

        # 4. Generate Validation Test Cases
        rule_registry = RuleRegistry()
        test_cases = rule_registry.generate_all(target_form.fields, example_config.raw_config)
        assert len(test_cases) > 15, f"Expected comprehensive test cases, got {len(test_cases)}"

        # 5. Execute Validation Tests
        executor = FormExecutor(example_config)
        results = executor.execute_suite(page, target_form, test_cases)

        assert len(results) == len(test_cases)
        # Check summary metrics
        passed = [r for r in results if r.status == TestStatus.PASS]
        failed = [r for r in results if r.status == TestStatus.FAIL]
        observations = [r for r in results if r.status == TestStatus.OBSERVATION]

        assert len(passed) > 0, "Expected multiple tests to pass."
        assert len(failed) == 0, f"Expected 0 failures, got {len(failed)}: {[f.test_case.rule_name for f in failed]}"
        assert len(observations) > 0, "Expected observation tests (e.g. name numbers/symbols)."

        # 6. Generate Reports
        ReportManager.save_json_summary(results, example_config.execution.output_dir)
        ReportManager.save_html_summary(results, example_config.execution.output_dir, example_config.project_name)

    finally:
        browser_manager.stop()
