"""Unit tests verifying FormDetector behavior on formless pages and empty <form> fallbacks."""
import pytest
from unittest.mock import MagicMock
from form_engine.form_detector import FormDetector
from form_engine.models import FieldDefinition, RequiredReason, SemanticType


def test_formless_page_detection_with_card_container():
    """Verify that a page without any <form> tags is detected via its container."""
    detector = FormDetector()

    # Mock Page
    mock_page = MagicMock()

    # No <form> tags
    def locator_mock(sel):
        loc = MagicMock()
        loc.count.return_value = 0
        return loc

    mock_page.locator.side_effect = locator_mock

    # Mock FieldDetector returning fields for body
    sample_fields = [
        FieldDefinition(name="patient_name", label="Patient Name", html_type="text", semantic_type=SemanticType.FULL_NAME, required=True, selector="#patient_name"),
        FieldDefinition(name="cnic", label="CNIC", html_type="text", semantic_type=SemanticType.CNIC, required=True, selector="#cnic"),
        FieldDefinition(name="phone", label="Phone", html_type="tel", semantic_type=SemanticType.PHONE, required=False, selector="#phone"),
    ]
    detector.field_detector.detect_fields = MagicMock(return_value=sample_fields)
    detector._detect_form_submit = MagicMock(return_value="#btn-save")

    forms = detector.detect_forms(mock_page)

    assert len(forms) == 1
    assert len(forms[0].fields) == 3
    assert forms[0].submit_element == "#btn-save"
    assert forms[0].fields[0].name == "patient_name"
    assert forms[0].fields[1].semantic_type == SemanticType.CNIC


def test_empty_form_tag_fallback_to_body_fields():
    """Verify that when a page has an empty <form id='logout-form'>, FormDetector falls back to page fields."""
    detector = FormDetector()

    mock_page = MagicMock()

    # <form> tag exists, but has 0 fields
    mock_forms = MagicMock()
    mock_forms.count.return_value = 1
    mock_f_loc = MagicMock()
    mock_f_loc.get_attribute.side_effect = lambda attr: "logout-form" if attr == "id" else None
    mock_forms.nth.return_value = mock_f_loc

    def locator_mock(sel):
        if sel == "form":
            return mock_forms
        loc = MagicMock()
        loc.count.return_value = 0
        return loc

    mock_page.locator.side_effect = locator_mock

    # FieldDetector returns 0 fields for the #logout-form, but 4 fields for body
    def detect_mock(page, container_selector="body"):
        if container_selector == "#logout-form":
            return []
        return [
            FieldDefinition(name="mr_number", label="MR Number", html_type="text", semantic_type=SemanticType.TEXT, required=True, selector="#mr"),
            FieldDefinition(name="patient_name", label="Full Name", html_type="text", semantic_type=SemanticType.FULL_NAME, required=True, selector="#pname"),
        ]

    detector.field_detector.detect_fields = MagicMock(side_effect=detect_mock)
    detector._detect_form_submit = MagicMock(return_value="#btn-register")

    forms = detector.detect_forms(mock_page)

    assert len(forms) == 1
    assert len(forms[0].fields) == 2
    assert forms[0].fields[0].name == "mr_number"
    assert forms[0].submit_element == "#btn-register"
