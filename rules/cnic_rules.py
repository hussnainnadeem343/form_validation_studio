"""Validation rules for CNIC (Computerized National Identity Card) field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class CNICRule(BaseRule):
    """Generates validation rules for 13-digit Pakistani CNIC fields (with or without dashes)."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        c_cfg = config.get("rules", {}).get("cnic", {})

        # 1. Empty / Required check
        cases.extend(make_required_rule(field, c_cfg))

        # 2. Alphabetic text in CNIC
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="alphabetic_cnic",
                input_value="35202abcdefg1",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Alphabetic characters in CNIC should trigger validation.",
            )
        )

        # 3. Too short CNIC (less than 13 digits)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="too_short_cnic",
                input_value="35202123456",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="CNIC with fewer than 13 digits should trigger validation.",
            )
        )

        # 4. Valid formatted CNIC (with dashes)
        if "valid_cnic" in context:
            valid_cnic_dashed = context["valid_cnic"]
        else:
            import random
            mid = random.randint(1000000, 9999999)
            last = random.randint(1, 9)
            valid_cnic_dashed = f"35202-{mid}-{last}"
            context["valid_cnic"] = valid_cnic_dashed

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_cnic_dashed",
                input_value=valid_cnic_dashed,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Standard valid 13-digit CNIC with dashes (XXXXX-XXXXXXX-X).",
            )
        )

        # 5. Valid plain numeric CNIC (13 digits)
        valid_cnic_plain = valid_cnic_dashed.replace("-", "")
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_cnic_plain",
                input_value=valid_cnic_plain,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Standard valid 13-digit CNIC without dashes.",
            )
        )

        # 6. Special characters in CNIC (' " < > & / \)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="special_characters_cnic",
                input_value="'\"<>&/\\",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Special characters (' \" < > & / \\) in CNIC should trigger validation.",
            )
        )

        # 7. Whitespace-only in CNIC
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="whitespace_only_cnic",
                input_value="   ",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Whitespace-only input in CNIC should trigger validation.",
            )
        )

        # 8. Leading and trailing spaces around valid CNIC
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="leading_trailing_spaces_cnic",
                input_value=f"  {valid_cnic_dashed}  ",
                expected_behavior=ExpectedBehavior.OBSERVE,
                description="Evaluating behavior when valid CNIC has leading/trailing spaces (auto-trim vs rejection).",
            )
        )

        # 9. Unicode / Multilingual / Urdu text in CNIC
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="unicode_cnic",
                input_value="۳۵۲۰۲-۱۲۳۴۵۶۷-۱",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Non-standard/Eastern Arabic numerals or Urdu text in CNIC should trigger validation.",
            )
        )

        # 10. HTML markup in CNIC
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="html_markup_cnic",
                input_value="<b>3520212345671</b>",
                expected_behavior=ExpectedBehavior.OBSERVE,
                description="Evaluating behavior when HTML markup is entered into CNIC field.",
            )
        )

        # 11. Null-like literal strings ("null", "undefined")
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="null_like_strings_cnic",
                input_value="null",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Literal string 'null' in CNIC field should trigger validation.",
            )
        )
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="undefined_like_strings_cnic",
                input_value="undefined",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Literal string 'undefined' in CNIC field should trigger validation.",
            )
        )

        return cases
