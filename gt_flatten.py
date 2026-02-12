"""
Ground-truth flattening shared by expand_schemas_from_gt and test_pipeline.
Form 127 uses nested "Vehicle 1", "Vehicle 2", "Driver 1", "Driver 2" etc.;
we flatten to flat keys with suffix _A, _B, _C so schema and comparison use the same keys.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# Suffix for index 1, 2, 3, ... (127 Vehicle/Driver)
INDEX_SUFFIXES = ["_A", "_B", "_C", "_D", "_E", "_F", "_G", "_H", "_I", "_J"]


def _normalize_inner_key(s: str) -> str:
    """Normalize a key from nested GT (e.g. 'Seq #' -> 'Seq_Number', 'Given Name' -> 'Given_Name')."""
    if not s:
        return s
    s = s.strip()
    s = re.sub(r"\s+", "_", s)
    s = s.replace("/", "_")
    if "#" in s:
        s = re.sub(r"#+", "Number", s)
    return s or "value"


def _flatten_dict_recursive(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Flatten a dict: nested dicts get prefix key_; leaves stay as prefix+key."""
    out: Dict[str, Any] = {}
    for k, v in d.items():
        nk = _normalize_inner_key(k)
        key = f"{prefix}_{nk}" if prefix else nk
        if isinstance(v, dict):
            out.update(_flatten_dict_recursive(v, key))
        elif not isinstance(v, list):
            out[key] = v
    return out


def flatten_127_full(gt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten 127 ground truth so that 'Vehicle 1', 'Vehicle 2', 'Driver 1', 'Driver 2'
    become flat keys with suffix _A, _B, _C (same convention as schema).
    Top-level flat keys are kept as-is. Nested Coverages etc. become Vehicle_Coverages_Liability_A, etc.
    """
    result: Dict[str, Any] = {}

    for key, value in gt.items():
        if isinstance(value, list):
            continue
        if isinstance(value, dict):
            key_strip = key.strip()
            # Vehicle 1, Vehicle 2, Vehicle 3, ...
            if re.match(r"^Vehicle\s+\d+$", key_strip, re.IGNORECASE):
                idx = int(key_strip.split()[-1])
                suffix = INDEX_SUFFIXES[idx - 1] if 1 <= idx <= len(INDEX_SUFFIXES) else f"_{idx}"
                flat_inner = _flatten_dict_recursive(value, "Vehicle")
                for ik, iv in flat_inner.items():
                    result[ik.rstrip("_") + suffix] = iv
                continue
            # Driver 1, Driver 2, ...
            if re.match(r"^Driver\s+\d+$", key_strip, re.IGNORECASE):
                idx = int(key_strip.split()[-1])
                suffix = INDEX_SUFFIXES[idx - 1] if 1 <= idx <= len(INDEX_SUFFIXES) else f"_{idx}"
                flat_inner = _flatten_dict_recursive(value, "Driver")
                for ik, iv in flat_inner.items():
                    result[ik.rstrip("_") + suffix] = iv
                continue
            # Other nested (e.g. LinesOfBusiness_A) - flatten with prefix
            flat_inner = _flatten_dict_recursive(value, key)
            result.update(flat_inner)
            continue
        result[key] = value

    return result


def flatten_gt_for_comparison(gt: Dict[str, Any], form_type: str) -> Dict[str, Any]:
    """
    Flatten ground truth for comparison (and for schema key collection).
    - 127: full flatten including Vehicle 1/2, Driver 1/2 -> _A, _B keys.
    - 125, 137: only top-level keys (skip nested dicts/lists).
    """
    if form_type == "127":
        return flatten_127_full(gt)
    flat: Dict[str, Any] = {}
    for k, v in gt.items():
        if isinstance(v, (dict, list)):
            continue
        flat[k] = v
    return flat


def collect_all_gt_keys_flat(gt: Dict[str, Any], form_type: str) -> set:
    """Return set of all flat keys present in this GT (for schema expansion)."""
    flat = flatten_gt_for_comparison(gt, form_type)
    return set(flat.keys())
