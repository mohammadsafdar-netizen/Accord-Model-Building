import pytest
from src.tools.doc_intel import (
    perform_ocr,
    extract_form_fields,
    detect_form_type
)

def test_perform_ocr():
    txt, conf = perform_ocr("img.png")
    assert "Extracted text" in txt

def test_extraction():
    data, conf = extract_form_fields("img", "125")
    assert data["insured_name"] == "John Doe from OCR"
    assert conf["insured_name"] > 0.9

def test_detection():
    type_, ver, conf = detect_form_type("form_125_scan.pdf")
    assert type_ == "125"
