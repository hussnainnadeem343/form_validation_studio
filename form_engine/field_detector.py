"""Field detector for discovering and inspecting form controls on a web page."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from playwright.sync_api import Locator, Page
from form_engine.field_classifier import FieldClassifier
from form_engine.models import FieldDefinition, FieldOption, RequiredReason, SemanticType


class FieldDetector:
    """Discovers inputs, selects, textareas, extracts metadata and resolves semantic types."""

    def __init__(self, classifier: Optional[FieldClassifier] = None, config: Optional[Dict[str, Any]] = None):
        self.classifier = classifier or FieldClassifier()
        self.config = config or {}

    def detect_fields(self, page: Page, container_selector: str = "body") -> List[FieldDefinition]:
        """Scans the page container for interactive form fields."""
        container = page.locator(container_selector).first

        # Query all candidate inputs, selects, textareas
        candidates = container.locator(
            "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset']), "
            "select, textarea"
        )

        detected_fields: List[FieldDefinition] = []
        count = candidates.count()

        for i in range(count):
            elem = candidates.nth(i)
            if not elem.is_visible():
                continue

            field_def = self._inspect_field(elem, i)
            if field_def:
                # Classify the semantic type
                field_def.semantic_type = self.classifier.classify(field_def)
                # Check if configuration specifies required
                self._apply_config_required(field_def)
                detected_fields.append(field_def)

        return detected_fields

    def _inspect_field(self, elem: Locator, index: int) -> Optional[FieldDefinition]:
        """Extracts all structural and textual attributes from an element."""
        try:
            tag = (elem.evaluate("el => el.tagName") or "input").lower()
            html_type = (elem.get_attribute("type") or ("select" if tag == "select" else "text")).lower()
            name = elem.get_attribute("name") or ""
            elem_id = elem.get_attribute("id") or ""
            placeholder = elem.get_attribute("placeholder") or ""
            aria_label = elem.get_attribute("aria-label") or ""
            current_val = elem.input_value() if tag in ("input", "textarea") else ""

            # Stable selector generation
            if elem_id:
                selector = f"#{elem_id}"
            elif name:
                selector = f"{tag}[name='{name}']"
            elif aria_label:
                selector = f"{tag}[aria-label='{aria_label}']"
            elif placeholder:
                selector = f"{tag}[placeholder='{placeholder}']"
            else:
                selector = f"{tag}:nth-of-type({index + 1})"

            # Label resolution (7-step strategy)
            label = self._resolve_label(elem, elem_id, placeholder, aria_label, name)

            # Required state detection
            required, reason = self._detect_required(elem, label)

            # Dropdown options
            options: List[FieldOption] = []
            if tag == "select":
                options_data = elem.evaluate("""sel => {
                    return Array.from(sel.options).map(o => ({
                        value: o.value,
                        text: o.text.trim(),
                        selected: o.selected
                    }));
                }""")
                options = [FieldOption(value=o["value"], text=o["text"], selected=o["selected"]) for o in options_data]

            attrs = {
                "class": elem.get_attribute("class") or "",
                "type": html_type,
            }
            for attr_name in ["min", "max", "data-provide", "data-date-format", "data-format", "readonly", "role", "title", "data-testid"]:
                val = elem.get_attribute(attr_name)
                if val:
                    attrs[attr_name] = val

            return FieldDefinition(
                name=name or elem_id or f"field_{index}",
                label=label,
                html_type=html_type,
                semantic_type=SemanticType.UNKNOWN,
                required=required,
                required_reason=reason,
                selector=selector,
                tag=tag,
                field_id=elem_id,
                placeholder=placeholder,
                aria_label=aria_label,
                value=current_val,
                options=options,
                attributes=attrs,
            )
        except Exception:
            return None

    def _resolve_label(
        self,
        elem: Locator,
        elem_id: str,
        placeholder: str,
        aria_label: str,
        name: str,
    ) -> str:
        """Determines the associated label using the 7-step priority."""
        try:
            # 1. <label for="elem_id">
            if elem_id:
                lbl = elem.page.locator(f"label[for='{elem_id}']")
                if lbl.count() > 0 and lbl.first.is_visible():
                    text = lbl.first.inner_text().strip()
                    if text:
                        return text

            # 2. Parent <label>
            parent_lbl = elem.locator("xpath=ancestor::label")
            if parent_lbl.count() > 0:
                text = parent_lbl.first.inner_text().strip()
                if text:
                    return text

            # 3. Nearby preceding sibling or parent container text
            nearby_text = elem.evaluate("""el => {
                // Check preceding sibling
                let prev = el.previousElementSibling;
                while (prev) {
                    if (prev.tagName === 'LABEL' || prev.className.includes('label')) {
                        return prev.innerText.trim();
                    }
                    prev = prev.previousElementSibling;
                }
                // Check closest form-group
                let group = el.closest('.form-group, .form-row, .field, .mb-3, div');
                if (group) {
                    let lbl = group.querySelector('label, .control-label, .field-label');
                    if (lbl) return lbl.innerText.trim();
                }
                return '';
            }""")
            if nearby_text:
                return nearby_text

            # 4. aria-label or aria-labelledby
            if aria_label:
                return aria_label

            aria_by = elem.get_attribute("aria-labelledby")
            if aria_by:
                by_elem = elem.page.locator(f"#{aria_by}")
                if by_elem.count() > 0:
                    text = by_elem.first.inner_text().strip()
                    if text:
                        return text

            # 5. placeholder
            if placeholder:
                return placeholder

            # 6. name
            if name:
                return self._clean_token(name)

            # 7. id
            if elem_id:
                return self._clean_token(elem_id)

        except Exception:
            pass

        return ""

    def _detect_required(self, elem: Locator, label: str) -> tuple[bool, RequiredReason]:
        """Detects if field is required via HTML attributes, ARIA, or visual markers."""
        try:
            # 1. HTML required attribute
            has_html_req = elem.evaluate("el => el.hasAttribute('required') || el.required === true")
            if has_html_req:
                return True, RequiredReason.HTML_REQUIRED

            # 2. aria-required="true"
            aria_req = elem.get_attribute("aria-required")
            if aria_req and aria_req.lower() == "true":
                return True, RequiredReason.ARIA_REQUIRED

            # 3. Visual indicators such as '*' in label or required class on wrapper
            if "*" in label:
                return True, RequiredReason.INFERRED

            is_inferred_class = elem.evaluate("""el => {
                const group = el.closest('.form-group, .field, div');
                if (group && (group.className.includes('required') || group.querySelector('.required, .text-danger, .star'))) {
                    return true;
                }
                return false;
            }""")
            if is_inferred_class:
                return True, RequiredReason.INFERRED

        except Exception:
            pass

        return False, RequiredReason.NONE

    def _apply_config_required(self, field: FieldDefinition) -> None:
        """Applies configured required setting if explicitly defined."""
        rules_cfg = self.config.get("rules", {})
        type_key = field.semantic_type.value.lower()
        if type_key in rules_cfg:
            cfg_req = rules_cfg[type_key].get("required")
            if cfg_req is True:
                field.required = True
                field.required_reason = RequiredReason.CONFIG

    def _clean_token(self, token: str) -> str:
        words = re.sub(r"([a-z])([A-Z])", r"\1 \2", token)
        words = re.sub(r"[_\-\.]", " ", words).strip()
        return words.title()
