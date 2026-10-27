"""CLI Entry point for Generic Web Form Validation Automation Framework."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from config.config_loader import ConfigLoader, FrameworkConfig
from core.browser.browser_manager import BrowserManager
from core.login.login_manager import LoginManager, LoginException
from core.navigation.navigator import Navigator, NavigationException
from demo.server import DemoServer
from form_engine.field_classifier import FieldClassifier
from form_engine.field_detector import FieldDetector
from form_engine.form_detector import FormDetector
from form_engine.form_executor import FormExecutor
from form_engine.models import TestStatus
from reporting.logger import logger
from reporting.report_manager import ReportManager
from rules.rule_registry import RuleRegistry


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generic Web Form Validation Automation Framework — V1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --config config/projects/example.yaml
  python run.py --config config/projects/example.yaml --headed
  python run.py --config config/projects/example.yaml --headless --demo
  python run.py --help
        """,
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config/projects/example.yaml",
        help="Path to YAML configuration file (default: config/projects/example.yaml)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=False,
        help="Run browser in visible (headed) mode",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=None,
        help="Slow down Playwright execution by specified milliseconds",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=False,
        help="Automatically launch local demo server on port 8080 before testing",
    )
    parser.add_argument(
        "--report-dir",
        type=str,
        default=None,
        help="Directory to save execution reports (overrides config setting)",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        default=False,
        help="Halt test suite execution on first failed validation test",
    )
    return parser.parse_args()


def run_framework(args: argparse.Namespace) -> int:
    """Executes the full automated form validation pipeline."""
    # 1. Load Configuration
    config_path = Path(args.config)
    if not config_path.exists():
        fallback = Path("config/config.yaml")
        if fallback.exists():
            config_path = fallback
        else:
            logger.error(f"Config file not found: {args.config}")
            return 1

    logger.info(f"Loading configuration from: {config_path}")
    config = ConfigLoader.load(config_path)

    # CLI Overrides
    headless_override = None
    if args.headed:
        headless_override = False
    elif args.headless:
        headless_override = True

    if args.slow_mo is not None:
        config.browser.slow_mo = args.slow_mo
    if args.report_dir:
        config.execution.output_dir = args.report_dir
    if args.stop_on_failure:
        config.execution.stop_on_failure = True

    # 2. Local Demo Server management
    demo_server = None
    needs_demo = args.demo or "127.0.0.1:8080" in config.application.base_url or "localhost:8080" in config.application.base_url
    if needs_demo:
        demo_server = DemoServer(port=8080)
        demo_server.start()
        time.sleep(0.5)

    browser_manager = BrowserManager(config, headless_override=headless_override)

    try:
        # 3. Open Browser
        page = browser_manager.start()
        logger.info("Application started")

        # 4. Detect Login Page & Authenticate
        login_manager = LoginManager(config)
        page = login_manager.authenticate(page)

        # 5. Navigate to Target Form URL
        navigator = Navigator(config)
        page = navigator.navigate_to_target(page)
        logger.info(f"Target form opened: {page.url}")

        # 6. Detect Form & Fields
        classifier = FieldClassifier(overrides=config.field_overrides)
        field_detector = FieldDetector(classifier=classifier, config=config.raw_config)
        form_detector = FormDetector(field_detector=field_detector)

        forms = form_detector.detect_forms(page)
        if not forms:
            logger.error("No form or interactive input container detected on target page.")
            return 1

        forms_with_fields = [f for f in forms if len(f.fields) > 0]
        if not forms_with_fields:
            logger.error("Forms were found on the page, but none contained interactive fields.")
            return 1

        target_form = max(forms_with_fields, key=lambda f: len(f.fields))
        logger.info(f"Target form '{target_form.selector}' selected with {len(target_form.fields)} fields.")

        # Log classified fields
        for f in target_form.fields:
            logger.info(f"Field '{f.name}' classified as {f.semantic_type.value} (required={f.required}, reason={f.required_reason.value})")

        # 7. Generate Validation Test Cases
        rule_registry = RuleRegistry()
        test_cases = rule_registry.generate_all(target_form.fields, config.raw_config)
        logger.info(f"Generating test cases: {len(test_cases)} validation cases generated.")

        # 8. Execute Validation Tests
        executor = FormExecutor(config, form_detector=form_detector, rule_registry=rule_registry)
        results = executor.execute_suite(page, target_form, test_cases)
        logger.info("Execution completed")

        # 9. Reporting
        ReportManager.print_console_summary(results)
        ReportManager.save_json_summary(results, config.execution.output_dir)
        ReportManager.save_html_summary(results, config.execution.output_dir, config.project_name)

        has_failures = any(r.status == TestStatus.FAIL for r in results)
        return 1 if has_failures else 0

    except (LoginException, NavigationException) as auth_err:
        logger.error(f"Authentication/Navigation error: {auth_err}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected framework execution error: {e}")
        return 1
    finally:
        browser_manager.stop()
        if demo_server:
            demo_server.stop()


def main():
    args = parse_args()
    exit_code = run_framework(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
