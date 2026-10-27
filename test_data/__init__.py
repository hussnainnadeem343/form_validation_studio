"""Test data package for form validation automation."""
from test_data.data_generator import DataGenerator
from test_data.valid_data import get_valid_value
from test_data.invalid_data import get_invalid_emails, get_invalid_phones, get_invalid_numbers

__all__ = [
    "DataGenerator",
    "get_valid_value",
    "get_invalid_emails",
    "get_invalid_phones",
    "get_invalid_numbers",
]
