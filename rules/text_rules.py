"""Validation rules for generic TEXT field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class TextRule(BaseRule):
    """Generates standard text boundary and valid content test cases."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        t_cfg = config.get("rules", {}).get("text", {})

        min_len = int(t_cfg.get("min_length", 1))
        max_len = int(t_cfg.get("max_length", 255))

        # 1. Empty / Required check
        cases.extend(make_required_rule(field, t_cfg))

        # 2. Valid standard text
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_text",
                input_value="Standard Text Input",
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Valid standard text string.",
            )
        )

        # 3. Special characters
        if "allow_special_chars" in t_cfg:
            exp_spec = ExpectedBehavior.ACCEPTED if t_cfg["allow_special_chars"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_spec = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="special_characters_text",
                input_value='Test !@#$%^&*()\'"<>?/\\',
                expected_behavior=exp_spec,
                description="Evaluating behavior when special characters are included in text field.",
            )
        )

        # 4. Whitespace-only input
        if "allow_whitespace_only" in t_cfg:
            exp_ws = ExpectedBehavior.ACCEPTED if t_cfg["allow_whitespace_only"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_ws = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="whitespace_only_text",
                input_value="   ",
                expected_behavior=exp_ws,
                description="Evaluating behavior when text contains only whitespace.",
            )
        )

        # 5. Leading/trailing spaces
        if "allow_leading_trailing_spaces" in t_cfg:
            exp_lts = ExpectedBehavior.ACCEPTED if t_cfg["allow_leading_trailing_spaces"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_lts = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="leading_trailing_spaces_text",
                input_value="  Standard Text Input  ",
                expected_behavior=exp_lts,
                description="Evaluating behavior when text has leading/trailing spaces.",
            )
        )

        # 6. Unicode and multilingual text
        if "allow_unicode_text" in t_cfg:
            exp_uni = ExpectedBehavior.ACCEPTED if t_cfg["allow_unicode_text"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_uni = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="unicode_text",
                input_value="Test avec accents é à ü 测试 اختبار",
                expected_behavior=exp_uni,
                description="Evaluating behavior when text contains Unicode/multilingual characters.",
            )
        )

        # 7. Line breaks in text
        if "allow_line_breaks" in t_cfg:
            exp_lb = ExpectedBehavior.ACCEPTED if t_cfg["allow_line_breaks"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_lb = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="line_breaks_text",
                input_value="Line 1\nLine 2\nLine 3",
                expected_behavior=exp_lb,
                description="Evaluating behavior when text contains multiple line breaks.",
            )
        )

        # 8. HTML markup in text
        if "allow_html_markup" in t_cfg:
            exp_html = ExpectedBehavior.ACCEPTED if t_cfg["allow_html_markup"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_html = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="html_markup_text",
                input_value="<b>Test</b> <script>alert('xss')</script>",
                expected_behavior=exp_html,
                description="Evaluating behavior when HTML markup is included in text field.",
            )
        )

        # 9. Null-like strings ("null", "undefined")
        if "allow_null_strings" in t_cfg:
            exp_null = ExpectedBehavior.ACCEPTED if t_cfg["allow_null_strings"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_null = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="null_like_strings_text",
                input_value="null",
                expected_behavior=exp_null,
                description="Evaluating behavior when literal string 'null' or 'undefined' is entered as text.",
            )
        )

        return cases
