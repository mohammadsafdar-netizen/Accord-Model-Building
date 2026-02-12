#!/usr/bin/env python3
"""
Phase 1 extraction: OCR + prefill + text-only LLM → extracted JSON
==================================================================
Runs the full extraction pipeline without any vision model. Best option for
getting a first-pass JSON from form text and layout. Later you can add a VLM
on top (Phase 2) to fill or correct missing fields.

Pipeline:
  1. OCR: Docling (structure) + EasyOCR or Surya (bbox) → spatial index, label_value_pairs
  2. Prefill: spatial rules + label-value matching → prefilled_form.json
  3. Text LLM: category-by-category + gap-fill to fill remaining nulls → extracted.json

Usage:
  python run_phase1_extraction.py --pdf path/to/form.pdf [--form 125]
  python run_phase1_extraction.py --pdf form.pdf --form 125 --model qwen2.5:7b --ocr-backend surya --out phase1_out
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocr_engine import OCREngine
from llm_engine import LLMEngine
from schema_registry import SchemaRegistry
from extractor import ACORDExtractor
from compare import compare_fields, load_ground_truth, print_report
from gt_flatten import flatten_gt_for_comparison
from utils import save_json, prune_empty_fields


def main():
    p = argparse.ArgumentParser(
        description="Phase 1: OCR + prefill + text-only LLM extraction (no VLM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--pdf", type=Path, default=None, help="Path to PDF")
    p.add_argument("--form", type=str, default=None, choices=("125", "127", "137"), help="Form type (auto-detect if not set)")
    p.add_argument("--model", type=str, default="qwen2.5:7b", help="Ollama text model for extraction")
    p.add_argument("--ollama-url", type=str, default="http://localhost:11434", help="Ollama API URL")
    p.add_argument("--gpu", action="store_true", help="Use GPU for OCR")
    p.add_argument("--ocr-backend", choices=("easyocr", "surya"), default="easyocr", help="Bbox OCR backend")
    p.add_argument("--docling-gpu", action="store_true", help="Run Docling on GPU (faster on 24GB VRAM)")
    p.add_argument("--out", type=Path, default=None, help="Output directory (default: phase1_output/<pdf_stem>)")
    p.add_argument("--ground-truth", type=Path, default=None, help="Ground truth JSON (default: <pdf>.json beside PDF)")
    p.add_argument("--fast", action="store_true", help="Use fast path: 2–8 fill-nulls LLM calls instead of full category extraction (faster, lower accuracy)")
    p.add_argument("--max-llm-chunks", type=int, default=0, help="With --fast: max chunks (0=all). Use 4–6 for quick run.")
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
    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}")
        return 1

    if args.out is None:
        args.out = Path(__file__).parent / "phase1_output" / args.pdf.stem
    args.out = Path(args.out)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.fast:
        # Delegate to fast script (OCR + prefill + few fill-nulls calls)
        import subprocess
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "run_phase1_fast.py"),
            "--pdf", str(args.pdf),
            "--model", args.model,
            "--ollama-url", args.ollama_url,
            "--out", str(args.out),
            "--ocr-backend", args.ocr_backend,
        ]
        if args.form:
            cmd += ["--form", args.form]
        if args.gpu:
            cmd += ["--gpu"]
        if getattr(args, "docling_gpu", False):
            cmd += ["--docling-gpu"]
        if args.ground_truth:
            cmd += ["--ground-truth", str(args.ground_truth)]
        if args.max_llm_chunks > 0:
            cmd += ["--max-llm-chunks", str(args.max_llm_chunks)]
        return subprocess.run(cmd).returncode

    print("\n" + "=" * 60)
    print("  PHASE 1 EXTRACTION (text-only LLM, no VLM)")
    print("  PDF:", args.pdf.name)
    print("  Model:", args.model)
    print("  OCR bbox backend:", args.ocr_backend)
    print("  Output:", args.out)
    print("=" * 60 + "\n")

    # OCR
    ocr = OCREngine(
        dpi=300,
        easyocr_gpu=args.gpu,
        force_cpu=not args.gpu,
        docling_cpu_when_gpu=not args.docling_gpu,  # --docling-gpu: Docling on GPU (24GB)
        parallel_ocr=True,
        bbox_backend=args.ocr_backend,
    )

    # Text-only LLM (no vision model)
    llm = LLMEngine(
        model=args.model,
        base_url=args.ollama_url,
        vision_model=None,
        vision_describer_model=None,
    )

    registry = SchemaRegistry(schemas_dir=Path(__file__).parent / "schemas")
    extractor = ACORDExtractor(ocr, llm, registry, use_vision=False)

    result = extractor.extract(
        pdf_path=args.pdf,
        form_type=args.form,
        output_dir=args.out,
    )

    extracted = result["extracted_fields"]
    metadata = result["metadata"]
    form_type = metadata.get("form_type", args.form or "125")

    # Save Phase 1 outputs
    extracted_path = args.out / "extracted.json"
    save_json(prune_empty_fields(extracted), extracted_path)
    meta_path = args.out / "extraction_metadata.json"
    save_json(metadata, meta_path)

    # ---- Compare to ground truth ----
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
        print_report(comparison, title=f"Phase 1 vs Ground Truth - {args.pdf.stem}")
        metadata["accuracy"] = comparison["accuracy"]
        metadata["exact_match_rate"] = comparison["exact_match_rate"]
        metadata["coverage"] = comparison["coverage"]
        metadata["ground_truth_path"] = str(gt_path)
        save_json(metadata, meta_path)
    else:
        if args.ground_truth and not Path(args.ground_truth).exists():
            print(f"  [WARN] Ground truth not found: {args.ground_truth}")
        print("\n  No ground truth found (optional: --ground-truth path/to/gt.json)")

    print("\n" + "=" * 60)
    print("  PHASE 1 COMPLETE")
    print("  Extracted fields:", len(extracted))
    print("  Saved:", extracted_path)
    print("  Metadata:", meta_path)
    print("=" * 60)
    print("\nTo add Phase 2 (VLM on top), run full pipeline with --vision:")
    print("  python main.py", str(args.pdf), "--vision --vision-model <vlm>")
    print("  or use test_pipeline.py with --vision for batch runs.")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
