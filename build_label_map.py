#!/usr/bin/env python3
"""
Build Label Map: Offline label→field mapping generator
========================================================
Cross-references ground truth values with OCR label-value pairs to
auto-discover which OCR labels correspond to which schema field names.

Algorithm (Bidirectional Label+Value Matching):
  Phase A: Find all value matches (candidate pairs)
  Phase B: Score label affinity for each candidate
  Phase C: Optimal one-to-one assignment (greedy by score)
  Phase D: Position-based disambiguation for ties

Usage:
    .venv/bin/python build_label_map.py --form 125
    .venv/bin/python build_label_map.py --all
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import TEST_DATA_DIR, OUTPUT_DIR
from gt_flatten import flatten_gt_for_comparison
from schema_registry import SchemaRegistry, SUPPORTED_FORMS


# ============================================================================
# Constants
# ============================================================================

# Y-region buckets (from ~3300px page height at 300 DPI)
Y_REGIONS = [
    ("top", 0, 600),
    ("upper_mid", 600, 1200),
    ("lower_mid", 1200, 1800),
    ("bottom", 1800, 99999),
]

# Minimum value length to attempt matching (avoid single-char noise)
MIN_VALUE_LEN = 2

# Fuzzy match threshold (Levenshtein ratio)
FUZZY_THRESHOLD = 0.85


# ============================================================================
# Value normalisation (reuses patterns from compare.py)
# ============================================================================

_DATE_FORMATS = [
    "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
    "%B %d, %Y", "%b %d, %Y", "%m/%d/%y", "%Y/%m/%d",
]


def _normalise_date(s: str) -> str:
    """Parse date → YYYY-MM-DD; else return lowered."""
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
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
    """Strip $, commas; keep digits and decimal."""
    cleaned = re.sub(r"[^\d.]", "", str(s).strip())
    if cleaned and "." in cleaned:
        a, b = cleaned.split(".", 1)
        if b == "0" * len(b):
            cleaned = a or "0"
    return cleaned or str(s).lower()


def _normalise_phone(s: str) -> str:
    """Extract only digits from a phone number."""
    return re.sub(r"[^\d]", "", str(s).strip())


def normalise_for_matching(value: Any, field_name: str = "") -> str:
    """Normalise a value for cross-matching GT↔OCR."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""  # skip booleans
    if isinstance(value, (int, float)):
        return str(int(value)) if value == int(value) else str(value)

    s = str(value).strip()
    if not s:
        return ""

    fn = field_name.lower()

    # Date fields
    if "date" in fn and "update" not in fn:
        return _normalise_date(s)

    # Amount fields
    if any(x in fn for x in ("amount", "limit", "premium", "deductible", "cost",
                               "area", "revenue", "employee")):
        return _normalise_amount(s)

    # Phone/fax
    if any(x in fn for x in ("phone", "fax")):
        return _normalise_phone(s)

    return s.lower().strip()


def normalise_ocr_value(s: str) -> str:
    """Normalise an OCR value for matching (no field name context)."""
    s = str(s).strip()
    if not s:
        return ""
    return s.lower().strip()


# ============================================================================
# Matching helpers
# ============================================================================

