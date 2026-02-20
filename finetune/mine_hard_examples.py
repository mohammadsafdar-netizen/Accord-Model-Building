#!/usr/bin/env python3
"""Mine hard training examples from pipeline errors.

Analyzes comparison.json files from test runs to find wrong/partial/missing
fields, then generates targeted training examples for fine-tuning.

Three strategies:
  1. focused_category  — category examples with only error-prone fields
  2. error_correction  — prompt includes wrong value, asks model to re-extract
  3. hard_field_subset — top-N hardest fields grouped into focused examples

Output: finetune/data/hard_examples.jsonl (same format as prepare_dataset.py)

Usage:
    .venv/bin/python finetune/mine_hard_examples.py --report
    .venv/bin/python finetune/mine_hard_examples.py --output finetune/data/hard_examples.jsonl
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

# Reuse from prepare_dataset
SCHEMAS_DIR = ROOT / "schemas"
TEST_OUTPUT_DIR = ROOT / "test_output"
OUTPUT_DIR = ROOT / "finetune" / "data"

FORM_TYPES = {
    "ACORD_0125": ("125", "125.json"),
    "127_Business_Auto": ("127", "127.json"),
    "ACORD_137": ("137", "137.json"),
    "ACORD_163": ("163", "163.json"),
}

SYSTEM_PROMPT = (
    "You are an expert ACORD insurance form data extractor. "
    "Given an image of an ACORD form page, extract the requested fields "
    "and return ONLY valid JSON with field names as keys and extracted values."
)

# Map form_type directory prefix to form number
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


def detect_form_type_from_dir(form_dir_name: str) -> Optional[Tuple[str, str]]:
    """Detect form type from test_output directory name like 'form_125'."""
    return FORM_DIR_PREFIX.get(form_dir_name)


def find_comparison_files(test_output_dir: Path) -> List[Dict[str, Any]]:
    """Scan test_output for comparison.json files.

    Returns list of dicts with: form_type, schema_file, stem, comparison_path,
    images_dir, gt_path, extracted_path.
    """
    results = []
    for form_dir in sorted(test_output_dir.iterdir()):
        if not form_dir.is_dir() or not form_dir.name.startswith("form_"):
            continue
        type_info = detect_form_type_from_dir(form_dir.name)
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
                "gt_path": stem_dir / "gt.json",
                "extracted_path": stem_dir / "extracted.json",
            })
    return results


def analyze_errors(
    comparisons: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Aggregate errors by field name across all comparisons.

    Returns: {field_name: [error_info, ...]} where error_info contains:
        form_type, stem, status, expected, extracted, category, field_type.
    """
    errors: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for comp_info in comparisons:
        form_type = comp_info["form_type"]
        stem = comp_info["stem"]
        schema_file = comp_info["schema_file"]

        comparison = json.loads(comp_info["comparison_path"].read_text())
        schema_fields = load_schema(schema_file)

        field_results = comparison.get("field_results", {})
        for field_name, result in field_results.items():
            status = result.get("status", "matched")
            if status == "matched":
                continue

            field_def = schema_fields.get(field_name, {})
            category = field_def.get("category", "general") if isinstance(field_def, dict) else "general"
            field_type = field_def.get("type", "text") if isinstance(field_def, dict) else "text"

            errors[field_name].append({
                "form_type": form_type,
                "stem": stem,
                "status": status,
                "expected": result.get("expected"),
                "extracted": result.get("extracted"),
                "category": category,
                "field_type": field_type,
            })

    return dict(errors)


def _find_page_images(images_dir: Path, stem: str) -> List[Path]:
    """Find page images for a form stem. Returns sorted list of page image paths."""
    if not images_dir.exists():
        return []
    # Pattern: {stem}_page_{N}.png
    images = sorted(images_dir.glob(f"{stem}_page_*.png"))
    # Exclude _clean variants for training (use original scanned images)
    images = [p for p in images if "_clean" not in p.name]
    if not images:
        # Fallback: try any page_*.png
        images = sorted(images_dir.glob("*_page_*.png"))
        images = [p for p in images if "_clean" not in p.name]
    return images


