"""Registry mapping SemanticType to rule generation engines."""
from __future__ import annotations

from typing import Dict, List, Optional, Type
from form_engine.models import FieldDefinition, SemanticType, TestCase
from rules.base_rule import BaseRule
from rules.username_rules import UsernameRule
from rules.fullname_rules import FullNameRule
from rules.email_rules import EmailRule
from rules.password_rules import PasswordRule
from rules.confirm_password_rules import ConfirmPasswordRule
from rules.phone_rules import PhoneRule
from rules.cnic_rules import CNICRule
from rules.number_rules import NumberRule
from rules.dropdown_rules import DropdownRule
from rules.text_rules import TextRule
from rules.date_rules import DateRule


class RuleRegistry:
    """Central registry of validation rule generators for semantic field types."""

    def __init__(self):
        self._rules: Dict[SemanticType, BaseRule] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(SemanticType.USERNAME, UsernameRule())
        self.register(SemanticType.FULL_NAME, FullNameRule())
        self.register(SemanticType.EMAIL, EmailRule())
        self.register(SemanticType.PASSWORD, PasswordRule())
        self.register(SemanticType.CONFIRM_PASSWORD, ConfirmPasswordRule())
        self.register(SemanticType.PHONE, PhoneRule())
        self.register(SemanticType.CNIC, CNICRule())
        self.register(SemanticType.NUMBER, NumberRule())
        self.register(SemanticType.DROPDOWN, DropdownRule())
        self.register(SemanticType.TEXT, TextRule())
        self.register(SemanticType.DATE, DateRule())

    def register(self, semantic_type: SemanticType, rule_instance: BaseRule) -> None:
        """Register or override a rule generator for a semantic field type."""
        self._rules[semantic_type] = rule_instance

    def get_rule(self, semantic_type: SemanticType) -> Optional[BaseRule]:
        """Retrieve rule generator for a semantic type, falling back to None or generic Text."""
        return self._rules.get(semantic_type)

    def generate_all(
        self,
        fields: List[FieldDefinition],
        config: Dict[str, any],
    ) -> List[TestCase]:
        """Generates the complete ordered suite of test cases across all form fields.
        Password fields are processed before confirm_password fields to ensure context propagation.
        """
        all_cases: List[TestCase] = []
        context: Dict[str, any] = {}

        # Sort fields so PASSWORD comes before CONFIRM_PASSWORD
        def sort_key(f: FieldDefinition) -> int:
            if f.semantic_type == SemanticType.PASSWORD:
                return 0
            if f.semantic_type == SemanticType.CONFIRM_PASSWORD:
                return 1
            return 2

        ordered_fields = sorted(fields, key=sort_key)

        for f in ordered_fields:
            rule_engine = self.get_rule(f.semantic_type)
            if rule_engine:
                cases = rule_engine.generate_test_cases(f, config, context)
                all_cases.extend(cases)

        return all_cases
