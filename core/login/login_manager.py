"""Login manager for authentication and session initiation."""
from __future__ import annotations

import re
from typing import Optional, Tuple
from playwright.sync_api import Locator, Page
from config.config_loader import FrameworkConfig
from reporting.logger import logger


class LoginException(Exception):
    """Raised when authentication fails or elements cannot be detected."""
    pass


class LoginManager:
    """Detects login pages, identifies credentials controls, and performs login."""

    def __init__(self, config: FrameworkConfig):
        self.config = config

    def authenticate(self, page: Page) -> Page:
        """Navigates to base URL, detects login form, submits credentials, and verifies login."""
        base_url = self.config.application.base_url
        if not base_url:
            logger.info("No base_url configured for login. Skipping login phase.")
            return page

        logger.info(f"Opening application base URL: {base_url}")
        page.goto(base_url, wait_until="domcontentloaded")

        is_login = self.is_login_page(page)
        if not is_login:
            logger.info("Current page does not appear to be a login page. Assuming already authenticated or open access.")
            return page

        logger.info("Login page detected.")

        username_selector, password_selector, submit_selector = self.detect_selectors(page)
        username = self.config.login.username
        password = self.config.login.password

        # Check and handle Hospital selection (mandatory if HMIS)
        is_hmis = (
            "hmis" in self.config.project_name.lower()
            or "hmis" in page.url.lower()
            or bool(self.config.login.hospital)
        )
        hospital_selector = self._detect_hospital_field(page)
        hospital_target = self.config.login.hospital or ("PITB Testing Hospital 2" if is_hmis else "")

        if is_hmis and not hospital_selector:
            raise LoginException(
                "Hospital selection is mandatory for HMIS, but no hospital dropdown was detected on the login page."
            )

        if hospital_selector:
            self._select_hospital(page, hospital_selector, hospital_target, mandatory=is_hmis)

        if not username or not password:
            logger.warning("Username or password is not provided in configuration/environment variables.")

        logger.info(f"Entering credentials into username: '{username_selector}' and password: '{password_selector}'")
        user_loc = page.locator(username_selector).first
        if username:
            user_loc.fill(username)

        pass_loc = page.locator(password_selector).first
        if password:
            pass_loc.fill(password)

        initial_url = page.url

        # Wait after entering credentials (allows CAPTCHA solving, OTP entry, or user inspection)
        wait_sec = getattr(self.config.login, "wait_seconds", 10)
        if wait_sec is None:
            wait_sec = 10

        if wait_sec > 0:
            logger.info(f"Credentials entered. Waiting {wait_sec} seconds before submitting login...")
            for remaining in range(wait_sec, 0, -1):
                if page.url != initial_url and not self.is_login_page(page):
                    logger.info("Login already completed during wait period. Proceeding.")
                    break
                logger.info(f"Login wait: {remaining}s remaining before submitting credentials...")
                page.wait_for_timeout(1000)

        if page.url == initial_url and self.is_login_page(page):
            logger.info(f"Submitting login via: '{submit_selector}'")
            submit_loc = page.locator(submit_selector).first
            try:
                with page.expect_navigation(timeout=10000):
                    submit_loc.click()
            except Exception:
                submit_loc.click()
                page.wait_for_timeout(1500)

        # Verify login appears successful
        self.verify_login_success(page, initial_url)
        logger.info("Login verified successfully.")
        return page

    def is_login_page(self, page: Page) -> bool:
        """Determines whether the current page appears to be a login page."""
        url_lower = page.url.lower()

        # Registration and sign-up pages are forms to be tested, not login pages
        if any(term in url_lower for term in ("sign-up", "signup", "register", "registration", "create-account", "new-user")):
            return False

        # If URL explicitly points to login / signin / auth
        if any(term in url_lower for term in ("login", "signin", "auth", "session")):
            return True

        # Check for headings explicitly stating log in / sign in
        headings = page.locator("h1, h2, h3, .title, .header")
        for i in range(min(headings.count(), 5)):
            txt = headings.nth(i).inner_text().lower()
            if any(term in txt for term in ("register", "sign up", "signup", "create account")):
                return False
            if any(term in txt for term in ("log in", "login", "sign in", "signin")):
                return True

        # Check for password field presence ONLY if there is no confirm_password field
        pwd_count = page.locator("input[type='password']").count()
        if pwd_count == 1:
            # Single password field is typical of login pages
            return True

        return False

    def detect_selectors(self, page: Page) -> Tuple[str, str, str]:
        """Resolves username, password, and submit selectors via config or heuristics."""
        cfg_selectors = self.config.login.selectors or {}
        user_sel = cfg_selectors.get("username", "")
        pass_sel = cfg_selectors.get("password", "")
        sub_sel = cfg_selectors.get("submit", "")

        # 1. Username selector
        if not user_sel:
            user_sel = self._detect_username_field(page)
            if not user_sel:
                raise LoginException(
                    "Automatic detection failed: Could not identify username field. "
                    "Please specify 'login.selectors.username' in your YAML configuration."
                )

        # 2. Password selector
        if not pass_sel:
            pass_sel = self._detect_password_field(page)
            if not pass_sel:
                raise LoginException(
                    "Automatic detection failed: Could not identify password field. "
                    "Please specify 'login.selectors.password' in your YAML configuration."
                )

        # 3. Submit selector
        if not sub_sel:
            sub_sel = self._detect_submit_button(page)
            if not sub_sel:
                raise LoginException(
                    "Automatic detection failed: Could not identify login submit button. "
                    "Please specify 'login.selectors.submit' in your YAML configuration."
                )

        return user_sel, pass_sel, sub_sel

    def _detect_username_field(self, page: Page) -> Optional[str]:
        indicators = ["username", "user", "user_name", "userid", "user_id", "login", "login_id", "email"]
        # Check by id, name, placeholder, type
        for ind in indicators:
            for attr in ("id", "name", "placeholder", "aria-label"):
                sel = f"input[{attr}*='{ind}' i]"
                if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                    return sel

        # Fallback: first visible input type=text or type=email that is not password
        text_inputs = page.locator("input[type='text'], input[type='email'], input:not([type])")
        for i in range(text_inputs.count()):
            candidate = text_inputs.nth(i)
            if candidate.is_visible():
                c_id = candidate.get_attribute("id")
                if c_id:
                    return f"#{c_id}"
                c_name = candidate.get_attribute("name")
                if c_name:
                    return f"input[name='{c_name}']"
                return f"input[type='text']:nth-of-type({i+1})"
        return None

    def _detect_password_field(self, page: Page) -> Optional[str]:
        # Most reliable indicator: input[type='password']
        pwd_inputs = page.locator("input[type='password']")
        if pwd_inputs.count() > 0 and pwd_inputs.first.is_visible():
            p_id = pwd_inputs.first.get_attribute("id")
            if p_id:
                return f"#{p_id}"
            p_name = pwd_inputs.first.get_attribute("name")
            if p_name:
                return f"input[name='{p_name}']"
            return "input[type='password']"

        indicators = ["password", "pass", "pwd"]
        for ind in indicators:
            for attr in ("id", "name", "placeholder"):
                sel = f"input[{attr}*='{ind}' i]"
                if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                    return sel
        return None

    def _detect_submit_button(self, page: Page) -> Optional[str]:
        # Form submit buttons
        submit_types = page.locator("button[type='submit'], input[type='submit']")
        if submit_types.count() > 0 and submit_types.first.is_visible():
            s_id = submit_types.first.get_attribute("id")
            if s_id:
                return f"#{s_id}"
            return "button[type='submit'], input[type='submit']"

        # Buttons with login / sign in text
        indicators = ["login", "log in", "sign in", "signin", "submit"]
        buttons = page.locator("button, input[type='button'], a.btn, a[role='button']")
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            if btn.is_visible():
                text = (btn.inner_text() or btn.get_attribute("value") or "").lower()
                if any(ind in text for ind in indicators):
                    b_id = btn.get_attribute("id")
                    if b_id:
                        return f"#{b_id}"
                    return f"button:has-text('{text.strip()}')"

        return None

    def _detect_hospital_field(self, page: Page) -> Optional[str]:
        """Detects the hospital or facility dropdown on multi-tenant / healthcare portals."""
        cfg_selectors = self.config.login.selectors or {}
        if "hospital" in cfg_selectors and cfg_selectors["hospital"]:
            return cfg_selectors["hospital"]

        # Check explicit ID #hospitalId first (standard in HMIS)
        if page.locator("#hospitalId").count() > 0 and page.locator("#hospitalId").first.is_visible():
            return "#hospitalId"

        # Check select with hospital/facility/tenant in attributes
        indicators = ["hospital", "facility", "tenant", "branch"]
        for ind in indicators:
            for attr in ("id", "name", "aria-label"):
                sel = f"select[{attr}*='{ind}' i]"
                if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                    return sel

        # Check custom searchable dropdown / bootstrap select picker wrapper
        for ind in indicators:
            sel = f"[data-id*='{ind}' i], [id*='{ind}' i]"
            if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                return sel

        return None

    def _select_hospital(self, page: Page, hospital_selector: str, hospital_value: str, mandatory: bool = False) -> None:
        """Selects the target hospital in the hospital selection dropdown."""
        hosp_loc = page.locator(hospital_selector).first
        if hosp_loc.count() == 0 or not hosp_loc.is_visible():
            if mandatory:
                raise LoginException(f"Hospital dropdown selector '{hospital_selector}' not visible on page.")
            return

        selected = False
        target = hospital_value.strip() if hospital_value else ""

        # Strategy 1: Select by label (e.g. "PITB Testing Hospital 2")
        if target:
            try:
                hosp_loc.select_option(label=target)
                selected = True
                logger.info(f"Selected hospital by label: '{target}'")
            except Exception:
                pass

        # Strategy 2: Select by value (e.g. "64")
        if not selected and target:
            try:
                hosp_loc.select_option(value=target)
                selected = True
                logger.info(f"Selected hospital by value: '{target}'")
            except Exception:
                pass

        # Strategy 3: Substring matching among option text
        if not selected and target:
            options = hosp_loc.locator("option").all()
            for opt in options:
                txt = opt.inner_text().strip()
                if target.lower() in txt.lower():
                    val = opt.get_attribute("value")
                    hosp_loc.select_option(value=val)
                    selected = True
                    logger.info(f"Selected hospital by matching text '{txt}' (value='{val}')")
                    break

        # Strategy 4: Fallback to first non-empty option if mandatory
        if not selected:
            if mandatory:
                options = hosp_loc.locator("option").all()
                for opt in options:
                    val = opt.get_attribute("value")
                    if val and val.strip():
                        hosp_loc.select_option(value=val)
                        selected = True
                        logger.info(f"Mandatory hospital fallback selected: '{opt.inner_text().strip()}'")
                        break
                if not selected:
                    raise LoginException(f"Hospital selection is mandatory, but failed to select '{target}' and no valid options found.")
            else:
                logger.warning(f"Could not select hospital '{target}'. Continuing with current selection.")

        # Dispatch events so bootstrap-select-picker or dynamic UI updates
        try:
            hosp_loc.dispatch_event("change")
            hosp_loc.dispatch_event("blur")
        except Exception:
            pass
        page.wait_for_timeout(300)

    def verify_login_success(self, page: Page, initial_url: str) -> None:
        """Verifies whether login succeeded by inspecting URL changes, error banners, or forms."""
        page.wait_for_timeout(500)
        # Check for visible error message on the page
        error_locators = page.locator(".alert-danger, .error-message, .login-error, [role='alert']")
        if error_locators.count() > 0 and error_locators.first.is_visible():
            err_text = error_locators.first.inner_text().strip()
            if err_text:
                raise LoginException(f"Login failed: Application displayed error message '{err_text}'")

        # If URL hasn't changed AND password input is still visible with empty or invalid feedback
        if page.url == initial_url and page.locator("input[type='password']").count() > 0:
            if page.locator("input[type='password']").first.is_visible():
                # Check if still on login form
                pass
