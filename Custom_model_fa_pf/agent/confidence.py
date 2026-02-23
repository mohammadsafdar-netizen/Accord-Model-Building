"""Confidence scoring and human review routing for intake fields."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConfidenceLevel(str, Enum):
    HIGH = "high"          # >= 0.90
    MEDIUM = "medium"      # 0.70 - 0.89
    LOW = "low"            # 0.50 - 0.69
    VERY_LOW = "very_low"  # < 0.50

    @staticmethod
    def from_score(score: float) -> "ConfidenceLevel":
        if score >= 0.90:
            return ConfidenceLevel.HIGH
        elif score >= 0.70:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.50:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW


# Fields that MUST be correct — flag for review if low confidence.
CRITICAL_FIELDS = {
    "business_name", "business.business_name",
    "policy.effective_date", "policy.expiration_date",
    "vehicles[].vin", "vin",
    "tax_id", "business.tax_id", "fein",
    "drivers[].license_number", "license_number",
    "coverage.liability_limit",
}


class ConfidenceScorer:
    """Score field values based on source, validation, and patterns."""

    SOURCE_WEIGHTS = {
        "user_stated": 0.95,
        "user_confirmed": 1.00,
        "llm_inferred": 0.60,
        "validated_external": 0.98,
        "defaulted": 0.50,
        "ocr_extracted": 0.80,
    }
    DEFAULT_WEIGHT = 0.50

    def score(
        self,
        field_name: str,
        value: str,
        source: str = "user_stated",
        validation_passed: Optional[bool] = None,
    ) -> float:
        """Compute confidence score for a field value."""
        base = self.SOURCE_WEIGHTS.get(source, self.DEFAULT_WEIGHT)

        if validation_passed is True:
            base = min(base + 0.10, 1.0)
        elif validation_passed is False:
            base = max(base - 0.30, 0.10)

        return round(min(max(base, 0.0), 1.0), 2)


@dataclass
class ReviewDecision:
    action: str  # "auto_process", "human_review_required", "human_review_optional"
    flagged_fields: list = field(default_factory=list)
    message: str = ""


class ReviewRouter:
    """Route forms to auto-processing or human review based on confidence."""

    def __init__(
        self,
        auto_threshold: float = 0.90,
        review_threshold: float = 0.70,
    ):
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold

    def route(self, confidence_scores: dict) -> ReviewDecision:
        if not confidence_scores:
            return ReviewDecision(action="auto_process", message="No fields to review")

        flagged = []
        for field_name, score in confidence_scores.items():
            if score < self.review_threshold:
                flagged.append({"field": field_name, "confidence": score})

        if not flagged:
            return ReviewDecision(action="auto_process", message="All fields above threshold")

        critical_flags = [
            f for f in flagged
            if any(c in f["field"] for c in CRITICAL_FIELDS)
        ]

        if critical_flags:
            return ReviewDecision(
                action="human_review_required",
                flagged_fields=flagged,
                message=f"{len(critical_flags)} critical fields need review",
            )

        return ReviewDecision(
            action="human_review_optional",
            flagged_fields=flagged,
            message=f"{len(flagged)} non-critical fields flagged",
        )
