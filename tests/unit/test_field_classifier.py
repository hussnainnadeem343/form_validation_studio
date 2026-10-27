"""Unit tests for FieldClassifier heuristics and configuration overrides."""
import pytest
from form_engine.field_classifier import FieldClassifier
from form_engine.models import FieldDefinition, SemanticType


@pytest.fixture
def classifier():
    return FieldClassifier()


def test_classify_username(classifier):
    field = FieldDefinition(
        name="user_name",
        label="Username",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#username",
    )
    assert classifier.classify(field) == SemanticType.USERNAME


def test_classify_full_name(classifier):
    field = FieldDefinition(
        name="full_name",
        label="Full Name",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#fullname",
    )
    assert classifier.classify(field) == SemanticType.FULL_NAME


def test_classify_email(classifier):
    field = FieldDefinition(
        name="email_addr",
        label="Email Address",
        html_type="email",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#email",
    )
    assert classifier.classify(field) == SemanticType.EMAIL


def test_classify_password(classifier):
    field = FieldDefinition(
        name="password",
        label="Password",
        html_type="password",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#password",
    )
    assert classifier.classify(field) == SemanticType.PASSWORD


def test_classify_confirm_password(classifier):
    field = FieldDefinition(
        name="confirm_password",
        label="Confirm Password",
        html_type="password",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#confirm_pwd",
    )
    assert classifier.classify(field) == SemanticType.CONFIRM_PASSWORD


def test_classify_phone(classifier):
    field = FieldDefinition(
        name="contact_number",
        label="Mobile Phone",
        html_type="tel",
        semantic_type=SemanticType.UNKNOWN,
        required=False,
        selector="#phone",
    )
    assert classifier.classify(field) == SemanticType.PHONE


def test_classify_number(classifier):
    field = FieldDefinition(
        name="user_age",
        label="Age",
        html_type="number",
        semantic_type=SemanticType.UNKNOWN,
        required=False,
        selector="#age",
    )
    assert classifier.classify(field) == SemanticType.NUMBER


def test_classify_cnic(classifier):
    field = FieldDefinition(
        name="cnic",
        label="CNIC Number *",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#cnic",
    )
    assert classifier.classify(field) == SemanticType.CNIC


def test_classify_dropdown(classifier):
    field = FieldDefinition(
        name="role",
        label="User Role",
        html_type="select",
        tag="select",
        semantic_type=SemanticType.UNKNOWN,
        required=False,
        selector="#role",
    )
    assert classifier.classify(field) == SemanticType.DROPDOWN


def test_classify_unknown(classifier):
    field = FieldDefinition(
        name="xyz999_obscure",
        label="",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=False,
        selector="#xyz",
    )
    # Generic text input defaults to TEXT, but if html_type is unrecognized, UNKNOWN
    field.html_type = "custom-widget"
    assert classifier.classify(field) == SemanticType.UNKNOWN


def test_field_override():
    overrides = {
        "patient_identifier": {"semantic_type": "TEXT"},
        "custom_code": "NUMBER",
    }
    custom_classifier = FieldClassifier(overrides=overrides)
    field = FieldDefinition(
        name="patient_identifier",
        label="Patient Identifier",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=True,
        selector="#patient_id",
    )
    assert custom_classifier.classify(field) == SemanticType.TEXT

    field2 = FieldDefinition(
        name="custom_code",
        label="Code",
        html_type="text",
        semantic_type=SemanticType.UNKNOWN,
        required=False,
        selector="#code",
    )
    assert custom_classifier.classify(field2) == SemanticType.NUMBER
