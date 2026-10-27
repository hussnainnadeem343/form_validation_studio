"""Validation rules for NUMBER field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class NumberRule(BaseRule):
    """Generates numeric range and character validation test cases."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        n_cfg = config.get("rules", {}).get("number", {})

        min_val = float(n_cfg.get("min", 0))
        max_val = float(n_cfg.get("max", 999999))
        allow_decimal = n_cfg.get("allow_decimal", False)
        allow_negative = n_cfg.get("allow_negative", False)

        # 1. Empty / Required check
        cases.extend(make_required_rule(field, n_cfg))

        # 2. Alphabetic text
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="alphabetic_value_in_number",
                input_value="abc",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Alphabetic text in numeric field should trigger validation.",
            )
        )

        # 3. Decimal if disallowed
        if not allow_decimal:
            decimal_val = f"{int(min_val) + 1}.5"
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="disallowed_decimal",
                    input_value=decimal_val,
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Decimal value when integers only are configured.",
                )
            )

        # 4. Negative number if disallowed
        if not allow_negative:
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="disallowed_negative_number",
                    input_value="-5",
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Negative number when negatives are disallowed.",
                )
            )

        # 5. Below minimum boundary
        below_min = min_val - 1
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="below_min_boundary",
                input_value=str(int(below_min) if below_min.is_integer() else below_min),
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description=f"Value below minimum bound ({below_min} < {min_val}) should trigger validation.",
            )
        )

        # 6. Above maximum boundary
        above_max = max_val + 1
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="above_max_boundary",
                input_value=str(int(above_max) if above_max.is_integer() else above_max),
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description=f"Value above maximum bound ({above_max} > {max_val}) should trigger validation.",
            )
        )

        # 7. Valid value within bounds
        mid_val = int((min_val + max_val) / 2)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_number_within_bounds",
                input_value=str(mid_val),
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description=f"Valid integer ({mid_val}) within allowed range [{min_val}, {max_val}].",
            )
        )
        context["valid_number"] = str(mid_val)

        return cases
