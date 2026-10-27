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

        return cases
