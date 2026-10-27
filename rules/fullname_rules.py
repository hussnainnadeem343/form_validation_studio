"""Validation rules for FULL_NAME field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class FullNameRule(BaseRule):
    """Generates validation rules for full name fields, utilizing OBSERVATION for ambiguous constraints."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        fn_cfg = config.get("rules", {}).get("full_name", {})

        min_len = int(fn_cfg.get("min_length", 2))
        max_len = int(fn_cfg.get("max_length", 100))

        # 1. Empty / Required
        cases.extend(make_required_rule(field, fn_cfg))

        # 2. Min length - 1 (if > 1)
        if min_len > 1:
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="min_length_minus_1",
                    input_value="a" * (min_len - 1),
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description=f"Full name below minimum length ({min_len - 1} chars) should trigger validation.",
                )
            )

        # 3. Minimum length boundary
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="min_length_boundary",
                input_value="Jo",
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description=f"Full name meeting minimum length boundary ({min_len} chars).",
            )
        )

        # 4. Maximum length + 1
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="max_length_plus_1",
                input_value="A" * (max_len + 1),
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description=f"Full name exceeding max length ({max_len + 1} chars).",
            )
        )

        # 5. Numbers in full name
        # If not explicitly configured, mark as OBSERVE rather than FAIL
        if "allow_numbers" in fn_cfg:
            exp_num = ExpectedBehavior.ACCEPTED if fn_cfg["allow_numbers"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_num = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="numbers_in_name",
                input_value="John Doe 123",
                expected_behavior=exp_num,
                description="Evaluating behavior when numbers are included in full name.",
            )
        )

        # 6. Special characters in full name
        # If not explicitly configured, mark as OBSERVE rather than FAIL
        if "allow_special_chars" in fn_cfg:
            exp_spec = ExpectedBehavior.ACCEPTED if fn_cfg["allow_special_chars"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_spec = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="special_characters_in_name",
                input_value="John <Doe> #1!",
                expected_behavior=exp_spec,
                description="Evaluating behavior when special characters are included in full name.",
            )
        )

        # 7. Valid standard full name
        valid_name = "Jane Doe"
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_full_name",
                input_value=valid_name,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Standard valid full name.",
            )
        )
        context["valid_full_name"] = valid_name

        return cases
