#!/usr/bin/env python3
"""
Verify extracted JSON against ground truth.
Compares extracted.json to a GT file and prints accuracy report.

Usage:
  python verify_against_gt.py --extracted path/to/extracted.json --ground-truth path/to/gt.json [--form 125]
  python verify_against_gt.py --extracted test_output/form_125/ACORD_..._4b87c3fc/extracted.json  # GT auto: same stem .json in test_data
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare import compare_fields, load_ground_truth, print_report
from gt_flatten import flatten_gt_for_comparison
from schema_registry import SchemaRegistry


def main():
    p = argparse.ArgumentParser(description="Compare extracted.json to ground truth")
    p.add_argument("--extracted", type=Path, required=True, help="Path to extracted.json")
    p.add_argument("--ground-truth", type=Path, default=None, help="Path to GT JSON (default: infer from extracted path)")
    p.add_argument("--form", type=str, default="125", choices=("125", "127", "137"), help="Form type for flattening GT")
    p.add_argument("--save", type=Path, default=None, help="Save comparison.json to this path")
    args = p.parse_args()

    extracted_path = Path(args.extracted)
    if not extracted_path.exists():
        print(f"Error: extracted file not found: {extracted_path}")
        return 1

    with open(extracted_path, encoding="utf-8") as f:
        extracted = json.load(f)

    gt_path = args.ground_truth
    if gt_path is None:
        # Infer: test_output/form_125/<stem>/extracted.json -> test_data/.../ form with same stem
        stem = extracted_path.parent.name
        for test_dir in [Path(__file__).parent / "test_data"]:
            for sub in test_dir.iterdir():
                if not sub.is_dir():
                    continue
                candidate = sub / f"{stem}.json"
                if candidate.exists():
                    gt_path = candidate
                    break
            if gt_path is not None:
                break
    if gt_path is None:
        gt_path = extracted_path.parent / "ground_truth.json"  # fallback
    gt_path = Path(gt_path)
    if not gt_path.exists():
        print(f"Error: ground truth not found: {gt_path}")
        print("  Use --ground-truth path/to/gt.json")
        return 1

    gt_raw = load_ground_truth(gt_path)
    gt_flat = flatten_gt_for_comparison(gt_raw, args.form)

    registry = SchemaRegistry(schemas_dir=Path(__file__).parent / "schemas")
    schema = registry.get_schema(args.form)
    checkbox_fields = set()
    if schema:
        for fname, finfo in schema.fields.items():
            if getattr(finfo, "field_type", None) in ("checkbox", "radio"):
                checkbox_fields.add(fname)

    comparison = compare_fields(extracted, gt_flat, None, checkbox_fields)
    print_report(comparison, title=f"Extracted vs GT — {extracted_path.parent.name}")

    if args.save:
        args.save = Path(args.save)
        args.save.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)
        print(f"  Comparison saved to {args.save}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
