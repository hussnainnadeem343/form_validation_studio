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

        # 8. Unicode characters in email
        if "allow_unicode_text" in e_cfg:
            exp_uni = ExpectedBehavior.ACCEPTED if e_cfg["allow_unicode_text"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_uni = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="unicode_email",
                input_value="josé@ejemplo.com",
                expected_behavior=exp_uni,
                description="Evaluating behavior when email contains Unicode/multilingual characters.",
            )
        )

        # 9. HTML markup in email
        if "allow_html_markup" in e_cfg:
            exp_html = ExpectedBehavior.ACCEPTED if e_cfg["allow_html_markup"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_html = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="html_markup_email",
                input_value="<b>user@example.com</b>",
                expected_behavior=exp_html,
                description="Evaluating behavior when HTML markup is included in email address.",
            )
        )

        # 10. Null-like strings ("null", "undefined")
        if "allow_null_strings" in e_cfg:
            exp_null = ExpectedBehavior.ACCEPTED if e_cfg["allow_null_strings"] else ExpectedBehavior.VALIDATION_TRIGGERED
        else:
            exp_null = ExpectedBehavior.OBSERVE

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="null_like_strings_email",
                input_value="null",
                expected_behavior=exp_null,
                description="Evaluating behavior when literal string 'null' or 'undefined' is entered as email.",
            )
        )

        return cases