def _get_page_for_field(field_name: str, schema_fields: dict) -> int:
    """Get page number (0-indexed) for a field from schema."""
    field_def = schema_fields.get(field_name, {})
    if isinstance(field_def, dict):
        return field_def.get("page", 0)
    return 0


def make_example(
    image_path: Path,
    user_text: str,
    assistant_json: dict,
    example_type: str = "hard",
) -> dict:
    """Create a single training example in Unsloth conversation format."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": user_text},
                ],
            },
            {
                "role": "assistant",
                "content": json.dumps(assistant_json, ensure_ascii=False),
            },
        ],
        "images": [str(image_path.resolve())],
        "metadata": {"type": example_type},
    }


def generate_focused_category_examples(
    errors: Dict[str, List[Dict[str, Any]]],
    comparisons: List[Dict[str, Any]],
    min_error_count: int = 1,
) -> List[dict]:
    """Strategy 1: Category examples with only error-prone fields.

    For each (form_type, stem, category) that has errors, generate a training
    example focusing on the error-prone fields with correct GT values.
    """
    examples = []

    # Group errors by (form_type, stem, category)
    groups: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    for field_name, error_list in errors.items():
        if len(error_list) < min_error_count:
            continue
        for err in error_list:
            key = (err["form_type"], err["stem"], err["category"])
            if field_name not in groups[key]:
                groups[key].append(field_name)

    # Build lookup from (form_type, stem) -> comp_info
    comp_lookup = {}
    for comp_info in comparisons:
        comp_lookup[(comp_info["form_type"], comp_info["stem"])] = comp_info

    for (form_type, stem, category), field_names in groups.items():
        comp_info = comp_lookup.get((form_type, stem))
        if not comp_info:
            continue

        schema_fields = load_schema(comp_info["schema_file"])
        comparison = json.loads(comp_info["comparison_path"].read_text())
        field_results = comparison.get("field_results", {})

        # Build GT dict for these fields
        gt_values = {}
        for fname in field_names:
            result = field_results.get(fname, {})
            expected = result.get("expected")
            if expected is not None:
                gt_values[fname] = expected

        if not gt_values:
            continue

        # Find the page image for these fields
        page_nums = set()
        for fname in field_names:
            page_nums.add(_get_page_for_field(fname, schema_fields))

        page_images = _find_page_images(comp_info["images_dir"], stem)

        for page_num in page_nums:
            if page_num >= len(page_images):
                continue
            image_path = page_images[page_num]

            # Filter to fields on this page
            page_gt = {}
            for fname, val in gt_values.items():
                if _get_page_for_field(fname, schema_fields) == page_num:
                    page_gt[fname] = val

            if not page_gt:
                continue

            cat_label = category.replace("_", " ").title()
            user_text = (
                f"Extract the {cat_label} fields from this ACORD {form_type} form page. "
                f"Pay special attention to these commonly misread fields. "
                f"Return a JSON object with field names as keys and their values. "
                f"Fields to extract: {', '.join(sorted(page_gt.keys()))}"
            )
            examples.append(make_example(image_path, user_text, page_gt, "focused_category"))

    return examples


def generate_error_correction_examples(
    errors: Dict[str, List[Dict[str, Any]]],
    comparisons: List[Dict[str, Any]],
    min_error_count: int = 1,
) -> List[dict]:
    """Strategy 2: Error correction examples.

    Prompt includes the wrong value and asks the model to re-extract correctly.
    Teaches the model to recognize and fix its own mistakes.
    """
    examples = []

    comp_lookup = {}
    for comp_info in comparisons:
        comp_lookup[(comp_info["form_type"], comp_info["stem"])] = comp_info

    # Group errors by (form_type, stem, page)
    page_errors: Dict[Tuple[str, str, int], List[Dict[str, Any]]] = defaultdict(list)
    for field_name, error_list in errors.items():
        if len(error_list) < min_error_count:
            continue
        for err in error_list:
            if err["status"] not in ("wrong", "partial_match"):
                continue
            comp_info = comp_lookup.get((err["form_type"], err["stem"]))
            if not comp_info:
                continue
            schema_fields = load_schema(comp_info["schema_file"])
            page_num = _get_page_for_field(field_name, schema_fields)
            key = (err["form_type"], err["stem"], page_num)
            page_errors[key].append({
                "field_name": field_name,
                "expected": err["expected"],
                "extracted": err["extracted"],
            })

    for (form_type, stem, page_num), field_errors in page_errors.items():
        comp_info = comp_lookup.get((form_type, stem))
        if not comp_info:
            continue

        page_images = _find_page_images(comp_info["images_dir"], stem)
        if page_num >= len(page_images):
            continue
        image_path = page_images[page_num]

        # Build the correction prompt
        wrong_lines = []
        gt_values = {}
        for fe in field_errors:
            wrong_lines.append(f"  - {fe['field_name']}: extracted \"{fe['extracted']}\" (incorrect)")
            gt_values[fe["field_name"]] = fe["expected"]

        user_text = (
            f"Look at this ACORD {form_type} form page carefully. "
            f"Previous extraction got these fields wrong:\n"
            + "\n".join(wrong_lines) + "\n\n"
            f"Re-extract these fields with the correct values. "
            f"Return a JSON object with field names as keys and corrected values."
        )
        examples.append(make_example(image_path, user_text, gt_values, "error_correction"))

    return examples


def generate_hard_field_subset_examples(
    errors: Dict[str, List[Dict[str, Any]]],
    comparisons: List[Dict[str, Any]],
    top_n: int = 50,
) -> List[dict]:
    """Strategy 3: Top-N hardest fields grouped into focused examples.

    Ranks fields by total error count and generates examples that focus
    specifically on these hard fields.
    """
    examples = []

    # Rank fields by error count
    ranked = sorted(errors.items(), key=lambda x: len(x[1]), reverse=True)[:top_n]
    hard_field_names = {name for name, _ in ranked}

    if not hard_field_names:
        return examples

    comp_lookup = {}
    for comp_info in comparisons:
        comp_lookup[(comp_info["form_type"], comp_info["stem"])] = comp_info

    # For each comparison file, generate an example with only the hard fields
    for comp_info in comparisons:
        form_type = comp_info["form_type"]
        stem = comp_info["stem"]
        schema_fields = load_schema(comp_info["schema_file"])
        comparison = json.loads(comp_info["comparison_path"].read_text())
        field_results = comparison.get("field_results", {})

        # Group hard fields by page
        page_fields: Dict[int, Dict[str, Any]] = defaultdict(dict)
        for field_name in hard_field_names:
            if field_name not in field_results:
                continue
            result = field_results[field_name]
            expected = result.get("expected")
            if expected is None:
                continue
            page_num = _get_page_for_field(field_name, schema_fields)
            page_fields[page_num][field_name] = expected

        page_images = _find_page_images(comp_info["images_dir"], stem)

        for page_num, gt_values in page_fields.items():
            if page_num >= len(page_images) or not gt_values:
                continue
            image_path = page_images[page_num]

            user_text = (
                f"Extract these specific fields from this ACORD {form_type} form page. "
                f"These fields are frequently misread — examine the form carefully. "
                f"Return a JSON object with field names as keys and their values. "
                f"Fields: {', '.join(sorted(gt_values.keys()))}"
            )
            examples.append(make_example(image_path, user_text, gt_values, "hard_field_subset"))

    return examples


def print_error_report(
    errors: Dict[str, List[Dict[str, Any]]],
    comparisons: List[Dict[str, Any]],
    top_n: int = 50,
) -> None:
    """Print analysis of errors across all comparisons."""
    print(f"\n{'='*70}")
    print(f"  HARD EXAMPLE MINING — ERROR ANALYSIS")
    print(f"{'='*70}")
    print(f"\n  Comparison files analyzed: {len(comparisons)}")
    print(f"  Total fields with errors: {len(errors)}")

    total_errors = sum(len(v) for v in errors.values())
    print(f"  Total error instances: {total_errors}")

    # Error type breakdown
    type_counts = defaultdict(int)
    for error_list in errors.values():
        for err in error_list:
            type_counts[err["status"]] += 1
    print(f"\n  Error type breakdown:")
    for status, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {status}: {count}")

    # Category breakdown
    cat_counts = defaultdict(int)
    for error_list in errors.values():
        for err in error_list:
            cat_counts[err["category"]] += 1
    print(f"\n  Errors by category:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"    {cat}: {count}")

    # Form type breakdown
    form_counts = defaultdict(int)
    for error_list in errors.values():
        for err in error_list:
            form_counts[err["form_type"]] += 1
    print(f"\n  Errors by form type:")
    for ft, count in sorted(form_counts.items()):
        print(f"    Form {ft}: {count}")

    # Top-N hardest fields
    ranked = sorted(errors.items(), key=lambda x: len(x[1]), reverse=True)[:top_n]
    print(f"\n  Top {min(top_n, len(ranked))} hardest fields:")
    for field_name, error_list in ranked:
        statuses = [e["status"] for e in error_list]
        wrong = statuses.count("wrong")
        partial = statuses.count("partial_match")
        missing = statuses.count("missing")
        parts = []
        if wrong:
            parts.append(f"{wrong}W")
        if partial:
            parts.append(f"{partial}P")
        if missing:
            parts.append(f"{missing}M")
        cat = error_list[0]["category"]
        print(f"    {field_name} ({cat}): {len(error_list)} errors ({'/'.join(parts)})")

    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Mine hard training examples from pipeline errors",
    )
    parser.add_argument(
        "--test-output-dir", type=Path, default=TEST_OUTPUT_DIR,
        help=f"Test output directory (default: {TEST_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--output", type=Path, default=OUTPUT_DIR / "hard_examples.jsonl",
        help="Output JSONL file (default: finetune/data/hard_examples.jsonl)",
    )
    parser.add_argument(
        "--min-error-count", type=int, default=1,
        help="Minimum error count for a field to be included (default: 1)",
    )
    parser.add_argument(
        "--strategies", type=str, default="focused_category,error_correction,hard_field_subset",
        help="Comma-separated strategies to use (default: all three)",
    )
    parser.add_argument(
        "--top-n-fields", type=int, default=50,
        help="Top N hardest fields for hard_field_subset strategy (default: 50)",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Print error analysis report only (no example generation)",
    )
    args = parser.parse_args()

    # Find all comparison files
    comparisons = find_comparison_files(args.test_output_dir)
    if not comparisons:
        print(f"No comparison.json files found in {args.test_output_dir}")
        sys.exit(1)

    print(f"Found {len(comparisons)} comparison files")

    # Analyze errors
    errors = analyze_errors(comparisons)
    if not errors:
        print("No errors found across all comparisons")
        sys.exit(0)

    # Report mode
    print_error_report(errors, comparisons, top_n=args.top_n_fields)
    if args.report:
        return

    # Generate examples
    strategies = [s.strip() for s in args.strategies.split(",")]
    all_examples = []

    for strategy in strategies:
        if strategy == "focused_category":
            examples = generate_focused_category_examples(
                errors, comparisons, min_error_count=args.min_error_count,
            )
            print(f"  [focused_category] Generated {len(examples)} examples")
            all_examples.extend(examples)

        elif strategy == "error_correction":
            examples = generate_error_correction_examples(
                errors, comparisons, min_error_count=args.min_error_count,
            )
            print(f"  [error_correction] Generated {len(examples)} examples")
            all_examples.extend(examples)

        elif strategy == "hard_field_subset":
            examples = generate_hard_field_subset_examples(
                errors, comparisons, top_n=args.top_n_fields,
            )
            print(f"  [hard_field_subset] Generated {len(examples)} examples")
            all_examples.extend(examples)

        else:
            print(f"  WARNING: Unknown strategy '{strategy}', skipping")

    if not all_examples:
        print("No examples generated")
        sys.exit(0)

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(all_examples)} hard examples to {args.output}")


if __name__ == "__main__":
    main()
