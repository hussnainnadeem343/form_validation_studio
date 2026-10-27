"""Generators and collections of known invalid inputs for negative testing."""
from typing import List


def get_invalid_emails() -> List[str]:
    """Returns a list of structurally malformed email addresses."""
    return [
        "",
        "plainaddress",
        "#@%^%#$@#$@#.com",
        "@example.com",
        "Joe Smith <email@example.com>",
        "email.example.com",
        "email@example@example.com",
        ".email@example.com",
        "email.@example.com",
        "email..email@example.com",
        "email@example.com (Joe Smith)",
        "email@example",
        "email@-example.com",
        "email@111.222.333.44444",
        "email@example..com",
        "Abc..123@example.com",
        "test with spaces@domain.com",
    ]


def get_invalid_phones() -> List[str]:
    """Returns invalid phone inputs (non-numeric, symbols, bad lengths)."""
    return [
        "abcd",
        "123",
        "12345678901234567890",
        "123-abc-4567",
        "+++!!@@",
        "phone_number",
    ]


def get_invalid_numbers() -> List[str]:
    """Returns invalid numeric inputs."""
    return [
        "not_a_number",
        "12.34.56",
        "--5",
        "NaN",
        "Infinity",
        "1e10",
        "abc123",
    ]


def get_invalid_dates() -> List[str]:
    """Returns invalid date strings (malformed syntax, impossible calendar days)."""
    return [
        "invalid-date",
        "31/02/2026",
        "2026-02-31",
        "2026-13-45",
        "99/99/9999",
        "not_a_date",
    ]

