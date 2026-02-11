import pytest
from src.tools.form_population import (
    fill_pdf_form_field,
    read_pdf_form_fields,
    get_form_template,
    auto_fill_common_fields_all_forms,
    MOCK_FILE_SYSTEM
)

def setup_function():
    MOCK_FILE_SYSTEM.clear()

def test_fill_and_read():
    path = "form1.pdf"
    assert fill_pdf_form_field(path, "name", "John") is True
    
    data = read_pdf_form_fields(path)
    assert data["name"] == "John"

def test_get_template():
    assert "acord_125.pdf" in get_form_template("125")

def test_auto_fill_all():
    forms = ["f1.pdf", "f2.pdf"]
    data = {"name": "Safdar"}
    results = auto_fill_common_fields_all_forms(data, forms)
    
    assert results["f1.pdf"] is True
    assert read_pdf_form_fields("f1.pdf")["name"] == "Safdar"
    assert read_pdf_form_fields("f2.pdf")["name"] == "Safdar"
