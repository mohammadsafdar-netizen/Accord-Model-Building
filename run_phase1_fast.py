#!/usr/bin/env python3
"""
Phase 1 FAST: OCR + prefill + 2–8 fill-nulls LLM calls (no category-by-category).
Much faster than full Phase 1. Uses one-shot fill-nulls prompts in chunks.

Usage:
  python run_phase1_fast.py --pdf path/to/form.pdf [--form 125] [--model qwen2.5:7b]
  python run_phase1_fast.py --pdf form.pdf --out phase1_fast_out --max-llm-chunks 4   # only 4 LLM calls
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocr_engine import OCREngine, OCRResult
from llm_engine import LLMEngine
from schema_registry import SchemaRegistry
from spatial_extract import spatial_preextract
from form_json_builder import (
    build_empty_form_json_from_schema,
    prefill_form_json_from_ocr,
    label_value_pairs_to_json_list,
    save_empty_form_json,
)
from schema_registry import detect_form_type, EXTRACTION_ORDER
from collections import defaultdict
from prompts import build_fill_nulls_prompt
from compare import compare_fields, load_ground_truth, print_report
from gt_flatten import flatten_gt_for_comparison
from utils import save_json, prune_empty_fields


# Chunk size for fill-nulls (one LLM call per chunk). 80–120 keeps prompts manageable.
FILL_NULLS_CHUNK = 100
# Max docling/bbox chars per chunk to speed up inference
MAX_DOCLING = 5000
MAX_BBOX = 3500
MAX_LV = 2000


def load_ocr_result_from_dir(out_dir: Path, ocr_engine: OCREngine) -> OCRResult:
    """Build OCRResult from saved bbox_pages.json, docling_pages.json, images."""
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
            page_bbox, 0, 0, page_num,
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
    p = argparse.ArgumentParser(description="Phase 1 FAST: OCR + prefill + few fill-nulls LLM calls")
    p.add_argument("--pdf", type=Path, default=None)
    p.add_argument("--form", type=str, default=None, choices=("125", "127", "137"))
    p.add_argument("--model", type=str, default="qwen2.5:7b")
    p.add_argument("--ollama-url", type=str, default="http://localhost:11434")
    p.add_argument("--gpu", action="store_true")
    p.add_argument("--docling", action="store_true", help="Run Docling OCR (required for fill-nulls text; off by default)")
    p.add_argument("--ocr-backend", choices=("none", "easyocr", "surya"), default="none", help="Bbox OCR: none (default), easyocr, or surya")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--ground-truth", type=Path, default=None)
    p.add_argument("--max-llm-chunks", type=int, default=0, help="Max fill-nulls chunks (0=all). Use 3–4 for quick run.")
    p.add_argument("--chunk-by-category", action="store_true", default=True, help="Group missing fields by schema category (better accuracy, default on)")
    p.add_argument("--no-chunk-by-category", action="store_false", dest="chunk_by_category", help="Use fixed-size chunks instead of by category")
    p.add_argument("--docling-gpu", action="store_true", help="Run Docling on GPU (faster on 24GB VRAM)")
    args = p.parse_args()

    if args.pdf is None:
        test_data = Path(__file__).parent / "test_data"
        for d in test_data.iterdir():
            if d.is_dir() and "125" in d.name:
                pdfs = list(d.glob("*.pdf"))
                if pdfs:
                    args.pdf = pdfs[0]
                    break
        if args.pdf is None:
            print("No PDF found. Use --pdf path/to/form.pdf")
            return 1

    args.pdf = Path(args.pdf)
    if not getattr(args, "docling", False) and not args.form:
        print("Phase 1 fast needs either --docling (for form detection + text) or --form 125|127|137.")
        return 1
    if args.out is None:
        args.out = Path(__file__).parent / "phase1_fast_output" / args.pdf.stem
    args.out = Path(args.out)
    args.out.mkdir(parents=True, exist_ok=True)

    registry = SchemaRegistry(schemas_dir=Path(__file__).parent / "schemas")
    has_ocr = (args.out / "bbox_pages.json").exists()

    if has_ocr:
        print("\n  [FAST] Loading existing OCR from", args.out)
        ocr = OCREngine(dpi=300)
        ocr_result = load_ocr_result_from_dir(args.out, ocr)
        form_type = args.form or detect_form_type(ocr_result.full_docling_text, args.pdf.name) or "125"
        docling_text = ocr_result.full_docling_text
        bbox_text = OCREngine.format_bbox_as_rows(ocr_result.all_bbox_data())
        lv_parts = []
        for si in ocr_result.spatial_indices:
            for pair in si.label_value_pairs:
                lv_parts.append(f"{pair.label.text} -> {pair.value.text}")
        lv_text = "\n".join(lv_parts)
        # Load prefilled from disk
        with open(args.out / "prefilled_form.json", encoding="utf-8") as f:
            prefilled = json.load(f)
    else:
        print("\n  [FAST] Running OCR + prefill ...")
        bbox_backend = None if args.ocr_backend == "none" else args.ocr_backend
        ocr = OCREngine(
            dpi=300,
            easyocr_gpu=args.gpu,
            bbox_backend=bbox_backend,
            use_docling=getattr(args, "docling", False),
            docling_cpu_when_gpu=not args.docling_gpu,  # --docling-gpu: Docling on GPU (24GB)
        )
        ocr_result = ocr.process(args.pdf, args.out)
        form_type = args.form or detect_form_type(ocr_result.full_docling_text, args.pdf.name) or "125"
        schema = registry.get_schema(form_type)
        if not schema:
            print("No schema for form", form_type)
            return 1
        page_bbox = ocr_result.bbox_pages
        spatial_fields = spatial_preextract(form_type, page_bbox)
        empty_json = build_empty_form_json_from_schema(schema)
        lv_list = label_value_pairs_to_json_list(ocr_result.spatial_indices)
        prefilled, _src, _ = prefill_form_json_from_ocr(empty_json, schema, spatial_fields, lv_list)
        save_empty_form_json(empty_json, args.out / "empty_form.json")
        save_json(prefilled, args.out / "prefilled_form.json")
        docling_text = ocr_result.full_docling_text
        bbox_text = OCREngine.format_bbox_as_rows(ocr_result.all_bbox_data())
        lv_parts = []
        for si in ocr_result.spatial_indices:
            for pair in si.label_value_pairs:
                lv_parts.append(f"{pair.label.text} -> {pair.value.text}")
        lv_text = "\n".join(lv_parts)

    schema = registry.get_schema(form_type)
    if not schema:
        print("No schema for form", form_type)
        return 1

    # Start from prefilled
    extracted = {k: v for k, v in prefilled.items() if v is not None and str(v).strip()}
    missing = [f for f in sorted(schema.fields) if f not in extracted]
    tooltips = registry.get_tooltips(form_type, missing)

    if not missing:
        print("  [FAST] No missing fields after prefill.")
    else:
        if args.chunk_by_category:
            # Group by category (better context per call); split large categories
            by_cat = defaultdict(list)
            for f in missing:
                fi = schema.fields.get(f)
                cat = (fi.category if fi else None) or "general"
                by_cat[cat].append(f)
            chunks = []
            for cat in EXTRACTION_ORDER:
                if cat not in by_cat or not by_cat[cat]:
                    continue
                fields_in_cat = by_cat[cat]
                for i in range(0, len(fields_in_cat), FILL_NULLS_CHUNK):
                    chunks.append(fields_in_cat[i : i + FILL_NULLS_CHUNK])
            # Any category not in EXTRACTION_ORDER
            for cat, flist in by_cat.items():
                if cat in EXTRACTION_ORDER:
                    continue
                for i in range(0, len(flist), FILL_NULLS_CHUNK):
                    chunks.append(flist[i : i + FILL_NULLS_CHUNK])
        else:
            chunks = [missing[i:i + FILL_NULLS_CHUNK] for i in range(0, len(missing), FILL_NULLS_CHUNK)]
        if args.max_llm_chunks > 0:
            chunks = chunks[: args.max_llm_chunks]
        print(f"  [FAST] Fill-nulls: {len(chunks)} LLM call(s) for {sum(len(c) for c in chunks)} fields (model={args.model})")
        llm = LLMEngine(model=args.model, base_url=args.ollama_url, vision_model=None)
        prefilled_summary = ", ".join(f"{k}={v}" for k, v in list(extracted.items())[:40])
        if len(extracted) > 40:
            prefilled_summary += " ..."
        t0 = time.time()
        for i, chunk in enumerate(chunks):
            chunk_tooltips = {k: tooltips.get(k, "") for k in chunk}
            prompt = build_fill_nulls_prompt(
                form_type=form_type,
                missing_fields=chunk,
                tooltips=chunk_tooltips,
                docling_text=docling_text,
                bbox_text=bbox_text,
                label_value_text=lv_text,
                prefilled_summary=prefilled_summary,
                max_docling=MAX_DOCLING,
                max_bbox=MAX_BBOX,
                max_lv=MAX_LV,
            )
            resp = llm.generate(prompt)
            result = llm.parse_json(resp)
            for k, v in result.items():
                if k in chunk and v is not None and str(v).strip():
                    extracted[k] = v
            print(f"    Chunk {i+1}/{len(chunks)}: +{len(result)} fields")
        print(f"  [FAST] LLM done in {time.time()-t0:.1f}s")
    extracted = prune_empty_fields(extracted)
    save_json(extracted, args.out / "extracted.json")

    # Compare to GT
    gt_path = args.ground_truth or args.pdf.with_suffix(".json")
    if gt_path and Path(gt_path).exists():
        gt_raw = load_ground_truth(gt_path)
        gt_flat = flatten_gt_for_comparison(gt_raw, form_type)
        checkbox_fields = set()
        for fname, finfo in schema.fields.items():
            if getattr(finfo, "field_type", None) in ("checkbox", "radio"):
                checkbox_fields.add(fname)
        comparison = compare_fields(extracted, gt_flat, None, checkbox_fields)
        save_json(comparison, args.out / "comparison.json")
        print_report(comparison, title=f"Phase 1 FAST (7B) vs Ground Truth — {args.pdf.stem}")
    else:
        print("  No ground truth; skipping comparison.")

    print("\n  Saved:", args.out / "extracted.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
