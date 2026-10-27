"""Main orchestrator for generating synthetic test datasets for form execution."""
from __future__ import annotations

from typing import Any, Dict, List
from form_engine.models import FieldDefinition
from test_data.valid_data import get_valid_value
from test_data.invalid_data import get_invalid_emails, get_invalid_phones, get_invalid_numbers


class DataGenerator:
    """Provides valid baseline datasets and targeted test input data."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def generate_baseline_dataset(
        self,
        fields: List[FieldDefinition],
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Generates a complete dictionary of valid values for all fields in the form.
        Password and confirm_password are kept matching.
        """
        ctx = context or {}
        baseline: Dict[str, Any] = {}

        # First pass: generate everything except confirm_password
        for field in fields:
            val = get_valid_value(field, self.config, ctx)
            baseline[field.name] = val
            if field.semantic_type.value == "PASSWORD":
                ctx["valid_password"] = val

        # Second pass: ensure confirmation fields match their primary field exactly
        for field in fields:
            if field.semantic_type.value == "CONFIRM_PASSWORD":
                baseline[field.name] = ctx.get("valid_password", baseline.get(field.name, "Pass123!Valid"))
            
            # Paired confirmation fields (e.g. email_confirmation, mobile_no_confirmation)
            paired_key = field.attributes.get("paired_field")
            if paired_key:
                # Find matching primary field in baseline
                for k, v in baseline.items():
                    if k.lower() == paired_key.lower():
                        baseline[field.name] = v
                        break

        return baseline
