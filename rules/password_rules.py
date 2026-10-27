"""Validation rules for PASSWORD field type."""
from __future__ import annotations

import random
import string
from typing import Any, Dict, List
from form_engine.models import ExpectedBehavior, FieldDefinition, TestCase
from rules.base_rule import BaseRule
from rules.common_rules import make_required_rule


def generate_compliant_password(min_length: int = 12) -> str:
    """Generates a password satisfying uppercase, lowercase, digits, and special characters."""
    length = max(min_length, 12)
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice("@$!%*?&#")
    remaining_len = length - 4
    all_chars = string.ascii_letters + string.digits + "@$!%*?&#"
    remaining = "".join(random.choice(all_chars) for _ in range(remaining_len))
    pwd_list = list(upper + lower + digit + special + remaining)
    random.shuffle(pwd_list)
    return "".join(pwd_list)


class PasswordRule(BaseRule):
    """Generates password complexity and boundary test cases."""

    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        cases: List[TestCase] = []
        p_cfg = config.get("rules", {}).get("password", {})

        min_len = int(p_cfg.get("min_length", 12))
        req_upper = p_cfg.get("uppercase", True)
        req_lower = p_cfg.get("lowercase", True)
        req_num = p_cfg.get("number", True)
        req_special = p_cfg.get("special_character", True)

        # 1. Empty / Required
        cases.extend(make_required_rule(field, p_cfg))

        # 2. Min length - 1 (Invalid)
        if min_len > 1:
            short_pwd = "Aa1!" + "a" * (min_len - 5) if min_len >= 5 else "Aa1"[: min_len - 1]
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="min_length_minus_1",
                    input_value=short_pwd,
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description=f"Password shorter than minimum ({len(short_pwd)} < {min_len}) should trigger validation.",
                )
            )

        # 3. Minimum length boundary
        boundary_pwd = generate_compliant_password(min_len)
        if len(boundary_pwd) > min_len:
            boundary_pwd = boundary_pwd[:min_len]
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="min_length_boundary",
                input_value=boundary_pwd,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description=f"Password meeting exact minimum length ({min_len} chars) should be accepted.",
            )
        )

        # 4. Valid length (min_len + 1)
        valid_len_pwd = generate_compliant_password(min_len + 1)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_length_password",
                input_value=valid_len_pwd,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description=f"Password exceeding minimum length ({min_len + 1} chars) should be accepted.",
            )
        )

        # 5. Missing uppercase
        if req_upper:
            no_upper = "secret" + "12345678" + "@!"
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="missing_uppercase",
                    input_value=no_upper,
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Password without uppercase letter should trigger validation.",
                )
            )

        # 6. Missing lowercase
        if req_lower:
            no_lower = "SECRET" + "12345678" + "@!"
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="missing_lowercase",
                    input_value=no_lower,
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Password without lowercase letter should trigger validation.",
                )
            )

        # 7. Missing number
        if req_num:
            no_num = "SecretPass" + "Word" + "@!"
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="missing_number",
                    input_value=no_num,
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Password without numeric digits should trigger validation.",
                )
            )

        # 8. Missing special character
        if req_special:
            no_special = "SecretPass123456"
            cases.append(
                TestCase(
                    field_name=field.name,
                    semantic_type=field.semantic_type,
                    rule_name="missing_special_character",
                    input_value=no_special,
                    expected_behavior=ExpectedBehavior.VALIDATION_TRIGGERED,
                    description="Password without special character should trigger validation.",
                )
            )

        # 9. Fully valid password
        valid_password = generate_compliant_password(min_len + 2)
        cases.append(
            TestCase(
                field_name=field.name,
                semantic_type=field.semantic_type,
                rule_name="valid_password",
                input_value=valid_password,
                expected_behavior=ExpectedBehavior.ACCEPTED,
                description="Fully valid password satisfying all complexity constraints.",
            )
        )

        # Save generated valid password to context for confirm_password rules
        context["valid_password"] = valid_password
        context["password_field_name"] = field.name

        return cases
