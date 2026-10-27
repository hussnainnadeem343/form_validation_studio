"""Validator for inspecting the invalid state of individual form input fields."""
from __future__ import annotations

from typing import Tuple
from playwright.sync_api import Page, Locator


class FieldStateValidator:
    """Inspects HTML5 validity, ARIA attributes, and CSS styling to determine if an input is invalid."""

    @staticmethod
    def is_field_invalid(locator: Locator) -> Tuple[bool, str]:
        """Returns (is_invalid, reason) for the target element."""
        try:
            # 1. Native HTML5 validity check
            is_valid_html5 = locator.evaluate("el => el.checkValidity ? el.checkValidity() : true")
            if not is_valid_html5:
                validation_msg = locator.evaluate("el => el.validationMessage || ''")
                return True, f"HTML5 validation failed: {validation_msg}"

            # 2. aria-invalid attribute
            aria_invalid = locator.get_attribute("aria-invalid")
            if aria_invalid and aria_invalid.lower() in ("true", "grammar", "spelling"):
                return True, f"aria-invalid='{aria_invalid}'"

            # 3. CSS error classes on the element
            class_attr = locator.get_attribute("class") or ""
            class_names = class_attr.lower().split()
            error_class_indicators = [
                "is-invalid", "invalid", "error", "has-error",
                "field-error", "input-error", "ng-invalid", "border-danger",
            ]
            for ind in error_class_indicators:
                if any(ind in c for c in class_names):
                    return True, f"CSS error class detected: '{class_attr}'"

            # 4. Parent container classes (e.g. div.form-group.has-error)
            parent_classes = locator.evaluate("""el => {
                let p = el.parentElement;
                let classes = [];
                while (p && p.tagName !== 'FORM' && classes.length < 3) {
                    if (p.className) classes.push(p.className);
                    p = p.parentElement;
                }
                return classes.join(' ');
            }""")
            for ind in ["has-error", "is-invalid", "field-with-errors"]:
                if ind in parent_classes.lower():
                    return True, f"Parent error class detected: '{parent_classes}'"

        except Exception as e:
            # If element disappeared or inspection failed
            return False, f"Inspection error: {e}"

        return False, ""
