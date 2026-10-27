# Copilot instructions for kind-euclid

## Project overview

This repository is a Python 3.11+ browser automation framework for validating generic web forms. It is designed to work against many apps without hardcoding project-specific selectors: the framework detects login flows, recognizes form fields, classifies them into semantic types, generates validation cases, executes them with Playwright, and produces pass/fail/observation results with screenshots and reports.

The most important workflow is: configuration -> browser startup -> login/navigation -> form detection -> field classification -> validation rule generation -> execution -> reporting.

## Build, test, and validation commands

### Environment setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### Run the demo app locally

```bash
python demo/server.py
```

Or let the CLI launch it automatically:

```bash
python run.py --config config/projects/example.yaml --demo
```

### Run the framework

```bash
python run.py --config config/projects/example.yaml
python run.py --config config/projects/example.yaml --headed
python run.py --config config/projects/example.yaml --stop-on-failure
```

### Run pytest

```bash
pytest tests/unit -v
pytest tests/test_generic_form.py -v
pytest tests/unit/test_field_classifier.py -q
pytest tests/unit/test_date_rules.py -q
pytest tests/unit/test_field_classifier.py::test_field_classifier_returns_expected_semantic_types -q
```

### Allure reporting

```bash
pytest --alluredir=reports/allure-results
allure serve reports/allure-results
```

### Linting

No dedicated lint task or config (`ruff`, `flake8`, `pylint`, `mypy`, `tox`, `nox`, or similar) was found in this repository. The repo's validation entry point is pytest; use that as the default check before considering a change safe.

## High-level architecture

### Entry point and orchestration

- `run.py` is the main CLI entrypoint. It loads YAML config, optionally starts the demo server, opens a Playwright browser, authenticates, navigates to the target page, discovers forms, generates validation cases, executes them, and writes reports.
- `config/config_loader.py` loads YAML config files and resolves environment variables such as `${VAR_NAME}`. This is the main integration point for app-specific configuration.
- `config/projects/*.yaml` holds app-specific project configuration. The default example config is `config/projects/example.yaml`.

### Browser, login, and navigation

- `core/browser/browser_manager.py` owns browser lifecycle and Playwright page creation.
- `core/login/login_manager.py` handles login-page detection and authentication.
- `core/navigation/navigator.py` moves to the target form after authentication.

### Form detection and field classification

- `form_engine/form_detector.py` finds candidate form containers and wizard flows.
- `form_engine/field_detector.py` discovers fields inside each form.
- `form_engine/field_classifier.py` classifies each field into semantic types such as `USERNAME`, `EMAIL`, `PASSWORD`, `PHONE`, `NUMBER`, `DATE`, `DROPDOWN`, and `TEXT` using heuristics from names, labels, placeholders, HTML input types, and config overrides.
- `form_engine/models.py` defines the dataclasses that represent fields, forms, test cases, and results.

### Rules and validation behavior

- `rules/` contains rule implementations for each semantic type (for example `email_rules.py`, `password_rules.py`, `date_rules.py`, `number_rules.py`, and `dropdown_rules.py`).
- `rules/rule_registry.py` is the central registry that maps semantic types to rule engines. It intentionally orders `PASSWORD` before `CONFIRM_PASSWORD` so paired validation context is available during generation.
- `validators/` checks whether the UI changed state as expected and whether validation messages appeared or disappeared in a way consistent with the field rule.

### Execution and reporting

- `form_engine/form_executor.py` drives the Playwright interactions and organizes suites, including wizard flows.
- `reporting/report_manager.py` writes console summaries, JSON output, HTML summaries, and integrates with Allure attachments.
- `reports/` and `screenshots/` are the output directories used during runtime.
- `demo/` contains the bundled demo app used for local validation and examples.

## Key conventions

- Prefer configuration-driven behavior over app-specific code. Add project settings in `config/projects/*.yaml` rather than hardcoding selectors or validation rules into the execution logic.
- Use `TEST_USERNAME` and `TEST_PASSWORD` environment variables for credentials; they override the YAML credentials during config loading.
- Field classification is heuristic and intentionally configurable. For non-standard names or custom apps, use `field_overrides` in YAML rather than modifying classifier logic unless the underlying detection pattern is broadly wrong.
- The framework distinguishes between `PASS`, `FAIL`, and `OBSERVATION`. Indeterminate UI behavior should be treated as `OBSERVATION`, not as a hard assertion failure.
- Rule generation is semantic-type driven. If you add a new field type or validation rule, register it in `rules/rule_registry.py` and add the corresponding rule implementation in `rules/`.
- Tests stay in the `tests/` tree and follow pytest naming conventions (`test_*.py`). Shared fixtures live in `tests/conftest.py`.
- The project is built around dataclasses and explicit configuration objects (`FrameworkConfig`, `FieldDefinition`, `FormDefinition`, `TestCase`, etc.) rather than ad hoc dictionaries. Keep new behavior aligned with those structures.
- The demo app is intentionally simple and meant to exercise generic form validation patterns. Treat it as a reference for expected behavior, not as a template for app-specific logic.

## Relevant repo conventions and guardrails

- Do not add project-specific selectors or business logic directly into the generic engine unless a new semantic type or a broad bug fix justifies it.
- Keep changes aligned with the existing architecture: browser/login/navigation logic in `core/`, detection/classification in `form_engine/`, rules in `rules/`, reporting in `reporting/`.
- Prefer extending the existing semantic classification and rule engine over adding one-off special cases scattered across execution code.
