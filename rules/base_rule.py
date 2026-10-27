"""Base class and interfaces for field validation rule generators."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from form_engine.models import FieldDefinition, TestCase


class BaseRule(ABC):
    """Abstract base class that generates test cases for a specific semantic field type."""

    @abstractmethod
    def generate_test_cases(
        self,
        field: FieldDefinition,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestCase]:
        """Generates a list of validation test cases for the target field."""
        pass
