# Generic Web Form Validation Automation Framework — V1

A modular, reusable, and configuration-driven test automation framework for web forms built with **Python 3.11+**, **Playwright**, **Pytest**, **YAML**, **Faker**, and **Allure Reporting**.

Designed to validate common web form controls and business logic across different projects and web applications without hardcoded application logic or brittle project-specific selectors.

---

## Architecture & Complete Flow

```text
Application URL
      ↓
Open Application (BrowserManager)
      ↓
Detect Login Page (LoginManager)
      ↓
Login (Auto-detection or Selectors)
      ↓
Navigate to Target Form URL (Navigator)
      ↓
Detect Form (FormDetector)
      ↓
Detect Fields (FieldDetector)
      ↓
Classify Fields (FieldClassifier)
      ↓
Load Generic Validation Rules (RuleRegistry)
      ↓
Generate Test Data (DataGenerator)
      ↓
Execute Validation Tests (FormExecutor)
      ↓
Verify Validation Behavior (Validators)
      ↓
Generate Test Report (ReportManager & Allure)
```

---

## Key Features

- **Decoupled Architecture**: Clear separation of browser lifecycle, authentication, navigation, form/field detection, semantic classification, rule generation, test data synthesis, execution, validation, and multi-tier reporting.
- **Dynamic Field Classification**: Multi-signal heuristic detection classifying inputs into semantic types (`USERNAME`, `FULL_NAME`, `EMAIL`, `PASSWORD`, `CONFIRM_PASSWORD`, `PHONE`, `TEXT`, `NUMBER`, `DROPDOWN`, `UNKNOWN`).
- **Resilient Validation Verification**: Does not assume a single CSS class for errors; inspects HTML5 native validity (`checkValidity()`), `aria-invalid`, CSS error classes (`is-invalid`, `error`, `has-error`), adjacent DOM error feedback, and form-level alerts.
- **PASS / FAIL / OBSERVATION Logic**: Differentiates between hard assertion failures and indeterminate exploratory behaviors (such as whether names accept numbers/symbols when unconfigured).
- **Extensible Rule Engine**: Register new semantic types and custom validation rules without modifying core execution logic.
- **Comprehensive Reporting**: Generates interactive HTML summaries, structured JSON results, automatic failure/observation screenshots, and native Allure test attachments.

---

## Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python 3.11+** | Modern typed programming language |
| **Playwright** | Fast, reliable cross-browser automation |
| **Pytest** | Test runner, assertions, and test fixtures |
| **YAML (PyYAML)** | Declarative project configurations and validation rules |
| **Faker** | Realistic synthetic and boundary test data generation |
| **Allure Reporting** | Detailed test diagnostics, steps, and artifact attachments |

---

## Installation

### 1. Clone & Set Up Virtual Environment

```bash
# Clone repository
git clone <repository_url>
cd kind-euclid

# Create virtual environment
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on Linux / macOS
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Running the Demo Application

The repository includes a self-contained demo web application with modern client-side validation (`demo/login.html` and `demo/create_user.html`).

### Option A: Automatic Launch via CLI Runner

Use the `--demo` flag with `run.py` to start the demo server automatically on port 8080 during execution:

```bash
python run.py --config config/projects/example.yaml --demo
```

### Option B: Standalone Demo Server

You can also run the server independently in a dedicated terminal:

```bash
python demo/server.py
```

Then visit:
- **Login Page**: `http://127.0.0.1:8080/login.html`
- **User Creation Form**: `http://127.0.0.1:8080/create_user.html`

Demo Admin Credentials:
- **Username**: `admin`
- **Password**: `Admin@123456`

---

## Running Form Validation

### Using the CLI (`run.py`)

```bash
# Run against demo project configuration (headless by default)
python run.py --config config/projects/example.yaml

# Run in visible (headed) browser mode
python run.py --config config/projects/example.yaml --headed

# Run with slow-motion (e.g. 100ms per step) for visual inspection
python run.py --config config/projects/example.yaml --headed --slow-mo 100

# Stop execution immediately upon first failure
python run.py --config config/projects/example.yaml --stop-on-failure
```

### Running Pytest Suites

```bash
# Run unit tests
pytest tests/unit -v

# Run end-to-end integration test
pytest tests/test_generic_form.py -v

# Run with Allure report results generation
pytest --alluredir=reports/allure-results
```

To view the generated Allure report (requires Allure CLI installed):

```bash
allure serve reports/allure-results
```

---

## Configuration Reference

Configuration files are located in `config/` (global defaults in `config/config.yaml` and project profiles in `config/projects/*.yaml`).

```yaml
project:
  name: "Demo Application Form Validation"

application:
  base_url: "http://127.0.0.1:8080/login.html"         # Entry / login page
  target_url: "http://127.0.0.1:8080/create_user.html" # Form to validate

login:
  username: "admin"          # Fallback credentials (overridden by TEST_USERNAME env var)
  password: "Admin@123456"   # Fallback credentials (overridden by TEST_PASSWORD env var)

  selectors:                 # Optional: Explicit selectors. Auto-detected if empty!
    username: ""
    password: ""
    submit: ""

browser:
  browser: "chromium"        # "chromium", "firefox", or "webkit"
  headless: true             # Headless execution mode
  slow_mo: 0                 # Milliseconds delay between browser actions
  timeout: 30000             # Playwright timeout in ms

execution:
  screenshot_on_failure: true
  screenshot_on_observation: true
  stop_on_failure: false
  output_dir: "reports"
  screenshots_dir: "screenshots"

rules:
  username:
    required: true
    min_length: 3
    max_length: 50
    allow_spaces: false
    allow_special_chars: false

  full_name:
    required: true
    min_length: 2
    max_length: 100

  email:
    required: true

  password:
    required: true
    min_length: 12
    uppercase: true
    lowercase: true
    number: true
    special_character: true

  confirm_password:
    required: true

  phone:
    required: false
    min_length: 10
    max_length: 15
    numeric_only: true

  number:
    required: false
    min: 18
    max: 99
    allow_decimal: false
    allow_negative: false

# Override automatic classification for non-standard or domain-specific fields
field_overrides:
  patient_identifier:
    semantic_type: "TEXT"
```

