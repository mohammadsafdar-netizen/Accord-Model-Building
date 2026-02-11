import pytest
from src.tools.validator import (
    validate_field_type,
    validate_ssn,
    validate_email,
    validate_phone,
    validate_date,
    validate_currency
)

def test_validate_field_type():
    assert validate_field_type("age", "25", "int")[0] is True
    assert validate_field_type("cost", "10.50", "float")[0] is True
    assert validate_field_type("age", "abc", "int")[0] is False

def test_validate_ssn():
    assert validate_ssn("123-45-6789")[0] is True
    assert validate_ssn("123456789")[0] is False # Missing dashes

def test_validate_email():
    assert validate_email("test@example.com")[0] is True
    assert validate_email("invalid-email")[0] is False

def test_validate_phone():
    assert validate_phone("123-456-7890")[0] is True
    assert validate_phone("(123) 456-7890")[0] is True
    assert validate_phone("123")[0] is False

def test_validate_date():
    assert validate_date("2023-01-01")[0] is True
    assert validate_date("01/01/2023")[0] is True
    assert validate_date("not a date")[0] is False

def test_validate_currency():
    assert validate_currency("$1,000.00")[0] is True
    assert validate_currency("1000")[1] == 1000.0
    assert validate_currency("abc")[0] is False
