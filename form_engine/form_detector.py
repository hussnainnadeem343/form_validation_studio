"""Form detector for identifying forms, interactive input groups, and multi-step wizard workflows."""
from __future__ import annotations

from typing import List, Optional
from playwright.sync_api import Locator, Page
from form_engine.field_detector import FieldDetector
from form_engine.models import FieldDefinition, FormDefinition
from reporting.logger import logger


class FormDetector:
    """Discovers <form> elements, interactive input containers, and multi-step wizard workflows."""

    def __init__(self, field_detector: Optional[FieldDetector] = None):
        self.field_detector = field_detector or FieldDetector()

    def detect_forms(self, page: Page) -> List[FormDefinition]:
        """Identifies forms on the page, with seamless support for multi-step wizards and formless pages."""
        forms: List[FormDefinition] = []

        # 1. First, check all <form> tags on the page
        form_locators = page.locator("form")
        form_count = form_locators.count()

        if form_count > 0:
            for i in range(form_count):
                f_loc = form_locators.nth(i)
                f_id = f_loc.get_attribute("id")
                f_name = f_loc.get_attribute("name")
                selector = f"#{f_id}" if f_id else (f"form[name='{f_name}']" if f_name else f"form:nth-of-type({i+1})")

                # Only include form if it contains actual interactive fields
                fields = self.field_detector.detect_fields(page, container_selector=selector)
                if len(fields) > 0:
                    submit_el = self._detect_form_submit(f_loc, selector, page=page)
                    next_btn = self.detect_next_button(page, f_loc)
                    prev_btn = self.detect_prev_button(page, f_loc)
                    is_wiz = next_btn is not None or self.is_multi_step_wizard(page)

                    forms.append(FormDefinition(
                        selector=selector,
                        fields=fields,
                        submit_element=submit_el or (next_btn or ""),
                        is_wizard=is_wiz,
                        next_element=next_btn or "",
                        prev_element=prev_btn or "",
                        step_number=1,
                    ))

        # If any <form> tags with fields were found, return them
        if len(forms) > 0:
            logger.info(f"Detected {len(forms)} <form> element(s) containing interactive fields.")
            return forms

        # 2. Formless page fallback: No <form> tags contain interactive fields.
        logger.info("No <form> tags containing interactive fields found. Scanning entire page for input controls...")

        page_fields = self.field_detector.detect_fields(page, container_selector="body")
        if not page_fields:
            logger.warning("No interactive fields found anywhere on the page.")
            return []

        logger.info(f"Discovered {len(page_fields)} interactive fields on formless page.")

        # Candidate containers where input groups typically live
        container_candidates = [
            ".modal-content", ".modal-body", ".modal",
            "main", "[role='main']",
            ".card-body", ".card", ".panel-body", ".panel", ".box",
            ".tab-pane.active", ".tab-pane",
            ".form-container", ".form-wrapper", ".content", "#content", "#main-content",
            ".container", "section", "article"
        ]

        best_container: Optional[str] = None
        best_fields: List[FieldDefinition] = []

        # Find the most specific container that encloses the detected fields
        for cand in container_candidates:
            loc = page.locator(cand)
            try:
                cand_count = int(loc.count())
            except Exception:
                cand_count = 0

            for idx in range(min(cand_count, 3)):
                cand_loc = loc.nth(idx)
                if cand_loc.is_visible():
                    cand_sel = f"{cand}:nth-of-type({idx+1})" if cand_count > 1 else cand
                    cand_fields = self.field_detector.detect_fields(page, container_selector=cand_sel)
                    if len(cand_fields) > len(best_fields):
                        best_container = cand_sel
                        best_fields = cand_fields

        # If a specific container captured the fields, use it; otherwise use 'body' as universal root
        if best_container and len(best_fields) >= 1:
            chosen_selector = best_container
            chosen_fields = best_fields
            container_locator = page.locator(chosen_selector).first
        else:
            chosen_selector = "body"
            chosen_fields = page_fields
            container_locator = page.locator("body").first

        submit_el = self._detect_form_submit(container_locator, chosen_selector, page=page)
        next_btn = self.detect_next_button(page, container_locator)
        prev_btn = self.detect_prev_button(page, container_locator)
        is_wiz = next_btn is not None or self.is_multi_step_wizard(page)

        logger.info(f"Created container-based FormDefinition for '{chosen_selector}' with {len(chosen_fields)} fields (is_wizard={is_wiz}).")

        return [FormDefinition(
            selector=chosen_selector,
            fields=chosen_fields,
            submit_element=submit_el or (next_btn or ""),
            is_wizard=is_wiz,
            next_element=next_btn or "",
            prev_element=prev_btn or "",
            step_number=1,
        )]

    def detect_next_button(self, page: Page, container: Optional[Locator] = None) -> Optional[str]:
        """Detects visible 'Next', 'Continue', or step progression action button."""
        try:
            c_count = int(container.count()) if container else 0
        except Exception:
            c_count = 0
        search_root = container if container and c_count > 0 else page
        next_keywords = ["next", "continue", "proceed", "next step"]

        # 1. Explicit IDs / Data attributes
        for sel in ["#nextBtn", "#btnNext", "#btn-next", ".btn-next", "[data-action='next']", "[data-wizard-action='next']"]:
            loc = search_root.locator(sel)
            try:
                l_count = int(loc.count())
            except Exception:
                l_count = 0
            if l_count > 0 and loc.first.is_visible():
                return sel

        # 2. Buttons matching progression keywords
        buttons = search_root.locator("button, input[type='button'], a.btn, [role='button']")
        try:
            b_count = int(buttons.count())
        except Exception:
            b_count = 0

        for i in range(b_count):
            btn = buttons.nth(i)
            if btn.is_visible():
                text = (btn.inner_text() or btn.get_attribute("value") or "").lower().strip()
                if any(text == kw or text.startswith(f"{kw} ") or text.endswith(f" {kw}") for kw in next_keywords):
                    b_id = btn.get_attribute("id")
                    if b_id:
                        return f"#{b_id}"
                    b_name = btn.get_attribute("name")
                    if b_name:
                        return f"button[name='{b_name}']"
                    first_line = text.split("\n")[0].strip()
                    return f"button:has-text('{first_line}')"

        return None

    def detect_prev_button(self, page: Page, container: Optional[Locator] = None) -> Optional[str]:
        """Detects visible 'Previous', 'Back', or return action button."""
        try:
            c_count = int(container.count()) if container else 0
        except Exception:
            c_count = 0
        search_root = container if container and c_count > 0 else page
        prev_keywords = ["previous", "back", "prev", "prev step"]

        for sel in ["#prevBtn", "#btnPrev", "#btn-prev", "#btnBack", ".btn-prev", "[data-action='prev']", "[data-wizard-action='prev']"]:
            loc = search_root.locator(sel)
            try:
                l_count = int(loc.count())
            except Exception:
                l_count = 0
            if l_count > 0 and loc.first.is_visible():
                return sel

        buttons = search_root.locator("button, input[type='button'], a.btn, [role='button']")
        try:
            b_count = int(buttons.count())
        except Exception:
            b_count = 0

        for i in range(b_count):
            btn = buttons.nth(i)
            if btn.is_visible():
                text = (btn.inner_text() or btn.get_attribute("value") or "").lower().strip()
                if any(text == kw or text.startswith(f"{kw} ") or text.endswith(f" {kw}") for kw in prev_keywords):
                    b_id = btn.get_attribute("id")
                    if b_id:
                        return f"#{b_id}"
                    first_line = text.split("\n")[0].strip()
                    return f"button:has-text('{first_line}')"

        return None

    def is_multi_step_wizard(self, page: Page) -> bool:
        """Determines if the page is currently in a multi-step wizard workflow."""
        if self.detect_next_button(page) is not None:
            return True

        stepper_selectors = [
            ".stepper", ".wizard", ".step-progress", "ul.steps",
            "[role='tablist'].steps", ".nav-pills-step"
        ]
        for sel in stepper_selectors:
            loc = page.locator(sel)
            try:
                l_count = int(loc.count())
            except Exception:
                l_count = 0
            if l_count > 0 and loc.first.is_visible():
                return True

        return False

    def _detect_form_submit(
        self,
        container: Locator,
        container_sel: str,
        page: Optional[Page] = None,
    ) -> str:
        """Finds submit button or primary action button inside or near the container."""
        # 1. Standard submit types
        submits = container.locator("button[type='submit'], input[type='submit']")
        if submits.count() > 0 and submits.first.is_visible():
            s_id = submits.first.get_attribute("id")
            if s_id:
                return f"#{s_id}"
            return f"{container_sel} button[type='submit'], {container_sel} input[type='submit']"

        # 2. Action buttons matching common registration/submission keywords
        keywords = [
            "submit", "save", "register", "registration", "create", "add",
            "send", "apply", "confirm", "proceed", "continue", "next",
            "done", "check in", "checkin", "book", "generate", "record"
        ]
        buttons = container.locator("button, input[type='button'], a.btn, [role='button']")
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            if btn.is_visible():
                text = (btn.inner_text() or btn.get_attribute("value") or "").lower().strip()
                if any(k in text for k in keywords):
                    b_id = btn.get_attribute("id")
                    if b_id:
                        return f"#{b_id}"
                    b_name = btn.get_attribute("name")
                    if b_name:
                        return f"button[name='{b_name}']"
                    clean_first_line = text.split("\n")[0].strip()
                    if clean_first_line:
                        return f"button:has-text('{clean_first_line}')"

        # 3. Primary action button style classes (Bootstrap / AdminLTE / Tailwind)
        primary_buttons = container.locator("button.btn-primary, button.btn-success, button.btn-auth")
        if primary_buttons.count() > 0 and primary_buttons.first.is_visible():
            p_id = primary_buttons.first.get_attribute("id")
            if p_id:
                return f"#{p_id}"
            return f"{container_sel} button.btn-primary, {container_sel} button.btn-success"

        # 4. If not found inside container, search page-wide (e.g. fixed footer or outer toolbar)
        if page and container_sel != "body":
            return self._detect_form_submit(page.locator("body").first, "body", page=None)

        return ""
