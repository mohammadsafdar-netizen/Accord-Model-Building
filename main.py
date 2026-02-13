#!/usr/bin/env python3
"""
Main CLI: ACORD Form Extraction Pipeline
==========================================
Entry point for extracting fields from scanned ACORD forms 125, 127, 137.

Usage:
    # Basic extraction
    python main.py path/to/form.pdf

    # Specify form type and model
    python main.py path/to/form.pdf --form-type 127 --model qwen2.5:7b

    # With accuracy comparison against ground truth
    python main.py path/to/form.pdf --ground-truth path/to/gt.json

    # Custom output directory
    python main.py path/to/form.pdf --output-dir ./results
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Avoid long Paddle connectivity check on import when paddleocr is installed (helps 6GB / low-VRAM)
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from config import get_schemas_dir, get_test_data_dir, get_rag_gt_dir, OLLAMA_URL_DEFAULT, USE_GPU_DEFAULT
from ocr_engine import OCREngine, SURYA_AVAILABLE, PADDLEOCR_AVAILABLE
from llm_engine import LLMEngine
from schema_registry import SchemaRegistry
from extractor import ACORDExtractor
from compare import compare_fields, load_ground_truth, print_report
from utils import save_json, prune_empty_fields


def main():
    parser = argparse.ArgumentParser(
        description="Extract fields from scanned ACORD forms (125, 127, 137)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py form127.pdf
  python main.py form125.pdf --form-type 125 --model qwen2.5:7b
  python main.py form127.pdf --ground-truth gt_127.json
        """,
    )
    parser.add_argument("pdf_path", type=Path, help="Path to the scanned PDF")
    parser.add_argument(
        "--form-type", choices=["125", "127", "137"], default=None,
        help="ACORD form type (auto-detected if not specified)",
    )
    parser.add_argument(
        "--model", default="qwen2.5:7b",
        help="Ollama model name (default: qwen2.5:7b)",
    )
    parser.add_argument(
        "--ollama-url", default=None,
        help="Ollama API base URL (default: from OLLAMA_URL env or http://localhost:11434)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Output directory for results (default: auto)",
    )
    parser.add_argument(
        "--ground-truth", type=Path, default=None,
        help="Ground truth JSON for accuracy comparison",
    )
    parser.add_argument(
        "--schemas-dir", type=Path, default=None,
        help="Directory containing schema JSON files (default: ./schemas)",
    )
    parser.add_argument(
        "--dpi", type=int, default=300,
        help="Image DPI for PDF conversion (default: 300)",
    )
    parser.add_argument(
        "--gpu", action="store_true",
        help="Use GPU for OCR (default: CPU unless USE_GPU=1)",
    )
    parser.add_argument(
        "--docling", action="store_true",
        help="Run Docling OCR (structure/markdown). Off by default.",
    )
    parser.add_argument(
        "--ocr-backend", choices=("none", "easyocr", "surya", "paddle"), default="surya",
        help="Bbox OCR backend (default: surya — best FOSS accuracy). Use 'none' to skip bbox OCR.",
    )
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="LLM request timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--vision", action="store_true",
        help="Run VLM on form images for extraction. Off by default.",
    )
    parser.add_argument(
        "--text-llm", action="store_true",
        help="Run text LLM for category/driver/vehicle/gap-fill. Off by default.",
    )
    parser.add_argument(
        "--use-rag", action="store_true",
        help="Use few-shot RAG from ground truth (improves accuracy). Needs --rag-gt-dir or test_data with GT JSONs.",
    )
    parser.add_argument(
        "--rag-gt-dir", type=Path, default=None,
        help="Directory of ground-truth JSONs for RAG (default: TEST_DATA_DIR from config).",
    )
    parser.add_argument(
        "--vision-model", type=str, default="llava:7b",
        help="Ollama vision model for --vision (default: llava:7b)",
    )
    parser.add_argument(
        "--vision-descriptions", action="store_true",
        help="Crop pages to regions, describe with small VLM, then extract with crops+descriptions",
    )
    parser.add_argument(
        "--vision-describer-model", type=str, default=None,
        help="Small VLM for describing regions when --vision-descriptions (default: same as --vision-model)",
    )

    args = parser.parse_args()

    if args.ollama_url is None:
        args.ollama_url = OLLAMA_URL_DEFAULT
    if not args.gpu and USE_GPU_DEFAULT:
        args.gpu = True

    if not args.pdf_path.exists():
        print(f"Error: PDF not found: {args.pdf_path}")
        sys.exit(1)

    if not args.docling and not args.form_type:
        print("Without --docling, form type cannot be auto-detected. Pass --form-type 125|127|137.")
        sys.exit(1)

    # --- Initialise components ---
    print("\nInitialising pipeline components ...")

    bbox_backend = None if args.ocr_backend == "none" else args.ocr_backend
    if bbox_backend == "surya" and not SURYA_AVAILABLE:
        print("  [OCR] surya-ocr not installed; using easyocr. pip install surya-ocr for best accuracy.")
        bbox_backend = "easyocr"
    if bbox_backend == "paddle" and not PADDLEOCR_AVAILABLE:
        print("  [OCR] PaddleOCR not installed; using easyocr. pip install paddleocr for PaddleOCR.")
        bbox_backend = "easyocr"
    ocr = OCREngine(
        dpi=args.dpi,
        easyocr_gpu=args.gpu,
        force_cpu=not args.gpu,
        docling_cpu_when_gpu=True,  # CPU offload for Docling so GPU is free for bbox OCR + LLM
        bbox_backend=bbox_backend,
        use_docling=args.docling,
    )

    llm = LLMEngine(
        model=args.model,
        base_url=args.ollama_url,
        timeout=args.timeout,
        vision_model=args.vision_model if args.vision else None,
        vision_describer_model=args.vision_describer_model if args.vision else None,
    )

    schemas_dir = args.schemas_dir or get_schemas_dir()
    registry = SchemaRegistry(schemas_dir=schemas_dir)

    rag_store = None
    if args.use_rag:
        from rag_examples import build_example_store
        gt_dir = args.rag_gt_dir or get_rag_gt_dir()
        rag_store = build_example_store(gt_dir, schemas_dir)
        print("  [RAG] Few-shot examples enabled (loaded from ground truth).")

    extractor = ACORDExtractor(
        ocr, llm, registry,
        use_vision=args.vision,
        use_text_llm=args.text_llm,
        use_vision_descriptions=args.vision_descriptions,
        rag_store=rag_store,
    )

    # --- Run extraction ---
    result = extractor.extract(
        pdf_path=args.pdf_path,
        form_type=args.form_type,
        output_dir=args.output_dir,
    )

    extracted = result["extracted_fields"]
    metadata = result["metadata"]

    # --- Save results ---
    output_dir = args.output_dir or (
        args.pdf_path.parent / "best_project_output" / args.pdf_path.stem
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full result
    result_path = output_dir / f"{args.pdf_path.stem}_extracted.json"
    save_json(prune_empty_fields(extracted), result_path)
    print(f"Extracted fields saved to: {result_path}")

    # Save metadata
    meta_path = output_dir / f"{args.pdf_path.stem}_metadata.json"
    save_json(metadata, meta_path)

    # --- Accuracy comparison ---
    if args.ground_truth:
        if not args.ground_truth.exists():
            print(f"Warning: Ground truth not found: {args.ground_truth}")
        else:
            gt = load_ground_truth(args.ground_truth)
            comparison = compare_fields(extracted, gt)
            print_report(
                comparison,
                title=f"ACORD {metadata['form_type']} Accuracy Report",
            )

            # Save comparison
            comp_path = output_dir / f"{args.pdf_path.stem}_accuracy.json"
            # Remove field_results for compact output
            compact = {k: v for k, v in comparison.items() if k != "field_results"}
            save_json(compact, comp_path)
            print(f"Accuracy report saved to: {comp_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
