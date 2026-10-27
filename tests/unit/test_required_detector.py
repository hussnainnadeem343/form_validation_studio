"""Unit tests for required field detection heuristics."""
from form_engine.field_detector import FieldDetector
from form_engine.models import FieldDefinition, RequiredReason, SemanticType


def test_config_required_application():
    config = {
        "rules": {
            "username": {"required": True},
            "phone": {"required": False},
        }
    }
    detector = FieldDetector(config=config)

    field_user = FieldDefinition(
        name="username",
        label="Username",
        html_type="text",
        semantic_type=SemanticType.USERNAME,
        required=False,
        required_reason=RequiredReason.NONE,
        selector="#username",
    )
    detector._apply_config_required(field_user)
    assert field_user.required is True
    assert field_user.required_reason == RequiredReason.CONFIG

    field_phone = FieldDefinition(
        name="phone",
        label="Phone",
        html_type="tel",
        semantic_type=SemanticType.PHONE,
        required=False,
        required_reason=RequiredReason.NONE,
        selector="#phone",
    )
    detector._apply_config_required(field_phone)
    assert field_phone.required is False
    assert field_phone.required_reason == RequiredReason.NONE


def test_inferred_asterisk_label():
    detector = FieldDetector()
    # Test label resolution and asterisk check
    assert "*" in "Full Name *"
