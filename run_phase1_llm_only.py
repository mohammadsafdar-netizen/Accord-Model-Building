#!/usr/bin/env python3
"""
Run only the text-LLM extraction step using existing OCR output.
Use when OCR + prefill already ran (e.g. phase1_7b_out) but the full run timed out.
Loads bbox_pages.json, docling_pages.json, rebuilds spatial indices, runs extractor.

Usage:
  python run_phase1_llm_only.py --pdf path/to/form.pdf --out phase1_7b_out [--form 125] [--model qwen2.5:7b]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocr_engine import OCREngine, OCRResult
from llm_engine import LLMEngine
from schema_registry import SchemaRegistry
from extractor import ACORDExtractor
from compare import compare_fields, load_ground_truth, print_report
from gt_flatten import flatten_gt_for_comparison
from utils import save_json, prune_empty_fields


def load_ocr_result_from_dir(out_dir: Path, ocr_engine: OCREngine) -> OCRResult:
    """Build OCRResult from saved bbox_pages.json, docling_pages.json, and images."""
    out_dir = Path(out_dir)
    with open(out_dir / "bbox_pages.json", encoding="utf-8") as f:
        bbox_pages = json.load(f)
    with open(out_dir / "docling_pages.json", encoding="utf-8") as f:
        docling_pages = json.load(f)

    images_dir = out_dir / "images"
    if not images_dir.exists():
        images_dir = out_dir
    image_paths = sorted(images_dir.glob("*_clean.png")) or sorted(images_dir.glob("*.png"))
    clean_paths = list(image_paths)
    if not image_paths:
        image_paths = [out_dir / f"page_{i+1}.png" for i in range(len(docling_pages))]
        clean_paths = image_paths

    spatial_indices = []
    for page_num, (page_bbox, docling_md) in enumerate(zip(bbox_pages, docling_pages), 1):
        si = ocr_engine.build_spatial_index(
            page_bbox,
            page_width=0,
            page_height=0,
            page=page_num,
            docling_markdown=docling_md,
            docling_native_pairs=None,
        )
        spatial_indices.append(si)

    return OCRResult(
        docling_pages=docling_pages,
        bbox_pages=bbox_pages,
        spatial_indices=spatial_indices,
        image_paths=[Path(p) for p in image_paths],
        clean_image_paths=[Path(p) for p in clean_paths],
        num_pages=len(docling_pages),
        docling_regions_per_page=None,
        docling_native_pairs_per_page=None,
    )


def main():
    p = argparse.ArgumentParser(description="Run text-LLM extraction only (use existing OCR output)")
    p.add_argument("--pdf", type=Path, required=True, help="Path to PDF (for form type / paths)")
    p.add_argument("--out", type=Path, required=True, help="Output dir with bbox_pages.json, docling_pages.json, images/")
    p.add_argument("--form", type=str, default="125", choices=("125", "127", "137"))
    p.add_argument("--model", type=str, default="qwen2.5:7b")
    p.add_argument("--ollama-url", type=str, default="http://localhost:11434")
    p.add_argument("--ground-truth", type=Path, default=None)
    args = p.parse_args()

    args.pdf = Path(args.pdf)
    args.out = Path(args.out)
    if not (args.out / "bbox_pages.json").exists():
        print(f"Error: {args.out} must contain bbox_pages.json (run Phase 1 OCR first)")
        return 1

    print("\n  [LLM-only] Loading OCR from", args.out)
    ocr = OCREngine(dpi=300)
    ocr_result = load_ocr_result_from_dir(args.out, ocr)

    llm = LLMEngine(model=args.model, base_url=args.ollama_url, vision_model=None)
    registry = SchemaRegistry(schemas_dir=Path(__file__).parent / "schemas")
    extractor = ACORDExtractor(ocr, llm, registry, use_vision=False)

    print("  [LLM-only] Running text-LLM extraction (7B model)...")
    result = extractor.extract(
        pdf_path=args.pdf,
        form_type=args.form,
        output_dir=args.out,
        ocr_result=ocr_result,
    )

    extracted = result["extracted_fields"]
    metadata = result["metadata"]
    form_type = metadata.get("form_type", args.form)

    extracted_path = args.out / "extracted.json"
    save_json(prune_empty_fields(extracted), extracted_path)
    meta_path = args.out / "extraction_metadata.json"
    save_json(metadata, meta_path)

    gt_path = args.ground_truth or args.pdf.with_suffix(".json")
    if gt_path and Path(gt_path).exists():
        gt_raw = load_ground_truth(gt_path)
        gt_flat = flatten_gt_for_comparison(gt_raw, form_type)
        schema = registry.get_schema(form_type)
        checkbox_fields = set()
        if schema:
            for fname, finfo in schema.fields.items():
                if getattr(finfo, "field_type", None) in ("checkbox", "radio"):
                    checkbox_fields.add(fname)
        comparison = compare_fields(extracted, gt_flat, None, checkbox_fields)
        save_json(comparison, args.out / "comparison.json")
        print_report(comparison, title=f"Phase 1 (7B) vs Ground Truth — {args.pdf.stem}")
        metadata["accuracy"] = comparison["accuracy"]
        metadata["exact_match_rate"] = comparison["exact_match_rate"]
        metadata["coverage"] = comparison["coverage"]
        save_json(metadata, meta_path)
    else:
        print("  No ground truth found; skipping comparison.")

    print("\n  Extracted:", extracted_path)
    print("  Metadata:", meta_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
