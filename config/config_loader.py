"""Configuration loader for the generic form automation framework."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


def _resolve_env_vars(data: Any) -> Any:
    """Recursively expand environment variables formatted as ${VAR_NAME} in strings."""
    if isinstance(data, dict):
        return {k: _resolve_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_env_vars(item) for item in data]
    elif isinstance(data, str):
        pattern = re.compile(r"\$\{([^}^{]+)\}")
        matches = pattern.findall(data)
        for var in matches:
            val = os.getenv(var, "")
            data = data.replace(f"${{{var}}}", val)
        return data
    return data


@dataclass
class BrowserConfig:
    browser: str = "chromium"
    headless: bool = True
    slow_mo: int = 0
    timeout: int = 30000


@dataclass
class ExecutionConfig:
    screenshot_on_failure: bool = True
    screenshot_on_observation: bool = True
    stop_on_failure: bool = False
    output_dir: str = "reports"
    screenshots_dir: str = "screenshots"


@dataclass
class LoginConfig:
    username: str = ""
    password: str = ""
    hospital: str = ""
    wait_seconds: int = 10
    selectors: Dict[str, str] = field(default_factory=dict)
    extra_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationConfig:
    base_url: str = ""
    target_url: str = ""


@dataclass
class FrameworkConfig:
    project_name: str = "Generic Form Automation"
    application: ApplicationConfig = field(default_factory=ApplicationConfig)
    login: LoginConfig = field(default_factory=LoginConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    rules: Dict[str, Any] = field(default_factory=dict)
    field_overrides: Dict[str, Any] = field(default_factory=dict)
    raw_config: Dict[str, Any] = field(default_factory=dict)


class ConfigLoader:
    """Loads and parses framework configuration from YAML files and environment variables."""

    @classmethod
    def load(cls, config_path: str | Path) -> FrameworkConfig:
        path = Path(config_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

        # Resolve environment variable substitutions
        resolved_data = _resolve_env_vars(raw_data)

        # Login credentials: env vars take highest precedence
        login_section = resolved_data.get("login", {}) or {}
        env_user = os.getenv("TEST_USERNAME")
        env_pass = os.getenv("TEST_PASSWORD")
        username = env_user if env_user is not None else login_section.get("username", "")
        password = env_pass if env_pass is not None else login_section.get("password", "")

        app_section = resolved_data.get("application", {}) or {}
        browser_section = resolved_data.get("browser", {}) or {}
        exec_section = resolved_data.get("execution", {}) or {}

        return FrameworkConfig(
            project_name=resolved_data.get("project", {}).get("name", "Generic Form Automation"),
            application=ApplicationConfig(
                base_url=app_section.get("base_url", ""),
                target_url=app_section.get("target_url", ""),
            ),
            login=LoginConfig(
                username=username,
                password=password,
                hospital=login_section.get("hospital", ""),
                wait_seconds=int(login_section.get("wait_seconds", 10)),
                selectors=login_section.get("selectors", {}) or {},
                extra_fields=login_section.get("extra_fields", {}) or {},
            ),
            browser=BrowserConfig(
                browser=browser_section.get("browser", "chromium"),
                headless=browser_section.get("headless", True),
                slow_mo=browser_section.get("slow_mo", 0),
                timeout=browser_section.get("timeout", 30000),
            ),
            execution=ExecutionConfig(
                screenshot_on_failure=exec_section.get("screenshot_on_failure", True),
                screenshot_on_observation=exec_section.get("screenshot_on_observation", True),
                stop_on_failure=exec_section.get("stop_on_failure", False),
                output_dir=exec_section.get("output_dir", "reports"),
                screenshots_dir=exec_section.get("screenshots_dir", "screenshots"),
            ),
            rules=resolved_data.get("rules", {}) or {},
            field_overrides=resolved_data.get("field_overrides", {}) or {},
            raw_config=resolved_data,
        )
