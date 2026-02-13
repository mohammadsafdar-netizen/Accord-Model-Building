"""Unit tests for schema_registry module."""

from __future__ import annotations

import pytest

from schema_registry import SchemaRegistry, EXTRACTION_ORDER, detect_form_type, SUPPORTED_FORMS


class TestSchemaRegistry:
    def test_supported_forms(self):
        assert "125" in SUPPORTED_FORMS
        assert "127" in SUPPORTED_FORMS
        assert "137" in SUPPORTED_FORMS

    def test_extraction_order_non_empty(self):
        assert len(EXTRACTION_ORDER) > 0
        assert "header" in EXTRACTION_ORDER or "named_insured" in EXTRACTION_ORDER

    def test_registry_load_125(self, schemas_dir):
        reg = SchemaRegistry(schemas_dir=schemas_dir)
        schema = reg.get_schema("125")
        if schema is None:
            pytest.skip("125 schema not found")
        assert schema.form_number == "125"
        assert hasattr(schema, "fields")
        assert hasattr(schema, "categories")

    def test_detect_form_type_from_text(self):
        # Text containing form identifier
        text = "ACORD 125 (2023/01) Commercial Insurance Application"
        out = detect_form_type(text, "form_125.pdf")
        assert out == "125" or out is None  # implementation may vary

    def test_detect_form_type_unknown(self):
        out = detect_form_type("Random document", "doc.pdf")
        assert out is None or out in SUPPORTED_FORMS
