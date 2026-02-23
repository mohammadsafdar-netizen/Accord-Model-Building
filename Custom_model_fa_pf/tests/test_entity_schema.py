"""Tests for entity schema — new dataclasses and serialization."""

import pytest
from Custom_model_fa_pf.entity_schema import (
    CustomerSubmission, BusinessInfo, Address, VehicleInfo,
    DriverInfo, CoverageRequest, AdditionalInterest,
    PriorInsurance, CyberInfo, _normalize_entity_type,
)


class TestAdditionalInterest:
    def test_from_dict(self):
        data = {
            "name": "First National Bank",
            "address": {"line_one": "100 Finance Blvd", "city": "Chicago", "state": "IL"},
            "interest_type": "lienholder",
            "account_number": "LOAN-123",
            "certificate_required": True,
        }
        ai = AdditionalInterest.from_dict(data)
        assert ai.name == "First National Bank"
        assert ai.address.city == "Chicago"
        assert ai.interest_type == "lienholder"
        assert ai.certificate_required is True

    def test_to_dict(self):
        ai = AdditionalInterest(name="Test Bank", interest_type="mortgagee")
        d = ai.to_dict()
        assert d["name"] == "Test Bank"
        assert "address" not in d  # None excluded

    def test_from_dict_none(self):
        assert AdditionalInterest.from_dict(None) is None


class TestPriorInsurance:
    def test_from_dict(self):
        data = {
            "carrier_name": "State Farm",
            "policy_number": "SF-123",
            "effective_date": "01/01/2025",
            "premium": "5000",
        }
        pi = PriorInsurance.from_dict(data)
        assert pi.carrier_name == "State Farm"
        assert pi.premium == "5000"

    def test_to_dict(self):
        pi = PriorInsurance(carrier_name="GEICO", premium="3000")
        d = pi.to_dict()
        assert d["carrier_name"] == "GEICO"
        assert "policy_number" not in d


class TestCyberInfo:
    def test_from_dict(self):
        data = {
            "annual_revenue": "5000000",
            "records_count": "50000",
            "has_mfa": True,
            "data_types": ["PII", "PHI"],
        }
        ci = CyberInfo.from_dict(data)
        assert ci.records_count == "50000"
        assert ci.has_mfa is True
        assert "PHI" in ci.data_types

    def test_to_dict(self):
        ci = CyberInfo(annual_revenue="1000000", has_encryption=True)
        d = ci.to_dict()
        assert d["annual_revenue"] == "1000000"
        assert d["has_encryption"] is True
        assert "data_types" not in d  # Empty list excluded


class TestCustomerSubmissionExpanded:
    def test_from_llm_json_with_new_fields(self):
        data = {
            "business": {"business_name": "Test Corp"},
            "additional_interests": [
                {"name": "Bank A", "interest_type": "lienholder"},
            ],
            "prior_insurance": [
                {"carrier_name": "Old Insurer", "premium": "4000"},
            ],
            "cyber_info": {
                "annual_revenue": "2000000",
                "has_mfa": True,
            },
        }
        sub = CustomerSubmission.from_llm_json(data)
        assert len(sub.additional_interests) == 1
        assert sub.additional_interests[0].name == "Bank A"
        assert len(sub.prior_insurance) == 1
        assert sub.prior_insurance[0].carrier_name == "Old Insurer"
        assert sub.cyber_info.has_mfa is True

    def test_from_llm_json_null_new_fields(self):
        data = {
            "business": {"business_name": "Test"},
            "additional_interests": None,
            "prior_insurance": None,
            "cyber_info": None,
        }
        sub = CustomerSubmission.from_llm_json(data)
        assert sub.additional_interests == []
        assert sub.prior_insurance == []
        assert sub.cyber_info is None

    def test_to_dict_includes_new_fields(self):
        sub = CustomerSubmission(
            business=BusinessInfo(business_name="Test"),
            additional_interests=[AdditionalInterest(name="Bank")],
            prior_insurance=[PriorInsurance(carrier_name="Insurer")],
            cyber_info=CyberInfo(annual_revenue="1000000"),
        )
        d = sub.to_dict()
        assert "additional_interests" in d
        assert "prior_insurance" in d
        assert "cyber_info" in d


class TestEntityTypeNormalization:
    def test_corp_normalized(self):
        assert _normalize_entity_type("Corp") == "corporation"

    def test_llc_normalized(self):
        assert _normalize_entity_type("LLC") == "llc"

    def test_s_corp_normalized(self):
        assert _normalize_entity_type("S Corporation") == "subchapter_s"

    def test_none_returns_none(self):
        assert _normalize_entity_type(None) is None

    def test_empty_returns_none(self):
        assert _normalize_entity_type("") is None