def _levenshtein_ratio(a: str, b: str) -> float:
    """Simple Levenshtein similarity ratio (0-1)."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    len_a, len_b = len(a), len(b)
    # Quick length check
    if abs(len_a - len_b) / max(len_a, len_b) > (1 - FUZZY_THRESHOLD):
        return 0.0
    # DP distance
    matrix = [[0] * (len_b + 1) for _ in range(len_a + 1)]
    for i in range(len_a + 1):
        matrix[i][0] = i
    for j in range(len_b + 1):
        matrix[0][j] = j
    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )
    dist = matrix[len_a][len_b]
    return 1.0 - dist / max(len_a, len_b)


def value_match_score(gt_norm: str, ocr_norm: str, ocr_raw: str) -> float:
    """Score how well an OCR value matches a GT value. Returns 0-1."""
    if not gt_norm or not ocr_norm:
        return 0.0

    # Exact normalised match
    if gt_norm == ocr_norm:
        return 1.0

    # Normalised numeric match (both are digits)
    gt_digits = re.sub(r"[^\d]", "", gt_norm)
    ocr_digits = re.sub(r"[^\d]", "", ocr_norm)
    if gt_digits and ocr_digits and gt_digits == ocr_digits and len(gt_digits) >= 3:
        return 0.95

    # Date match (both parse to same date)
    gt_date = _normalise_date(gt_norm)
    ocr_date = _normalise_date(ocr_norm)
    if gt_date == ocr_date and re.search(r"\d{4}-\d{2}-\d{2}", gt_date):
        return 0.95

    # Phone digits match
    gt_phone = _normalise_phone(gt_norm)
    ocr_phone = _normalise_phone(ocr_norm)
    if gt_phone and ocr_phone and gt_phone == ocr_phone and len(gt_phone) >= 7:
        return 0.93

    # Contains match (one contains the other)
    if len(gt_norm) >= 3 and len(ocr_norm) >= 3:
        if gt_norm in ocr_norm or ocr_norm in gt_norm:
            shorter = min(len(gt_norm), len(ocr_norm))
            longer = max(len(gt_norm), len(ocr_norm))
            if shorter / longer >= 0.5:
                return 0.80

    # Fuzzy (Levenshtein)
    ratio = _levenshtein_ratio(gt_norm, ocr_norm)
    if ratio >= FUZZY_THRESHOLD:
        return ratio * 0.85  # discount fuzzy matches

    return 0.0


def label_affinity_score(
    label_text: str,
    field_name: str,
    tooltip: Optional[str],
) -> float:
    """Score how well an OCR label matches a GT field name/tooltip. Returns 0-1."""
    label_norm = re.sub(r"[:\-#]", " ", label_text.lower().strip())
    label_norm = re.sub(r"\s+", " ", label_norm).strip()
    label_words = [w for w in label_norm.split() if len(w) > 1]

    if not label_words:
        return 0.1

    name_lower = field_name.replace("_", " ").lower()

    # Tooltip match (strongest signal)
    if tooltip and len(label_norm) > 2:
        tip_lower = tooltip.lower()
        if label_norm in tip_lower:
            return 0.95
        matching_words = sum(1 for w in label_words if len(w) > 2 and w in tip_lower)
        if len(label_words) >= 2 and matching_words >= 2:
            return 0.90
        if len(label_words) == 1 and label_words[0] in tip_lower and len(label_words[0]) > 4:
            return 0.85

    # Field name match
    if label_norm in name_lower:
        return 0.75
    matching_name_words = sum(1 for w in label_words if w in name_lower)
    if len(label_words) >= 2 and matching_name_words >= 2:
        return 0.70
    if label_words and label_words[0] in name_lower and len(label_words[0]) > 4:
        return 0.65

    return 0.1


def get_y_region(y: float) -> str:
    """Map a Y coordinate to a region bucket."""
    for name, y_min, y_max in Y_REGIONS:
        if y_min <= y < y_max:
            return name
    return "bottom"


# ============================================================================
# Core algorithm
# ============================================================================

def build_label_map_for_form(
    form_type: str,
    registry: SchemaRegistry,
    test_data_dir: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Build the label→field mapping for one form type.

    Finds all GT+OCR pairs, runs the bidirectional matching algorithm,
    and outputs the mapping JSON.
    """
    schema = registry.get_schema(form_type)
    if not schema:
        print(f"  No schema for form {form_type}")
        return {}

    # Discover all GT+output pairs for this form type
    pairs_data = _discover_form_data(form_type, test_data_dir, output_dir)
    if not pairs_data:
        print(f"  No test data found for form {form_type}")
        return {}

    print(f"\n  Building label map for form {form_type} ({len(pairs_data)} PDF(s)) ...")

    # Accumulate mappings across all PDFs
    all_mappings: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    total_candidates = 0
    total_assigned = 0

    for pdf_info in pairs_data:
        gt_path = pdf_info["gt"]
        lv_path = pdf_info["lv"]
        bbox_path = pdf_info["bbox"]
        stem = pdf_info["stem"]

        print(f"    Processing {stem} ...")

        # Load data
        gt_raw = json.loads(gt_path.read_text())
        gt_flat = flatten_gt_for_comparison(gt_raw, form_type)
        lv_pairs = json.loads(lv_path.read_text())
        bbox_pages = json.loads(bbox_path.read_text())

        # Phase A: Find all value-match candidates
        candidates = _phase_a_value_match(gt_flat, lv_pairs, schema)
        total_candidates += len(candidates)

        # Phase B: Score label affinity
        scored = _phase_b_label_affinity(candidates, schema)

        # Phase C: Greedy one-to-one assignment
        assignments = _phase_c_greedy_assign(scored)
        total_assigned += len(assignments)

        # Phase D: Record with position info
        for assign in assignments:
            label_norm = re.sub(r"[:\-#]", " ", assign["label"].lower().strip())
            label_norm = re.sub(r"\s+", " ", label_norm).strip()

            entry = {
                "field_name": assign["gt_field"],
                "page": assign["page"],
                "y_region": assign["y_region"],
                "match_confidence": round(assign["final_score"], 3),
                "value_score": round(assign["value_score"], 3),
                "label_score": round(assign["label_score"], 3),
                "source_pdf": stem,
            }
            all_mappings[label_norm].append(entry)

    # Aggregate across PDFs
    final_mappings, ambiguous = _aggregate_mappings(all_mappings)

    result = {
        "form_type": form_type,
        "total_mappings": sum(len(v) for v in final_mappings.values()),
        "total_labels": len(final_mappings),
        "mappings": final_mappings,
        "ambiguous": ambiguous,
    }

    # Build report
    report = _build_report(form_type, schema, final_mappings, ambiguous,
                           total_candidates, total_assigned, len(pairs_data))

    return {"map": result, "report": report}