### Credentials via Environment Variables

Never commit production or sensitive credentials into git repositories. Pass them via environment variables:

```bash
# Windows PowerShell
$env:TEST_USERNAME="admin"
$env:TEST_PASSWORD="Admin@123456"
python run.py --config config/projects/example.yaml

# Linux / macOS
export TEST_USERNAME="admin"
export TEST_PASSWORD="Admin@123456"
python run.py --config config/projects/example.yaml
```

---

## Adding New Field Types (e.g. CNIC, Date, Patient MRN)

The framework is built around an extensible registry pattern. Adding a new field type takes 3 simple steps:

### 1. Register the Semantic Type
In `form_engine/models.py`, add the type to `SemanticType`:
```python
class SemanticType(str, Enum):
    # Existing types...
    CNIC = "CNIC"
    DATE = "DATE"
    MRN = "MRN"
```

### 2. Implement the Rule Generator
Create a new rule file in `rules/cnic_rules.py` inheriting from `BaseRule`:
```python
from rules.base_rule import BaseRule
from form_engine.models import FieldDefinition, TestCase, ExpectedBehavior

class CNICRule(BaseRule):
    def generate_test_cases(self, field, config, context):
        return [
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="cnic_format_check",
                input_value="12345-1234567-1",
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Valid CNIC standard 13-digit format.",
            )
        ]
```

### 3. Register in `RuleRegistry` & `FieldClassifier`
In `rules/rule_registry.py`:
```python
self.register(SemanticType.CNIC, CNICRule())
```
In `form_engine/field_classifier.py`, add signal heuristics or allow users to specify it in YAML `field_overrides`.

---

## Adding New Rules to Existing Fields

To add or modify rules for existing fields:
1. Open the field's rule generator (e.g. `rules/password_rules.py`).
2. Add new `TestCase` instances with the target input value, `expected_behavior` (`VALIDATION_TRIGGERED`, `ACCEPTED`, or `OBSERVE`), and description.
3. Configure any thresholds in the YAML `rules` section.

---

## Project Structure

```text
kind-euclid/
├── core/
│   ├── browser/
│   │   ├── browser_manager.py
│   │   └── __init__.py
│   ├── login/
│   │   ├── login_manager.py
│   │   └── __init__.py
│   ├── navigation/
│   │   ├── navigator.py
│   │   └── __init__.py
│   └── __init__.py
│
├── form_engine/
│   ├── models.py
│   ├── form_detector.py
│   ├── field_detector.py
│   ├── field_classifier.py
│   ├── form_executor.py
│   └── __init__.py
│
├── rules/
│   ├── base_rule.py
│   ├── rule_registry.py
│   ├── common_rules.py
│   ├── username_rules.py
│   ├── fullname_rules.py
│   ├── email_rules.py
│   ├── password_rules.py
│   ├── confirm_password_rules.py
│   ├── phone_rules.py
│   ├── number_rules.py
│   ├── dropdown_rules.py
│   ├── text_rules.py
│   └── __init__.py
│
├── test_data/
│   ├── data_generator.py
│   ├── valid_data.py
│   ├── invalid_data.py
│   └── __init__.py
│
├── validators/
│   ├── field_state_validator.py
│   ├── validation_message_validator.py
│   └── __init__.py
│
├── reporting/
│   ├── logger.py
│   ├── report_manager.py
│   └── __init__.py
│
├── config/
│   ├── config_loader.py
│   ├── config.yaml
│   └── projects/
│       └── example.yaml
│
├── demo/
│   ├── login.html
│   ├── create_user.html
│   └── server.py
│
├── tests/
│   ├── unit/
│   │   ├── test_field_classifier.py
│   │   ├── test_required_detector.py
│   │   ├── test_rules.py
│   │   └── test_data_generator.py
│   ├── conftest.py
│   └── test_generic_form.py
│
├── reports/
├── screenshots/
├── pytest.ini
├── requirements.txt
├── README.md
└── run.py
```

---

## Architecture Principles

1. **Reusability**: No project-specific logic or HMIS hardcoding in the core engine.
2. **Separation of Concerns**: Modular decoupled layers for browser, auth, detection, classification, rules, data, execution, validation, and reporting.
3. **Configuration over Hardcoding**: Change targets, credentials, selectors, and rule bounds purely via YAML.
4. **Resilient Heuristics & Graceful Degradation**: Clear diagnostics when elements cannot be resolved; fallback to user-specified selectors and overrides.
5. **Observation vs Hard Failure**: Avoid false positives on ambiguous inputs.

---

## Known Limitations (V1) & Future Roadmap

### V1 Limitations
- Heuristic field classification is not omniscient; non-standard or heavily obfuscated field names should use `field_overrides` in YAML.
- Multi-step wizard forms or dynamic multi-stage async forms will be expanded in V2.

### Future Roadmap
- **V2**: CNIC, Date/DateTime pickers, File Upload, Radio buttons, Checkboxes, Textareas, Searchable Dropdowns.
- **V3**: API-backed validation verification, Database state verification, Multi-step wizard workflows.
- **V4**: AI-assisted field classification and automated rule boundary inference.
