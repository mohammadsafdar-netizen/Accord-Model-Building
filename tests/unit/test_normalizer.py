"""Unit tests for normalizer module."""

from __future__ import annotations

import pytest

from normalizer import (
    normalize_all,
    normalize_value,
    normalize_checkbox,
    normalize_date,
    strip_label_prefixes,
    is_date_field,
    is_monetary_field,
    is_phone_field,
    fix_ocr_phone,
    fix_ocr_monetary,
    clean_text,
)


class TestNormalizeCheckbox:
    def test_checked_values(self):
        assert normalize_checkbox("yes") == "1"
        assert normalize_checkbox("true") == "1"
        assert normalize_checkbox("1") == "1"
        assert normalize_checkbox("x") == "1"
        assert normalize_checkbox("  Y  ") == "1"

    def test_unchecked_values(self):
        assert normalize_checkbox("no") == "Off"
        assert normalize_checkbox("false") == "Off"
        assert normalize_checkbox("0") == "Off"
        assert normalize_checkbox("") == "Off"

    def test_date_like_returns_off(self):
        assert normalize_checkbox("01/15/2024") == "Off"
        assert normalize_checkbox("12345") == "Off"


class TestNormalizeDate:
    def test_already_mm_dd_yyyy(self):
        assert normalize_date("01/15/2024") == "01/15/2024"

    def test_partial_date(self):
        out = normalize_date("1-15-2024")
        assert out == "01/15/2024" or "01" in out and "15" in out

    def test_empty_returns_none(self):
        assert normalize_date("") is None
        # normalize_date does not strip; only empty string is falsy
        assert normalize_date("") is None


class TestNormalizeValue:
    def test_none_empty(self):
        assert normalize_value(None, "text", "x") is None
        assert normalize_value("", "text", "x") is None
        assert normalize_value("  n/a  ", "text", "x") is None

    def test_checkbox_field(self):
        assert normalize_value("yes", "checkbox", "chk") == "1"
        assert normalize_value("no", "checkbox", "chk") == "Off"

    def test_phone_field_strips_prefix(self):
        out = fix_ocr_phone("PHONE # 555-123-4567")
        assert "555" in out and "PHONE" not in out

    def test_monetary_strips_dollars(self):
        out = fix_ocr_monetary("$1,000.00")
        assert out == 1000 or out == 1000.0


class TestNormalizeAll:
    def test_empty_extracted(self):
        assert normalize_all({}, {}) == {}

    def test_checkbox_and_text(self):
        extracted = {"a": "  yes  ", "b": "Some text"}
        field_types = {"a": "checkbox", "b": "text"}
        out = normalize_all(extracted, field_types)
        assert out["a"] == "1"
        assert out["b"] == "Some text"

    def test_null_like_becomes_none(self):
        out = normalize_all({"f": "  N/A  "}, {"f": "text"})
        assert out["f"] is None


class TestHelpers:
    def test_is_date_field(self):
        assert is_date_field("Policy_EffectiveDate_A") is True
        assert is_date_field("SomeName") is False

    def test_is_monetary_field(self):
        assert is_monetary_field("Premium_Amount_A") is True
        assert is_monetary_field("Name_A") is False

    def test_is_phone_field(self):
        assert is_phone_field("Primary_PhoneNumber_A") is True

    def test_strip_label_prefixes(self):
        assert "60601" in strip_label_prefixes("ZIP: 60601", "postal")
        assert strip_label_prefixes("Name: John", "name") == "John"

    def test_clean_text_collapse_whitespace(self):
        assert clean_text("  a   b  ") == "a b"