def _discover_form_data(
    form_type: str,
    test_data_dir: Path,
    output_dir: Path,
) -> List[Dict[str, Path]]:
    """Find all GT JSON + output label_value_pairs.json + bbox_pages.json."""
    results = []

    # Find test data subfolders matching this form type
    form_output_dir = output_dir / f"form_{form_type}"
    if not form_output_dir.exists():
        return results

    for subfolder in sorted(test_data_dir.iterdir()):
        if not subfolder.is_dir():
            continue
        # Check if folder matches form type
        folder_lower = subfolder.name.lower()
        if form_type == "125" and ("0125" not in folder_lower and "125" not in folder_lower):
            continue
        if form_type == "127" and "127" not in folder_lower:
            continue
        if form_type == "137" and "137" not in folder_lower:
            continue

        for gt_path in sorted(subfolder.glob("*.json")):
            stem = gt_path.stem
            # Find matching output directory
            out_dir = form_output_dir / stem
            if not out_dir.exists():
                continue

            lv_path = out_dir / "label_value_pairs.json"
            bbox_path = out_dir / "bbox_pages.json"

            if lv_path.exists() and bbox_path.exists():
                results.append({
                    "gt": gt_path,
                    "lv": lv_path,
                    "bbox": bbox_path,
                    "stem": stem,
                    "output_dir": out_dir,
                })

    return results


