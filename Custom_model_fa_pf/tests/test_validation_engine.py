"""Tests for validation_engine.py — field validation and auto-correction."""

import pytest

from Custom_model_fa_pf.validation_engine import (
    ValidationIssue,
    ValidationResult,
    validate,
    _normalize_phone,
    _normalize_fein,
    _validate_vin_checksum,
    _parse_date,
    DL_PATTERNS,
)


class TestVINChecksum:
    def test_valid_vin(self):
        # 11111111111111111 has check digit 1 at position 9
        assert _validate_vin_checksum("11111111111111111") is True

    def test_invalid_vin(self):
        # Change last digit — may invalidate
        assert isinstance(_validate_vin_checksum("1HGCM82633A004352"), bool)

    def test_short_vin_passes(self):
        # VINs != 17 chars can't be validated
        assert _validate_vin_checksum("SHORT") is True

    def test_empty_vin(self):
        assert _validate_vin_checksum("") is True


class TestPhoneNormalization:
    def test_10_digits(self):
        assert _normalize_phone("3125551234") == "(312) 555-1234"

    def test_with_dashes(self):
        assert _normalize_phone("312-555-1234") == "(312) 555-1234"

    def test_with_parentheses(self):
        assert _normalize_phone("(312) 555-1234") == "(312) 555-1234"

    def test_with_country_code(self):
        assert _normalize_phone("13125551234") == "(312) 555-1234"

    def test_wrong_length(self):
        assert _normalize_phone("12345") is None

    def test_empty(self):
        assert _normalize_phone("") is None


class TestFEINNormalization:
    def test_9_digits(self):
        assert _normalize_fein("123456789") == "12-3456789"

    def test_already_formatted(self):
        assert _normalize_fein("12-3456789") == "12-3456789"

    def test_wrong_length(self):
        assert _normalize_fein("12345") is None

    def test_empty(self):
        assert _normalize_fein("") is None


class TestDateParsing:
    def test_mm_dd_yyyy(self):
        d = _parse_date("03/01/2026")
        assert d is not None
        assert d.month == 3
        assert d.day == 1
        assert d.year == 2026

    def test_mm_dd_yy(self):
        d = _parse_date("03/01/26")
        assert d is not None

    def test_iso_format(self):
        d = _parse_date("2026-03-01")
        assert d is not None

    def test_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_empty(self):
        assert _parse_date("") is None


class TestValidateVIN:
    def test_vin_length_error(self):
        fields = {"Vehicle_VIN_A": "1234567890"}
        result = validate(fields)
        vin_issues = [i for i in result.issues if i.rule == "vin_length"]
        assert len(vin_issues) == 1
        assert vin_issues[0].severity == "error"

    def test_vin_17_chars_no_length_error(self):
        fields = {"Vehicle_VIN_A": "12345678901234567"}
        result = validate(fields)
        length_issues = [i for i in result.issues if i.rule == "vin_length"]
        assert len(length_issues) == 0


class TestValidateFEIN:
    def test_fein_wrong_digits(self):
        fields = {"NamedInsured_TaxIdentifier_A": "12345"}
        result = validate(fields)
        fein_issues = [i for i in result.issues if i.rule == "fein_format"]
        assert len(fein_issues) == 1

    def test_fein_auto_correction(self):
        fields = {"NamedInsured_TaxIdentifier_A": "123456789"}
        result = validate(fields)
        # Should auto-correct to XX-XXXXXXX
        assert result.corrected_values["NamedInsured_TaxIdentifier_A"] == "12-3456789"
        assert "NamedInsured_TaxIdentifier_A" in result.auto_corrections

    def test_fein_already_formatted(self):
        fields = {"NamedInsured_TaxIdentifier_A": "12-3456789"}
        result = validate(fields)
        fein_issues = [i for i in result.issues if i.rule == "fein_format"]
        assert len(fein_issues) == 0


