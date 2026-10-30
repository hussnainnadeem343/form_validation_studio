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

        # 9. Whitespace-only input
        exp_ws = ExpectedBehavior.VALIDATION_TRIGGERED if (field.required or not allow_spaces) else ExpectedBehavior.OBSERVE
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="whitespace_only_username",
                input_value="   ",
                expected_behavior=exp_ws,
                description="Whitespace-only input in username should be rejected.",
            )
        )

        # 10. Leading/trailing spaces
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="leading_trailing_spaces_username",
                input_value=f"  {valid_user}  ",
                expected_behavior=ExpectedBehavior.OBSERVE,
                description="Evaluating behavior when username has leading/trailing spaces (auto-trim vs rejection).",
            )
        )

        # 11. Escaping & Injection special characters (' " < > & / \)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="special_characters_escaping_username",
                input_value="user'\"<>&/\\",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED if not allow_special_chars else ExpectedBehavior.OBSERVE,
                description="Special injection characters (' \" < > & / \\) in username.",
            )
        )

        # 12. Unicode characters in username
        if "allow_unicode_text" in u_cfg:
            exp_uni = ExpectedBehavior.ACCEPTED if u_cfg["allow_unicode_text"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_uni = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="unicode_username",
                input_value="José_احمد",
                expected_behavior=exp_uni,
                description="Evaluating behavior when username contains Unicode/multilingual/Urdu characters.",
            )
        )

        # 13. HTML markup in username
        if "allow_html_markup" in u_cfg:
            exp_html = ExpectedBehavior.ACCEPTED if u_cfg["allow_html_markup"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_html = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="html_markup_username",
                input_value="<b>testuser</b>",
                expected_behavior=exp_html,
                description="Evaluating behavior when HTML markup is included in username.",
            )
        )

        # 14. Null-like literal strings ("null", "undefined")
        if "allow_null_strings" in u_cfg:
            exp_null = ExpectedBehavior.ACCEPTED if u_cfg["allow_null_strings"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_null = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="null_like_strings_username",
                input_value="null",
                expected_behavior=exp_null,
                description="Evaluating behavior when literal string 'null' is entered as username.",
            )
        )
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="undefined_like_strings_username",
                input_value="undefined",
                expected_behavior=exp_null,
                description="Evaluating behavior when literal string 'undefined' is entered as username.",
            )
        )

        return cases
