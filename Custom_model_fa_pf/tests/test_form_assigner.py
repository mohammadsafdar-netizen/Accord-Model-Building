"""Unit tests for form_assigner — pure logic, no LLM needed."""

import pytest
from Custom_model_fa_pf.lob_classifier import LOBClassification
from Custom_model_fa_pf.form_assigner import assign


def _make_classification(lob_id: str, confidence: float = 0.95) -> LOBClassification:
    return LOBClassification(lob_id=lob_id, confidence=confidence, reasoning="test")


class TestFormAssigner:
    def test_commercial_auto_assigns_three_forms(self):
        lobs = [_make_classification("commercial_auto")]
        assignments = assign(lobs)
        form_nums = [a.form_number for a in assignments]
        assert "125" in form_nums
        assert "127" in form_nums
        assert "137" in form_nums
        assert len(assignments) == 3

    def test_commercial_umbrella_assigns_two_forms(self):
        lobs = [_make_classification("commercial_umbrella")]
        assignments = assign(lobs)
        form_nums = [a.form_number for a in assignments]
        assert "125" in form_nums
        assert "163" in form_nums
        assert len(assignments) == 2

    def test_multi_lob_deduplicates_form_125(self):
        lobs = [
            _make_classification("commercial_auto"),
            _make_classification("commercial_umbrella"),
        ]
        assignments = assign(lobs)
        form_nums = [a.form_number for a in assignments]
        # Form 125 should appear exactly once
        assert form_nums.count("125") == 1
        # Should have 125, 127, 137, 163
        assert set(form_nums) == {"125", "127", "137", "163"}

    def test_form_125_appears_first(self):
        lobs = [_make_classification("commercial_auto")]
        assignments = assign(lobs)
        assert assignments[0].form_number == "125"

    def test_schema_availability(self):
        lobs = [_make_classification("general_liability")]
        assignments = assign(lobs)
        for a in assignments:
            if a.form_number == "125":
                assert a.schema_available is True
            elif a.form_number == "126":
                assert a.schema_available is False  # No schema for 126

    def test_lobs_tracked_per_form(self):
        lobs = [
            _make_classification("commercial_auto"),
            _make_classification("commercial_umbrella"),
        ]
        assignments = assign(lobs)
        form_125 = next(a for a in assignments if a.form_number == "125")
        assert "commercial_auto" in form_125.lobs
        assert "commercial_umbrella" in form_125.lobs

    def test_empty_classifications(self):
        assignments = assign([])
        assert assignments == []

    def test_unknown_lob_ignored(self):
        lobs = [_make_classification("unknown_lob")]
        assignments = assign(lobs)
        assert assignments == []

    def test_workers_comp_assigns_forms(self):
        lobs = [_make_classification("workers_compensation")]
        assignments = assign(lobs)
        form_nums = [a.form_number for a in assignments]
        assert "125" in form_nums
        assert "130" in form_nums

    def test_to_dict(self):
        lobs = [_make_classification("commercial_auto")]
        assignments = assign(lobs)
        d = assignments[0].to_dict()
        assert "form_number" in d
        assert "purpose" in d
        assert "schema_available" in d
        assert "lobs" in d
