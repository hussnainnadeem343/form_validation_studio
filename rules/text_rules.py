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

        return cases
