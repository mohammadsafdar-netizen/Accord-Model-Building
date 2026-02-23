"""Tests for form_reader.py — dynamic AcroForm PDF reader."""

import pytest
from pathlib import Path

from Custom_model_fa_pf.config import FORM_TEMPLATES_DIR
from Custom_model_fa_pf.form_reader import (
    FormCatalog,
    FormField,
    FormSection,
    read_pdf_form,
    find_template,
    read_all_templates,
    _infer_category,
    _extract_suffix,
    _detect_form_number,
)

# Expected field counts from schemas (cleaned)
EXPECTED_FIELD_COUNTS = {
    "125": 548,
    "127": 634,
    "137": 403,
    "163": None,  # varies — generic TextNN fields
}


class TestFormField:
    def test_to_dict_minimal(self):
        f = FormField(name="test_field", field_type="text")
        d = f.to_dict()
        assert d["name"] == "test_field"
        assert d["field_type"] == "text"
        assert "tooltip" not in d  # None fields excluded

    def test_to_dict_full(self):
        f = FormField(
            name="Driver_GivenName_A",
            field_type="text",
            tooltip="First name of driver A",
            page=1,
            rect=(100.0, 200.0, 300.0, 220.0),
            category="driver",
            suffix="_A",
            base_name="Driver_GivenName",
        )
        d = f.to_dict()
        assert d["tooltip"] == "First name of driver A"
        assert d["suffix"] == "_A"
        assert d["base_name"] == "Driver_GivenName"
        assert d["rect"] == [100.0, 200.0, 300.0, 220.0]


class TestCategoryInference:
    def test_driver_prefix(self):
        assert _infer_category("Driver_GivenName_A") == "driver"

    def test_vehicle_prefix(self):
        assert _infer_category("Vehicle_VIN_A") == "vehicle"

    def test_policy_prefix(self):
        assert _infer_category("Policy_EffectiveDate_A") == "policy"

    def test_producer_prefix(self):
        assert _infer_category("Producer_FullName_A") == "producer"

    def test_named_insured_prefix(self):
        assert _infer_category("NamedInsured_FullName_A") == "named_insured"

    def test_checkbox_keyword(self):
        assert _infer_category("SomeIndicator") == "checkbox"

    def test_generic_text_form_163(self):
        assert _infer_category("Text15[0]") == "generic_text"

    def test_marital_form_163(self):
        assert _infer_category("maritalstatus1[0]") == "driver"

    def test_unknown_defaults_general(self):
        assert _infer_category("RandomFieldName") == "general"


class TestSuffixExtraction:
    def test_letter_suffix(self):
        suffix, base = _extract_suffix("Driver_GivenName_A")
        assert suffix == "_A"
        assert base == "Driver_GivenName"

    def test_suffix_M(self):
        suffix, base = _extract_suffix("Driver_BirthDate_M")
        assert suffix == "_M"
        assert base == "Driver_BirthDate"

    def test_no_suffix(self):
        suffix, base = _extract_suffix("Form_CompletionDate")
        assert suffix is None
        assert base is None

    def test_numeric_suffix(self):
        suffix, base = _extract_suffix("Location_Area_3")
        assert suffix == "_3"
        assert base == "Location_Area"


class TestFormNumberDetection:
    def test_detect_125(self):
        fields = {
            "NamedInsured_FullName_A",
            "Policy_EffectiveDate_A",
            "LOB_BusinessAutoIndicator",
        }
        assert _detect_form_number(fields) == "125"

    def test_detect_127(self):
        fields = {
            "Driver_GivenName_A",
            "Vehicle_VIN_A",
            "Driver_BirthDate_A",
        }
        assert _detect_form_number(fields) == "127"

    def test_detect_163(self):
        fields = {"Text15[0]", "Text13[0]", "marital[0]"}
        assert _detect_form_number(fields) == "163"

    def test_no_match(self):
        fields = {"RandomField1", "RandomField2"}
        assert _detect_form_number(fields) is None


class TestFormCatalog:
    def test_get_fields_by_category(self):
        catalog = FormCatalog(pdf_path="test.pdf")
        catalog.fields = {
            "f1": FormField(name="f1", field_type="text", category="driver"),
            "f2": FormField(name="f2", field_type="text", category="vehicle"),
            "f3": FormField(name="f3", field_type="text", category="driver"),
        }
        drivers = catalog.get_fields_by_category("driver")
        assert len(drivers) == 2

    def test_get_unmapped_fields(self):
        catalog = FormCatalog(pdf_path="test.pdf")
        catalog.fields = {
            "f1": FormField(name="f1", field_type="text"),
            "f2": FormField(name="f2", field_type="text"),
            "f3": FormField(name="f3", field_type="text"),
        }
        unmapped = catalog.get_unmapped_fields({"f1", "f3"})
        assert len(unmapped) == 1
        assert unmapped[0].name == "f2"


# --- Integration tests (require template PDFs) ---

@pytest.mark.skipif(
    not FORM_TEMPLATES_DIR.exists(),
    reason="Template directory not found",
)
class TestReadTemplates:
    def test_find_template_125(self):
        path = find_template("125")
        assert path is not None
        assert path.exists()

    def test_find_template_nonexistent(self):
        path = find_template("999")
        assert path is None

    def test_read_form_125(self):
        path = find_template("125")
        if path is None:
            pytest.skip("Form 125 template not found")
        catalog = read_pdf_form(path)
        assert catalog.total_fields > 0
        assert len(catalog.sections) > 0
        # Should have a mix of text and checkbox fields
        assert len(catalog.text_fields) > 0
        assert len(catalog.checkbox_fields) > 0

    def test_read_form_127(self):
        path = find_template("127")
        if path is None:
            pytest.skip("Form 127 template not found")
        catalog = read_pdf_form(path)
        assert catalog.total_fields > 0
        # Should detect driver and vehicle categories
        categories = {f.category for f in catalog.fields.values()}
        assert "driver" in categories or "general" in categories

    def test_read_form_137(self):
        path = find_template("137")
        if path is None:
            pytest.skip("Form 137 template not found")
        catalog = read_pdf_form(path)
        assert catalog.total_fields > 0

    def test_read_nonexistent_pdf(self):
        catalog = read_pdf_form(Path("/nonexistent/path.pdf"))
        assert catalog.total_fields == 0
        assert len(catalog.fields) == 0

    def test_read_all_templates(self):
        catalogs = read_all_templates()
        assert len(catalogs) > 0
        for form_num, catalog in catalogs.items():
            assert catalog.total_fields > 0
            assert catalog.form_number == form_num

    def test_tooltips_present(self):
        """At least some fields should have tooltips (from /TU key)."""
        path = find_template("125")
        if path is None:
            pytest.skip("Form 125 template not found")
        catalog = read_pdf_form(path)
        fields_with_tooltips = catalog.get_fields_with_tooltips()
        # We expect a good percentage to have tooltips
        assert len(fields_with_tooltips) > 0
