#!/usr/bin/env python3
"""
Run OCR + pre-fill only (no vision, no text LLM). Saves all artifacts and prefilled_form.json
for inspection. Use for testing and analysis.

Usage:
  python run_ocr_and_prefill.py --pdf path/to/form.pdf [--form 125]
  python run_ocr_and_prefill.py   # uses first PDF in test_data for form 125
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocr_engine import OCREngine
from schema_registry import SchemaRegistry
from spatial_extract import spatial_preextract
from form_json_builder import (
    build_empty_form_json_from_schema,
    prefill_form_json_from_ocr,
    label_value_pairs_to_json_list,
    save_empty_form_json,
)
from schema_registry import detect_form_type
from utils import save_json


def main():
    p = argparse.ArgumentParser(description="Run OCR and pre-fill only")
    p.add_argument("--pdf", type=Path, default=None, help="Path to PDF")
    p.add_argument("--form", type=str, default="125", choices=("125", "127", "137"), help="Form type")
    p.add_argument("--gpu", action="store_true", help="Use GPU for OCR")
    p.add_argument("--ocr-backend", choices=("easyocr", "surya"), default="easyocr", help="Bbox OCR: easyocr or surya (Marker)")
    p.add_argument("--out", type=Path, default=None, help="Output dir (default: pdf_stem under test_output/form_<type>)")
    args = p.parse_args()

    if args.pdf is None:
        # Default: first 125 PDF in test_data
        test_data = Path(__file__).parent / "test_data"
        for d in test_data.iterdir():
            if d.is_dir() and "125" in d.name:
                pdfs = list(d.glob("*.pdf"))
                if pdfs:
                    args.pdf = pdfs[0]
                    break
        if args.pdf is None:
            print("No PDF found in test_data. Use --pdf path/to/form.pdf")
            return 1

    args.pdf = Path(args.pdf)
    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}")
        return 1

    form_type = args.form
    output_dir = args.out or (Path(__file__).parent / "test_output" / f"form_{form_type}" / args.pdf.stem)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {output_dir}")

    # OCR
    bbox_backend = None if getattr(args, "ocr_backend", "easyocr") == "none" else args.ocr_backend
    ocr = OCREngine(
        dpi=300,
        easyocr_gpu=args.gpu,
        force_cpu=not args.gpu,
        docling_cpu_when_gpu=True,
        parallel_ocr=True,
        bbox_backend=bbox_backend,
        use_docling=True,
    )
    print(f"Running OCR (Docling + {ocr.bbox_backend or 'none'} + spatial index) ...")
    ocr_result = ocr.process(args.pdf, output_dir)

    # Form type from doc if not forced
    if not form_type:
        form_type = detect_form_type(ocr_result.full_docling_text, args.pdf.name) or "125"
    print(f"Form type: {form_type}")

    # Schema
    registry = SchemaRegistry(schemas_dir=Path(__file__).parent / "schemas")
    schema = registry.get_schema(form_type)
    if not schema:
        print(f"No schema for {form_type}")
        return 1

    # Spatial pre-extraction
    page_bbox = ocr_result.bbox_pages
    spatial_fields = spatial_preextract(form_type, page_bbox)
    print(f"Spatial pre-extract: {len(spatial_fields)} fields")

    # Save intermediates (same as extractor)
    from ocr_engine import OCREngine as OCRE
    save_json(ocr_result.docling_pages, output_dir / "docling_pages.json")
    save_json(ocr_result.bbox_pages, output_dir / "bbox_pages.json")
    all_bbox = ocr_result.all_bbox_data()
    with open(output_dir / "bbox_rows.txt", "w") as f:
        f.write(OCRE.format_bbox_as_rows(all_bbox))
    lv_text = ""
    for page_num, si in enumerate(ocr_result.spatial_indices, 1):
        lv_text += f"--- Page {page_num} ---\n"
        for pair in si.label_value_pairs:
            lv_text += f"  {pair.label.text} -> {pair.value.text}\n"
        lv_text += "\n"
    with open(output_dir / "label_value_pairs.txt", "w") as f:
        f.write(lv_text)
    save_json(spatial_fields, output_dir / "spatial_preextract.json")

    # Empty JSON + pre-fill
    empty_json = build_empty_form_json_from_schema(schema, use_defaults=False)
    lv_list = label_value_pairs_to_json_list(ocr_result.spatial_indices)
    prefilled_json, prefill_sources, prefill_details = prefill_form_json_from_ocr(
        empty_json, schema, spatial_fields, lv_list
    )
    save_empty_form_json(empty_json, output_dir / "empty_form.json")
    save_json(prefilled_json, output_dir / "prefilled_form.json")
    save_json(lv_list, output_dir / "label_value_pairs.json")
    save_json(prefill_sources, output_dir / "prefill_sources.json")
    save_json(prefill_details, output_dir / "prefill_details.json")

    prefill_count = len([v for v in prefilled_json.values() if v is not None and str(v).strip()])
    spatial_count = sum(1 for s in prefill_sources.values() if s == "spatial")
    lv_count = sum(1 for s in prefill_sources.values() if s == "label_value")
    print(f"\n[PREFILL] Total pre-filled: {prefill_count} (spatial: {spatial_count}, label_value: {lv_count})")
    print(f"  Artifacts in: {output_dir}")
    print("  - empty_form.json, prefilled_form.json, label_value_pairs.json, prefill_sources.json, prefill_details.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
