"""Navigation manager for navigating to target application forms."""
from __future__ import annotations

from playwright.sync_api import Page
from config.config_loader import FrameworkConfig
from reporting.logger import logger


class NavigationException(Exception):
    """Raised when navigation to target form fails or redirects back to login."""
    pass


class Navigator:
    """Manages navigation to authenticated target URLs with session validation."""

    def __init__(self, config: FrameworkConfig):
        self.config = config

    def navigate_to_target(self, page: Page) -> Page:
        """Navigates to the configured target_url and verifies session retention."""
        target_url = self.config.application.target_url
        if not target_url:
            logger.info("No target_url specified in configuration; staying on current page.")
            return page

        # If already on the target URL (e.g. login redirected straight there)
        if page.url.rstrip("/") == target_url.rstrip("/"):
            logger.info(f"Already at target form URL: {target_url}")
            return page

        logger.info(f"Navigating to target form URL: {target_url}")
        page.goto(target_url, wait_until="domcontentloaded")

        # Verify that we were not redirected back to a login screen
        current_url = page.url.lower()
        if ("login" in current_url or "signin" in current_url) and ("login" not in target_url.lower()):
            raise NavigationException(
                f"Navigation to target URL '{target_url}' failed: Application redirected back to login page ({page.url}). "
                "The authentication session may have expired or credentials lacked required authorization."
            )

        logger.info(f"Target form URL loaded successfully: {page.url}")
        return page
