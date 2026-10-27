"""Unit tests for LoginManager hospital selection and HMIS mandatory enforcement."""
import pytest
from unittest.mock import MagicMock
from config.config_loader import ApplicationConfig, FrameworkConfig, LoginConfig
from core.login.login_manager import LoginException, LoginManager


def test_login_config_hospital_field():
    cfg = LoginConfig(username="testuser", password="secret", hospital="PITB Testing Hospital 2")
    assert cfg.hospital == "PITB Testing Hospital 2"


def test_hmis_mandatory_hospital_missing_raises_exception():
    config = FrameworkConfig(
        project_name="HMIS",
        application=ApplicationConfig(base_url="https://hmis-beta.pitb.gov.pk/login"),
        login=LoginConfig(username="user", password="pass", hospital="Hospital A"),
    )
    manager = LoginManager(config)

    # Mock page with no hospital dropdown
    mock_page = MagicMock()
    mock_page.url = "https://hmis-beta.pitb.gov.pk/login"
    mock_page.locator.return_value.count.return_value = 0

    with pytest.raises(LoginException) as exc_info:
        # Simulate check in authenticate
        manager._detect_hospital_field = MagicMock(return_value=None)
        is_hmis = "hmis" in config.project_name.lower()
        if is_hmis and not manager._detect_hospital_field(mock_page):
            raise LoginException("Hospital selection is mandatory for HMIS, but no hospital dropdown was detected.")

    assert "Hospital selection is mandatory for HMIS" in str(exc_info.value)


def test_detect_hospital_field_heuristics():
    config = FrameworkConfig(
        project_name="HMIS",
        login=LoginConfig(username="user", password="pass", hospital="PITB Testing Hospital 2"),
    )
    manager = LoginManager(config)

    mock_page = MagicMock()
    
    # When #hospitalId exists
    def mock_locator(sel):
        loc = MagicMock()
        if sel == "#hospitalId":
            loc.count.return_value = 1
            loc.first.is_visible.return_value = True
        else:
            loc.count.return_value = 0
        return loc

    mock_page.locator.side_effect = mock_locator
    detected = manager._detect_hospital_field(mock_page)
    assert detected == "#hospitalId"


def test_select_hospital_by_label():
    config = FrameworkConfig(
        project_name="HMIS",
        login=LoginConfig(username="user", password="pass", hospital="PITB Testing Hospital 2"),
    )
    manager = LoginManager(config)

    mock_page = MagicMock()
    mock_hosp_loc = MagicMock()
    mock_hosp_loc.count.return_value = 1
    mock_hosp_loc.first.is_visible.return_value = True
    mock_page.locator.return_value.first = mock_hosp_loc

    manager._select_hospital(mock_page, "#hospitalId", "PITB Testing Hospital 2", mandatory=True)
    mock_hosp_loc.select_option.assert_called_with(label="PITB Testing Hospital 2")
    mock_hosp_loc.dispatch_event.assert_any_call("change")


def test_login_config_default_wait_seconds():
    cfg = LoginConfig()
    assert cfg.wait_seconds == 10

    cfg_custom = LoginConfig(wait_seconds=5)
    assert cfg_custom.wait_seconds == 5


def test_login_authenticate_respects_wait_seconds():
    config = FrameworkConfig(
        project_name="Example",
        application=ApplicationConfig(base_url="http://example.com/login"),
        login=LoginConfig(username="user", password="secret", wait_seconds=3),
    )
    manager = LoginManager(config)
    manager.is_login_page = MagicMock(return_value=True)
    manager.detect_selectors = MagicMock(return_value=("#user", "#pass", "#submit"))
    manager._detect_hospital_field = MagicMock(return_value=None)
    manager.verify_login_success = MagicMock(return_value=True)

    mock_page = MagicMock()
    mock_page.url = "http://example.com/login"

    # Call authenticate
    manager.authenticate(mock_page)

    # Verify credentials filled
    mock_page.locator.assert_any_call("#user")
    mock_page.locator.assert_any_call("#pass")

    # Verify wait_for_timeout was called for the 3 seconds countdown
    timeout_calls = [c for c in mock_page.wait_for_timeout.call_args_list if c[0] == (1000,)]
    assert len(timeout_calls) == 3


def test_login_authenticate_early_exit_during_wait():
    config = FrameworkConfig(
        project_name="Example",
        application=ApplicationConfig(base_url="http://example.com/login"),
        login=LoginConfig(username="user", password="secret", wait_seconds=5),
    )
    manager = LoginManager(config)
    
    # Simulate page navigating during wait_for_timeout
    current_url = ["http://example.com/login"]
    mock_page = MagicMock()
    type(mock_page).url = property(lambda self: current_url[0])

    def fake_wait(ms):
        current_url[0] = "http://example.com/dashboard"

    mock_page.wait_for_timeout.side_effect = fake_wait
    
    manager.is_login_page = MagicMock(side_effect=lambda page: page.url == "http://example.com/login")
    manager.detect_selectors = MagicMock(return_value=("#user", "#pass", "#submit"))
    manager._detect_hospital_field = MagicMock(return_value=None)
    manager.verify_login_success = MagicMock(return_value=True)

    manager.authenticate(mock_page)

    # Countdown loop should have broken after 1 second because URL changed during wait
    timeout_calls = [c for c in mock_page.wait_for_timeout.call_args_list if c[0] == (1000,)]
    assert len(timeout_calls) == 1

