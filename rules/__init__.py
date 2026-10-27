"""Rules package for form validation automation."""
from rules.base_rule import BaseRule
from rules.rule_registry import RuleRegistry
from rules.username_rules import UsernameRule
from rules.fullname_rules import FullNameRule
from rules.email_rules import EmailRule
from rules.password_rules import PasswordRule
from rules.confirm_password_rules import ConfirmPasswordRule
from rules.phone_rules import PhoneRule
from rules.number_rules import NumberRule
from rules.dropdown_rules import DropdownRule
from rules.text_rules import TextRule

__all__ = [
    "BaseRule",
    "RuleRegistry",
    "UsernameRule",
    "FullNameRule",
    "EmailRule",
    "PasswordRule",
    "ConfirmPasswordRule",
    "PhoneRule",
    "NumberRule",
    "DropdownRule",
    "TextRule",
]
