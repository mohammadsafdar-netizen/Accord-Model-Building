#!/usr/bin/env python3
"""
Test Pipeline: End-to-end accuracy test for all ACORD forms
==============================================================
Auto-discovers all PDF+JSON pairs in test_data/ subfolders.
Runs the extraction pipeline on each and compares against ground truth.
Saves ALL intermediate outputs (images, docling, bbox, spatial, etc.)
for full monitoring and debugging.

Usage:
    python test_pipeline.py --gpu
    python test_pipeline.py --gpu --forms 125 127 137
    python test_pipeline.py --gpu --one-per-form   # 3 PDFs total: one 125, one 127, one 137
    python test_pipeline.py --gpu --model qwen2.5:7b
    python test_pipeline.py --gpu --vision --vision-model qwen2.5-vl:30b --vram-reserve 2  # or qwen3-vl:30b
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reduce PyTorch CUDA memory fragmentation on limited GPUs
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# VRAM reserve (GB) for OCR process - leave this much for Ollama / other processes
VRAM_RESERVE_GB_DEFAULT = 2

from ocr_engine import OCREngine
from llm_engine import LLMEngine
from schema_registry import SchemaRegistry
from extractor import ACORDExtractor
from compare import compare_fields, load_ground_truth, print_report
from gt_flatten import flatten_gt_for_comparison
from utils import save_json


# ===========================================================================
# Test data discovery
# ===========================================================================

TEST_DATA_DIR = Path(__file__).parent / "test_data"
OUTPUT_DIR = Path(__file__).parent / "test_output"

# Map folder-name patterns to form types
FOLDER_TYPE_MAP = {
    "0125": "125",
    "125": "125",
    "127": "127",
    "137": "137",
}


def detect_form_type_from_folder(folder_name: str) -> Optional[str]:
    """Detect form type from the test data subfolder name."""
    folder_lower = folder_name.lower()
    for pattern, form_type in FOLDER_TYPE_MAP.items():
        if pattern in folder_lower:
            return form_type
    return None


def discover_test_forms() -> Dict[str, List[Dict[str, Path]]]:
    """
    Auto-discover all PDF+JSON pairs in test_data/ subfolders.

    Returns:
        {form_type: [{pdf: Path, gt: Path, stem: str}, ...]}
    """
    discovered: Dict[str, List[Dict[str, Path]]] = {}

    if not TEST_DATA_DIR.exists():
        print(f"  WARNING: test_data dir not found: {TEST_DATA_DIR}")
        return discovered

    for subfolder in sorted(TEST_DATA_DIR.iterdir()):
        if not subfolder.is_dir():
            continue

        form_type = detect_form_type_from_folder(subfolder.name)
        if form_type is None:
            print(f"  WARNING: Cannot determine form type for folder: {subfolder.name}")
            continue

        if form_type not in discovered:
            discovered[form_type] = []

        # Find all PDF files and their matching JSON ground truth
        for pdf_path in sorted(subfolder.glob("*.pdf")):
            gt_path = pdf_path.with_suffix(".json")
            entry = {
                "pdf": pdf_path,
                "gt": gt_path if gt_path.exists() else None,
                "stem": pdf_path.stem,
            }
            discovered[form_type].append(entry)

    return discovered


# ===========================================================================
# Ground truth flattening (handles nested objects in 127 GT format)
# ===========================================================================

def flatten_ground_truth(gt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten ground truth to only flat (non-nested) key-value pairs.

    Skips:
      - Nested dicts (e.g., Vehicle objects in Form 127)
      - List values (e.g., loss history arrays)
      - Signature / empty-string-only fields
    """
    flat: Dict[str, Any] = {}
    for key, value in gt.items():
        # Skip nested objects (Vehicle 1, Vehicle 2, etc.)
        if isinstance(value, dict):
            continue
        # Skip list values
        if isinstance(value, list):
            continue
        flat[key] = value
    return flat


# ===========================================================================
# Intermediate output saving
# ===========================================================================

