"""Validator for capturing validation and error messages associated with fields or forms."""
from __future__ import annotations

import re
from typing import Optional, Tuple, TYPE_CHECKING
from playwright.sync_api import Locator, Page

if TYPE_CHECKING:
    from form_engine.models import FieldDefinition


class ValidationMessageValidator:
    """Finds and extracts validation messages using multiple heuristic strategies."""

    @staticmethod
    def _is_alert_relevant_to_field(alert_text: str, target_field: Optional[FieldDefinition]) -> bool:
        """Determines whether a page or form alert applies to the target field."""
        if not target_field or not alert_text:
            return True
        alert_lower = alert_text.lower()

        # Keywords that indicate the message is about the target field
        field_tokens = set()
        if target_field.name:
            field_tokens.update([tok for tok in re.split(r"[_\-\s]+", target_field.name.lower()) if len(tok) >= 3])
        if target_field.label:
            field_tokens.update([tok for tok in re.split(r"[_\-\s]+", target_field.label.lower()) if len(tok) >= 3])
        if target_field.friendly_name:
            field_tokens.update([tok for tok in re.split(r"[_\-\s]+", target_field.friendly_name.lower()) if len(tok) >= 3])
        field_tokens.add(target_field.semantic_type.value.lower())

        if any(tok in alert_lower for tok in field_tokens):
            return True

        # Check if the alert exclusively complains about other known field types
        other_field_types = {"cnic", "email", "phone", "mobile", "password", "username", "captcha"}
        other_field_types = {t for t in other_field_types if t not in field_tokens}

        if any(other in alert_lower for other in other_field_types):
            return False

        # Generic messages (e.g. 'Please fill out required fields') are accepted as relevant
        return True

    @staticmethod
    def find_validation_message(
        page: Page,
        locator: Locator,
        form_locator: Optional[Locator] = None,
        target_field: Optional[FieldDefinition] = None,
    ) -> Tuple[bool, str, str]:
        """Detects error messages near the field, in ARIA references, HTML5 messages, or form-level alerts.
        Returns (found, message_text, detection_source).
        """
        try:
            # 1. Native HTML5 validationMessage
            html5_msg = locator.evaluate("el => el.validationMessage || ''")
            if html5_msg and html5_msg.strip():
                return True, html5_msg.strip(), "HTML5 native validation message"

            # 2. aria-errormessage or aria-describedby
            for attr in ("aria-errormessage", "aria-describedby"):
                ref_id = locator.get_attribute(attr)
                if ref_id:
                    for id_token in ref_id.split():
                        ref_elem = page.locator(f"#{id_token}")
                        if ref_elem.count() > 0 and ref_elem.is_visible():
                            text = (ref_elem.evaluate("el => el.innerText || ''") or "").strip()
                            if text:
                                return True, text, f"{attr} referenced element"

            # 3. Direct sibling or parent container error containers
            # Query standard error element classes adjacent to this field
            sibling_text = locator.evaluate("""el => {
                const parent = el.parentElement;
                if (!parent) return '';
                const selectors = [
                    '.invalid-feedback', '.error-message', '.error-text',
                    '.help-block', '.text-danger', '.field-error',
                    '[role="alert"]', '.alert', '.errormsg', '.form-text-error'
                ];
                for (const sel of selectors) {
                    const found = parent.querySelector(sel);
                    if (found && found.offsetParent !== null && found.innerText.trim()) {
                        return found.innerText.trim();
                    }
                }
                // Check next sibling
                let next = el.nextElementSibling;
                while (next) {
                    if (next.offsetParent !== null && next.innerText.trim() &&
                        (next.className.includes('error') || next.className.includes('invalid') || next.className.includes('feedback') || next.getAttribute('role') === 'alert')) {
                        return next.innerText.trim();
                    }
                    next = next.nextElementSibling;
                }
                return '';
            }""")
            if sibling_text:
                return True, sibling_text, "Adjacent error container"

            # 4. Form-level error alerts
            if form_locator and form_locator.count() > 0:
                form_alert = form_locator.evaluate("""f => {
                    const alerts = f.querySelectorAll('.alert-danger, .error-summary, .form-errors, [role="alert"]');
                    for (const a of alerts) {
                        if (a.offsetParent !== null && a.innerText.trim()) {
                            return a.innerText.trim();
                        }
                    }
                    return '';
                }""")
                if form_alert and ValidationMessageValidator._is_alert_relevant_to_field(form_alert, target_field):
                    return True, form_alert, "Form-level error banner"

            # 5. Page-level alerts
            page_alerts = page.locator(".alert-danger, [role='alert'].alert, .toast-error")
            if page_alerts.count() > 0 and page_alerts.first.is_visible():
                text = (page_alerts.first.evaluate("el => el.innerText || ''") or "").strip()
                if text and ValidationMessageValidator._is_alert_relevant_to_field(text, target_field):
                    return True, text, "Page alert toast/banner"

        except Exception as e:
            return False, f"Message detection error: {e}", "exception"

        return False, "", "none"
