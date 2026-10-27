"""Common validation rules shared across multiple field types."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase


def make_required_rule(field: FieldDefinition, config: Dict[str, Any]) -> List[TestCase]:
    """Generates an empty-value test case if the field is required by HTML, ARIA, or config."""
    is_required = field.required or config.get("required", False)
    if not is_required:
        return []

    return [
        TestCase(
            field_name=field.name,
            semantic_type=field.semantic_type,
            rule_name="required_empty_check",
            input_value="",
            expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
            description=f"Field '{field.label or field.name}' is required: submitting empty should trigger validation.",
            metadata={"field_id": field.field_id, "required_reason": field.required_reason.value},
        )
    ]
