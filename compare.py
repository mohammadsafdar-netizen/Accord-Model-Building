#!/usr/bin/env python3
"""
Accuracy Comparison: field-level evaluation against ground truth
================================================================
Compares extracted fields against a ground truth JSON and reports:
  - Accuracy  (exact + partial matches / total)
  - Exact match rate
  - Coverage  (non-missing / total)
  - Per-field status: matched, partial, wrong, missing
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# ===========================================================================
# Value normalisation
# ===========================================================================

_CHECKBOX_TRUE = {"true", "1", "on", "yes", "x", "checked"}
_CHECKBOX_FALSE = {"false", "0", "off", "no", "unchecked", ""}


def normalise_value(
    value: Any,
    field_name: str = "",
    checkbox_fields: Optional[set] = None,
) -> str:
    """Normalise a value to a comparable lowercase string.
    
    For checkbox/indicator fields, normalises to 'true' or 'false'.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        s = str(value)
    elif isinstance(value, dict):
        s = json.dumps(value, sort_keys=True).lower()
    elif isinstance(value, list):
        s = json.dumps(value, sort_keys=True).lower()
    else:
        s = str(value).strip().lower()

    # Normalise checkbox/indicator fields to true/false
    is_checkbox = (
        "indicator" in field_name.lower()
        or field_name.lower().startswith("chk")
        or (checkbox_fields and field_name in checkbox_fields)
    )
    if is_checkbox:
        if s in _CHECKBOX_TRUE:
            return "true"
        elif s in _CHECKBOX_FALSE:
            return "false"
        # Non-standard value for a checkbox - keep as-is for mismatch detection
        return s

    return s


# ===========================================================================
# Field comparison
# ===========================================================================

def compare_fields(
    extracted: Dict[str, Any],
    ground_truth: Dict[str, Any],
    key_fields: Optional[List[str]] = None,
    checkbox_fields: Optional[set] = None,
) -> Dict[str, Any]:
    """
    Compare extracted fields against ground truth.

    Args:
        extracted:     {field_name: extracted_value}
        ground_truth:  {field_name: true_value}
        key_fields:    Optional subset of fields to evaluate.
                       If None, evaluates all ground truth keys.
        checkbox_fields: Set of field names that are checkboxes (from schema).

    Returns:
        Dict with metrics and per-field results.
    """
    if key_fields is None:
        key_fields = list(ground_truth.keys())

    results = {
        "total_gt_fields": len(key_fields),
        "matched": 0,
        "partial_match": 0,
        "missing": 0,
        "wrong": 0,
        "field_results": {},
    }

    for field_name in key_fields:
        gt_val = ground_truth.get(field_name)
        ext_val = extracted.get(field_name)

        gt_norm = normalise_value(gt_val, field_name, checkbox_fields)
        ext_norm = normalise_value(ext_val, field_name, checkbox_fields)

        # Skip empty ground truth
        if not gt_norm:
            results["total_gt_fields"] -= 1
            continue

        if not ext_norm:
            results["missing"] += 1
            results["field_results"][field_name] = {
                "status": "missing",
                "expected": gt_val,
                "extracted": None,
            }
        elif gt_norm == ext_norm:
            results["matched"] += 1
            results["field_results"][field_name] = {
                "status": "matched",
                "expected": gt_val,
                "extracted": ext_val,
            }
        elif gt_norm in ext_norm or ext_norm in gt_norm:
            results["partial_match"] += 1
            results["field_results"][field_name] = {
                "status": "partial",
                "expected": gt_val,
                "extracted": ext_val,
            }
        else:
            results["wrong"] += 1
            results["field_results"][field_name] = {
                "status": "wrong",
                "expected": gt_val,
                "extracted": ext_val,
            }

    # ---- Metrics ----
    total = results["total_gt_fields"]
    if total > 0:
        results["accuracy"] = round(
            (results["matched"] + results["partial_match"] * 0.5) / total * 100, 2
        )
        results["exact_match_rate"] = round(results["matched"] / total * 100, 2)
        results["coverage"] = round((total - results["missing"]) / total * 100, 2)
    else:
        results["accuracy"] = 0.0
        results["exact_match_rate"] = 0.0
        results["coverage"] = 0.0

    return results


# ===========================================================================
# Printing
# ===========================================================================

def print_report(results: Dict[str, Any], title: str = "Accuracy Report") -> None:
    """Print a formatted accuracy report to stdout."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(f"  Total GT fields:   {results['total_gt_fields']}")
    print(f"  Exact matches:     {results['matched']}")
    print(f"  Partial matches:   {results['partial_match']}")
    print(f"  Wrong:             {results['wrong']}")
    print(f"  Missing:           {results['missing']}")
    print(f"  ---")
    print(f"  Accuracy:          {results['accuracy']}%")
    print(f"  Exact match rate:  {results['exact_match_rate']}%")
    print(f"  Coverage:          {results['coverage']}%")

    # Show mismatches
    fr = results.get("field_results", {})
    wrongs = [(k, v) for k, v in fr.items() if v["status"] == "wrong"]
    if wrongs:
        print(f"\n  Top mismatches (wrong):")
        for k, v in wrongs[:15]:
            print(f"    {k}")
            print(f"      expected:  {v['expected']}")
            print(f"      got:       {v['extracted']}")

    missings = [(k, v) for k, v in fr.items() if v["status"] == "missing"]
    if missings:
        print(f"\n  Missing fields ({len(missings)}):")
        for k, _ in missings[:15]:
            print(f"    {k}")
        if len(missings) > 15:
            print(f"    ... and {len(missings) - 15} more")

    print(f"{'='*60}\n")


# ===========================================================================
# Convenience
# ===========================================================================

def load_ground_truth(gt_path: str | Path) -> Dict[str, Any]:
    """Load a ground truth JSON file."""
    with open(gt_path) as f:
        return json.load(f)
