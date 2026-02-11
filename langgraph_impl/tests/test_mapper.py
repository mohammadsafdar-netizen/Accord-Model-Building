import pytest
from src.tools.mapper import (
    map_to_common_schema,
    map_common_field_to_all_forms,
    convert_to_schema_type,
    navigate_nested_schema
)

def test_map_to_common_schema():
    path, val = map_to_common_schema("name", "John")
    assert path == "common.insured_name"
    assert val == "John"
    
def test_map_common_fields():
    res = map_common_field_to_all_forms("common.insured_name", "Safdar")
    assert "form_1_data.namedInsured.fullName" in res
    assert res["form_1_data.namedInsured.fullName"] == "Safdar"
    
    # Unknown field
    res = map_common_field_to_all_forms("unknown", "val")
    assert res == {}

def test_convert_type():
    val, success = convert_to_schema_type("123", "int")
    assert val == 123
    assert success is True

def test_navigate_nested():
    initial = {}
    updated = navigate_nested_schema("a.b.c", 10, initial)
    assert updated["a"]["b"]["c"] == 10
