#!/usr/bin/env python3
"""Build DPO preference pairs from pipeline comparison results.

Reads comparison.json files and generates preference pairs where:
  - chosen  = extraction with ground truth (correct) values
  - rejected = extraction with model's wrong values (incorrect)

Output format follows TRL conversational DPO with shared prompts.

Usage:
    .venv/bin/python finetune/build_preference_pairs.py
    .venv/bin/python finetune/build_preference_pairs.py --include-partial --include-missing
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCHEMAS_DIR = ROOT / "schemas"
TEST_OUTPUT_DIR = ROOT / "test_output"
OUTPUT_DIR = ROOT / "finetune" / "data"

SYSTEM_PROMPT = (
    "You are an expert ACORD insurance form data extractor. "
    "Given an image of an ACORD form page, extract the requested fields "
    "and return ONLY valid JSON with field names as keys and extracted values."
)

FORM_DIR_PREFIX = {
    "form_125": ("125", "125.json"),
    "form_127": ("127", "127.json"),
    "form_137": ("137", "137.json"),
    "form_163": ("163", "163.json"),
}


def load_schema(schema_file: str) -> dict:
    """Load schema and return fields dict."""
    path = SCHEMAS_DIR / schema_file
    data = json.loads(path.read_text())
    return data.get("fields", data)


def find_comparison_files(test_output_dir: Path) -> List[Dict[str, Any]]:
    """Scan test_output for comparison.json files with associated data."""
    results = []
    for form_dir in sorted(test_output_dir.iterdir()):
        if not form_dir.is_dir() or not form_dir.name.startswith("form_"):
            continue
        type_info = FORM_DIR_PREFIX.get(form_dir.name)
        if not type_info:
            continue
        form_number, schema_file = type_info

        for stem_dir in sorted(form_dir.iterdir()):
            if not stem_dir.is_dir():
                continue
            comp_path = stem_dir / "comparison.json"
            if not comp_path.exists():
                continue
            results.append({
                "form_type": form_number,
                "schema_file": schema_file,
                "stem": stem_dir.name,
                "comparison_path": comp_path,
                "images_dir": stem_dir / "images",
                "extracted_path": stem_dir / "extracted.json",
            })
    return results


def _find_page_images(images_dir: Path, stem: str) -> List[Path]:
    """Find page images for a form stem."""
    if not images_dir.exists():
        return []
    images = sorted(images_dir.glob(f"{stem}_page_*.png"))
    images = [p for p in images if "_clean" not in p.name]
    if not images:
        images = sorted(images_dir.glob("*_page_*.png"))
        images = [p for p in images if "_clean" not in p.name]
    return images


def _get_page_for_field(field_name: str, schema_fields: dict) -> int:
    """Get page number (0-indexed) for a field from schema."""
    field_def = schema_fields.get(field_name, {})
    if isinstance(field_def, dict):
        return field_def.get("page", 0)
    return 0


def build_preference_pairs(
    comparisons: List[Dict[str, Any]],
    include_partial: bool = False,
    include_missing: bool = False,
) -> List[dict]:
    """Generate DPO preference pairs from comparison results.

    For each page with errors, creates a pair where:
      - chosen: response with GT values (correct)
      - rejected: response with model's extracted values (wrong)
    """
    pairs = []
    error_statuses = {"wrong"}
    if include_partial:
        error_statuses.add("partial_match")
    if include_missing:
        error_statuses.add("missing")

    for comp_info in comparisons:
        form_type = comp_info["form_type"]
        stem = comp_info["stem"]
        schema_fields = load_schema(comp_info["schema_file"])
        comparison = json.loads(comp_info["comparison_path"].read_text())
        field_results = comparison.get("field_results", {})

        # Group errors by page
        page_errors: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for field_name, result in field_results.items():
            status = result.get("status", "matched")
            if status not in error_statuses:
                continue
            page_num = _get_page_for_field(field_name, schema_fields)
            page_errors[page_num].append({
                "field_name": field_name,
                "expected": result.get("expected"),
                "extracted": result.get("extracted"),
                "status": status,
            })

        if not page_errors:
            continue

        page_images = _find_page_images(comp_info["images_dir"], stem)

        for page_num, errors in page_errors.items():
            if page_num >= len(page_images):
                continue
            image_path = page_images[page_num]

            # Build the chosen (GT) and rejected (model output) JSON dicts
            # Include ALL fields for this page (correct + wrong) to provide full context
            chosen_json = {}
            rejected_json = {}

            for field_name, result in field_results.items():
                if _get_page_for_field(field_name, schema_fields) != page_num:
                    continue
                expected = result.get("expected")
                extracted = result.get("extracted")
                if expected is not None:
                    chosen_json[field_name] = expected
                if extracted is not None:
                    rejected_json[field_name] = extracted
                elif expected is not None:
                    # Missing field: rejected omits it, chosen includes it
                    pass

            if not chosen_json or not rejected_json:
                continue

            # Skip if chosen and rejected are identical
            if json.dumps(chosen_json, sort_keys=True) == json.dumps(rejected_json, sort_keys=True):
                continue

            field_list = ", ".join(sorted(chosen_json.keys()))
            user_text = (
                f"Extract ALL fields from this ACORD {form_type} form, "
                f"page {page_num + 1}. "
                f"Return a JSON object with field names as keys and their values."
            )

            user_content = [
                {"type": "image"},
                {"type": "text", "text": user_text},
            ]

            pair = {
                "chosen": [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": json.dumps(chosen_json, ensure_ascii=False)},
                ],
                "rejected": [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": json.dumps(rejected_json, ensure_ascii=False)},
                ],
                "images": [str(image_path.resolve())],
            }
            pairs.append(pair)

    return pairs


def main():
    parser = argparse.ArgumentParser(
        description="Build DPO preference pairs from comparison results",
    )
    parser.add_argument(
        "--test-output-dir", type=Path, default=TEST_OUTPUT_DIR,
        help=f"Test output directory (default: {TEST_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--output", type=Path, default=OUTPUT_DIR / "preference_pairs.jsonl",
        help="Output JSONL file (default: finetune/data/preference_pairs.jsonl)",
    )
    parser.add_argument(
        "--include-partial", action="store_true",
        help="Include partial matches as errors in preference pairs",
    )
    parser.add_argument(
        "--include-missing", action="store_true",
        help="Include missing fields as errors in preference pairs",
    )
    args = parser.parse_args()

    # Find comparison files
    comparisons = find_comparison_files(args.test_output_dir)
    if not comparisons:
        print(f"No comparison.json files found in {args.test_output_dir}")
        sys.exit(1)

    print(f"Found {len(comparisons)} comparison files")

    # Build preference pairs
    pairs = build_preference_pairs(
        comparisons,
        include_partial=args.include_partial,
        include_missing=args.include_missing,
    )

    if not pairs:
        print("No preference pairs generated (no errors found)")
        sys.exit(0)

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"Generated {len(pairs)} preference pairs → {args.output}")


if __name__ == "__main__":
    main()
