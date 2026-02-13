#!/usr/bin/env python3
"""
Semantic Field Matcher: MiniLM embedding-based label matching
==============================================================
Uses sentence-transformers/all-MiniLM-L6-v2 (80MB, CPU) to match
OCR-extracted labels to schema field names via cosine similarity.

Solves: "AGENCY" failing to match "Producer_FullName_A" because
substring matching misses semantic equivalents.

Usage:
    from semantic_matcher import SemanticFieldMatcher
    matcher = SemanticFieldMatcher(schema)
    field_name, score = matcher.match("AGENCY")
    results = matcher.batch_match(["AGENCY", "CARRIER", "NAIC CODE"])
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


# Default cosine similarity threshold for accepting a match
DEFAULT_THRESHOLD = 0.65

# Common ACORD label aliases that help embedding matching
LABEL_ALIASES = {
    "agency": "insurance agency producer broker",
    "carrier": "insurance carrier insurer company",
    "naic code": "NAIC identification code insurer",
    "naic": "NAIC identification code",
    "named insured": "named insured applicant customer",
    "producer": "producer agent agency broker",
    "policy number": "policy number identifier",
    "effective date": "policy effective date start date",
    "expiration date": "policy expiration date end date",
    "date": "form completion date",
    "phone": "phone number telephone",
    "fax": "fax number facsimile",
    "email": "email address electronic mail",
    "address": "mailing address street",
    "city": "city name municipality",
    "state": "state province code",
    "zip": "zip code postal code",
    "premium": "premium amount dollar",
    "deductible": "deductible amount",
    "limit": "coverage limit amount",
    "driver": "driver operator person",
    "vehicle": "vehicle automobile car",
    "vin": "vehicle identification number VIN",
    "dob": "date of birth birthday",
    "license": "driver license number",
    "marital": "marital status married single",
    "sex": "sex gender male female",
    "underwriter": "underwriter person name",
}


class SemanticFieldMatcher:
    """
    Matches OCR-extracted labels to schema field names using MiniLM embeddings.

    Pre-computes embeddings for all schema fields (name + tooltip) at init time,
    then matches incoming labels via cosine similarity.
    """

    def __init__(
        self,
        schema: Any,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = DEFAULT_THRESHOLD,
        device: str = "cpu",
    ):
        """
        Args:
            schema: FormSchema with .fields dict of {name: FieldInfo}.
            model_name: HuggingFace sentence-transformers model.
            threshold: Minimum cosine similarity for a match.
            device: "cpu" or "cuda".
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for semantic matching. "
                "Install with: pip install sentence-transformers"
            )

        self.threshold = threshold
        self.schema = schema
        self.field_names: List[str] = []
        self.field_descriptions: List[str] = []

        # Build field descriptions for embedding
        for name, fi in schema.fields.items():
            self.field_names.append(name)
            # Combine: human-readable name + tooltip for richer semantic signal
            readable = self._field_name_to_readable(name)
            tooltip = getattr(fi, "tooltip", "") or ""
            desc = f"{readable}. {tooltip}".strip()
            self.field_descriptions.append(desc)

        # Load model and pre-compute field embeddings
        self._model = SentenceTransformer(model_name, device=device)
        self._field_embeddings = self._model.encode(
            self.field_descriptions,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # Cache for repeated labels
        self._cache: Dict[str, Tuple[Optional[str], float]] = {}

    @staticmethod
    def _field_name_to_readable(name: str) -> str:
        """Convert schema field name to readable text.

        E.g. "Producer_FullName_A" -> "producer full name"
        """
        # Remove suffix (_A, _B, etc.)
        clean = re.sub(r"_[A-Z]$", "", name)
        # Split on underscores and camelCase
        parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", clean)
        parts = parts.replace("_", " ")
        return parts.lower().strip()

    def _enrich_label(self, label: str) -> str:
        """Enrich a label with known aliases for better matching."""
        label_lower = label.strip().lower()
        alias = LABEL_ALIASES.get(label_lower, "")
        if alias:
            return f"{label} {alias}"
        return label

    def match(self, label: str) -> Tuple[Optional[str], float]:
        """
        Match a single label to the best schema field.

        Args:
            label: OCR-extracted label text.

        Returns:
            (field_name, score) or (None, 0.0) if no match above threshold.
        """
        if not label or not label.strip():
            return None, 0.0

        cache_key = label.strip().lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        enriched = self._enrich_label(label)
        label_embedding = self._model.encode(
            [enriched],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # Cosine similarity (embeddings are already normalized)
        similarities = np.dot(self._field_embeddings, label_embedding.T).flatten()
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        if best_score >= self.threshold:
            result = (self.field_names[best_idx], best_score)
        else:
            result = (None, best_score)

        self._cache[cache_key] = result
        return result

    def batch_match(
        self, labels: List[str]
    ) -> List[Tuple[str, Optional[str], float]]:
        """
        Match multiple labels efficiently in one batch.

        Args:
            labels: List of OCR-extracted label texts.

        Returns:
            List of (label, field_name_or_None, score) tuples.
        """
        if not labels:
            return []

        results: List[Tuple[str, Optional[str], float]] = []
        uncached_labels: List[str] = []
        uncached_indices: List[int] = []

        for i, label in enumerate(labels):
            cache_key = label.strip().lower()
            if cache_key in self._cache:
                field_name, score = self._cache[cache_key]
                results.append((label, field_name, score))
            else:
                results.append((label, None, 0.0))  # placeholder
                uncached_labels.append(self._enrich_label(label))
                uncached_indices.append(i)

        if uncached_labels:
            label_embeddings = self._model.encode(
                uncached_labels,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            similarities = np.dot(
                self._field_embeddings, label_embeddings.T
            )  # (n_fields, n_labels)

            for j, idx in enumerate(uncached_indices):
                col = similarities[:, j]
                best_field_idx = int(np.argmax(col))
                best_score = float(col[best_field_idx])

                if best_score >= self.threshold:
                    field_name = self.field_names[best_field_idx]
                else:
                    field_name = None

                results[idx] = (labels[idx], field_name, best_score)
                cache_key = labels[idx].strip().lower()
                self._cache[cache_key] = (field_name, best_score)

        return results

    def get_top_k(self, label: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        Get top-k field matches for a label (useful for debugging).

        Returns:
            List of (field_name, score) sorted by score descending.
        """
        enriched = self._enrich_label(label)
        label_embedding = self._model.encode(
            [enriched],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        similarities = np.dot(self._field_embeddings, label_embedding.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:k]
        return [
            (self.field_names[int(i)], float(similarities[i]))
            for i in top_indices
        ]
