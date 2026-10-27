"""Browser lifecycle and context manager for Playwright."""
from __future__ import annotations

from typing import Optional
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
from config.config_loader import FrameworkConfig
from reporting.logger import logger


class BrowserManager:
    """Manages Playwright browser instance, context, page creation, and cleanup."""

    def __init__(self, config: FrameworkConfig, headless_override: Optional[bool] = None):
        self.config = config
        self.headless = headless_override if headless_override is not None else config.browser.headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self) -> Page:
        """Starts Playwright, launches the browser, creates a context and page."""
        logger.info(f"Starting Playwright with browser: {self.config.browser.browser} (headless={self.headless})")
        self.playwright = sync_playwright().start()

        browser_type_name = self.config.browser.browser.lower()
        if browser_type_name == "firefox":
            browser_launcher = self.playwright.firefox
        elif browser_type_name in ("webkit", "safari"):
            browser_launcher = self.playwright.webkit
        else:
            browser_launcher = self.playwright.chromium

        self.browser = browser_launcher.launch(
            headless=self.headless,
            slow_mo=self.config.browser.slow_mo,
        )

        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )
        self.context.set_default_timeout(self.config.browser.timeout)

        self.page = self.context.new_page()
        return self.page

    def get_page(self) -> Page:
        """Returns the current active page."""
        if not self.page:
            return self.start()
        return self.page

    def stop(self) -> None:
        """Closes page, context, browser, and stops Playwright cleanly."""
        try:
            if self.page:
                self.page.close()
                self.page = None
            if self.context:
                self.context.close()
                self.context = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
            logger.info("Browser stopped and Playwright session closed.")
        except Exception as e:
            logger.warning(f"Error while stopping browser: {e}")

    def __enter__(self) -> Page:
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
