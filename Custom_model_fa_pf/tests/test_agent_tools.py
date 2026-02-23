"""Tests for agent tool definitions."""

import json
import pytest
from Custom_model_fa_pf.agent.tools import (
    get_all_tools,
    save_field_tool,
    validate_fields_tool,
    classify_lobs_tool,
    extract_entities_tool,
    assign_forms_tool,
    read_form_tool,
    map_fields_tool,
    analyze_gaps_tool,
)


class TestToolDefinitions:
    def test_all_tools_list(self):
        tools = get_all_tools()
        assert len(tools) >= 8
        names = [t.name for t in tools]
        assert "save_field" in names
        assert "validate_fields" in names
        assert "classify_lobs" in names

    def test_tools_have_descriptions(self):
        for tool in get_all_tools():
            assert tool.description, f"Tool {tool.name} has no description"
            assert len(tool.description) > 10

    def test_tools_have_args_schema(self):
        """Each tool should have typed arguments."""
        for tool in get_all_tools():
            schema = tool.args_schema
            assert schema is not None, f"Tool {tool.name} has no args schema"


class TestSaveFieldTool:
    def test_save_field_returns_json(self):
        result = save_field_tool.invoke(
            {"field_name": "business_name", "value": "Acme LLC", "source": "user_stated"}
        )
        parsed = json.loads(result)
        assert parsed["status"] == "saved"
        assert parsed["field_name"] == "business_name"
        assert parsed["value"] == "Acme LLC"
        assert "confidence" in parsed

    def test_save_field_empty_value(self):
        result = save_field_tool.invoke(
            {"field_name": "phone", "value": "", "source": "user_stated"}
        )
        parsed = json.loads(result)
        assert parsed["status"] == "skipped"


class TestValidateFieldsTool:
    def test_validate_vin_error(self):
        fields = json.dumps({"Vehicle_VIN_A": "SHORTVIN"})
        result = validate_fields_tool.invoke({"fields_json": fields})
        parsed = json.loads(result)
        assert parsed["error_count"] >= 1

    def test_validate_clean_fields(self):
        fields = json.dumps({"Policy_EffectiveDate_A": "03/01/2026"})
        result = validate_fields_tool.invoke({"fields_json": fields})
        parsed = json.loads(result)
        assert parsed["error_count"] == 0

    def test_validate_auto_correction(self):
        fields = json.dumps({"NamedInsured_TaxIdentifier_A": "123456789"})
        result = validate_fields_tool.invoke({"fields_json": fields})
        parsed = json.loads(result)
        assert "12-3456789" in json.dumps(parsed)
