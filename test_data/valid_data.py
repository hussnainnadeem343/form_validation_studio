"""Generators for valid form field inputs satisfying typical business constraints."""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any, Dict
from faker import Faker
from form_engine.models import FieldDefinition, SemanticType

fake = Faker()


def get_valid_value(field: FieldDefinition, config: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Returns a valid value for the given field based on its semantic type and configuration."""
    rules_cfg = config.get("rules", {})

    if field.semantic_type == SemanticType.USERNAME:
        u_cfg = rules_cfg.get("username", {})
        min_len = int(u_cfg.get("min_length", 3))
        max_len = int(u_cfg.get("max_length", 50))
        user = f"user_{fake.user_name().replace('.', '').replace('-', '')[:10]}"
        if len(user) < min_len:
            user = user.ljust(min_len, "1")
        elif len(user) > max_len:
            user = user[:max_len]
        return user

    elif field.semantic_type == SemanticType.FULL_NAME:
        return fake.name()

    elif field.semantic_type == SemanticType.EMAIL:
        if "valid_email" in context:
            return context["valid_email"]
        email = f"qa_test_{random.randint(100000, 999999)}@example.com"
        context["valid_email"] = email
        return email

    elif field.semantic_type == SemanticType.PASSWORD:
        if "valid_password" in context:
            return context["valid_password"]
        # Generate valid password satisfying all common complexity rules
        p_cfg = rules_cfg.get("password", {})
        min_len = max(int(p_cfg.get("min_length", 12)), 12)
        pwd = f"Pass123!{fake.password(length=min_len - 8, special_chars=False)}"
        context["valid_password"] = pwd
        return pwd

    elif field.semantic_type == SemanticType.CONFIRM_PASSWORD:
        # Must match the password
        if "valid_password" in context:
            return context["valid_password"]
        return "Pass123!ValidPassword"

    elif field.semantic_type == SemanticType.PHONE:
        if "valid_phone" in context:
            return context["valid_phone"]
        p_cfg = rules_cfg.get("phone", {})
        min_len = int(p_cfg.get("min_length", 10))
        max_len = int(p_cfg.get("max_length", 15))
        # Support realistic 11-digit mobile starting with 03
        random_digits = "".join([str(random.randint(0, 9)) for _ in range(7)])
        phone = f"0300{random_digits}"
        if len(phone) < min_len:
            phone = phone.ljust(min_len, "0")
        elif len(phone) > max_len:
            phone = phone[:max_len]
        context["valid_phone"] = phone
        return phone

    elif field.semantic_type == SemanticType.CNIC:
        if "valid_cnic" in context:
            return context["valid_cnic"]
        mid = random.randint(1000000, 9999999)
        last = random.randint(1, 9)
        cnic = f"35202-{mid}-{last}"
        context["valid_cnic"] = cnic
        return cnic

    elif field.semantic_type == SemanticType.NUMBER:
        n_cfg = rules_cfg.get("number", {})
        min_val = int(n_cfg.get("min", 18))
        max_val = int(n_cfg.get("max", 99))
        name_lower = f"{field.name} {field.field_id} {field.label}".lower()
        if "age" in name_lower:
            # Generate realistic applicant age (e.g. 25-50) so max age limits (e.g. 70 years) are not exceeded
            return str(random.randint(25, 50))
        return str(random.randint(min_val, max_val))

    elif field.semantic_type == SemanticType.DROPDOWN:
        name_lower = f"{field.name} {field.field_id} {field.label}".lower()
        # If CNIC validity dropdown, prefer 'Expiry Date' option so date fields are active
        if "validity" in name_lower or "valid" in name_lower:
            for opt in field.options:
                val = (opt.value or "").strip()
                txt = (opt.text or "").strip()
                if "expir" in txt.lower() or "expir" in val.lower():
                    return val or txt

        # Return first genuinely valid non-placeholder option
        for opt in field.options:
            val = (opt.value or "").strip()
            txt = (opt.text or "").strip()
            if val and not any(ph in val.lower() for ph in ["select", "choose", "none", "--"]):
                return val
            if val:
                return val
        for opt in field.options:
            txt = (opt.text or "").strip()
            if txt and not any(ph in txt.lower() for ph in ["select", "choose", "none", "--"]):
                return txt
        return "1"

    elif field.semantic_type == SemanticType.FILE_UPLOAD:
        return ""

    elif field.semantic_type == SemanticType.TEXT:
        return "Valid Text Value"

    elif field.semantic_type == SemanticType.DATE:
        context_type = field.attributes.get("date_context", "GENERAL")
        fmt = field.attributes.get("date_format", "YYYY-MM-DD")
        today = date.today()

        if context_type == "EXPIRY":
            # Future date: e.g. +5 years
            try:
                target_date = today.replace(year=today.year + 5)
            except ValueError:
                # Handle leap year Feb 29
                target_date = today + timedelta(days=365 * 5)
        elif context_type == "BIRTH":
            # Past date: 25 years ago
            try:
                target_date = today.replace(year=today.year - 25)
            except ValueError:
                target_date = today - timedelta(days=365 * 25)
        elif context_type == "ISSUE":
            # Past date: 2 years ago
            try:
                target_date = today.replace(year=today.year - 2)
            except ValueError:
                target_date = today - timedelta(days=365 * 2)
        else:
            # General date: tomorrow
            target_date = today + timedelta(days=1)

        if fmt == "DD/MM/YYYY":
            return target_date.strftime("%d/%m/%Y")
        elif fmt == "DD-MM-YYYY":
            return target_date.strftime("%d-%m-%Y")
        elif fmt == "MM/DD/YYYY":
            return target_date.strftime("%m/%d/%Y")
        else:
            return target_date.strftime("%Y-%m-%d")

    return "Sample Value"
