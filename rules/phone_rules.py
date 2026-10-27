"""Validation rules for PHONE field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class PhoneRule(BaseRule):
    """Generates phone number validation test cases according to configuration."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        p_cfg = config.get("rules", {}).get("phone", {})

        min_len = int(p_cfg.get("min_length", 10))
        max_len = int(p_cfg.get("max_length", 15))
        numeric_only = p_cfg.get("numeric_only", True)

        # 1. Empty / Required check
        cases.extend(make_required_rule(field, p_cfg))

        # 2. Alphabetic characters
        if numeric_only:
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="alphabetic_phone",
                    input_value="abcdefghij",
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Alphabetic characters in phone field should trigger validation.",
                )
            )

        # 3. Special symbols
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="disallowed_special_symbols",
                input_value="1234#$@!5678",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Disallowed special symbols in phone field should trigger validation.",
            )
        )

        # 4. Too short
        if min_len > 1:
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="too_short_phone",
                    input_value="1" * (min_len - 1),
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description=f"Phone number shorter than minimum ({min_len - 1} digits) should trigger validation.",
                )
            )

        # 5. Too long
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="too_long_phone",
                input_value="9" * (max_len + 1),
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description=f"Phone number exceeding maximum ({max_len + 1} digits) should trigger validation.",
            )
        )

        # 6. Valid numeric value
        if "valid_phone" in context:
            valid_phone = context["valid_phone"]
        else:
            import random
            random_digits = "".join([str(random.randint(0, 9)) for _ in range(7)])
            valid_phone = f"0300{random_digits}"
            if len(valid_phone) < min_len:
                valid_phone = valid_phone.ljust(min_len, "0")
            elif len(valid_phone) > max_len:
                valid_phone = valid_phone[:max_len]
            context["valid_phone"] = valid_phone

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_phone",
                input_value=valid_phone,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Valid numeric phone number satisfying length constraints.",
            )
        )

        return cases
