#!/usr/bin/env python3
"""Ingest human correction manifests into training data.

Reads correction manifests from finetune/corrections/ and generates:
  - SFT training examples (corrections.jsonl)
  - DPO preference pairs (correction_preferences.jsonl)

Correction manifest format:
{
  "form_type": "125",
  "stem": "ACORD_0125_..._00d73f3c",
  "corrections": {
    "FieldName": {"original_extracted": "wrong", "corrected_value": "right"}
  },
  "confirmed_correct": ["Field1", "Field2"]
}

Usage:
    .venv/bin/python finetune/ingest_corrections.py
    .venv/bin/python finetune/ingest_corrections.py --corrections-dir finetune/corrections/
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCHEMAS_DIR = ROOT / "schemas"
TEST_OUTPUT_DIR = ROOT / "test_output"
CORRECTIONS_DIR = ROOT / "finetune" / "corrections"
OUTPUT_DIR = ROOT / "finetune" / "data"

FORM_DIR_MAP = {
    "125": "form_125",
    "127": "form_127",
    "137": "form_137",
    "163": "form_163",
}

SCHEMA_MAP = {
    "125": "125.json",
    "127": "127.json",
    "137": "137.json",
    "163": "163.json",
}

SYSTEM_PROMPT = (
    "You are an expert ACORD insurance form data extractor. "
    "Given an image of an ACORD form page, extract the requested fields "
    "and return ONLY valid JSON with field names as keys and extracted values."
)


def load_schema(schema_file: str) -> dict:
    """Load schema and return fields dict."""
    path = SCHEMAS_DIR / schema_file
    data = json.loads(path.read_text())
    return data.get("fields", data)


def load_correction_manifest(path: Path) -> Dict[str, Any]:
    """Validate and load a correction manifest."""
    data = json.loads(path.read_text())

    required = ["form_type", "stem", "corrections"]
    for key in required:
        if key not in data:
            raise ValueError(f"Missing required key '{key}' in {path}")

    if not isinstance(data["corrections"], dict):
        raise ValueError(f"'corrections' must be a dict in {path}")

    return data


def _find_page_images(form_type: str, stem: str) -> List[Path]:
    """Find page images for a form in test_output."""
    form_dir = FORM_DIR_MAP.get(form_type, f"form_{form_type}")
    images_dir = TEST_OUTPUT_DIR / form_dir / stem / "images"
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


def _load_extracted(form_type: str, stem: str) -> Dict[str, Any]:
    """Load the extracted.json from test output for a form."""
    form_dir = FORM_DIR_MAP.get(form_type, f"form_{form_type}")
    extracted_path = TEST_OUTPUT_DIR / form_dir / stem / "extracted.json"
    if extracted_path.exists():
        return json.loads(extracted_path.read_text())
    return {}


def generate_correction_examples(
    manifest: Dict[str, Any],
) -> List[dict]:
    """Generate SFT training examples from a correction manifest.

    Creates per-page examples with corrected values as the target output.
    """
    form_type = manifest["form_type"]
    stem = manifest["stem"]
    corrections = manifest["corrections"]
    confirmed_correct = set(manifest.get("confirmed_correct", []))

    schema_file = SCHEMA_MAP.get(form_type)
    if not schema_file:
        print(f"  WARNING: Unknown form type '{form_type}', skipping")
        return []

    schema_fields = load_schema(schema_file)
    page_images = _find_page_images(form_type, stem)
    extracted = _load_extracted(form_type, stem)

    if not page_images:
        print(f"  WARNING: No page images found for {stem}")
        return []

    # Build the corrected GT: start from extracted, apply corrections
    corrected_gt = dict(extracted)
    for field_name, correction in corrections.items():
        corrected_gt[field_name] = correction["corrected_value"]

    # Group corrected + confirmed fields by page
    relevant_fields = set(corrections.keys()) | confirmed_correct
    page_fields: Dict[int, Dict[str, Any]] = {}
    for field_name in relevant_fields:
        if field_name not in corrected_gt:
            continue
        page_num = _get_page_for_field(field_name, schema_fields)
        if page_num not in page_fields:
            page_fields[page_num] = {}
        page_fields[page_num][field_name] = corrected_gt[field_name]

    examples = []
    for page_num, gt_values in page_fields.items():
        if page_num >= len(page_images) or not gt_values:
            continue
        image_path = page_images[page_num]

        user_text = (
            f"Extract ALL fields from this ACORD {form_type} form, "
            f"page {page_num + 1}. "
            f"Return a JSON object with field names as keys and their values."
        )

        example = {
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
                    "content": json.dumps(gt_values, ensure_ascii=False),
                },
            ],
            "images": [str(image_path.resolve())],
            "metadata": {"type": "correction", "stem": stem, "form_type": form_type},
        }
        examples.append(example)

    return examples


def generate_correction_preference_pairs(
    manifest: Dict[str, Any],
) -> List[dict]:
    """Generate DPO preference pairs from corrections (wrong vs corrected)."""
    form_type = manifest["form_type"]
    stem = manifest["stem"]
    corrections = manifest["corrections"]

    schema_file = SCHEMA_MAP.get(form_type)
    if not schema_file:
        return []

    schema_fields = load_schema(schema_file)
    page_images = _find_page_images(form_type, stem)
    extracted = _load_extracted(form_type, stem)

    if not page_images:
        return []

    # Group corrections by page
    page_corrections: Dict[int, Dict[str, Dict[str, Any]]] = {}
    for field_name, correction in corrections.items():
        page_num = _get_page_for_field(field_name, schema_fields)
        if page_num not in page_corrections:
            page_corrections[page_num] = {}
        page_corrections[page_num][field_name] = correction

    pairs = []
    for page_num, page_corr in page_corrections.items():
        if page_num >= len(page_images):
            continue
        image_path = page_images[page_num]

        # Build chosen (corrected) and rejected (original) responses
        chosen_json = {}
        rejected_json = {}
        for field_name, correction in page_corr.items():
            chosen_json[field_name] = correction["corrected_value"]
            rejected_json[field_name] = correction["original_extracted"]

        if not chosen_json:
            continue

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


def deduplicate_against_existing(
    new_examples: List[dict],
    existing_path: Path,
) -> List[dict]:
    """Remove examples that already exist in the target file."""
    if not existing_path.exists():
        return new_examples

    existing_keys: Set[str] = set()
    with open(existing_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            # Key: image path + assistant content
            images = tuple(ex.get("images", []))
            msgs = ex.get("messages", [])
            assistant = ""
            for m in msgs:
                if m.get("role") == "assistant":
                    assistant = m.get("content", "")
                    break
            existing_keys.add(f"{images}|{assistant}")

    deduped = []
    for ex in new_examples:
        images = tuple(ex.get("images", []))
        msgs = ex.get("messages", [])
        assistant = ""
        for m in msgs:
            if m.get("role") == "assistant":
                assistant = m.get("content", "")
                break
        key = f"{images}|{assistant}"
        if key not in existing_keys:
            deduped.append(ex)

    return deduped


def main():
    parser = argparse.ArgumentParser(
        description="Ingest human corrections into training data",
    )
    parser.add_argument(
        "--corrections-dir", type=Path, default=CORRECTIONS_DIR,
        help=f"Directory containing correction manifests (default: {CORRECTIONS_DIR})",
    )
    parser.add_argument(
        "--output", type=Path, default=OUTPUT_DIR / "corrections.jsonl",
        help="Output JSONL for SFT examples (default: finetune/data/corrections.jsonl)",
    )
    parser.add_argument(
        "--preference-output", type=Path, default=OUTPUT_DIR / "correction_preferences.jsonl",
        help="Output JSONL for DPO pairs (default: finetune/data/correction_preferences.jsonl)",
    )
    parser.add_argument(
        "--deduplicate", action="store_true", default=True,
        help="Deduplicate against existing output files (default: True)",
    )
    args = parser.parse_args()

    if not args.corrections_dir.exists():
        print(f"Corrections directory not found: {args.corrections_dir}")
        print("  Create it and add correction manifest JSON files.")
        sys.exit(1)

    # Find all correction manifests
    manifest_files = sorted(args.corrections_dir.glob("*.json"))
    if not manifest_files:
        print(f"No correction manifests found in {args.corrections_dir}")
        sys.exit(0)

    print(f"Found {len(manifest_files)} correction manifests")

    all_sft_examples = []
    all_dpo_pairs = []

    for mf in manifest_files:
        try:
            manifest = load_correction_manifest(mf)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  WARNING: Skipping {mf.name}: {e}")
            continue

        stem = manifest["stem"]
        form_type = manifest["form_type"]
        n_corrections = len(manifest["corrections"])
        print(f"  {mf.name}: form {form_type}, {stem}, {n_corrections} corrections")

        sft_examples = generate_correction_examples(manifest)
        dpo_pairs = generate_correction_preference_pairs(manifest)

        all_sft_examples.extend(sft_examples)
        all_dpo_pairs.extend(dpo_pairs)

    # Deduplicate
    if args.deduplicate:
        before = len(all_sft_examples)
        all_sft_examples = deduplicate_against_existing(all_sft_examples, args.output)
        if before != len(all_sft_examples):
            print(f"  Deduplication: {before} → {len(all_sft_examples)} SFT examples")

    # Write SFT examples
    if all_sft_examples:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "a") as f:
            for ex in all_sft_examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
        print(f"\nAppended {len(all_sft_examples)} SFT examples to {args.output}")
    else:
        print("\nNo new SFT examples generated")

    # Write DPO pairs
    if all_dpo_pairs:
        args.preference_output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.preference_output, "a") as f:
            for pair in all_dpo_pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")
        print(f"Appended {len(all_dpo_pairs)} DPO pairs to {args.preference_output}")


if __name__ == "__main__":
    main()
