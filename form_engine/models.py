"""Domain models and data structures for form automation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SemanticType(str, Enum):
    """Semantic classification of form fields."""
    USERNAME = "USERNAME"
    FULL_NAME = "FULL_NAME"
    EMAIL = "EMAIL"
    PASSWORD = "PASSWORD"
    CONFIRM_PASSWORD = "CONFIRM_PASSWORD"
    PHONE = "PHONE"
    CNIC = "CNIC"
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DROPDOWN = "DROPDOWN"
    DATE = "DATE"
    FILE_UPLOAD = "FILE_UPLOAD"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_string(cls, value: str) -> "SemanticType":
        try:
            return cls(value.upper())
        except ValueError:
            return cls.UNKNOWN


class RequiredReason(str, Enum):
    """Reason why a field was marked as required."""
    HTML_REQUIRED = "html_required"
    ARIA_REQUIRED = "aria_required"
    CONFIG = "config"
    INFERRED = "inferred"
    NONE = "none"


class ExpectedBehavior(str, Enum):
    """Expected outcome of applying test input."""
    VALIDATION_TRIGGERED = "validation_triggered"
    ACCEPTED = "accepted"
    OBSERVE = "observe"


class TestStatus(str, Enum):
    """Status of executed test case."""
    __test__ = False
    PASS = "PASS"
    FAIL = "FAIL"
    OBSERVATION = "OBSERVATION"
    SKIPPED = "SKIPPED"


@dataclass
class FieldOption:
    """Option entry for a select/dropdown field."""
    value: str
    text: str
    selected: bool = False


@dataclass
class FieldDefinition:
    """Detailed structural and semantic definition of a detected form field."""
    name: str
    label: str
    html_type: str
    semantic_type: SemanticType
    required: bool
    selector: str
    tag: str = "input"
    field_id: str = ""
    placeholder: str = ""
    aria_label: str = ""
    value: str = ""
    required_reason: RequiredReason = RequiredReason.NONE
    options: List[FieldOption] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class FormDefinition:
    """Structured representation of a detected form container."""
    selector: str
    fields: List[FieldDefinition] = field(default_factory=list)
    submit_element: str = ""
    is_wizard: bool = False
    next_element: str = ""
    prev_element: str = ""
    step_number: int = 1


@dataclass
class TestCase:
    """Specification of a single validation test case."""
    __test__ = False
    field_name: str
    semantic_type: SemanticType
    rule_name: str
    input_value: Any
    expected_behavior: ExpectedBehavior
    description: str = ""
    step_number: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Outcome and diagnostics of an executed TestCase."""
    __test__ = False
    test_case: TestCase
    status: TestStatus
    actual_behavior: str
    validation_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    message: str = ""
    duration_ms: float = 0.0
    step_number: int = 1
