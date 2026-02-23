"""Tests for the multi-source input parser."""

import pytest
from Custom_model_fa_pf.input_parser import parse, _normalize_text


class TestEmailParsing:
    def test_structured_email(self):
        email = """From: John Smith <john@company.com>
To: agent@insurance.com
Subject: Quote Request - Commercial Auto
Date: 02/23/2026

Hi, I need commercial auto insurance for my trucking company.
We have 3 trucks and 5 drivers.
"""
        msg = parse(email)
        assert msg.source_type == "email"
        assert msg.sender_name == "John Smith"
        assert msg.sender_email == "john@company.com"
        assert msg.subject == "Quote Request - Commercial Auto"
        assert "3 trucks" in msg.text
        assert "5 drivers" in msg.text

    def test_email_without_angle_brackets(self):
        email = """From: john@company.com
Subject: Insurance Quote

Need coverage for my business.
"""
        msg = parse(email)
        assert msg.source_type == "email"
        assert msg.sender_email == "john@company.com"

    def test_email_preserves_body(self):
        email = """From: Agent <agent@ins.com>
Subject: Fleet Insurance

We need coverage for:
- 2024 Ford F-350, VIN: 1HGCM82633A004352
- 2023 Chevy Silverado, VIN: 2GCUDDED0N1234567
"""
        msg = parse(email)
        assert "1HGCM82633A004352" in msg.text
        assert "2GCUDDED0N1234567" in msg.text


class TestChatParsing:
    def test_chat_message(self):
        chat = """Chat transcript
John Smith says: I need insurance for my business.
We're a trucking company in Springfield, IL.
"""
        msg = parse(chat)
        assert msg.source_type == "chat"
        assert "trucking company" in msg.text

    def test_chat_with_wrote_pattern(self):
        chat = """Customer wrote: Need a quote for commercial auto.
3 vehicles, 2 mil liability limit.
"""
        msg = parse(chat)
        assert msg.source_type == "chat"
        assert "2000000" in msg.text  # normalized


class TestRawTextParsing:
    def test_simple_raw_text(self):
        msg = parse("I need commercial auto insurance for my fleet of 5 trucks.")
        assert msg.source_type == "raw"
        assert "5 trucks" in msg.text

    def test_preserves_content(self):
        text = "Business: ABC Trucking LLC\nAddress: 123 Main St, Springfield, IL 62701"
        msg = parse(text)
        assert "ABC Trucking LLC" in msg.text
        assert "123 Main St" in msg.text


class TestTextNormalization:
    def test_million_shorthand(self):
        assert "1000000" in _normalize_text("I want 1 mil coverage")
        assert "2000000" in _normalize_text("2mil liability")

    def test_k_shorthand(self):
        assert "500000" in _normalize_text("deductible of 500k")
        assert "100000" in _normalize_text("100k limit")

    def test_excessive_whitespace_cleaned(self):
        text = "line one\n\n\n\nline two"
        result = _normalize_text(text)
        assert "\n\n\n" not in result

    def test_double_spaces_cleaned(self):
        text = "too  many   spaces"
        result = _normalize_text(text)
        assert "  " not in result

    def test_normal_text_unchanged(self):
        text = "Normal business insurance request."
        assert _normalize_text(text) == text
