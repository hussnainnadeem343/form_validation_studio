"""Unit tests for validation rule generation engines."""
import pytest
from form_engine.models import ExpectedBehavior, FieldDefinition, RequiredReason, SemanticType
from rules.confirm_password_rules import ConfirmPasswordRule
from rules.email_rules import EmailRule
from rules.fullname_rules import FullNameRule
from rules.number_rules import NumberRule
from rules.password_rules import PasswordRule
from rules.phone_rules import PhoneRule
from rules.rule_registry import RuleRegistry
from rules.username_rules import UsernameRule


@pytest.fixture
def base_config():
    return {
        "rules": {
            "username": {"required": True, "min_length": 3, "max_length": 50},
            "full_name": {"required": True, "min_length": 2, "max_length": 100},
            "email": {"required": True},
            "password": {
                "required": True,
                "min_length": 12,
                "uppercase": True,
                "lowercase": True,
                "number": True,
                "special_character": True,
            },
            "confirm_password": {"required": True},
            "phone": {"required": False, "min_length": 10, "max_length": 15, "numeric_only": True},
            "number": {"required": False, "min": 18, "max": 99, "allow_decimal": False, "allow_negative": False},
        }
    }


def test_password_rule_generation(base_config):
    field = FieldDefinition(
        name="password",
        label="Password",
        html_type="password",
        semantic_type=SemanticType.PASSWORD,
        required=True,
        required_reason=RequiredReason.HTML_REQUIRED,
        selector="#password",
    )
    rule = PasswordRule()
    context = {}
    cases = rule.generate_test_cases(field, base_config, context)

    rule_names = [c.rule_name for c in cases]
    assert "required_empty_check" in rule_names
    assert "min_length_minus_1" in rule_names
    assert "min_length_boundary" in rule_names
    assert "missing_uppercase" in rule_names
    assert "missing_lowercase" in rule_names
    assert "missing_number" in rule_names
    assert "missing_special_character" in rule_names
    assert "valid_password" in rule_names

    # Check context propagation
    assert "valid_password" in context
    assert len(context["valid_password"]) >= 12


def test_confirm_password_rule_generation(base_config):
    field = FieldDefinition(
        name="confirm_password",
        label="Confirm Password",
        html_type="password",
        semantic_type=SemanticType.CONFIRM_PASSWORD,
        required=True,
        required_reason=RequiredReason.HTML_REQUIRED,
        selector="#confirm_password",
    )
    context = {"valid_password": "MySecretPass!99"}
    rule = ConfirmPasswordRule()
    cases = rule.generate_test_cases(field, base_config, context)

    rule_names = [c.rule_name for c in cases]
    assert "required_empty_check" in rule_names
    assert "mismatched_password" in rule_names
    assert "matching_password" in rule_names

    matching_tc = next(c for c in cases if c.rule_name == "matching_password")
    assert matching_tc.input_value == "MySecretPass!99"
    assert matching_tc.expected_behavior == ExpectedBehavior.ACCEPTED

    mismatched_tc = next(c for c in cases if c.rule_name == "mismatched_password")
    assert mismatched_tc.input_value != "MySecretPass!99"
    assert mismatched_tc.expected_behavior == ExpectedBehavior.VALIDATION_TRIGGERED


def test_username_rule_generation(base_config):
    field = FieldDefinition(
        name="username",
        label="Username",
        html_type="text",
        semantic_type=SemanticType.USERNAME,
        required=True,
        required_reason=RequiredReason.HTML_REQUIRED,
        selector="#username",
    )
    rule = UsernameRule()
    cases = rule.generate_test_cases(field, base_config, {})
    rule_names = [c.rule_name for c in cases]
    assert "min_length_minus_1" in rule_names
    assert "spaces_in_username" in rule_names
    assert "special_characters" in rule_names
    assert "valid_username" in rule_names


def test_fullname_observation_rule(base_config):
    field = FieldDefinition(
        name="full_name",
        label="Full Name",
        html_type="text",
        semantic_type=SemanticType.FULL_NAME,
        required=True,
        required_reason=RequiredReason.HTML_REQUIRED,
        selector="#fullname",
    )
    rule = FullNameRule()
    cases = rule.generate_test_cases(field, base_config, {})

    # Since allow_numbers and allow_special_chars are unspecified in base_config,
    # they should be marked as OBSERVE
    num_case = next(c for c in cases if c.rule_name == "numbers_in_name")
    assert num_case.expected_behavior == ExpectedBehavior.OBSERVE

    spec_case = next(c for c in cases if c.rule_name == "special_characters_in_name")
    assert spec_case.expected_behavior == ExpectedBehavior.OBSERVE


def test_email_rule_generation(base_config):
    field = FieldDefinition(
        name="email",
        label="Email",
        html_type="email",
        semantic_type=SemanticType.EMAIL,
        required=True,
        required_reason=RequiredReason.HTML_REQUIRED,
        selector="#email",
    )
    rule = EmailRule()
    cases = rule.generate_test_cases(field, base_config, {})
    rule_names = [c.rule_name for c in cases]
    assert "missing_at_symbol" in rule_names
    assert "missing_domain" in rule_names
    assert "spaces_in_email" in rule_names
    assert "valid_email" in rule_names


def test_cnic_rule_generation(base_config):
    from rules.cnic_rules import CNICRule
    field = FieldDefinition(
        name="cnic",
        label="CNIC Number",
        html_type="text",
        semantic_type=SemanticType.CNIC,
        required=True,
        required_reason=RequiredReason.HTML_REQUIRED,
        selector="#cnic",
    )
    rule = CNICRule()
    cases = rule.generate_test_cases(field, base_config, {})
    rule_names = [c.rule_name for c in cases]
    assert "required_empty_check" in rule_names
    assert "alphabetic_cnic" in rule_names
    assert "too_short_cnic" in rule_names
    assert "valid_cnic_dashed" in rule_names


def test_registry_ordering():
    registry = RuleRegistry()
    fields = [
        FieldDefinition(name="confirm_password", label="Confirm Password", html_type="password", semantic_type=SemanticType.CONFIRM_PASSWORD, required=True, selector="#cp"),
        FieldDefinition(name="password", label="Password", html_type="password", semantic_type=SemanticType.PASSWORD, required=True, selector="#p"),
        FieldDefinition(name="email", label="Email", html_type="email", semantic_type=SemanticType.EMAIL, required=True, selector="#e"),
    ]
    cases = registry.generate_all(fields, {"rules": {}})
    # Password cases must precede Confirm Password cases in generated list
    pwd_indices = [i for i, c in enumerate(cases) if c.semantic_type == SemanticType.PASSWORD]
    cp_indices = [i for i, c in enumerate(cases) if c.semantic_type == SemanticType.CONFIRM_PASSWORD]
    assert min(pwd_indices) < min(cp_indices)
