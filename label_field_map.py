#!/usr/bin/env python3
"""
Label Field Map: Runtime lookup for label→field mappings
==========================================================
Lightweight class that loads the pre-built JSON map and provides
fast deterministic lookup at runtime.

Usage:
    from label_field_map import LabelFieldMap
    lfm = LabelFieldMap("125")
    result = lfm.lookup("phone", page=1, y=300, value="202-123-4567")
    # → ("Producer_ContactPerson_PhoneNumber_A", 0.92)

    batch = lfm.batch_lookup(label_value_pairs)
    # → {"Producer_ContactPerson_PhoneNumber_A": ("202-123-4567", 0.92), ...}
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Y-region buckets (must match build_label_map.py)
Y_REGIONS = [
    ("top", 0, 600),
    ("upper_mid", 600, 1200),
    ("lower_mid", 1200, 1800),
    ("bottom", 1800, 99999),
]


def _get_y_region(y: float) -> str:
    """Map a Y coordinate to a region bucket."""
    for name, y_min, y_max in Y_REGIONS:
        if y_min <= y < y_max:
            return name
    return "bottom"


def _normalise_label(s: str) -> str:
    """Normalise label for lookup: lowercase, collapse spaces, remove punctuation."""
    s = re.sub(r"[:\-#]", " ", s.lower().strip())
    return re.sub(r"\s+", " ", s).strip()


class LabelFieldMap:
    """
    Runtime label→field mapping lookup.

    Loads a pre-built mapping JSON and provides fast lookup for
    OCR label-value pairs → schema field names.
    """

    def __init__(self, form_type: str, maps_dir: Optional[Path] = None):
        """
        Load the label map for the given form type.

        Args:
            form_type: "125", "127", or "137"
            maps_dir: Directory containing label map JSONs. Default: ./label_maps/
        """
        self.form_type = form_type
        self._mappings: Dict[str, List[Dict[str, Any]]] = {}
        self._loaded = False

        if maps_dir is None:
            maps_dir = Path(__file__).parent / "label_maps"

        map_path = maps_dir / f"acord_{form_type}_label_map.json"
        if map_path.exists():
            try:
                data = json.loads(map_path.read_text())
                self._mappings = data.get("mappings", {})
                self._loaded = True
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  [LABEL-MAP] Failed to load {map_path}: {e}")

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def total_labels(self) -> int:
        return len(self._mappings)

    def lookup(
        self,
        label: str,
        page: int = 0,
        y: float = 0,
        value: str = "",
    ) -> Optional[Tuple[str, float]]:
        """
        Look up a single OCR label → (field_name, confidence).

        Args:
            label: OCR label text
            page: Page number (1-indexed)
            y: Y coordinate of the label/value
            value: The OCR value (for context, not used in lookup)

        Returns:
            (field_name, confidence) or None if no match.
        """
        if not self._loaded or not label:
            return None

        label_norm = _normalise_label(label)
        if not label_norm or len(label_norm) < 2:
            return None

        candidates = self._mappings.get(label_norm)
        if not candidates:
            return None

        if len(candidates) == 1:
            c = candidates[0]
            return (c["field_name"], c["match_confidence"])

        # Multiple candidates — disambiguate by page + y_region
        y_region = _get_y_region(y) if y > 0 else None

        best = None
        best_score = -1.0

        for c in candidates:
            score = c["match_confidence"] * c.get("seen_count", 1)

            # Page match bonus
            if page > 0 and c.get("page") == page:
                score *= 1.2

            # Y-region match bonus
            if y_region and c.get("y_region") == y_region:
                score *= 1.1

            if score > best_score:
                best_score = score
                best = c

        if best:
            return (best["field_name"], best["match_confidence"])

        return None

    def batch_lookup(
        self,
        label_value_pairs: List[Dict[str, Any]],
    ) -> Dict[str, Tuple[str, float]]:
        """
        Batch lookup for multiple OCR label-value pairs.

        Args:
            label_value_pairs: List of {"label": str, "value": str, "page"?: int,
                                         "label_y"?: float, "value_y"?: float}

        Returns:
            {field_name: (value, confidence)} — one entry per matched field.
            Each field_name appears at most once (first match wins).
        """
        if not self._loaded:
            return {}

        results: Dict[str, Tuple[str, float]] = {}
        used_fields: set = set()

        for pair in label_value_pairs:
            label = (pair.get("label") or "").strip()
            value = (pair.get("value") or "").strip()
            if not label or not value:
                continue

            page = pair.get("page", 0)
            y = pair.get("label_y") or pair.get("value_y") or 0

            match = self.lookup(label, page=page, y=y, value=value)
            if match is None:
                continue

            field_name, confidence = match
            if field_name in used_fields:
                continue

            used_fields.add(field_name)
            results[field_name] = (value, confidence)

        return results
