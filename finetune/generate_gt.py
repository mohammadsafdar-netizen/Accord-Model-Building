#!/usr/bin/env python3
"""
Generate Ground Truth JSON from AcroForm PDFs.

Reads AcroForm widget values from PDF form fields using PyMuPDF,
normalizes them, filters to schema-valid fields, and writes GT JSON
files alongside the PDFs in the correct test_data/ structure.

Usage:
    # Process PDFs already placed in test_data/ subdirectories:
    .venv/bin/python finetune/generate_gt.py

    # Process PDFs from an external source directory (auto-detects form type,
    # copies PDFs into test_data/ and generates GT JSONs):
    .venv/bin/python finetune/generate_gt.py --source /path/to/400_pdfs/

    # Dry run (preview without writing):
    .venv/bin/python finetune/generate_gt.py --source /path/to/pdfs/ --dry-run
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

try:
    import fitz
except ImportError:
    print("ERROR: PyMuPDF required. Install: uv pip install PyMuPDF")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = ROOT / "schemas"
TEST_DATA_DIR = ROOT / "test_data"

# Form type → (directory name, schema file, filename prefix)
FORM_CONFIGS = {
    "125": {
        "dir": "ACORD_0125_CommercialInsurance_Acroform",
        "schema": "125.json",
        "prefix": "ACORD_0125_CommercialInsurance_Acroform",
    },
    "127": {
        "dir": "127_Business_Auto_Section_2015_12",
        "schema": "127.json",
        "prefix": "127_Business_Auto_Section_2015_12",
    },
    "137": {
        "dir": "ACORD_137",
        "schema": "137.json",
        "prefix": "ACORD_137",
    },
    "163": {
        "dir": "ACORD_163",
        "schema": "163.json",
        "prefix": "ACORD_163",
    },
}


def load_schema_fields(schema_file: str) -> Dict[str, dict]:
    """Load schema and return {field_name: field_def} dict."""
    path = SCHEMAS_DIR / schema_file
    data = json.loads(path.read_text())
    return data.get("fields", data)


def get_widget_fields(pdf_path: Path) -> Dict[str, Any]:
    """Extract all AcroForm widget field names and values from a PDF."""
    doc = fitz.open(str(pdf_path))
    fields: Dict[str, Any] = {}
    for page in doc:
        try:
            widgets = list(page.widgets())
        except Exception:
            continue
        for widget in widgets:
            try:
                name = widget.field_name
                value = widget.field_value
                if not name:
                    continue
                # Checkbox (field_type 2)
                if widget.field_type == 2:
                    str_val = str(value).strip() if value is not None else "Off"
                    if str_val.lower() == "off" or not str_val:
                        fields[name] = False
                    else:
                        fields[name] = True
                else:
                    # Text / other field types
                    str_val = str(value).strip() if value is not None else ""
                    if str_val and str_val.lower() not in ("null", "none"):
                        fields[name] = str_val
                    else:
                        fields[name] = None
            except Exception:
                continue
    doc.close()
    return fields


def detect_form_type(pdf_path: Path, widget_names: Set[str]) -> Optional[str]:
    """Detect form type by matching widget names against schemas.
    Returns '125', '127', '137', or None.
    """
    # First try filename prefix matching
    stem = pdf_path.stem
    for form_type, cfg in FORM_CONFIGS.items():
        if stem.startswith(cfg["prefix"]):
            return form_type

    # Fall back to schema field overlap
    best_type = None
    best_overlap = 0
    for form_type, cfg in FORM_CONFIGS.items():
        schema_fields = load_schema_fields(cfg["schema"])
        overlap = len(widget_names & set(schema_fields.keys()))
        if overlap > best_overlap:
            best_overlap = overlap
            best_type = form_type

    # Require at least 10% overlap to be confident
    if best_type and best_overlap > 10:
        return best_type
    return None


def filter_to_schema(
    raw_fields: Dict[str, Any], schema_fields: Dict[str, dict]
) -> Dict[str, Any]:
    """Keep only fields present in the schema. Normalize checkbox values."""
    result = {}
    for name, value in raw_fields.items():
        if name not in schema_fields:
            continue
        field_def = schema_fields[name]
        # Normalize checkbox values
        if field_def.get("type") == "checkbox":
            if value is True or value == "1" or value == "Yes":
                result[name] = True
            else:
                result[name] = False
        else:
            result[name] = value
    return result


def file_hash(path: Path) -> str:
    """Generate 8-char hex hash from file contents."""
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h[:8]


def process_pdf(
    pdf_path: Path,
    form_type: str,
    dest_dir: Path,
    schema_fields: Dict[str, dict],
    dry_run: bool = False,
    copy_pdf: bool = False,
) -> Tuple[bool, str]:
    """Process a single PDF: extract GT, optionally copy, write JSON.

    Returns (success, message).
    """
    # Determine output paths
    if copy_pdf:
        # Generate standardized filename
        fhash = file_hash(pdf_path)
        prefix = FORM_CONFIGS[form_type]["prefix"]
        new_stem = f"{prefix}_{fhash}"
        dest_pdf = dest_dir / f"{new_stem}.pdf"
        dest_json = dest_dir / f"{new_stem}.json"
    else:
        # PDF is already in test_data, just create JSON alongside it
        dest_pdf = pdf_path
        dest_json = pdf_path.with_suffix(".json")

    # Skip if GT already exists
    if dest_json.exists():
        return True, f"SKIP (GT exists): {dest_json.name}"

    # Extract fields
    raw_fields = get_widget_fields(pdf_path)
    if not raw_fields:
        return False, f"SKIP (no AcroForm data): {pdf_path.name}"

    # Filter to schema
    gt = filter_to_schema(raw_fields, schema_fields)
    non_null = sum(1 for v in gt.values() if v is not None and v != "" and v is not False)

    if dry_run:
        return True, f"WOULD CREATE: {dest_json.name} ({len(gt)} fields, {non_null} non-empty)"

    # Copy PDF if from external source
    dest_dir.mkdir(parents=True, exist_ok=True)
    if copy_pdf and not dest_pdf.exists():
        shutil.copy2(pdf_path, dest_pdf)

    # Write GT JSON
    with open(dest_json, "w") as f:
        json.dump(gt, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return True, f"OK: {dest_json.name} ({len(gt)} fields, {non_null} non-empty)"


def process_source_dir(source_dir: Path, dry_run: bool = False):
    """Process all PDFs from an external source directory."""
    pdfs = sorted(source_dir.glob("**/*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {source_dir}")
        return

    print(f"Found {len(pdfs)} PDFs in {source_dir}\n")

    # Pre-load all schemas
    schemas = {}
    for form_type, cfg in FORM_CONFIGS.items():
        schemas[form_type] = load_schema_fields(cfg["schema"])

    stats = {"ok": 0, "skip": 0, "fail": 0}

    for pdf_path in pdfs:
        # Detect form type
        raw_fields = get_widget_fields(pdf_path)
        widget_names = set(raw_fields.keys())
        form_type = detect_form_type(pdf_path, widget_names)

        if form_type is None:
            print(f"  FAIL (unknown form type): {pdf_path.name}")
            stats["fail"] += 1
            continue

        dest_dir = TEST_DATA_DIR / FORM_CONFIGS[form_type]["dir"]
        success, msg = process_pdf(
            pdf_path,
            form_type,
            dest_dir,
            schemas[form_type],
            dry_run=dry_run,
            copy_pdf=True,
        )
        prefix = f"[{form_type}]"
        print(f"  {prefix:6s} {msg}")
        if "SKIP" in msg:
            stats["skip"] += 1
        elif success:
            stats["ok"] += 1
        else:
            stats["fail"] += 1

    print(f"\nDone: {stats['ok']} created, {stats['skip']} skipped, {stats['fail']} failed")


def process_test_data(dry_run: bool = False):
    """Process PDFs already in test_data/ that are missing GT JSONs."""
    schemas = {}
    for form_type, cfg in FORM_CONFIGS.items():
        schemas[form_type] = load_schema_fields(cfg["schema"])

    stats = {"ok": 0, "skip": 0, "fail": 0}

    for form_type, cfg in FORM_CONFIGS.items():
        form_dir = TEST_DATA_DIR / cfg["dir"]
        if not form_dir.exists():
            continue

        pdfs = sorted(form_dir.glob("*.pdf"))
        missing = [p for p in pdfs if not p.with_suffix(".json").exists()]

        if not missing:
            print(f"[{form_type}] All {len(pdfs)} PDFs already have GT JSONs")
            continue

        print(f"[{form_type}] {len(missing)}/{len(pdfs)} PDFs missing GT JSONs:")
        for pdf_path in missing:
            success, msg = process_pdf(
                pdf_path,
                form_type,
                form_dir,
                schemas[form_type],
                dry_run=dry_run,
                copy_pdf=False,
            )
            print(f"  {msg}")
            if "SKIP" in msg:
                stats["skip"] += 1
            elif success:
                stats["ok"] += 1
            else:
                stats["fail"] += 1

    print(f"\nDone: {stats['ok']} created, {stats['skip']} skipped, {stats['fail']} failed")


def main():
    parser = argparse.ArgumentParser(
        description="Generate GT JSON files from AcroForm PDFs"
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="External directory containing PDFs to import. "
        "PDFs will be copied into test_data/ with generated GT JSONs. "
        "If omitted, processes PDFs already in test_data/ that lack GT.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without writing files",
    )
    args = parser.parse_args()

    if args.source:
        if not args.source.exists():
            print(f"ERROR: Source directory not found: {args.source}")
            sys.exit(1)
        process_source_dir(args.source, dry_run=args.dry_run)
    else:
        process_test_data(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
