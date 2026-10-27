"""Validation rules for DROPDOWN / SELECT field type."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class DropdownRule(BaseRule):
    """Generates dropdown option selection test cases."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        d_cfg = config.get("rules", {}).get("dropdown", {})

        # Filter out empty placeholder options
        valid_options = [opt for opt in field.options if opt.value.strip() != ""]

        # 1. Required / Empty check if field is required
        cases.extend(make_required_rule(field, d_cfg))

        if not valid_options:
            # Fallback if options could not be detected statically
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="select_first_option",
                    input_value="1",
                    expected_behavior=ExpectedBehavior.ACCEPTED,
                    description="Select index 1 from dropdown options.",
                )
            )
            return cases

        # 2. First valid option
        first_opt = valid_options[0]
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="select_first_valid_option",
                input_value=first_opt.value,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description=f"Select first valid option '{first_opt.text}' (value={first_opt.value}).",
                metadata={"option_text": first_opt.text},
            )
        )
        context[f"valid_dropdown_{field.name}"] = first_opt.value

        # 3. Last valid option (if distinct from first)
        if len(valid_options) > 1:
            last_opt = valid_options[-1]
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="select_last_valid_option",
                    input_value=last_opt.value,
                    expected_behavior=ExpectedBehavior.ACCEPTED,
                    description=f"Select last valid option '{last_opt.text}' (value={last_opt.value}).",
                    metadata={"option_text": last_opt.text},
                )
            )

        # 4. Another valid option (middle option) if length >= 3
        if len(valid_options) >= 3:
            mid_opt = valid_options[len(valid_options) // 2]
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="select_middle_valid_option",
                    input_value=mid_opt.value,
                    expected_behavior=ExpectedBehavior.ACCEPTED,
                    description=f"Select middle valid option '{mid_opt.text}' (value={mid_opt.value}).",
                    metadata={"option_text": mid_opt.text},
                )
            )

        return cases