def _phase_a_value_match(
    gt_flat: Dict[str, Any],
    lv_pairs: List[Dict[str, Any]],
    schema: Any,
) -> List[Dict[str, Any]]:
    """Phase A: Find all (gt_field, ocr_pair) candidates by value matching."""
    candidates = []

    for gt_field, gt_value in gt_flat.items():
        if gt_value is None:
            continue
        if isinstance(gt_value, bool):
            continue  # skip checkbox booleans

        gt_str = str(gt_value).strip()
        if len(gt_str) < MIN_VALUE_LEN:
            continue

        gt_norm = normalise_for_matching(gt_value, gt_field)
        if not gt_norm or len(gt_norm) < MIN_VALUE_LEN:
            continue

        for pair_idx, pair in enumerate(lv_pairs):
            ocr_label = (pair.get("label") or "").strip()
            ocr_value = (pair.get("value") or "").strip()
            if not ocr_value or len(ocr_value) < MIN_VALUE_LEN:
                continue

            ocr_norm = normalise_for_matching(ocr_value)
            # Also try normalising with field context
            ocr_norm_ctx = normalise_for_matching(ocr_value, gt_field)

            score = max(
                value_match_score(gt_norm, ocr_norm, ocr_value),
                value_match_score(gt_norm, ocr_norm_ctx, ocr_value),
            )

            if score > 0:
                candidates.append({
                    "gt_field": gt_field,
                    "gt_value": gt_str,
                    "ocr_label": ocr_label,
                    "ocr_value": ocr_value,
                    "page": pair.get("page", 1),
                    "pair_idx": pair_idx,
                    "value_score": score,
                    # Y positions from bbox (will be enriched later)
                    "label_y": pair.get("label_y", 0),
                    "value_y": pair.get("value_y", 0),
                })

    return candidates


def _phase_b_label_affinity(
    candidates: List[Dict[str, Any]],
    schema: Any,
) -> List[Dict[str, Any]]:
    """Phase B: Score label affinity for each candidate."""
    scored = []
    for c in candidates:
        fi = schema.fields.get(c["gt_field"])
        tooltip = fi.tooltip if fi else None

        l_score = label_affinity_score(c["ocr_label"], c["gt_field"], tooltip)

        final = c["value_score"] * l_score
        scored.append({
            **c,
            "label_score": l_score,
            "final_score": final,
        })

    return scored


