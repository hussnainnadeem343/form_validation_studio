"""Pytest fixtures and configuration for framework test suites."""
import os
import sys
from pathlib import Path
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config_loader import ConfigLoader, FrameworkConfig
from demo.server import DemoServer


@pytest.fixture(scope="session")
def demo_server():
    """Starts local HTTP demo server on port 8080 for integration testing."""
    server = DemoServer(port=8080)
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def example_config() -> FrameworkConfig:
    """Provides parsed example.yaml configuration."""
    cfg_path = PROJECT_ROOT / "config" / "projects" / "example.yaml"
    return ConfigLoader.load(cfg_path)
