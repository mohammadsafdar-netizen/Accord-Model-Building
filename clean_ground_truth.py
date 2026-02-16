#!/usr/bin/env python3
"""
Clean Ground Truth: Remove non-widget fields from GT JSON files
================================================================
ACORD GT files contain a mix of real widget field names and alternate
names invented by annotators. This script keeps only fields that
correspond to actual AcroForm widgets in the reference PDFs.

Usage:
    .venv/bin/python clean_ground_truth.py --all
    .venv/bin/python clean_ground_truth.py --form 125
    .venv/bin/python clean_ground_truth.py --all --dry-run   # preview only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Set

try:
    import fitz
except ImportError:
    raise ImportError("PyMuPDF (fitz) is required. Install: uv pip install PyMuPDF")

from gt_flatten import flatten_gt_for_comparison


FORM_FOLDERS = {
    "125": "ACORD_0125_CommercialInsurance_Acroform",
    "127": "127_Business_Auto_Section_2015_12",
    "137": "ACORD_137",
}


def get_widget_names(pdf_path: Path) -> Set[str]:
    """Extract all widget field names from an AcroForm PDF."""
    doc = fitz.open(str(pdf_path))
    names = set()
    for page in doc:
        for w in page.widgets():
            if w.field_name:
                names.add(w.field_name)
    doc.close()
    return names


def clean_gt_flat(gt_raw: Dict[str, Any], form_type: str, widget_names: Set[str]) -> Dict[str, Any]:
    """
    Clean a GT file: keep only keys that match real widget names.

    For form 127 with nested Vehicle/Driver dicts, we need to rebuild
    the nested structure with only valid flattened keys.
    """
    if form_type == "127":
        return _clean_127(gt_raw, widget_names)
    else:
        # Forms 125, 137: flat top-level keys only
        cleaned = {}
        for k, v in gt_raw.items():
            if isinstance(v, (dict, list)):
                continue  # drop nested structures
            if k in widget_names:
                cleaned[k] = v
        return cleaned


def _clean_127(gt_raw: Dict[str, Any], widget_names: Set[str]) -> Dict[str, Any]:
    """
    Clean form 127 GT: flatten Vehicle/Driver nested dicts, keep only widget-name keys.
    Output is a flat dict (no nested Vehicle/Driver structures).
    """
    # Flatten everything first
    flat = flatten_gt_for_comparison(gt_raw, "127")

    # Keep only widget-name keys
    cleaned = {}
    for k, v in flat.items():
        if k in widget_names:
            cleaned[k] = v
    return cleaned


def main():
    parser = argparse.ArgumentParser(
        description="Clean GT JSON files to only keep real widget fields"
    )
    parser.add_argument("--form", choices=["125", "127", "137"])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--test-data-dir", type=Path, default=None)
    args = parser.parse_args()

    root = Path(__file__).parent
    test_data_dir = args.test_data_dir or root / "test_data"

    forms = ["125", "127", "137"] if args.all else ([args.form] if args.form else [])
    if not forms:
        parser.error("Specify --form or --all")

    for form_num in forms:
        folder_name = FORM_FOLDERS.get(form_num)
        if not folder_name:
            print(f"  ERROR: Unknown form {form_num}")
            continue

        folder = test_data_dir / folder_name
        if not folder.exists():
            print(f"  ERROR: Folder not found: {folder}")
            continue

        # Get widget names from first PDF
        pdfs = sorted(folder.glob("*.pdf"))
        if not pdfs:
            print(f"  ERROR: No PDFs in {folder}")
            continue

        widget_names = get_widget_names(pdfs[0])

        print(f"\nForm {form_num}: {len(widget_names)} widget fields from {pdfs[0].name}")
        print(f"  {'─'*60}")

        gt_files = sorted(folder.glob("*.json"))
        for gf in gt_files:
            gt_raw = json.loads(gf.read_text())

            # Count before
            flat_before = flatten_gt_for_comparison(gt_raw, form_num)
            before_count = len(flat_before)
            before_with_values = sum(
                1 for v in flat_before.values()
                if v is not None and str(v).strip()
                and str(v).strip().lower() not in ("", "null", "none")
            )

            # Clean
            cleaned = clean_gt_flat(gt_raw, form_num, widget_names)
            after_count = len(cleaned)
            after_with_values = sum(
                1 for v in cleaned.values()
                if v is not None and str(v).strip()
                and str(v).strip().lower() not in ("", "null", "none")
            )

            removed = before_count - after_count
            print(f"  {gf.name}:")
            print(f"    Before: {before_count} fields ({before_with_values} with values)")
            print(f"    After:  {after_count} fields ({after_with_values} with values)")
            print(f"    Removed: {removed} extra fields")

            if not args.dry_run:
                gf.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n")
                print(f"    Written: {gf}")
            else:
                print(f"    [DRY RUN] Would write {gf}")

    if args.dry_run:
        print("\n  (Dry run — no files were modified)")


if __name__ == "__main__":
    main()
