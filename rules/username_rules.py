"""Validation rules for USERNAME field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class UsernameRule(BaseRule):
    """Generates comprehensive boundary and character set test cases for username fields."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        u_cfg = config.get("rules", {}).get("username", {})

        min_len = int(u_cfg.get("min_length", 3))
        max_len = int(u_cfg.get("max_length", 50))
        allow_spaces = u_cfg.get("allow_spaces", False)
        allow_special_chars = u_cfg.get("allow_special_chars", False)

        # 1. Empty / Required
        cases.extend(make_required_rule(field, u_cfg))

        # 2. Min length - 1 (Invalid)
        if min_len > 1:
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="min_length_minus_1",
                    input_value="a" * (min_len - 1),
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description=f"Username below minimum length ({min_len - 1} chars) should trigger validation.",
                )
            )

        # 3. Minimum length boundary (Valid length)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="min_length_boundary",
                input_value="u" * min_len,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description=f"Username at exact minimum length ({min_len} chars) should be accepted.",
            )
        )

        # 4. Maximum length boundary (Valid length)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="max_length_boundary",
                input_value="u" * max_len,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description=f"Username at exact maximum length ({max_len} chars) should be accepted.",
            )
        )

        # 5. Maximum length + 1 (Invalid)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="max_length_plus_1",
                input_value="u" * (max_len + 1),
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description=f"Username exceeding maximum length ({max_len + 1} chars) should trigger validation.",
            )
        )

        # 6. Spaces test
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="spaces_in_username",
                input_value="test user",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED if not allow_spaces else ExpectedBehavior.ACCEPTED,
                description="Username containing embedded spaces.",
            )
        )

        # 7. Invalid special characters
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="special_characters",
                input_value="test@user!#",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED if not allow_special_chars else ExpectedBehavior.ACCEPTED,
                description="Username containing special characters.",
            )
        )

        # 8. Valid username
        if "valid_username" in context:
            valid_user = context["valid_username"]
        else:
            import random
            valid_user = f"user_{random.randint(10000, 99999)}"
            context["valid_username"] = valid_user

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_username",
                input_value=valid_user,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Valid standard alphanumeric username.",
            )
        )

        return cases