def save_intermediate_outputs(
    ocr_result,
    spatial_fields: Dict[str, Any],
    output_dir: Path,
) -> None:
    """Save all intermediate OCR and spatial extraction outputs for debugging."""

    # 1. Docling markdown pages
    save_json(ocr_result.docling_pages, output_dir / "docling_pages.json")

    # 2. EasyOCR bounding box data per page
    bbox_data = []
    for page_bbox in ocr_result.bbox_pages:
        bbox_data.append(page_bbox)
    save_json(bbox_data, output_dir / "bbox_pages.json")

    # 3. BBox rows as human-readable text
    all_bbox = ocr_result.all_bbox_data()
    rows_text = OCREngine.format_bbox_as_rows(all_bbox)
    with open(output_dir / "bbox_rows.txt", "w") as f:
        f.write(rows_text)

    # 4. Label-value pairs per page
    lv_text = ""
    for page_num, si in enumerate(ocr_result.spatial_indices, 1):
        lv_text += f"--- Page {page_num} ---\n"
        for pair in si.label_value_pairs:
            lv_text += f"  {pair.label.text} -> {pair.value.text}\n"
        lv_text += "\n"
    with open(output_dir / "label_value_pairs.txt", "w") as f:
        f.write(lv_text)

    # 5. Spatial pre-extraction results
    if spatial_fields:
        save_json(spatial_fields, output_dir / "spatial_preextract.json")

    # 6. Per-page bbox text (for easy inspection)
    for page_num, page_bbox in enumerate(ocr_result.bbox_pages, 1):
        page_rows = OCREngine.format_bbox_as_rows(page_bbox)
        with open(output_dir / f"bbox_rows_page{page_num}.txt", "w") as f:
            f.write(page_rows)

    print(f"    [SAVE] Intermediate outputs saved to: {output_dir}")


# ===========================================================================
# Single form extraction + evaluation
# ===========================================================================

def run_single_form(
    pdf_entry: Dict[str, Any],
    form_type: str,
    ocr: OCREngine,
    llm: LLMEngine,
    registry: SchemaRegistry,
    use_vision: bool = False,
    use_vision_descriptions: bool = False,
    vision_checkboxes_only: bool = False,
    vision_fast: bool = False,
    use_graph: bool = False,
    vision_batch_size: Optional[int] = None,
    vision_max_tokens: int = 16384,
) -> Dict[str, Any]:
    """
    Run extraction on a single PDF, save all outputs, compare against GT.

    Returns:
        Dict with extraction results and accuracy metrics.
    """
    pdf_path = pdf_entry["pdf"]
    gt_path = pdf_entry.get("gt")
    stem = pdf_entry["stem"]

    # Create a dedicated output dir for this specific PDF
    form_output_dir = OUTPUT_DIR / f"form_{form_type}" / stem

    if not pdf_path.exists():
        return {"error": f"PDF not found: {pdf_path}", "stem": stem}

    extractor = ACORDExtractor(
        ocr, llm, registry,
        use_vision=use_vision,
        use_text_llm=True,
        use_vision_descriptions=use_vision_descriptions,
        vision_checkboxes_only=vision_checkboxes_only,
        vision_fast=vision_fast,
        vision_batch_size=vision_batch_size,
        vision_max_tokens=vision_max_tokens,
    )

    start = time.time()
    try:
        if use_graph:
            from extraction_graph import run_extraction
            result = run_extraction(
                pdf_path=pdf_path,
                form_type=form_type,
                output_dir=form_output_dir,
                ocr_engine=ocr,
                extractor=extractor,
                use_graph=True,
            )
        else:
            result = extractor.extract(
                pdf_path=pdf_path,
                form_type=form_type,
                output_dir=form_output_dir,
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "stem": stem,
            "extraction_time_seconds": round(time.time() - start, 2),
        }

    elapsed = time.time() - start
    extracted = result["extracted_fields"]

    # ---- Save all intermediate outputs ----
    # The extractor already ran OCR inside; re-read the OCR result for saving
    # Actually, the images and clean images are already saved by the OCR engine.
    # We need to save the docling/bbox data. Let's run a lightweight re-read
    # of the already-computed OCR data from the extractor.
    # The extractor doesn't expose ocr_result, so we save from here.
    # We'll add saving inside the extractor.
    # For now, save what we have.

    # Save extracted fields
    save_json(extracted, form_output_dir / "extracted.json")
    save_json(result.get("metadata", {}), form_output_dir / "metadata.json")

    form_result: Dict[str, Any] = {
        "stem": stem,
        "form_type": form_type,
        "fields_extracted": len(extracted),
        "extraction_time_seconds": round(elapsed, 2),
        "output_dir": str(form_output_dir),
    }

    # ---- Compare against ground truth ----
    if gt_path and gt_path.exists():
        gt_raw = load_ground_truth(gt_path)
        gt_flat = flatten_gt_for_comparison(gt_raw, form_type)

        # Build checkbox field set from schema
        schema = registry.get_schema(form_type)
        checkbox_fields = set()
        if schema:
            for fname, finfo in schema.fields.items():
                if finfo.field_type in ("checkbox", "radio"):
                    checkbox_fields.add(fname)

        # Compare all flat GT fields (key_fields=None uses all GT keys)
        comparison = compare_fields(extracted, gt_flat, None, checkbox_fields)

        form_result.update({
            "accuracy": comparison["accuracy"],
            "exact_match_rate": comparison["exact_match_rate"],
            "coverage": comparison["coverage"],
            "matched": comparison["matched"],
            "partial_match": comparison["partial_match"],
            "wrong": comparison["wrong"],
            "missing": comparison["missing"],
            "total_gt_fields": comparison["total_gt_fields"],
        })

        # Save detailed comparison
        save_json(comparison, form_output_dir / "comparison.json")

        print_report(comparison, title=f"ACORD {form_type} - {stem}")
    else:
        form_result["note"] = "No ground truth available"
        print(f"\n  {stem}: {len(extracted)} fields extracted in {elapsed:.1f}s (no GT)")

    return form_result


