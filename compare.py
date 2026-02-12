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
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ===========================================================================
# Value normalisation
# ===========================================================================

_CHECKBOX_TRUE = {"true", "1", "on", "yes", "x", "checked", "y", "s"}
_CHECKBOX_FALSE = {"false", "0", "off", "no", "unchecked", "", "n"}

# Common date formats for parsing (order matters: try more specific first)
_DATE_FORMATS = [
    "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
    "%B %d, %Y", "%b %d, %Y", "%m/%d/%y", "%Y/%m/%d",
]


def _normalise_date(s: str) -> str:
    """Try to parse date string and return YYYY-MM-DD for comparison; else return original lowercased."""
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # 4-digit year somewhere
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", s)
    if m:
        try:
            mo, day, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= day <= 31:
                return f"{yr}-{mo:02d}-{day:02d}"
        except (ValueError, IndexError):
            pass
    return s.lower()


def _normalise_amount(s: str) -> str:
    """Strip currency symbols and commas; keep digits and one decimal point for comparison."""
    s = str(s).strip()
    # Remove $ , and spaces; keep digits and one period
    cleaned = re.sub(r"[^\d.]", "", s)
    # Normalise to integer if .00
    if cleaned and "." in cleaned:
        a, b = cleaned.split(".", 1)
        if b == "0" * len(b):
            cleaned = a or "0"
    return cleaned or s.lower()


def normalise_value(
    value: Any,
    field_name: str = "",
    checkbox_fields: Optional[set] = None,
) -> str:
    """Normalise a value to a comparable string.
    
    - Checkbox/indicator fields -> 'true' or 'false'.
    - Date-like fields (name contains 'date', not 'update') -> YYYY-MM-DD when parseable.
    - Amount-like fields (Amount, Limit, Premium, Deductible, Cost) -> digits only.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        s = str(value)
        # Checkbox: treat 1/0 as true/false when field is checkbox
        fn_lower = field_name.lower()
        is_checkbox = (
            "indicator" in fn_lower or fn_lower.startswith("chk")
            or (checkbox_fields and field_name in checkbox_fields)
        )
        if is_checkbox and value in (0, 1):
            return "true" if value == 1 else "false"
    elif isinstance(value, dict):
        s = json.dumps(value, sort_keys=True).lower()
    elif isinstance(value, list):
        s = json.dumps(value, sort_keys=True).lower()
    else:
        s = str(value).strip()

    fn_lower = field_name.lower()

    # Checkbox/indicator -> true/false
    is_checkbox = (
        "indicator" in fn_lower or fn_lower.startswith("chk")
        or (checkbox_fields and field_name in checkbox_fields)
    )
    if is_checkbox:
        sl = s.lower()
        if sl in _CHECKBOX_TRUE:
            return "true"
        if sl in _CHECKBOX_FALSE:
            return "false"
        return s.lower()

    # Date field (name has 'date', avoid 'update' / standalone 'time')
    if "date" in fn_lower and "update" not in fn_lower:
        return _normalise_date(s)

    # Time field (e.g. EffectiveTime): keep as digits for HHMM comparison
    if "effectivetime" in fn_lower or "expirationtime" in fn_lower:
        digits = re.sub(r"[^\d]", "", s)
        if len(digits) <= 4 and digits.isdigit():
            return digits.zfill(4)  # 1000, 0930
        return s.lower()

    # Amount-like: strip $ and commas for comparison
    if any(x in fn_lower for x in ("amount", "limit", "premium", "deductible", "cost")) and "count" not in fn_lower:
        return _normalise_amount(s)
    # Area/count fields that may have comma-formatted numbers (e.g. 100,000 vs 100000)
    if ("area" in fn_lower or "count" in fn_lower) and re.match(r"^[\d,.\s]+$", s):
        return _normalise_amount(s)

    return s.lower()


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