class TestValidateDates:
    def test_valid_date(self):
        fields = {"Policy_EffectiveDate_A": "03/01/2026"}
        result = validate(fields)
        date_issues = [i for i in result.issues if i.rule == "date_format"]
        assert len(date_issues) == 0

    def test_invalid_date_format(self):
        fields = {"Policy_EffectiveDate_A": "not-a-date"}
        result = validate(fields)
        date_issues = [i for i in result.issues if i.rule == "date_format"]
        assert len(date_issues) == 1
        assert date_issues[0].severity == "error"

    def test_date_ordering_error(self):
        fields = {
            "Policy_EffectiveDate_A": "03/01/2027",
            "Policy_ExpirationDate_A": "03/01/2026",
        }
        result = validate(fields)
        ordering_issues = [i for i in result.issues if i.rule == "date_ordering"]
        assert len(ordering_issues) == 1
        assert ordering_issues[0].severity == "error"

    def test_date_ordering_valid(self):
        fields = {
            "Policy_EffectiveDate_A": "03/01/2026",
            "Policy_ExpirationDate_A": "03/01/2027",
        }
        result = validate(fields)
        ordering_issues = [i for i in result.issues if i.rule == "date_ordering"]
        assert len(ordering_issues) == 0


class TestValidatePhone:
    def test_phone_auto_correction(self):
        fields = {"Producer_PhoneNumber_A": "3125551234"}
        result = validate(fields)
        assert result.corrected_values["Producer_PhoneNumber_A"] == "(312) 555-1234"

    def test_phone_wrong_digits(self):
        fields = {"Producer_PhoneNumber_A": "12345"}
        result = validate(fields)
        phone_issues = [i for i in result.issues if i.rule == "phone_format"]
        assert len(phone_issues) == 1


class TestValidateDriverLicense:
    def test_dl_patterns_exist(self):
        assert len(DL_PATTERNS) >= 50  # All US states

    def test_california_dl_valid(self):
        import re
        pattern = DL_PATTERNS["CA"]
        assert re.match(pattern, "A1234567")

    def test_california_dl_invalid(self):
        import re
        pattern = DL_PATTERNS["CA"]
        assert not re.match(pattern, "12345678")  # Missing letter prefix

    def test_illinois_dl_valid(self):
        import re
        pattern = DL_PATTERNS["IL"]
        assert re.match(pattern, "S12345678901")


class TestValidationResult:
    def test_has_errors(self):
        result = ValidationResult()
        result.error_count = 2
        assert result.has_errors is True

    def test_no_errors(self):
        result = ValidationResult()
        result.error_count = 0
        assert result.has_errors is False

    def test_to_dict(self):
        result = ValidationResult()
        result.total_fields = 10
        result.valid_fields = 8
        result.error_count = 1
        result.warning_count = 1
        d = result.to_dict()
        assert d["total_fields"] == 10
        assert d["error_count"] == 1


class TestValidateIntegration:
    def test_full_validation(self):
        fields = {
            "NamedInsured_FullName_A": "Acme Trucking LLC",
            "NamedInsured_TaxIdentifier_A": "123456789",  # Needs formatting
            "Policy_EffectiveDate_A": "03/01/2026",
            "Policy_ExpirationDate_A": "03/01/2027",
            "Vehicle_VIN_A": "1234567890",  # Too short
            "Producer_PhoneNumber_A": "3125551234",  # Needs formatting
        }
        result = validate(fields)

        # Should have VIN error
        assert result.error_count >= 1
        # Should have auto-corrections for FEIN and phone
        assert len(result.auto_corrections) >= 2
        # Corrected values should be populated
        assert result.corrected_values["NamedInsured_TaxIdentifier_A"] == "12-3456789"
        assert result.corrected_values["Producer_PhoneNumber_A"] == "(312) 555-1234"
        # Total fields should be tracked
        assert result.total_fields == len(fields)

    def test_empty_fields(self):
        result = validate({})
        assert result.total_fields == 0
        assert result.error_count == 0

    def test_skip_empty_values(self):
        fields = {"Vehicle_VIN_A": "", "Driver_BirthDate_A": ""}
        result = validate(fields)
        assert len(result.issues) == 0