# ===========================================================================
# Aggregate results per form type
# ===========================================================================

def aggregate_results(form_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate accuracy metrics across multiple forms of the same type."""
    valid = [r for r in form_results if "error" not in r and "accuracy" in r]

    if not valid:
        return {
            "forms_tested": len(form_results),
            "forms_successful": 0,
            "note": "No valid results to aggregate",
        }

    total_matched = sum(r["matched"] for r in valid)
    total_partial = sum(r["partial_match"] for r in valid)
    total_wrong = sum(r["wrong"] for r in valid)
    total_missing = sum(r["missing"] for r in valid)
    total_gt = sum(r["total_gt_fields"] for r in valid)
    total_time = sum(r["extraction_time_seconds"] for r in valid)

    if total_gt > 0:
        accuracy = round((total_matched + total_partial * 0.5) / total_gt * 100, 2)
        exact_match = round(total_matched / total_gt * 100, 2)
        coverage = round((total_gt - total_missing) / total_gt * 100, 2)
    else:
        accuracy = exact_match = coverage = 0.0

    return {
        "forms_tested": len(form_results),
        "forms_successful": len(valid),
        "forms_errored": len(form_results) - len(valid),
        "total_gt_fields": total_gt,
        "total_matched": total_matched,
        "total_partial": total_partial,
        "total_wrong": total_wrong,
        "total_missing": total_missing,
        "aggregate_accuracy": accuracy,
        "aggregate_exact_match_rate": exact_match,
        "aggregate_coverage": coverage,
        "total_time_seconds": round(total_time, 2),
        "per_form_accuracy": {
            r["stem"]: r.get("accuracy", "N/A") for r in form_results
        },
    }


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Test extraction pipeline on all ACORD forms"
    )
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument(
        "--forms", nargs="+", default=["125", "127", "137"],
        choices=["125", "127", "137"], help="Form types to test",
    )
    parser.add_argument(
        "--one-per-form",
        action="store_true",
        help="Run only one PDF per form type (e.g. 1×125, 1×127, 1×137 = 3 total)",
    )
    parser.add_argument("--gpu", action="store_true", help="Use GPU for OCR")
    parser.add_argument(
        "--ocr-backend",
        choices=("easyocr", "surya"),
        default="easyocr",
        help="Bbox OCR backend: easyocr (default) or surya (Marker's engine; often better accuracy)",
    )
    parser.add_argument(
        "--vram-reserve",
        type=float,
        default=VRAM_RESERVE_GB_DEFAULT,
        metavar="GB",
        help=f"Reserve this much GPU VRAM (GB) for Ollama / other processes; our OCR uses the rest (default: {VRAM_RESERVE_GB_DEFAULT}). Use with big VLMs (e.g. qwen2.5-vl:30b, qwen3-vl:30b).",
    )
    parser.add_argument(
        "--vision", action="store_true",
        help="Run vision pass (VLM) on form images for missing fields",
    )
    parser.add_argument(
        "--vision-model", type=str, default="llava:7b",
        help="Ollama vision model for --vision (e.g. llava:7b, qwen2.5-vl:7b, qwen2.5-vl:30b, qwen3-vl:30b). Default: llava:7b",
    )
    parser.add_argument(
        "--vision-descriptions", action="store_true",
        help="Use describe-then-extract: crop pages to regions, describe each with small VLM, then send crops+descriptions to main VLM",
    )
    parser.add_argument(
        "--vision-describer-model", type=str, default=None,
        help="Small VLM for describing image regions when --vision-descriptions (default: same as --vision-model)",
    )
    parser.add_argument(
        "--vision-checkboxes-only", action="store_true",
        help="Run only checkbox vision pass; skip general vision (much faster on large forms, text LLM fills the rest)",
    )
    parser.add_argument(
        "--vision-fast", action="store_true",
        help="Use larger vision batches (20) and 1 page; skip section crops. Faster but more risk of truncated VLM output.",
    )
    parser.add_argument(
        "--docling-gpu", action="store_true",
        help="Run Docling on GPU (faster OCR). Use with 24GB+ VRAM; leaves less headroom during OCR.",
    )
    parser.add_argument(
        "--unload-wait", type=int, default=8, metavar="SEC",
        help="Seconds to wait after unloading a model before loading the next (default: 8). Use 5 on 24GB+ VRAM for faster runs.",
    )
    parser.add_argument(
        "--use-graph", action="store_true",
        help="Run extraction via LangGraph (OCR node then extract node). Uses parallel Docling+EasyOCR when applicable.",
    )
    parser.add_argument(
        "--no-parallel-ocr", action="store_true",
        help="Disable parallel OCR (run Docling then EasyOCR sequentially).",
    )
    parser.add_argument(
        "--vision-batch-size", type=int, default=None, metavar="N",
        help="Fields per VLM call in general vision pass (default: 12). Higher = fewer calls, needs --vision-max-tokens. Try 15 with 16384 tokens.",
    )
    parser.add_argument(
        "--vision-max-tokens", type=int, default=16384, metavar="N",
        help="Max tokens per VLM response (default: 16384). Reduces truncation/empty batches; allows larger --vision-batch-size.",
    )
    args = parser.parse_args()

    # ---- GPU + CPU offload: reserve VRAM and hint Ollama ----
    if args.gpu and args.vram_reserve > 0:
        try:
            import torch
            if torch.cuda.is_available():
                total_bytes = torch.cuda.get_device_properties(0).total_memory
                reserve_bytes = int(args.vram_reserve * (1024 ** 3))
                if total_bytes > reserve_bytes:
                    fraction = (total_bytes - reserve_bytes) / total_bytes
                    fraction = max(0.1, min(1.0, fraction))
                    torch.cuda.set_per_process_memory_fraction(fraction)
                    print(f"  [GPU] Reserved {args.vram_reserve:.1f} GB VRAM for Ollama (using {fraction*100:.0f}% for OCR)")
                else:
                    print(f"  [GPU] VRAM reserve {args.vram_reserve} GB >= total; not limiting OCR")
        except Exception as e:
            print(f"  [GPU] Could not set VRAM reserve: {e}")
        # So that child processes (or restarted Ollama) use same reserve
        os.environ.setdefault("OLLAMA_GPU_OVERHEAD", str(int(args.vram_reserve * (1024 ** 3))))
        os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")
        if args.vision or "30b" in (args.model or "") or "vl" in (args.vision_model or "").lower():
            print("  [GPU] For big models: if Ollama runs in another process, start it with e.g.:")
            print("        OLLAMA_GPU_OVERHEAD=2147483648 OLLAMA_NUM_PARALLEL=1 ollama serve")

    gpu_mode = (
        "GPU (sequential: Docling→EasyOCR→LLM)"
        if args.gpu
        else "CPU (OCR) + GPU (LLM)"
    )

    # ---- Discover test data ----
    all_test_forms = discover_test_forms()
    # Optionally limit to one PDF per form type
    if args.one_per_form:
        all_test_forms = {
            ft: (forms[:1] if forms else [])
            for ft, forms in all_test_forms.items()
        }
    total_pdfs = sum(
        len(forms) for ft, forms in all_test_forms.items() if ft in args.forms
    )

    print("=" * 70)
    print("  BEST PROJECT - END-TO-END PIPELINE TEST")
    print(f"  Model: {args.model}")
    print(f"  Mode:  {gpu_mode}")
    print(f"  Forms: {', '.join(args.forms)}" + (" (one per form)" if args.one_per_form else ""))
    if args.vision:
        vision_note = args.vision_model
        if args.vision_checkboxes_only:
            vision_note += " (checkboxes only)"
        if args.vision_fast:
            vision_note += " [fast]"
        vision_note += (" + descriptions (crop→describe→extract)" if args.vision_descriptions else "")
        print(f"  Vision: {vision_note}")
    if args.docling_gpu or args.unload_wait != 8 or args.use_graph or args.no_parallel_ocr:
        speed_parts = []
        if args.docling_gpu:
            speed_parts.append("Docling=GPU")
        if args.unload_wait != 8:
            speed_parts.append(f"unload_wait={args.unload_wait}s")
        if args.use_graph:
            speed_parts.append("LangGraph")
        if args.no_parallel_ocr:
            speed_parts.append("no-parallel-OCR")
        print(f"  Speed: {', '.join(speed_parts)}")
    print(f"  Total PDFs to run: {total_pdfs}")
    for ft in args.forms:
        forms = all_test_forms.get(ft, [])
        print(f"    Form {ft}: {len(forms)} PDF(s)")
        for entry in forms:
            gt_status = "✓ GT" if entry.get("gt") else "✗ no GT"
            print(f"      - {entry['stem']} [{gt_status}]")
    print("=" * 70)

    # ---- Initialise shared components ----
    bbox_backend = None if getattr(args, "ocr_backend", "easyocr") == "none" else args.ocr_backend
    ocr = OCREngine(
        dpi=300,
        easyocr_gpu=args.gpu,
        force_cpu=not args.gpu,
        docling_cpu_when_gpu=not args.docling_gpu,  # --docling-gpu: Docling on GPU (faster, needs 24GB+)
        ocr_unload_wait_seconds=args.unload_wait,
        parallel_ocr=not args.no_parallel_ocr,  # Parallel Docling+bbox OCR when Docling=CPU, bbox=GPU
        bbox_backend=bbox_backend,
        use_docling=True,
    )
    llm = LLMEngine(
        model=args.model,
        base_url=args.ollama_url,
        vision_model=args.vision_model if args.vision else None,
        vision_describer_model=args.vision_describer_model if args.vision else None,
        unload_wait_seconds=args.unload_wait,
    )
    schemas_dir = Path(__file__).parent / "schemas"
    registry = SchemaRegistry(schemas_dir=schemas_dir)

    # ---- Run tests per form type ----
    all_results: Dict[str, Any] = {}
    form_counter = 0

    for form_type in args.forms:
        forms = all_test_forms.get(form_type, [])
        if not forms:
            print(f"\n  WARNING: No test PDFs found for form type {form_type}")
            all_results[f"form_{form_type}"] = {"error": "No test PDFs found"}
            continue

        print(f"\n{'='*70}")
        print(f"  TESTING FORM {form_type} ({len(forms)} PDFs)")
        print(f"{'='*70}")

        type_results: List[Dict[str, Any]] = []

        for i, entry in enumerate(forms, 1):
            form_counter += 1
            print(f"\n{'─'*70}")
            print(f"  [{form_counter}/{total_pdfs}] Form {form_type} - PDF {i}/{len(forms)}")
            print(f"  File: {entry['stem']}")
            print(f"{'─'*70}")

            result = run_single_form(
                entry, form_type, ocr, llm, registry,
                use_vision=args.vision,
                use_vision_descriptions=args.vision_descriptions,
                vision_checkboxes_only=args.vision_checkboxes_only,
                vision_fast=args.vision_fast,
                use_graph=args.use_graph,
                vision_batch_size=args.vision_batch_size,
                vision_max_tokens=args.vision_max_tokens,
            )
            type_results.append(result)

            # Aggressive GPU cleanup between forms; wait so next form has a clear GPU
            ocr.cleanup()
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            except ImportError:
                pass
            time.sleep(5)  # Let GPU release before next form's OCR

            # Progress update
            if "accuracy" in result:
                print(
                    f"  >>> {entry['stem']}: "
                    f"Accuracy={result['accuracy']}%, "
                    f"Coverage={result['coverage']}%, "
                    f"Time={result['extraction_time_seconds']}s"
                )
            elif "error" in result:
                print(f"  >>> {entry['stem']}: ERROR - {result['error']}")

        # Aggregate for this form type
        agg = aggregate_results(type_results)
        all_results[f"form_{form_type}"] = {
            "aggregate": agg,
            "per_form": type_results,
        }

        # Print type summary
        print(f"\n{'='*60}")
        print(f"  FORM {form_type} SUMMARY ({agg['forms_successful']}/{agg['forms_tested']} successful)")
        print(f"{'='*60}")
        if agg["forms_successful"] > 0:
            print(f"  Aggregate Accuracy:     {agg['aggregate_accuracy']}%")
            print(f"  Aggregate Exact Match:  {agg['aggregate_exact_match_rate']}%")
            print(f"  Aggregate Coverage:     {agg['aggregate_coverage']}%")
            print(f"  Total GT Fields:        {agg['total_gt_fields']}")
            print(f"  Matched/Partial/Wrong/Missing: "
                  f"{agg['total_matched']}/{agg['total_partial']}/"
                  f"{agg['total_wrong']}/{agg['total_missing']}")
            print(f"  Total Time:             {agg['total_time_seconds']}s")
            print(f"\n  Per-form accuracy:")
            for stem, acc in agg["per_form_accuracy"].items():
                print(f"    {stem}: {acc}%")
        print(f"{'='*60}")

    # ---- Overall summary ----
    print(f"\n{'='*70}")
    print("  OVERALL SUMMARY")
    print(f"{'='*70}")
    print(
        f"{'Form':<8}{'PDFs':<6}{'Accuracy':<12}{'ExactMatch':<12}"
        f"{'Coverage':<12}{'Match':<7}{'Wrong':<7}{'Miss':<7}{'Time(s)':<10}"
    )
    print("-" * 82)

    for form_type in args.forms:
        data = all_results.get(f"form_{form_type}", {})
        agg = data.get("aggregate", {})
        if "error" in data:
            print(f"{form_type:<8}{'0':<6}{'ERROR':<12}{data.get('error', '')}")
        elif agg.get("forms_successful", 0) > 0:
            print(
                f"{form_type:<8}"
                f"{agg['forms_tested']:<6}"
                f"{agg['aggregate_accuracy']:<12}"
                f"{agg['aggregate_exact_match_rate']:<12}"
                f"{agg['aggregate_coverage']:<12}"
                f"{agg['total_matched']:<7}"
                f"{agg['total_wrong']:<7}"
                f"{agg['total_missing']:<7}"
                f"{agg['total_time_seconds']:<10}"
            )
        else:
            print(f"{form_type:<8}{'0':<6}{'N/A':<12}")

    # ---- Save everything ----
    save_json(all_results, OUTPUT_DIR / "test_summary.json")
    print(f"\nFull results saved to: {OUTPUT_DIR / 'test_summary.json'}")
    print(f"Intermediate outputs in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
