"""Tests for LOB rules — BOP and Cyber additions."""

import pytest
from Custom_model_fa_pf.lob_rules import LOB_DEFINITIONS, LOB_KEYWORDS, REQUIRED_FIELDS_BY_LOB
from Custom_model_fa_pf.lob_classifier import LOBClassification
from Custom_model_fa_pf.form_assigner import assign


class TestLOBDefinitions:
    def test_seven_lobs_defined(self):
        assert len(LOB_DEFINITIONS) == 7

    def test_bop_defined(self):
        bop = LOB_DEFINITIONS["bop"]
        assert bop.display_name == "Business Owners Policy (BOP)"
        assert "125" in bop.forms
        assert bop.lob_checkbox_125 is not None

    def test_cyber_defined(self):
        cyber = LOB_DEFINITIONS["cyber"]
        assert cyber.display_name == "Cyber & Privacy Liability"
        assert "125" in cyber.forms
        assert cyber.lob_checkbox_125 is not None

    def test_bop_requires_locations(self):
        assert "locations" in LOB_DEFINITIONS["bop"].required_entity_types


class TestLOBKeywords:
    def test_bop_keywords(self):
        assert "bop" in [k.lower() for k in LOB_KEYWORDS["bop"]]
        assert "business owner" in [k.lower() for k in LOB_KEYWORDS["bop"]]

    def test_cyber_keywords(self):
        assert "cyber" in LOB_KEYWORDS["cyber"]
        assert "data breach" in LOB_KEYWORDS["cyber"]
        assert "ransomware" in LOB_KEYWORDS["cyber"]


class TestRequiredFields:
    def test_bop_has_required_fields(self):
        assert "bop" in REQUIRED_FIELDS_BY_LOB
        bop_reqs = REQUIRED_FIELDS_BY_LOB["bop"]
        assert "locations" in bop_reqs["critical"]

    def test_cyber_has_required_fields(self):
        assert "cyber" in REQUIRED_FIELDS_BY_LOB
        cyber_reqs = REQUIRED_FIELDS_BY_LOB["cyber"]
        assert "business.business_name" in cyber_reqs["critical"]


class TestFormAssignment:
    def test_bop_assigns_form_125(self):
        classifications = [LOBClassification(lob_id="bop", confidence=0.9, reasoning="BOP")]
        result = assign(classifications)
        form_nums = [a.form_number for a in result]
        assert "125" in form_nums

    def test_cyber_assigns_form_125(self):
        classifications = [LOBClassification(lob_id="cyber", confidence=0.85, reasoning="Cyber")]
        result = assign(classifications)
        form_nums = [a.form_number for a in result]
        assert "125" in form_nums

    def test_bop_cyber_deduplicates_125(self):
        classifications = [
            LOBClassification(lob_id="bop", confidence=0.9, reasoning="BOP"),
            LOBClassification(lob_id="cyber", confidence=0.85, reasoning="Cyber"),
        ]
        result = assign(classifications)
        form_nums = [a.form_number for a in result]
        assert form_nums.count("125") == 1  # Deduplicated
        # Both LOBs should be tracked on Form 125
        f125 = [a for a in result if a.form_number == "125"][0]
        assert "bop" in f125.lobs
        assert "cyber" in f125.lobs
