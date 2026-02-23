"""Tests for confidence scoring and review routing."""

import pytest
from Custom_model_fa_pf.agent.confidence import (
    ConfidenceScorer,
    ConfidenceLevel,
    ReviewRouter,
    ReviewDecision,
)


class TestConfidenceLevel:
    def test_from_score_high(self):
        assert ConfidenceLevel.from_score(0.95) == ConfidenceLevel.HIGH

    def test_from_score_medium(self):
        assert ConfidenceLevel.from_score(0.80) == ConfidenceLevel.MEDIUM

    def test_from_score_low(self):
        assert ConfidenceLevel.from_score(0.55) == ConfidenceLevel.LOW

    def test_from_score_very_low(self):
        assert ConfidenceLevel.from_score(0.30) == ConfidenceLevel.VERY_LOW

    def test_boundary_090(self):
        assert ConfidenceLevel.from_score(0.90) == ConfidenceLevel.HIGH

    def test_boundary_070(self):
        assert ConfidenceLevel.from_score(0.70) == ConfidenceLevel.MEDIUM


class TestConfidenceScorer:
    def setup_method(self):
        self.scorer = ConfidenceScorer()

    def test_user_stated(self):
        score = self.scorer.score("business_name", "Acme LLC", source="user_stated")
        assert score == 0.95

    def test_user_confirmed(self):
        score = self.scorer.score("business_name", "Acme LLC", source="user_confirmed")
        assert score == 1.0

    def test_llm_inferred(self):
        score = self.scorer.score("entity_type", "LLC", source="llm_inferred")
        assert score == 0.60

    def test_validated_boosts(self):
        base = self.scorer.score("vin", "1HGCM82633A004352", source="user_stated")
        boosted = self.scorer.score(
            "vin", "1HGCM82633A004352", source="user_stated", validation_passed=True
        )
        assert boosted > base

    def test_validation_failed_penalizes(self):
        base = self.scorer.score("vin", "BADVIN", source="user_stated")
        penalized = self.scorer.score(
            "vin", "BADVIN", source="user_stated", validation_passed=False
        )
        assert penalized < base

    def test_score_clamped_to_0_1(self):
        score = self.scorer.score("x", "y", source="user_confirmed", validation_passed=True)
        assert 0.0 <= score <= 1.0

    def test_unknown_source_defaults(self):
        score = self.scorer.score("field", "val", source="unknown_source")
        assert 0.0 < score < 1.0


class TestReviewRouter:
    def setup_method(self):
        self.router = ReviewRouter()

    def test_all_high_confidence_auto_accept(self):
        scores = {"name": 0.95, "address": 0.92, "phone": 0.98}
        decision = self.router.route(scores)
        assert decision.action == "auto_process"

    def test_low_critical_field_requires_review(self):
        scores = {"business_name": 0.45, "address": 0.95}
        decision = self.router.route(scores)
        assert decision.action == "human_review_required"
        assert len(decision.flagged_fields) > 0

    def test_low_noncritical_field_optional_review(self):
        scores = {"sic_code": 0.50, "business_name": 0.95}
        decision = self.router.route(scores)
        assert decision.action in ("auto_process", "human_review_optional")

    def test_empty_scores_auto_process(self):
        decision = self.router.route({})
        assert decision.action == "auto_process"
