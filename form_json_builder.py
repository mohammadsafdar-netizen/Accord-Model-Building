#!/usr/bin/env python3
"""
Form JSON Builder: Empty template and LLM-fill contract
=========================================================
Phase 2 of the label-value → empty JSON → LLM fill pipeline.

- build_empty_form_json(schema_registry, form_type) → dict with every schema key
  and value null (or default_value from schema when set). This JSON is the
  contract the LLM must fill from label-value pairs.

- Serialise/save as empty_form_125.json (etc.) for a given form type so the
  pipeline and finetuning can use a stable template.

Usage:
  from schema_registry import SchemaRegistry
  from form_json_builder import build_empty_form_json, save_empty_form_json
  registry = SchemaRegistry(schemas_dir=Path("schemas"))
  empty = build_empty_form_json(registry, "125")
  save_empty_form_json(empty, Path("output/empty_form_125.json"))
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from schema_registry import SchemaRegistry, FormSchema, FieldInfo


def _normalize_label(s: str) -> str:
    """Normalize label for matching: lowercase, collapse spaces, remove punctuation."""
    s = re.sub(r"\s+", " ", s.strip()).lower()
    s = re.sub(r"[:\-#]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Labels that must never match amount/premium/limit/deductible fields (avoid e.g. "NO. OF MEMBERS" → PARTNERSHIP filling a premium field)
_AMOUNT_FIELD_LABEL_BLOCKLIST = frozenset({
    "partnership", "owner", "bus", "cell", "home", "members", "no of members",
    "phone", "fax", "percent", "percentage", "use", "employer", "driver",
})


def _value_looks_numeric(value: str) -> bool:
    """True if value looks like a number (digits, optional $ and commas)."""
    s = (value or "").strip().replace("$", "").replace(",", "").replace(" ", "")
    if not s:
        return False
    return bool(re.match(r"^\d+\.?\d*$", s))


def _value_looks_like_address(value: str) -> bool:
    """True if value looks like a full street address (should not go in Occupancy)."""
    v = (value or "").strip().upper()
    return any(
        x in v for x in ("MAIN ST", "MAIN STREET", " AVE ", " AVE.", "BLVD", "SUITE", "STE ", " ST ", " ST.")
    )


def _is_allowed_checkbox_value(value: str) -> bool:
    """True if value is an allowed checkbox/radio prefill (1, 0, X, S, Yes, No, Off, true, false)."""
    v = (value or "").strip().lower()
    return v in ("1", "0", "x", "s", "yes", "no", "off", "true", "false", "on", "y", "n")


def _allow_label_value_prefill(
    field_name: str,
    fi: FieldInfo,
    label_norm: str,
    value: str,
) -> bool:
    """
    Return True if this label-value pair is allowed to prefill the given field.
    Enforces: amount-field blocklist + numeric value; occupancy vs address; checkbox allowed values only.
    """
    name_lower = field_name.lower()
    tip = (fi.tooltip or "").lower()

    # Checkbox/radio: only prefill from label-value if value is in allowed set
    if fi.field_type in ("checkbox", "radio"):
        if not _is_allowed_checkbox_value(value):
            return False

    # Amount-like fields: blocklist labels and require numeric value
    if any(x in name_lower for x in ("premium", "amount", "limit", "deductible")):
        label_words = set(label_norm.split())
        if label_words & _AMOUNT_FIELD_LABEL_BLOCKLIST:
            return False
        if label_norm in _AMOUNT_FIELD_LABEL_BLOCKLIST:
            return False
        if not _value_looks_numeric(value):
            return False

    # Occupancy vs address: do not put full street address in Occupancy field
    if "occupancy" in name_lower or "descriptionofoccupancy" in name_lower or "occupancy" in tip or "descriptionofoccupancy" in tip:
        if _value_looks_like_address(value):
            return False

    return True


def _label_matches_field(label_norm: str, field_name: str, tooltip: Optional[str]) -> bool:
    """True if label likely refers to this schema field (name or tooltip). Prefer tooltip to reduce false positives."""
    return _label_match_basis(label_norm, field_name, tooltip) is not None


def _label_match_basis(label_norm: str, field_name: str, tooltip: Optional[str]) -> Optional[str]:
    """
    Returns how the label matches the field: "tooltip", "field_name", or None if no match.
    Used to record fill basis and approximate confidence (tooltip = stronger).
    """
    if len(label_norm) < 3:
        return None
    name_lower = field_name.replace("_", " ").lower()
    label_words = [w for w in label_norm.split() if len(w) > 1]
    if tooltip and len(label_norm) > 3:
        tip_lower = tooltip.lower()
        if label_norm in tip_lower:
            return "tooltip"
        if len(label_words) >= 2 and sum(1 for w in label_words if len(w) > 2 and w in tip_lower) >= 2:
            return "tooltip"
        if len(label_words) == 1 and label_words[0] in tip_lower and len(label_words[0]) > 4:
            return "tooltip"
    if label_norm in name_lower:
        return "field_name"
    if len(label_words) >= 2 and sum(1 for w in label_words if w in name_lower) >= 2:
        return "field_name"
    generic = {"indicator", "explanation", "description", "amount", "date", "code", "number", "name"}
    if label_words and label_words[0] not in generic and label_words[0] in name_lower and len(label_words[0]) > 4:
        return "field_name"
    return None


def prefill_form_json_from_ocr(
    empty_json: Dict[str, Any],
    schema: FormSchema,
    spatial_fields: Dict[str, Any],
    label_value_pairs: List[Dict[str, Any]],
    semantic_matcher: Optional[Any] = None,
    label_map: Optional[Any] = None,
) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Dict[str, Any]]]:
    """
    Pre-fill empty form JSON with OCR-derived data. Spatial fields (exact schema keys)
    are applied first; then label-value pairs are matched to schema fields and overlaid.
    If a semantic_matcher is provided, unmatched labels are re-tried with MiniLM embeddings.

    Args:
        empty_json: Template with all schema keys and null.
        schema: Form schema for field names and tooltips.
        spatial_fields: Dict of schema_key -> value from spatial pre-extraction.
        label_value_pairs: List of {"label": str, "value": str, "page"?: int, "confidence"?: float}.
        semantic_matcher: Optional SemanticFieldMatcher for embedding-based matching.
        label_map: Optional LabelFieldMap for pre-built label→field lookup.

    Returns:
        (prefilled_json, source_map, details_map) where:
        - source_map is field_name -> "spatial" | "label_map" | "label_value" | "semantic".
        - details_map is field_name -> {source, basis, confidence}. basis explains how the
          value was chosen; confidence is OCR pair confidence for label_value, None for spatial.
    """
    prefilled = dict(empty_json)
    source_map: Dict[str, str] = {}
    details_map: Dict[str, Dict[str, Any]] = {}

    # 1. Overlay spatial extraction (already has schema keys)
    spatial_basis = (
        "Layout: label text located in bbox region, value from adjacent region (below/right) per form template."
    )
    for k, v in spatial_fields.items():
        if k in prefilled and v is not None and str(v).strip():
            prefilled[k] = v
            source_map[k] = "spatial"
            details_map[k] = {"source": "spatial", "basis": spatial_basis, "confidence": None}

    # 1.5. Label map lookup (pre-built deterministic mapping, don't overwrite spatial)
    if label_map is not None and getattr(label_map, "is_loaded", False):
        lm_results = label_map.batch_lookup(label_value_pairs)
        for field_name, (value, confidence) in lm_results.items():
            if field_name in source_map:
                continue
            if field_name not in prefilled:
                continue
            if prefilled.get(field_name) is not None and str(prefilled.get(field_name)).strip():
                continue
            fi = schema.fields.get(field_name)
            if fi is not None:
                label_norm_lm = _normalize_label(value)  # for allow check we pass the label
                if not _allow_label_value_prefill(field_name, fi, "", value):
                    continue
            prefilled[field_name] = value
            source_map[field_name] = "label_map"
            details_map[field_name] = {
                "source": "label_map",
                "basis": f"Pre-built label→field mapping (confidence={confidence:.3f})",
                "confidence": confidence,
            }

    # 2. Match label-value pairs to schema fields (don't overwrite spatial or label_map)
    unmatched_pairs: List[Dict[str, Any]] = []  # For semantic matching fallback
    for item in label_value_pairs:
        label = (item.get("label") or "").strip()
        value = (item.get("value") or "").strip()
        if not label or not value:
            continue
        label_norm = _normalize_label(label)
        if len(label_norm) < 2:
            continue
        pair_confidence = item.get("confidence")  # EasyOCR min(label, value) block confidence
        best_field: Optional[str] = None
        best_basis: Optional[str] = None
        for field_name in schema.fields:
            if field_name in source_map:
                continue
            fi = schema.fields[field_name]
            basis = _label_match_basis(label_norm, field_name, fi.tooltip)
            if basis is not None:
                if best_field is None:
                    best_field = field_name
                    best_basis = basis
                elif len(field_name) > len(best_field):
                    best_field = field_name
                    best_basis = basis
        if best_field is None:
            # Save for semantic matching pass
            unmatched_pairs.append(item)
            continue
        if prefilled.get(best_field) is not None and prefilled.get(best_field) != "":
            continue
        fi = schema.fields[best_field]
        # Stricter matching: reject bad prefill for amount, occupancy, and checkbox fields
        if not _allow_label_value_prefill(best_field, fi, label_norm, value):
            continue
        prefilled[best_field] = value
        source_map[best_field] = "label_value"
        basis_desc = (
            f"OCR pair \"{label}\" → value matched to field by {best_basis}."
        )
        details_map[best_field] = {
            "source": "label_value",
            "basis": basis_desc,
            "confidence": pair_confidence,
        }

    # 3. Semantic matching pass for unmatched labels (MiniLM embeddings)
    if semantic_matcher is not None and unmatched_pairs:
        unmatched_labels = [(item.get("label") or "").strip() for item in unmatched_pairs]
        semantic_results = semantic_matcher.batch_match(unmatched_labels)
        for (label, field_name, score), item in zip(semantic_results, unmatched_pairs):
            if field_name is None:
                continue
            if field_name in source_map:
                continue
            value = (item.get("value") or "").strip()
            if not value:
                continue
            if prefilled.get(field_name) is not None and prefilled.get(field_name) != "":
                continue
            fi = schema.fields.get(field_name)
            if fi is None:
                continue
            label_norm = _normalize_label(label)
            if not _allow_label_value_prefill(field_name, fi, label_norm, value):
                continue
            prefilled[field_name] = value
            source_map[field_name] = "semantic"
            pair_confidence = item.get("confidence")
            details_map[field_name] = {
                "source": "semantic",
                "basis": f"Semantic match: \"{label}\" → {field_name} (score={score:.3f})",
                "confidence": pair_confidence,
            }

    return prefilled, source_map, details_map


def build_empty_form_json(
    schema_registry: SchemaRegistry,
    form_type: str,
    use_defaults: bool = False,
) -> Dict[str, Any]:
    """
    Build a form-specific JSON with every schema field key and value null
    (or default_value from schema when use_defaults=True).

    This is the empty template the LLM will fill from label-value pairs.

    Args:
        schema_registry: Loaded schema registry (125, 127, 137).
        form_type: "125", "127", or "137".
        use_defaults: If True, set value to field.default_value when present.

    Returns:
        Dict mapping each schema field name to null or default.
    """
    schema = schema_registry.get_schema(form_type)
    if not schema:
        return {}

    out: Dict[str, Any] = {}
    for name in sorted(schema.fields.keys()):
        fi = schema.fields[name]
        if use_defaults and fi.default_value is not None and str(fi.default_value).strip():
            out[name] = fi.default_value
        else:
            out[name] = None
    return out


def save_empty_form_json(
    empty_json: Dict[str, Any],
    path: Path,
    indent: int = 2,
) -> None:
    """Write empty form JSON to a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(empty_json, indent=indent), encoding="utf-8")