def _phase_c_greedy_assign(
    scored: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Phase C: Greedy one-to-one assignment. Each OCR pair → one GT field."""
    # Sort by final_score descending
    scored.sort(key=lambda x: x["final_score"], reverse=True)

    used_gt: set = set()
    used_ocr: set = set()  # (pair_idx, page) tuples
    assignments = []

    for c in scored:
        gt_key = c["gt_field"]
        ocr_key = (c["pair_idx"], c["page"])

        if gt_key in used_gt or ocr_key in used_ocr:
            continue

        # Phase D: position tiebreaking is implicit — higher-scored wins
        y = c.get("label_y") or c.get("value_y") or 0
        c["y_region"] = get_y_region(y)
        c["label"] = c["ocr_label"]

        used_gt.add(gt_key)
        used_ocr.add(ocr_key)
        assignments.append(c)

    return assignments


def _aggregate_mappings(
    all_mappings: Dict[str, List[Dict[str, Any]]],
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
    """Aggregate mappings across PDFs. Higher seen_count = more reliable."""
    final: Dict[str, List[Dict[str, Any]]] = {}
    ambiguous: Dict[str, List[Dict[str, Any]]] = {}

    for label_norm, entries in all_mappings.items():
        # Group by field_name
        field_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for e in entries:
            field_groups[e["field_name"]].append(e)

        label_entries = []
        for field_name, group in field_groups.items():
            # Aggregate: best confidence, page mode, y_region mode, seen_count
            best_conf = max(e["match_confidence"] for e in group)
            pages = [e["page"] for e in group]
            page_mode = max(set(pages), key=pages.count)
            regions = [e["y_region"] for e in group]
            region_mode = max(set(regions), key=regions.count)

            label_entries.append({
                "field_name": field_name,
                "page": page_mode,
                "y_region": region_mode,
                "match_confidence": round(best_conf, 3),
                "seen_count": len(group),
            })

        # Sort entries by seen_count desc, then confidence desc
        label_entries.sort(key=lambda x: (x["seen_count"], x["match_confidence"]), reverse=True)

        if len(label_entries) == 1:
            final[label_norm] = label_entries
        elif len(label_entries) > 1:
            # If top entry has significantly more seen_count, it's clear
            top = label_entries[0]
            second = label_entries[1]
            if top["seen_count"] > second["seen_count"]:
                final[label_norm] = [top]
                ambiguous[label_norm] = label_entries
            elif top["match_confidence"] > second["match_confidence"] + 0.15:
                final[label_norm] = [top]
                ambiguous[label_norm] = label_entries
            else:
                # Multiple candidates — keep all, mark as ambiguous
                final[label_norm] = label_entries
                ambiguous[label_norm] = label_entries

    return final, ambiguous


def _build_report(
    form_type: str,
    schema: Any,
    final_mappings: Dict[str, List[Dict[str, Any]]],
    ambiguous: Dict[str, List[Dict[str, Any]]],
    total_candidates: int,
    total_assigned: int,
    num_pdfs: int,
) -> Dict[str, Any]:
    """Build a human-readable report of the mapping process."""
    mapped_fields = set()
    for entries in final_mappings.values():
        for e in entries:
            mapped_fields.add(e["field_name"])

    all_fields = set(schema.fields.keys())
    unmapped = all_fields - mapped_fields

    # Categorise unmapped by type
    unmapped_checkboxes = []
    unmapped_text = []
    for f in sorted(unmapped):
        fi = schema.fields.get(f)
        if fi and fi.field_type in ("checkbox", "radio"):
            unmapped_checkboxes.append(f)
        else:
            unmapped_text.append(f)

    return {
        "form_type": form_type,
        "pdfs_processed": num_pdfs,
        "total_candidates": total_candidates,
        "total_assigned": total_assigned,
        "total_labels_mapped": len(final_mappings),
        "total_fields_mapped": len(mapped_fields),
        "total_schema_fields": len(all_fields),
        "coverage_pct": round(len(mapped_fields) / len(all_fields) * 100, 1) if all_fields else 0,
        "ambiguous_labels": len(ambiguous),
        "unmapped_text_fields": unmapped_text[:50],
        "unmapped_text_count": len(unmapped_text),
        "unmapped_checkbox_count": len(unmapped_checkboxes),
    }


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Build label→field mapping from GT + OCR data")
    parser.add_argument("--form", type=str, help="Form type (125, 127, 137)")
    parser.add_argument("--all", action="store_true", help="Build for all form types")
    parser.add_argument("--test-data", type=str, default=None, help="Override test data dir")
    parser.add_argument("--output", type=str, default=None, help="Override test output dir")
    args = parser.parse_args()

    if not args.form and not args.all:
        parser.error("Specify --form TYPE or --all")

    test_data = Path(args.test_data) if args.test_data else TEST_DATA_DIR
    output = Path(args.output) if args.output else OUTPUT_DIR

    registry = SchemaRegistry()

    forms = list(SUPPORTED_FORMS) if args.all else [args.form]

    # Create label_maps directory
    maps_dir = Path(__file__).parent / "label_maps"
    maps_dir.mkdir(exist_ok=True)

    for form_type in forms:
        result = build_label_map_for_form(form_type, registry, test_data, output)
        if not result:
            continue

        label_map = result["map"]
        report = result["report"]

        # Save map
        map_path = maps_dir / f"acord_{form_type}_label_map.json"
        map_path.write_text(json.dumps(label_map, indent=2))
        print(f"\n  Saved: {map_path}")
        print(f"    {label_map['total_labels']} labels → {label_map['total_mappings']} mappings")

        # Save report
        report_path = maps_dir / f"build_report_{form_type}.json"
        report_path.write_text(json.dumps(report, indent=2))
        print(f"  Saved: {report_path}")
        print(f"    Coverage: {report['coverage_pct']}% ({report['total_fields_mapped']}/{report['total_schema_fields']} fields)")
        if report["ambiguous_labels"]:
            print(f"    Ambiguous labels: {report['ambiguous_labels']}")
        print(f"    Unmapped text fields: {report['unmapped_text_count']}")
        print(f"    Unmapped checkboxes: {report['unmapped_checkbox_count']}")


if __name__ == "__main__":
    main()
