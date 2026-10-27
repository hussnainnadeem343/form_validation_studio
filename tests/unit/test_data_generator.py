"""Unit tests for synthetic test data synthesis."""
from form_engine.models import FieldDefinition, RequiredReason, SemanticType
from test_data.data_generator import DataGenerator
from test_data.invalid_data import get_invalid_emails, get_invalid_phones, get_invalid_numbers


def test_baseline_dataset_generation():
    config = {
        "rules": {
            "username": {"min_length": 3, "max_length": 50},
            "password": {"min_length": 12},
            "phone": {"min_length": 10, "max_length": 15},
            "number": {"min": 18, "max": 99},
        }
    }
    generator = DataGenerator(config)

    fields = [
        FieldDefinition(name="username", label="Username", html_type="text", semantic_type=SemanticType.USERNAME, required=True, selector="#username"),
        FieldDefinition(name="email", label="Email", html_type="email", semantic_type=SemanticType.EMAIL, required=True, selector="#email"),
        FieldDefinition(name="password", label="Password", html_type="password", semantic_type=SemanticType.PASSWORD, required=True, selector="#password"),
        FieldDefinition(name="confirm_password", label="Confirm Password", html_type="password", semantic_type=SemanticType.CONFIRM_PASSWORD, required=True, selector="#confirm_password"),
    ]

    baseline = generator.generate_baseline_dataset(fields)
    assert "username" in baseline
    assert "email" in baseline
    assert "@" in baseline["email"]
    assert "password" in baseline
    assert "confirm_password" in baseline
    # confirm_password must equal password
    assert baseline["password"] == baseline["confirm_password"]


def test_invalid_collections():
    assert len(get_invalid_emails()) > 5
    assert len(get_invalid_phones()) > 3
    assert len(get_invalid_numbers()) > 3
