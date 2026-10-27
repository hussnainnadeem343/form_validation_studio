"""Semantic classifier for detected web form fields."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from form_engine.models import FieldDefinition, SemanticType


class FieldClassifier:
    """Classifies generic HTML form fields into semantic types using multi-signal heuristics."""

    def __init__(self, overrides: Optional[Dict[str, Any]] = None):
        self.overrides = overrides or {}

    def classify(self, field: FieldDefinition) -> SemanticType:
        """Determines the semantic type of a field using configuration overrides or heuristics."""
        # 1. Check explicit configuration overrides first
        override_type = self._check_overrides(field)
        if override_type:
            return override_type

        # 2. Check tag type directly
        if field.html_type.lower() == "file":
            return SemanticType.FILE_UPLOAD

        if field.tag.lower() == "select" or field.html_type.lower() == "select":
            return SemanticType.DROPDOWN

        cls = (field.attributes.get("class") or "").lower()
        role = (field.attributes.get("role") or "").lower()
        if role in ("combobox", "listbox") or any(c in cls for c in ("select2", "choices", "selectpicker", "custom-select")):
            return SemanticType.DROPDOWN

        # 3. Collect normalized signal texts
        signals = self._collect_signals(field)

        # 4. Confirm Password vs Password
        if self._is_confirm_password(field, signals):
            return SemanticType.CONFIRM_PASSWORD
        if self._is_password(field, signals):
            return SemanticType.PASSWORD

        # Detect paired confirmation fields (e.g. email_confirmation, mobile_no_confirmation)
        self._detect_paired_confirmation(field)

        # 5. Date Picker / Calendar
        if self._is_date(field, signals):
            self._enrich_date_attributes(field, signals)
            return SemanticType.DATE

        # 6. Email
        if self._is_email(field, signals):
            return SemanticType.EMAIL

        # 7. Phone
        if self._is_phone(field, signals):
            return SemanticType.PHONE

        # 8. CNIC / National ID
        if self._is_cnic(field, signals):
            return SemanticType.CNIC

        # 9. Username vs Full Name
        if self._is_username(field, signals):
            return SemanticType.USERNAME
        if self._is_full_name(field, signals):
            return SemanticType.FULL_NAME

        # 10. Number
        if self._is_number(field, signals):
            return SemanticType.NUMBER

        # 11. Generic Text
        if field.html_type.lower() in ("text", "search", ""):
            return SemanticType.TEXT

        return SemanticType.UNKNOWN

    def _detect_paired_confirmation(self, field: FieldDefinition) -> None:
        """Detects if field is a confirmation copy of another field (e.g. email_confirmation)."""
        name_lower = (field.name or field.field_id).lower()
        for suffix in ("_confirmation", "-confirmation", "_confirm", "-confirm"):
            if name_lower.endswith(suffix):
                primary = name_lower[:-len(suffix)]
                field.attributes["paired_field"] = primary
                return
        for prefix in ("confirm_", "confirm-"):
            if name_lower.startswith(prefix):
                primary = name_lower[len(prefix):]
                field.attributes["paired_field"] = primary
                return

    def _is_date(self, field: FieldDefinition, signals: List[str]) -> bool:
        # 1. Native date types
        if field.html_type.lower() in ("date", "datetime-local", "month"):
            return True

        # 2. Widget classes and data attributes
        cls = (field.attributes.get("class") or "").lower()
        datepicker_classes = [
            "datepicker", "hasdatepicker", "daterangepicker", "daterange",
            "flatpickr", "pika-single", "datetimepicker", "date-picker",
            "singledatepicker", "calendar", "bs-datepicker"
        ]
        if any(c in cls for c in datepicker_classes):
            return True

        if (
            field.attributes.get("data-provide") == "datepicker"
            or bool(field.attributes.get("data-date-format"))
            or bool(field.attributes.get("data-format"))
        ):
            return True

        # 3. Name / ID / Label / Placeholder indicators
        combined = f"{field.name} {field.field_id} {field.label} {field.placeholder}".lower()

        # Urdu date indicator
        if "تاریخ" in combined:
            return True

        date_keywords = [
            "date", "dob", "birth", "birthdate", "birthday", "bday",
            "expiry", "expiration", "valid_until", "valid_till", "expire", "exp",
            "issue", "issuance", "issued", "calendar", "calender",
            "appointment", "visit", "schedule"
        ]
        words = set(re.findall(r"[a-zA-Z0-9]+", combined))
        if any(kw in words or kw in signals for kw in date_keywords):
            return True

        # Check substring specifically for compound names
        compound_indicators = ["issuan", "issue", "expir", "valid_till", "valid_until", "birth", "dob", "schedul", "appoint"]
        if any(ind in combined for ind in compound_indicators):
            return True

        # 4. Check placeholder for date format patterns
        pl = (field.placeholder or "").lower()
        if re.search(r"\b(yyyy|yyyy-mm-dd|dd/mm/yyyy|mm/dd/yyyy|dd-mm-yyyy)\b", pl):
            return True

        return False

    def _enrich_date_attributes(self, field: FieldDefinition, signals: List[str]) -> None:
        """Determines date context (EXPIRY, BIRTH, ISSUE, GENERAL) and format hints."""
        combined = f"{field.name} {field.field_id} {field.label} {field.placeholder}".lower()
        words = set(re.findall(r"[a-zA-Z0-9]+", combined))

        expiry_words = {"expiry", "expiration", "expire", "valid_till", "valid_until", "exp"}
        birth_words = {"dob", "birth", "birthdate", "birthday", "bday"}
        issue_words = {"issue", "issuance", "issued"}

        if any(w in words or w in signals for w in expiry_words) or any(w in combined for w in ("expir", "valid_until")):
            field.attributes["date_context"] = "EXPIRY"
        elif any(w in words or w in signals for w in birth_words) or any(w in combined for w in ("birth", "dob")):
            field.attributes["date_context"] = "BIRTH"
        elif any(w in words or w in signals for w in issue_words) or any(w in combined for w in ("issuan", "issue")):
            field.attributes["date_context"] = "ISSUE"
        else:
            field.attributes["date_context"] = "GENERAL"

        # Format detection
        pl = field.placeholder or ""
        if "/" in pl:
            field.attributes["date_format"] = "DD/MM/YYYY"
        elif "-" in pl and "yyyy" in pl.lower() and pl.lower().startswith("dd"):
            field.attributes["date_format"] = "DD-MM-YYYY"
        else:
            field.attributes["date_format"] = "YYYY-MM-DD"

    def _is_cnic(self, field: FieldDefinition, signals: List[str]) -> bool:
        # A date, dropdown, or file upload is NEVER a CNIC number field
        if self._is_date(field, signals):
            return False
        if field.tag.lower() == "select" or field.html_type.lower() in ("select", "file"):
            return False

        combined = f"{field.name} {field.field_id} {field.label}".lower()

        # Reject non-CNIC number fields that happen to contain 'cnic' (e.g. 'CNIC ISSUANCE DATE', 'CNIC FRONT IMAGE')
        excluded_indicators = [
            "date", "issue", "issuance", "expiry", "expire", "exp", "valid_until", "valid_till", "validity",
            "front", "back", "image", "photo", "pic", "file", "document", "upload", "copy",
            "type", "category", "status", "تاریخ", "تصویر"
        ]
        if any(ex in combined for ex in excluded_indicators):
            return False

        cnic_indicators = ["cnic", "identity_card", "citizen_number", "national_id"]
        if any(ind in combined for ind in cnic_indicators):
            return True
        return any(ind in signals for ind in cnic_indicators)

    def _check_overrides(self, field: FieldDefinition) -> Optional[SemanticType]:
        """Check if any field identifier matches an override rule."""
        for key in (field.name, field.field_id, field.label):
            if key and key in self.overrides:
                override = self.overrides[key]
                if isinstance(override, dict):
                    sem_str = override.get("semantic_type") or override.get("type")
                else:
                    sem_str = str(override)
                if sem_str:
                    return SemanticType.from_string(sem_str)
        return None

    def _collect_signals(self, field: FieldDefinition) -> List[str]:
        """Collect and normalize string tokens from attributes."""
        raw_items = [
            field.name,
            field.field_id,
            field.label,
            field.placeholder,
            field.aria_label,
            field.attributes.get("title", ""),
            field.attributes.get("data-testid", ""),
        ]
        tokens: List[str] = []
        for text in raw_items:
            if text:
                # Split camelCase, snake_case, kebab-case, and spaces
                words = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
                words = re.sub(r"[_\-\.]", " ", words).lower().split()
                tokens.extend(words)
        return tokens

    def _matches_pattern(self, signals: List[str], patterns: List[str]) -> bool:
        full_text = " ".join(signals)
        for pattern in patterns:
            if re.search(r"\b" + re.escape(pattern) + r"\b", full_text):
                return True
        return False

    def _is_confirm_password(self, field: FieldDefinition, signals: List[str]) -> bool:
        confirm_indicators = ["confirm", "confirmation", "retype", "re-type", "reenter", "repeat", "verify", "password2"]
        password_indicators = ["password", "pass", "pwd"]

        has_confirm = any(ind in signals or any(ind in s for s in signals) for ind in confirm_indicators)
        has_password = field.html_type.lower() == "password" or any(ind in signals for ind in password_indicators)

        return has_confirm and (has_password or field.html_type.lower() == "password")

    def _is_password(self, field: FieldDefinition, signals: List[str]) -> bool:
        if field.html_type.lower() == "password":
            return True
        password_indicators = ["password", "pwd", "passcode"]
        return any(ind in signals for ind in password_indicators)

    def _is_email(self, field: FieldDefinition, signals: List[str]) -> bool:
        if field.html_type.lower() == "email":
            return True
        email_indicators = ["email", "e-mail", "mail", "user_email"]
        return any(ind in signals for ind in email_indicators)

    def _is_phone(self, field: FieldDefinition, signals: List[str]) -> bool:
        if field.html_type.lower() == "tel":
            return True
        phone_indicators = ["phone", "mobile", "telephone", "tel", "cell", "cellphone", "contact_number", "contact_no"]
        return any(ind in signals for ind in phone_indicators)

    def _is_username(self, field: FieldDefinition, signals: List[str]) -> bool:
        username_indicators = ["username", "user_name", "uname", "login", "login_id", "userid", "user_id"]
        return any(ind in signals for ind in username_indicators)

    def _is_full_name(self, field: FieldDefinition, signals: List[str]) -> bool:
        full_name_indicators = [
            "full_name", "fullname", "first_name", "firstname", "last_name",
            "lastname", "surname", "display_name", "client_name", "person_name",
            "name"
        ]
        return any(ind in signals for ind in full_name_indicators)

    def _is_number(self, field: FieldDefinition, signals: List[str]) -> bool:
        if field.html_type.lower() == "number":
            return True
        number_indicators = ["age", "quantity", "qty", "count", "amount", "total", "number", "num", "score", "price"]
        return any(ind in signals for ind in number_indicators)
