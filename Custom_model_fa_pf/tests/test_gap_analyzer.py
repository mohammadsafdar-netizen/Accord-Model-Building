"""Tests for the gap analyzer with contextual follow-up questions."""

import pytest
from Custom_model_fa_pf.entity_schema import (
    CustomerSubmission, BusinessInfo, Address, PolicyInfo,
    VehicleInfo, DriverInfo, CoverageRequest,
)
from Custom_model_fa_pf.form_assigner import FormAssignment
from Custom_model_fa_pf.gap_analyzer import analyze, _check_field, _build_contextual_questions


def _make_assignment(lob: str) -> FormAssignment:
    return FormAssignment(form_number="125", purpose="Test", schema_available=True, lobs=[lob])


class TestCheckField:
    def test_simple_field_present(self):
        sub = CustomerSubmission(
            business=BusinessInfo(business_name="Test Corp"),
        )
        assert _check_field(sub, "business.business_name") is True

    def test_simple_field_missing(self):
        sub = CustomerSubmission(business=BusinessInfo())
        assert _check_field(sub, "business.business_name") is False

    def test_list_field_present(self):
        sub = CustomerSubmission(vehicles=[VehicleInfo(vin="ABC123")])
        assert _check_field(sub, "vehicles") is True
        assert _check_field(sub, "vehicles[].vin") is True

    def test_list_field_empty(self):
        sub = CustomerSubmission()
        assert _check_field(sub, "vehicles") is False

    def test_nested_field_missing_parent(self):
        sub = CustomerSubmission()
        assert _check_field(sub, "business.business_name") is False

    def test_address_present(self):
        sub = CustomerSubmission(
            business=BusinessInfo(mailing_address=Address(city="Springfield")),
        )
        assert _check_field(sub, "business.mailing_address") is True


class TestGapAnalyzer:
    def test_complete_submission_high_score(self):
        sub = CustomerSubmission(
            business=BusinessInfo(
                business_name="Test Corp",
                mailing_address=Address(line_one="123 Main St", city="Springfield", state="IL"),
                tax_id="12-345",
                entity_type="corporation",
                operations_description="Trucking",
            ),
            policy=PolicyInfo(effective_date="03/01/2026"),
            vehicles=[VehicleInfo(vin="ABC", year="2024", make="Ford", model="F-350")],
            drivers=[DriverInfo(full_name="John Doe", dob="01/01/1985", license_number="D123", license_state="IL")],
        )
        report = analyze(sub, [_make_assignment("commercial_auto")], {})
        # All critical + all important fields are present → should be 100%
        assert report.completeness_pct == 100.0
        assert len(report.missing_critical) == 0
        assert len(report.missing_important) == 0

    def test_empty_submission_low_score(self):
        sub = CustomerSubmission()
        report = analyze(sub, [_make_assignment("commercial_auto")], {})
        assert report.completeness_pct < 30
        assert len(report.missing_critical) > 0

    def test_follow_up_questions_generated(self):
        sub = CustomerSubmission()
        report = analyze(sub, [_make_assignment("commercial_auto")], {})
        assert len(report.follow_up_questions) > 0

    def test_no_duplicates_in_questions(self):
        sub = CustomerSubmission()
        report = analyze(sub, [_make_assignment("commercial_auto")], {})
        texts = [q.question for q in report.follow_up_questions]
        assert len(texts) == len(set(texts))

    def test_questions_have_priorities(self):
        sub = CustomerSubmission()
        report = analyze(sub, [_make_assignment("commercial_auto")], {})
        priorities = {q.priority for q in report.follow_up_questions}
        # Should have at least critical questions for missing data
        assert "critical" in priorities or "important" in priorities


class TestContextualQuestions:
    def test_grouped_vehicle_question(self):
        missing_imp = [
            "[commercial_auto] vehicles[] > vin",
            "[commercial_auto] vehicles[] > year",
            "[commercial_auto] vehicles[] > make",
            "[commercial_auto] vehicles[] > model",
        ]
        questions = _build_contextual_questions([], missing_imp)
        # Should be grouped into one question about vehicles
        vehicle_qs = [q for q in questions if q.category == "Vehicle Information"]
        assert len(vehicle_qs) >= 1

    def test_individual_fallback(self):
        missing_crit = ["[commercial_auto] business > business name"]
        questions = _build_contextual_questions(missing_crit, [])
        assert len(questions) >= 1
