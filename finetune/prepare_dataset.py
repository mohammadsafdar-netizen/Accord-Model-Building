#!/usr/bin/env python3
"""Prepare fine-tuning dataset from ACORD forms + ground truth.

Generates training examples in Unsloth conversation format:
  - Per-page full extraction (all non-null fields on that page)
  - Per-category extraction (fields grouped by category)
  - Checkbox-focused extraction (only checkbox fields per page)

Outputs: finetune/data/train.jsonl, finetune/data/val.jsonl

Usage:
    .venv/bin/python finetune/prepare_dataset.py
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Configuration ──────────────────────────────────────────────────────
SCHEMAS_DIR = ROOT / "schemas"
TEST_DATA_DIR = ROOT / "test_data"
OUTPUT_DIR = ROOT / "finetune" / "data"
DPI = 300

# Form type mapping: directory name prefix → (form_number, schema file)
FORM_TYPES = {
    "ACORD_0125": ("125", "125.json"),
    "127_Business_Auto": ("127", "127.json"),
    "ACORD_137": ("137", "137.json"),
}

# Validation holdout: one form per type (by hash suffix)
# These will go into val.jsonl, everything else into train.jsonl
VAL_HOLDOUT_HASHES = {
    "125": "49df78c7",   # ACORD 125
    "127": "b07a4a25",   # ACORD 127
}
# 137 only has 1 form, so it stays in training

# System prompt for all training examples
SYSTEM_PROMPT = (
    "You are an expert ACORD insurance form data extractor. "
    "Given an image of an ACORD form page, extract the requested fields "
    "and return ONLY valid JSON with field names as keys and extracted values."
)


def detect_form_type(dirname: str) -> tuple[str, str] | None:
    """Detect form type from directory name. Returns (form_number, schema_file) or None."""
    for prefix, info in FORM_TYPES.items():
        if dirname.startswith(prefix):
            return info
    return None


def load_schema(schema_file: str) -> dict:
    """Load schema and return fields dict."""
    path = SCHEMAS_DIR / schema_file
    data = json.loads(path.read_text())
    return data.get("fields", data)


def get_form_hash(filename: str) -> str:
    """Extract the hash suffix from a form filename (e.g., '169592d5' from '...169592d5.json')."""
    return Path(filename).stem.rsplit("_", 1)[-1]


def find_all_forms() -> list[dict]:
    """Discover all forms with GT JSON and PDF files."""
    forms = []
    for subdir in sorted(TEST_DATA_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        form_info = detect_form_type(subdir.name)
        if form_info is None:
            continue
        form_number, schema_file = form_info

        # Find all GT JSON + PDF pairs
        json_files = sorted(subdir.glob("*.json"))
        for gt_json in json_files:
            pdf_path = gt_json.with_suffix(".pdf")
            if not pdf_path.exists():
                continue
            form_hash = get_form_hash(gt_json.name)
            forms.append({
                "form_number": form_number,
                "schema_file": schema_file,
                "gt_json": gt_json,
                "pdf_path": pdf_path,
                "form_hash": form_hash,
                "dirname": subdir.name,
            })
    return forms


def render_pdf_pages(pdf_path: Path, output_dir: Path) -> list[Path]:
    """Render PDF pages to PNG images. Returns list of image paths (1-indexed filenames)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    # Try PyMuPDF first (faster, no poppler dependency)
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        for i, page in enumerate(doc, 1):
            out = output_dir / f"{pdf_path.stem}_page_{i}.png"
            if not out.exists():
                mat = fitz.Matrix(DPI / 72, DPI / 72)
                pix = page.get_pixmap(matrix=mat)
                pix.save(str(out))
            paths.append(out)
        doc.close()
        return paths
    except ImportError:
        pass

    # Fallback to pdf2image
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(str(pdf_path), dpi=DPI)
        for i, img in enumerate(images, 1):
            out = output_dir / f"{pdf_path.stem}_page_{i}.png"
            if not out.exists():
                img.save(str(out), "PNG")
            paths.append(out)
        return paths
    except ImportError:
        raise RuntimeError(
            "No PDF renderer available. Install pymupdf or pdf2image."
        )


def get_page_images(form: dict) -> list[Path]:
    """Get or render page images for a form. Returns list of image paths."""
    # Check test_output for pre-rendered images
    form_number = form["form_number"]
    form_hash = form["form_hash"]
    form_dir_name = form["pdf_path"].stem

    test_output_img_dir = ROOT / "test_output" / f"form_{form_number}" / form_dir_name / "images"
    if test_output_img_dir.exists():
        # Use existing images (non-clean versions)
        pages = sorted([
            f for f in test_output_img_dir.iterdir()
            if f.suffix == ".png" and "_clean" not in f.name
        ])
        if pages:
            return pages

    # Render from PDF
    render_dir = OUTPUT_DIR / "images" / form_dir_name
    return render_pdf_pages(form["pdf_path"], render_dir)


def get_fields_for_page(fields: dict, page_num: int) -> dict:
    """Get all fields assigned to a specific page (0-indexed)."""
    return {
        k: v for k, v in fields.items()
        if isinstance(v, dict) and v.get("page") == page_num
    }


