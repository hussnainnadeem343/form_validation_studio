"""Validation rules for EMAIL field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class EmailRule(BaseRule):
    """Generates email format and structural validation test cases."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        e_cfg = config.get("rules", {}).get("email", {})

        # 1. Empty / Required
        cases.extend(make_required_rule(field, e_cfg))

        # 2. Invalid format without @ or domain
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="invalid_format_plain_text",
                input_value="plainaddress",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Email without @ or domain should trigger validation.",
            )
        )

        # 3. Missing @ symbol
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="missing_at_symbol",
                input_value="user.example.com",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Email missing @ symbol should trigger validation.",
            )
        )

        # 4. Missing domain part
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="missing_domain",
                input_value="user@",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Email missing domain part should trigger validation.",
            )
        )

        # 5. Missing username / local part
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="missing_username",
                input_value="@example.com",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Email missing username/local part should trigger validation.",
            )
        )

        # 6. Spaces within address
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="spaces_in_email",
                input_value="user name@example.com",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Email containing whitespace should trigger validation.",
            )
        )

        # 7. Valid email address
        if "valid_email" in context:
            valid_email = context["valid_email"]
        else:
            import random
            valid_email = f"qa_test_{random.randint(100000, 999999)}@example.com"
            context["valid_email"] = valid_email

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_email",
                input_value=valid_email,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Standard RFC-compliant valid email address.",
            )
        )

        return cases
