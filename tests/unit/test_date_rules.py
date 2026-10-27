"""Unit tests for Date Picker and Calendar validation rules and classification."""
from datetime import date
import pytest
from form_engine.field_classifier import FieldClassifier
from form_engine.models import ExpectedBehavior, FieldDefinition, RequiredReason, SemanticType
from rules.date_rules import DateRule
from rules.rule_registry import RuleRegistry
from test_data.valid_data import get_valid_value


def test_date_field_classification_native():
    classifier = FieldClassifier()
    field = FieldDefinition(
        name="visit_date",
        label="Visit Date",
        html_type="date",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#visit_date",
    )
    classified = classifier.classify(field)
    assert classified == SemanticType.DATE
    assert field.attributes.get("date_context") == "GENERAL"


def test_date_field_classification_datepicker_class():
    classifier = FieldClassifier()
    field = FieldDefinition(
        name="calendar_input",
        label="Select Date",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=False,
        selector="#calendar_input",
        attributes={"class": "form-control datepicker hasDatepicker"},
    )
    classified = classifier.classify(field)
    assert classified == SemanticType.DATE


def test_cnic_expiry_classified_as_date_not_cnic():
    classifier = FieldClassifier()
    field = FieldDefinition(
        name="cnic_expiry",
        label="CNIC Expiry Date",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#cnic_expiry",
        placeholder="YYYY-MM-DD",
    )
    classified = classifier.classify(field)
    assert classified == SemanticType.DATE
    assert field.attributes.get("date_context") == "EXPIRY"


def test_dob_classified_as_date_birth():
    classifier = FieldClassifier()
    field = FieldDefinition(
        name="dob",
        label="Date of Birth",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#dob",
        placeholder="DD/MM/YYYY",
    )
    classified = classifier.classify(field)
    assert classified == SemanticType.DATE
    assert field.attributes.get("date_context") == "BIRTH"
    assert field.attributes.get("date_format") == "DD/MM/YYYY"


def test_date_rule_generation_expiry():
    rule = DateRule()
    field = FieldDefinition(
        name="cnic_expiry",
        label="CNIC Expiry Date",
        html_type="text",
        semantic_type=SemanticType.DATE,
        required=True,
        selector="#cnic_expiry",
        required_reason=RequiredReason.HTML_REQUIRED,
        attributes={"date_context": "EXPIRY", "date_format": "YYYY-MM-DD"},
    )
    cases = rule.generate_test_cases(field, {}, {})
    rule_names = [c.rule_name for c in cases]

    assert "required_empty_check" in rule_names
    assert "invalid_date_format" in rule_names
    assert "impossible_calendar_date" in rule_names
    assert "expired_past_date" in rule_names
    assert "valid_date" in rule_names

    # Check that expired_past_date expects validation error
    expired_case = next(c for c in cases if c.rule_name == "expired_past_date")
    assert expired_case.expected_behavior == ExpectedBehavior.VALIDATION_TRIGGERED

    # Check that valid_date expects accepted
    valid_case = next(c for c in cases if c.rule_name == "valid_date")
    assert valid_case.expected_behavior == ExpectedBehavior.ACCEPTED
    # Valid date for expiry should be in the future
    assert int(valid_case.input_value.split("-")[0]) > date.today().year


def test_date_rule_generation_dob():
    rule = DateRule()
    field = FieldDefinition(
        name="dob",
        label="Date of Birth",
        html_type="text",
        semantic_type=SemanticType.DATE,
        required=True,
        selector="#dob",
        required_reason=RequiredReason.HTML_REQUIRED,
        attributes={"date_context": "BIRTH", "date_format": "YYYY-MM-DD"},
    )
    cases = rule.generate_test_cases(field, {}, {})
    rule_names = [c.rule_name for c in cases]

    assert "future_date_not_allowed" in rule_names
    future_case = next(c for c in cases if c.rule_name == "future_date_not_allowed")
    assert future_case.expected_behavior == ExpectedBehavior.VALIDATION_TRIGGERED
    assert int(future_case.input_value.split("-")[0]) > date.today().year


def test_valid_date_baseline_generation():
    # Expiry field should produce future year
    expiry_field = FieldDefinition(
        name="expiry",
        label="Expiry Date",
        html_type="text",
        semantic_type=SemanticType.DATE,
        required=True,
        selector="#expiry",
        attributes={"date_context": "EXPIRY", "date_format": "YYYY-MM-DD"},
    )
    val_exp = get_valid_value(expiry_field, {}, {})
    exp_year = int(val_exp.split("-")[0])
    assert exp_year > date.today().year

    # DOB field should produce past year (25 years ago)
    dob_field = FieldDefinition(
        name="dob",
        label="Date of Birth",
        html_type="text",
        semantic_type=SemanticType.DATE,
        required=True,
        selector="#dob",
        attributes={"date_context": "BIRTH", "date_format": "YYYY-MM-DD"},
    )
    val_dob = get_valid_value(dob_field, {}, {})
    dob_year = int(val_dob.split("-")[0])
    assert dob_year < date.today().year - 20


def test_rule_registry_includes_date():
    registry = RuleRegistry()
    rule = registry.get_rule(SemanticType.DATE)
    assert rule is not None
    assert isinstance(rule, DateRule)


def test_cnic_issuance_date_classified_as_date_not_cnic():
    classifier = FieldClassifier()
    field = FieldDefinition(
        name="cnic_issuance",
        label="CNIC ISSUANCE DATE *\nشناختی کارڈ جاری ہونے کی تاریخ *",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#cnic_issuance",
    )
    classified = classifier.classify(field)
    assert classified == SemanticType.DATE
    assert field.attributes.get("date_context") == "ISSUE"
    assert classified != SemanticType.CNIC


def test_cnic_validity_classified_as_dropdown_not_cnic():
    classifier = FieldClassifier()
    field = FieldDefinition(
        name="cnic_validity",
        label="CNIC VALIDITY *\nشناختی کارڈ کی معیاد *",
        html_type="select",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#cnic_validity",
        tag="select",
    )
    classified = classifier.classify(field)
    assert classified == SemanticType.DROPDOWN
    assert classified != SemanticType.CNIC


def test_cnic_front_image_classified_as_file_upload_not_cnic():
    classifier = FieldClassifier()
    field = FieldDefinition(
        name="cnic_front",
        label="CNIC FRONT IMAGE (JPEG/JPG MAX SIZE 50KB) *\nشناختی کارڈ سامنے کی تصویر *",
        html_type="file",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#cnic_front",
    )
    classified = classifier.classify(field)
    assert classified == SemanticType.FILE_UPLOAD
    assert classified != SemanticType.CNIC


def test_cnic_number_classified_as_cnic():
    classifier = FieldClassifier()
    field = FieldDefinition(
        name="cnic",
        label="CNIC / Citizen ID *",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#cnic",
    )
    classified = classifier.classify(field)
    assert classified == SemanticType.CNIC


def test_applicant_age_bounded_generation():
    field = FieldDefinition(
        name="age_of_applicant",
        label="AGE OF APPLICANT *\nدرخواست گزار کی عمر *",
        html_type="number",
        semantic_type=SemanticType.NUMBER,
        required=True,
        selector="#age_of_applicant",
    )
    for _ in range(20):
        val = int(get_valid_value(field, {}, {}))
        assert 18 <= val <= 65, f"Age {val} exceeded reasonable applicant limit (70 years)"

