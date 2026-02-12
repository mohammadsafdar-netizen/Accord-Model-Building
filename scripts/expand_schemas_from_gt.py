#!/usr/bin/env python3
"""
Expand ACORD schemas so that EVERY key present in ground truth is in the schema.
Collects all GT JSONs per form (125, 127, 137), flattens (127: Vehicle 1/2, Driver 1/2 -> _A, _B),
takes union of keys, and adds any missing key to the schema with inferred type/category/tooltip.

Run from best_project: python scripts/expand_schemas_from_gt.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Run from best_project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gt_flatten import flatten_gt_for_comparison

TEST_DATA_DIR = PROJECT_ROOT / "test_data"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"

# Map folder name patterns to form type
FOLDER_FORM_MAP = [
    ("0125", "125"),
    ("125", "125"),
    ("127", "127"),
    ("137", "137"),
]


def detect_form_type(folder_name: str) -> str | None:
    folder_lower = folder_name.lower()
    for pattern, form_type in FOLDER_FORM_MAP:
        if pattern in folder_lower:
            return form_type
    return None


def discover_gt_files_per_form() -> dict[str, list[Path]]:
    """Return {form_type: [path_to_gt_json, ...]}."""
    by_form: dict[str, list[Path]] = {}
    if not TEST_DATA_DIR.exists():
        return by_form
    for sub in sorted(TEST_DATA_DIR.iterdir()):
        if not sub.is_dir():
            continue
        form_type = detect_form_type(sub.name)
        if not form_type:
            continue
        if form_type not in by_form:
            by_form[form_type] = []
        for gt_path in sorted(sub.glob("*.json")):
            # Skip outputs under best_project_output
            if "best_project_output" in str(gt_path) or "test_output" in str(gt_path):
                continue
            by_form[form_type].append(gt_path)
    return by_form


def infer_type(value: object) -> str:
    if isinstance(value, bool):
        return "checkbox"
    if isinstance(value, (int, float)):
        return "text"  # schema uses text for numeric fields
    return "text"


def infer_category(key: str) -> str:
    key_lower = key.lower()
    if key_lower.startswith("vehicle_"):
        return "vehicle"
    if key_lower.startswith("driver_"):
        return "driver"
    if key_lower.startswith("policy_"):
        return "policy"
    if key_lower.startswith("producer_"):
        return "producer"
    if key_lower.startswith("insurer_"):
        return "insurer"
    if key_lower.startswith("namedinsured_") or key_lower.startswith("named_insured_"):
        return "named_insured"
    if key_lower.startswith("form_"):
        return "header"
    if key_lower.startswith("location") or key_lower.startswith("locationbuilding"):
        return "location"
    if "indicator" in key_lower or "checkbox" in key_lower:
        return "checkbox"
    if key_lower.startswith("commercialvehicle") or key_lower.startswith("commercial_vehicle"):
        return "vehicle"
    return "general"


def infer_suffix(key: str) -> str | None:
    """Return suffix _A, _B, _C if present at end of key."""
    parts = key.split("_")
    if len(parts) >= 2 and len(parts[-1]) == 1 and parts[-1].isalpha():
        return "_" + parts[-1]
    return None


def default_tooltip(key: str, field_type: str) -> str:
    if field_type == "checkbox":
        return f"Checkbox: {key}. Return 1 if checked, Off if not."
    return f"From GT: {key.replace('_', ' ')}"


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Expand schemas from all GT keys")
    p.add_argument("--dry-run", action="store_true", help="Print what would be added, do not write")
    args = p.parse_args()

    by_form = discover_gt_files_per_form()
    if not by_form:
        print("No test_data folders with GT JSONs found.")
        return

    for form_type in ("125", "127", "137"):
        paths = by_form.get(form_type, [])
        if not paths:
            print(f"  [SKIP] Form {form_type}: no GT files.")
            continue
        all_keys: set[str] = set()
        sample_values: dict[str, object] = {}  # key -> first seen value (for type inference)
        for gt_path in paths:
            try:
                gt = json.loads(gt_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  [WARN] Could not load {gt_path}: {e}")
                continue
            flat = flatten_gt_for_comparison(gt, form_type)
            for k, v in flat.items():
                all_keys.add(k)
                if k not in sample_values:
                    sample_values[k] = v
        if not all_keys:
            continue
        # Infer types from sample values for new keys when we add them
        def infer_type_from_key(key: str) -> str:
            if key in sample_values:
                return infer_type(sample_values[key])
            return "text"

        schema_path = SCHEMAS_DIR / f"{form_type}.json"
        if not schema_path.exists():
            continue
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        fields = data["fields"]
        existing = set(fields.keys())
        to_add = all_keys - existing
        if not to_add:
            print(f"  Form {form_type}: schema already has all {len(existing)} GT keys.")
            continue
        added = 0
        for key in sorted(to_add):
            field_type = infer_type_from_key(key)
            category = infer_category(key)
            suffix = infer_suffix(key)
            if suffix is None:
                suffix = "_A"
            elif not suffix.startswith("_"):
                suffix = "_" + suffix
            tooltip = default_tooltip(key, field_type)
            fields[key] = {
                "name": key,
                "type": field_type,
                "tooltip": tooltip,
                "default_value": None,
                "category": category,
                "suffix": suffix,
            }
            added += 1
        data["fields"] = dict(sorted(fields.items()))
        data["total_fields"] = len(fields)
        if not args.dry_run:
            schema_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"  Form {form_type}: added {added} fields (total {len(fields)}).")
    print("Done.")


if __name__ == "__main__":
    main()