def get_gt_for_fields(gt: dict, field_defs: dict) -> dict:
    """Get GT values for a set of field definitions. Skip null/empty."""
    result = {}
    for field_name, field_def in field_defs.items():
        if field_name in gt:
            val = gt[field_name]
            # Normalize checkbox values
            if field_def.get("type") == "checkbox":
                if val is True or val == "1" or val == "Yes":
                    val = True
                elif val is False or val == "Off" or val == "0" or val == "No":
                    val = False
            # Keep the field if it has a meaningful value
            if val is not None and val != "" and val != "Off":
                result[field_name] = val
    return result


def make_example(
    image_path: Path,
    user_text: str,
    assistant_json: dict,
    example_type: str = "full",
) -> dict:
    """Create a single training example in Unsloth conversation format."""
    return {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
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


def generate_examples(form: dict) -> list[dict]:
    """Generate all training examples for a single form."""
    examples = []

    # Load GT and schema
    gt = json.loads(form["gt_json"].read_text())
    fields = load_schema(form["schema_file"])
    form_number = form["form_number"]

    # Get page images
    page_images = get_page_images(form)
    num_pages = len(page_images)

    for page_idx in range(num_pages):
        page_num = page_idx  # Schema uses 0-indexed pages
        image_path = page_images[page_idx]

        # Get fields for this page
        page_fields = get_fields_for_page(fields, page_num)
        if not page_fields:
            continue

        # ── 1. Full-page extraction ──
        page_gt = get_gt_for_fields(gt, page_fields)
        if page_gt:
            user_text = (
                f"Extract ALL fields from this ACORD {form_number} form, "
                f"page {page_idx + 1} of {num_pages}. "
                f"Return a JSON object with field names as keys and their values."
            )
            examples.append(make_example(image_path, user_text, page_gt, "full_page"))

        # ── 2. Per-category extraction ──
        categories = defaultdict(dict)
        for fname, fdef in page_fields.items():
            cat = fdef.get("category", "general")
            categories[cat][fname] = fdef

        for cat, cat_fields in categories.items():
            cat_gt = get_gt_for_fields(gt, cat_fields)
            if not cat_gt:
                continue
            cat_label = cat.replace("_", " ").title()
            user_text = (
                f"Extract the {cat_label} fields from this ACORD {form_number} form page. "
                f"Return a JSON object with field names as keys and their values. "
                f"Fields to extract: {', '.join(sorted(cat_fields.keys()))}"
            )
            examples.append(make_example(image_path, user_text, cat_gt, f"category_{cat}"))

        # ── 3. Checkbox-focused extraction ──
        checkbox_fields = {
            k: v for k, v in page_fields.items()
            if isinstance(v, dict) and v.get("type") == "checkbox"
        }
        if checkbox_fields:
            checkbox_gt = get_gt_for_fields(gt, checkbox_fields)
            # For checkboxes, also include unchecked ones explicitly
            for fname in checkbox_fields:
                if fname not in checkbox_gt:
                    checkbox_gt[fname] = False

            if checkbox_gt:
                user_text = (
                    f"Look at this ACORD {form_number} form page and determine which "
                    f"checkboxes are checked. Return a JSON object with each checkbox "
                    f"field name mapped to true (checked) or false (unchecked). "
                    f"Checkboxes: {', '.join(sorted(checkbox_fields.keys()))}"
                )
                examples.append(make_example(image_path, user_text, checkbox_gt, "checkbox"))

    return examples


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Discover forms
    forms = find_all_forms()
    print(f"Found {len(forms)} forms:")
    for f in forms:
        print(f"  ACORD {f['form_number']}: {f['pdf_path'].name} (hash: {f['form_hash']})")

    # Split into train/val
    train_forms = []
    val_forms = []
    for f in forms:
        if f["form_hash"] in VAL_HOLDOUT_HASHES.get(f["form_number"], ""):
            val_forms.append(f)
        else:
            train_forms.append(f)

    print(f"\nTrain forms: {len(train_forms)}, Validation forms: {len(val_forms)}")

    # Generate examples
    train_examples = []
    val_examples = []

    for f in train_forms:
        print(f"  Processing (train): {f['pdf_path'].stem}...")
        exs = generate_examples(f)
        train_examples.extend(exs)
        print(f"    → {len(exs)} examples")

    for f in val_forms:
        print(f"  Processing (val): {f['pdf_path'].stem}...")
        exs = generate_examples(f)
        val_examples.extend(exs)
        print(f"    → {len(exs)} examples")

    # Write JSONL files
    train_path = OUTPUT_DIR / "train.jsonl"
    val_path = OUTPUT_DIR / "val.jsonl"

    with open(train_path, "w") as fout:
        for ex in train_examples:
            fout.write(json.dumps(ex, ensure_ascii=False) + "\n")

    with open(val_path, "w") as fout:
        for ex in val_examples:
            fout.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # Summary
    print(f"\n{'='*60}")
    print(f"Dataset prepared:")
    print(f"  Train: {len(train_examples)} examples → {train_path}")
    print(f"  Val:   {len(val_examples)} examples → {val_path}")

    # Breakdown by type
    for split_name, examples in [("Train", train_examples), ("Val", val_examples)]:
        type_counts = defaultdict(int)
        for ex in examples:
            type_counts[ex["metadata"]["type"]] += 1
        print(f"\n  {split_name} breakdown:")
        for t, c in sorted(type_counts.items()):
            print(f"    {t}: {c}")


if __name__ == "__main__":
    main()
