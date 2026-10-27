"""Validation rules for CONFIRM_PASSWORD field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class ConfirmPasswordRule(BaseRule):
    """Generates test cases validating password matching and divergence."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        cp_cfg = config.get("rules", {}).get("confirm_password", {})

        # Context holds the valid password established by the password rule
        base_password = context.get("valid_password", "Test@123456789")

        # 1. Empty / Required
        cases.extend(make_required_rule(field, cp_cfg))

        # 2. Mismatched password
        mismatched_password = base_password[:-1] if len(base_password) > 1 else base_password + "X"
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="mismatched_password",
                input_value=mismatched_password,
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Confirm password does not match primary password.",
                metadata={"paired_password": base_password},
            )
        )

        # 3. Matching password
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="matching_password",
                input_value=base_password,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Confirm password matches primary password exactly.",
                metadata={"paired_password": base_password},
            )
        )

        return cases
