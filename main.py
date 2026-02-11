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
import sys
from pathlib import Path

from ocr_engine import OCREngine
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
        "--ollama-url", default="http://localhost:11434",
        help="Ollama API base URL",
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
        help="Use GPU for OCR (default: CPU-only)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="LLM request timeout in seconds (default: 300)",
    )

    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"Error: PDF not found: {args.pdf_path}")
        sys.exit(1)

    # --- Initialise components ---
    print("\nInitialising pipeline components ...")

        ocr = OCREngine(
            dpi=args.dpi,
            easyocr_gpu=args.gpu,
            force_cpu=not args.gpu,
            docling_cpu_when_gpu=True,  # CPU offload for Docling so GPU is free for EasyOCR + LLM
        )

    llm = LLMEngine(
        model=args.model,
        base_url=args.ollama_url,
        timeout=args.timeout,
    )

    schemas_dir = args.schemas_dir or Path(__file__).parent / "schemas"
    registry = SchemaRegistry(schemas_dir=schemas_dir)

    extractor = ACORDExtractor(ocr, llm, registry)

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
