import pytest
from src.tools.completeness import (
    check_required_fields,
    validate_business_rules,
    calculate_submission_readiness
)

def test_check_required():
    data = {"name": "Bob"}
    required = ["name", "age"]
    
    complete, missing, count = check_required_fields(data, required)
    assert complete is False
    assert "age" in missing
    assert count == 1

def test_business_rules():
    assert validate_business_rules({"coverage_amount": 100})[0] is True
    assert validate_business_rules({"coverage_amount": -10})[0] is False

def test_readiness():
    # Ready
    score, blocks, ready = calculate_submission_readiness({}, [])
    assert ready is True
    assert score == 100
    
    # Not ready
    score, blocks, ready = calculate_submission_readiness({"missing": ["a"]}, [])
    assert ready is False
    assert score == 50