def load_empty_form_json(path: Path) -> Dict[str, Any]:
    """Load empty form JSON from a file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_empty_form_json_from_schema(schema: FormSchema, use_defaults: bool = False) -> Dict[str, Any]:
    """
    Build empty JSON from a FormSchema instance (no registry).
    Useful when you already have the schema loaded.
    """
    out: Dict[str, Any] = {}
    for name in sorted(schema.fields.keys()):
        fi = schema.fields[name]
        if use_defaults and fi.default_value is not None and str(fi.default_value).strip():
            out[name] = fi.default_value
        else:
            out[name] = None
    return out


def label_value_pairs_to_json_list(spatial_indices: list) -> list:
    """
    Convert spatial indices (from OCRResult.spatial_indices) to a list of
    {label, value, page, confidence?, label_y?, value_y?, label_x?} dicts
    for saving as label_value_pairs.json.
    confidence is min(label block confidence, value block confidence) from EasyOCR.
    label_y/value_y/label_x are centre coordinates from the TextBlock.
    """
    out = []
    for page_num, si in enumerate(spatial_indices, 1):
        for pair in getattr(si, "label_value_pairs", []):
            entry: Dict[str, Any] = {
                "label": pair.label.text.strip(),
                "value": pair.value.text.strip(),
                "page": page_num,
            }
            conf = getattr(pair, "confidence", None)
            if conf is not None:
                entry["confidence"] = conf
            # Include spatial positions for label-map disambiguation
            if hasattr(pair.label, "y"):
                entry["label_y"] = pair.label.y
            if hasattr(pair.value, "y"):
                entry["value_y"] = pair.value.y
            if hasattr(pair.label, "x"):
                entry["label_x"] = pair.label.x
            out.append(entry)
    return out
