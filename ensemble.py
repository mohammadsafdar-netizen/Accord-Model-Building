#!/usr/bin/env python3
"""
Ensemble Fusion: Multi-source confidence-weighted field merging
================================================================
Combines extraction results from multiple sources (spatial, template,
semantic, label_value, vision, text_llm, gap_fill) using confidence
scoring and agreement voting.

When 2+ sources agree on a value, confidence is boosted.
When sources disagree, the highest-confidence source wins.

Usage:
    from ensemble import EnsembleFusion
    fusion = EnsembleFusion()
    fusion.add_results("spatial", spatial_fields, confidence=0.95)
    fusion.add_results("text_llm", llm_fields, confidence=0.65)
    final_fields, metadata = fusion.fuse()
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Default confidence weights per source (higher = more trusted)
SOURCE_CONFIDENCE = {
    "acroform": 0.99,   # Direct PDF form field data (highest confidence)
    "spatial": 0.95,
    "template": 0.90,
    "semantic": 0.80,
    "label_value": 0.75,
    "vision": 0.70,
    "text_llm": 0.65,
    "gap_fill": 0.50,
}

# Boost when 2+ sources agree on the same value
AGREEMENT_BOOST = 0.10


@dataclass
class SourceResult:
    """A single field value from one source."""
    value: Any
    confidence: float
    source: str


@dataclass
class FieldFusion:
    """Fusion result for one field."""
    final_value: Any
    confidence: float
    winning_source: str
    agreement_count: int
    all_sources: List[SourceResult] = field(default_factory=list)


def _normalize_for_comparison(value: Any) -> str:
    """Normalize a value for agreement comparison."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s)
    # Remove common formatting
    s = s.replace(",", "").replace("$", "").replace("-", "")
    return s


class EnsembleFusion:
    """
    Multi-source confidence-weighted fusion engine.

    Accumulates results from multiple extraction sources, then fuses
    them using confidence scoring and agreement voting.
    """

    def __init__(self, source_confidence: Optional[Dict[str, float]] = None):
        """
        Args:
            source_confidence: Override default confidence weights per source.
        """
        self.weights = dict(SOURCE_CONFIDENCE)
        if source_confidence:
            self.weights.update(source_confidence)

        # field_name -> list of SourceResult
        self._results: Dict[str, List[SourceResult]] = {}

    def add_results(
        self,
        source: str,
        fields: Dict[str, Any],
        confidence: Optional[float] = None,
    ) -> None:
        """
        Add extraction results from one source.

        Args:
            source: Source name (e.g., "spatial", "text_llm", "vision").
            fields: Dict of {field_name: value}.
            confidence: Override confidence for this source (default: from SOURCE_CONFIDENCE).
        """
        conf = confidence if confidence is not None else self.weights.get(source, 0.5)

        for field_name, value in fields.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                continue

            sr = SourceResult(value=value, confidence=conf, source=source)

            if field_name not in self._results:
                self._results[field_name] = []
            self._results[field_name].append(sr)

    def fuse(self) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Fuse all accumulated results into final fields.

        Returns:
            (final_fields, metadata) where:
            - final_fields: {field_name: value}
            - metadata: {field_name: {confidence, source, agreement_count, all_sources}}
        """
        final_fields: Dict[str, Any] = {}
        metadata: Dict[str, Dict[str, Any]] = {}

        for field_name, source_results in self._results.items():
            if not source_results:
                continue

            fusion = self._fuse_field(field_name, source_results)
            final_fields[field_name] = fusion.final_value
            metadata[field_name] = {
                "confidence": round(fusion.confidence, 3),
                "source": fusion.winning_source,
                "agreement_count": fusion.agreement_count,
                "all_sources": [
                    {"source": sr.source, "value": str(sr.value), "confidence": sr.confidence}
                    for sr in fusion.all_sources
                ],
            }

        return final_fields, metadata

    def _fuse_field(
        self, field_name: str, source_results: List[SourceResult]
    ) -> FieldFusion:
        """Fuse results for a single field."""
        if len(source_results) == 1:
            sr = source_results[0]
            return FieldFusion(
                final_value=sr.value,
                confidence=sr.confidence,
                winning_source=sr.source,
                agreement_count=1,
                all_sources=source_results,
            )

        # Group by normalized value to find agreements
        value_groups: Dict[str, List[SourceResult]] = {}
        for sr in source_results:
            norm = _normalize_for_comparison(sr.value)
            if norm not in value_groups:
                value_groups[norm] = []
            value_groups[norm].append(sr)

        # Find the group with highest combined confidence
        best_group_key = None
        best_group_score = -1.0
        for norm_val, group in value_groups.items():
            # Score = max confidence in group + agreement boost per additional source
            max_conf = max(sr.confidence for sr in group)
            agreement_bonus = AGREEMENT_BOOST * (len(group) - 1)
            group_score = min(1.0, max_conf + agreement_bonus)
            if group_score > best_group_score:
                best_group_score = group_score
                best_group_key = norm_val

        winning_group = value_groups[best_group_key]
        # Use the value from the highest-confidence source in the winning group
        best_sr = max(winning_group, key=lambda sr: sr.confidence)
        agreement_count = len(winning_group)

        return FieldFusion(
            final_value=best_sr.value,
            confidence=min(1.0, best_group_score),
            winning_source=best_sr.source,
            agreement_count=agreement_count,
            all_sources=source_results,
        )

    def get_low_confidence_fields(
        self, threshold: float = 0.60
    ) -> List[Tuple[str, float]]:
        """
        Get fields with confidence below threshold (candidates for re-extraction).

        Returns:
            List of (field_name, confidence) tuples.
        """
        _, metadata = self.fuse()
        low = []
        for field_name, meta in metadata.items():
            if meta["confidence"] < threshold:
                low.append((field_name, meta["confidence"]))
        return sorted(low, key=lambda t: t[1])

    def get_disagreements(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get fields where sources disagree (different values from different sources).

        Returns:
            {field_name: [{source, value, confidence}, ...]} for disagreeing fields.
        """
        disagreements: Dict[str, List[Dict[str, Any]]] = {}

        for field_name, source_results in self._results.items():
            if len(source_results) < 2:
                continue

            # Check if values differ
            normalized_values = set(
                _normalize_for_comparison(sr.value) for sr in source_results
            )
            if len(normalized_values) > 1:
                disagreements[field_name] = [
                    {"source": sr.source, "value": str(sr.value), "confidence": sr.confidence}
                    for sr in source_results
                ]

        return disagreements
