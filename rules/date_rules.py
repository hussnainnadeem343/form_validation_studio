"""Validation rules for Date Picker and Calendar fields."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


class DateRule(BaseRule):
    """Generates validation rules for date pickers, native HTML5 dates, and calendar widgets."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        d_cfg = config.get("rules", {}).get("date", {})

        context_type = field.attributes.get("date_context", "GENERAL")
        fmt = field.attributes.get("date_format", "YYYY-MM-DD")
        today = date.today()

        # Helper to format dates according to detected field format
        def format_dt(dt: date) -> str:
            if fmt == "DD/MM/YYYY":
                return dt.strftime("%d/%m/%Y")
            elif fmt == "DD-MM-YYYY":
                return dt.strftime("%d-%m-%Y")
            elif fmt == "MM/DD/YYYY":
                return dt.strftime("%m/%d/%Y")
            return dt.strftime("%Y-%m-%d")

        # 1. Required / Empty check
        cases.extend(make_required_rule(field, d_cfg))

        # 2. Malformed / Invalid date format
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="invalid_date_format",
                input_value="invalid-date",
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Invalid alphanumeric string in date field should trigger validation.",
            )
        )

        # 3. Impossible calendar day (e.g. February 31)
        impossible_str = "31/02/2026" if fmt.startswith("DD") else ("02/31/2026" if fmt.startswith("MM") else "2026-02-31")
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="impossible_calendar_date",
                input_value=impossible_str,
                expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                description="Impossible calendar date (February 31) should trigger validation.",
            )
        )

        # 4. Contextual Date Rules
        if context_type == "EXPIRY":
            # For Expiry dates (e.g. CNIC expiry, license expiry): Past date is expired and invalid
            expired_date = today - timedelta(days=365 * 3)
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="expired_past_date",
                    input_value=format_dt(expired_date),
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Expired past date for CNIC/document expiration should trigger validation.",
                )
            )
        elif context_type in ("BIRTH", "ISSUE"):
            # For Birth / Issue dates: Future date is logically impossible
            future_date = today + timedelta(days=365 * 5)
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="future_date_not_allowed",
                    input_value=format_dt(future_date),
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Future date for Date of Birth / Issuance should trigger validation.",
                )
            )

        # 5. Min / Max range boundary violations (if present in HTML attributes)
        min_attr = field.attributes.get("min")
        max_attr = field.attributes.get("max")

        if min_attr:
            try:
                min_d = date.fromisoformat(min_attr)
                before_min = min_d - timedelta(days=1)
                cases.append(
                    TestCase(
                        field_name=field.name,
                        semantic_type=field.semantic_type,
                        rule_name="date_before_min",
                        input_value=format_dt(before_min),
                        expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                        description=f"Date before minimum allowed bound ({min_attr}) should trigger validation.",
                    )
                )
            except Exception:
                pass

        if max_attr:
            try:
                max_d = date.fromisoformat(max_attr)
                after_max = max_d + timedelta(days=1)
                cases.append(
                    TestCase(
                        field_name=field.name,
                        semantic_type=field.semantic_type,
                        rule_name="date_after_max",
                        input_value=format_dt(after_max),
                        expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                        description=f"Date after maximum allowed bound ({max_attr}) should trigger validation.",
                    )
                )
            except Exception:
                pass

        # 6. Valid date acceptance
        if context_type == "EXPIRY":
            try:
                valid_dt = today.replace(year=today.year + 5)
            except ValueError:
                valid_dt = today + timedelta(days=365 * 5)
        elif context_type == "BIRTH":
            try:
                valid_dt = today.replace(year=today.year - 25)
            except ValueError:
                valid_dt = today - timedelta(days=365 * 25)
        elif context_type == "ISSUE":
            try:
                valid_dt = today.replace(year=today.year - 2)
            except ValueError:
                valid_dt = today - timedelta(days=365 * 2)
        else:
            valid_dt = today + timedelta(days=1)

        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_date",
                input_value=format_dt(valid_dt),
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description=f"Valid formatted date for {context_type.lower()} should be accepted cleanly.",
            )
        )

        return cases
