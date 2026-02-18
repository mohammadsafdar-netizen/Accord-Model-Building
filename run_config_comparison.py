#!/usr/bin/env python3
"""
Run extraction with different configurations on 1 form per type,
compare against ground truth, and produce a comparison report.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

from compare import normalise_value

ROOT = Path(__file__).resolve().parent
TEST_DATA = ROOT / "test_data"
COMPARE_PY = ROOT / "compare.py"

# Pick 1 form per type
FORMS = {
    "125": {
        "pdf": TEST_DATA / "ACORD_0125_CommercialInsurance_Acroform" / "ACORD_0125_CommercialInsurance_Acroform_169592d5.pdf",
        "gt": TEST_DATA / "ACORD_0125_CommercialInsurance_Acroform" / "ACORD_0125_CommercialInsurance_Acroform_169592d5.json",
    },
    "127": {
        "pdf": TEST_DATA / "127_Business_Auto_Section_2015_12" / "127_Business_Auto_Section_2015_12_45df0c68.pdf",
        "gt": TEST_DATA / "127_Business_Auto_Section_2015_12" / "127_Business_Auto_Section_2015_12_45df0c68.json",
    },
    "137": {
        "pdf": TEST_DATA / "ACORD_137" / "ACORD_137_d9acd0fb.pdf",
        "gt": TEST_DATA / "ACORD_137" / "ACORD_137_d9acd0fb.json",
    },
}

# Common flags needed for full pipeline (Docling is critical for accuracy)
COMMON = ["--docling", "--gpu"]

# Previous best baseline: Positional + Smart Ensemble + Validation
# 125: 66.08%, 127: 73.80%, 137: 66.67%
BALANCED = COMMON + ["--text-llm", "--use-positional", "--smart-ensemble", "--validate-fields",
                     "--checkbox-crops", "--multimodal"]

# Configurations to test
CONFIGS = {
    "balanced": BALANCED,
    "balanced+KB": BALANCED + ["--use-knowledge-base"],
    "balanced+RAG": BALANCED + ["--use-rag"],
    "balanced+RAG+KB": BALANCED + ["--use-rag", "--use-knowledge-base"],
    "balanced+VLM": BALANCED + ["--vlm-extract", "--vlm-extract-model", "acord-vlm:latest"],
    "balanced+VLM+RAG+KB": BALANCED + ["--vlm-extract", "--vlm-extract-model", "acord-vlm:latest", "--use-rag", "--use-knowledge-base"],
}

OUTPUT_BASE = ROOT / "test_output" / "config_comparison"


def compare_results(extracted_path: Path, gt_path: Path) -> dict:
    """Compare extracted JSON against ground truth."""
    extracted = json.loads(extracted_path.read_text())
    gt = json.loads(gt_path.read_text())

    matched = 0
    partial = 0
    wrong = 0
    missing = 0
    total_gt = len(gt)

    for field, gt_val in gt.items():
        if gt_val is None or (isinstance(gt_val, str) and not gt_val.strip()):
            total_gt -= 1
            continue

        ext_val = extracted.get(field)
        if ext_val is None or (isinstance(ext_val, str) and not ext_val.strip()):
            missing += 1
            continue

        # Use compare.py's full normalization (booleans, dates, amounts, addresses, checkboxes)
        gt_str = normalise_value(gt_val, field)
        ext_str = normalise_value(ext_val, field)

        if gt_str == ext_str:
            matched += 1
        elif gt_str in ext_str or ext_str in gt_str:
            partial += 1
        else:
            wrong += 1

    accuracy = (matched / total_gt * 100) if total_gt > 0 else 0
    coverage = ((matched + partial + wrong) / total_gt * 100) if total_gt > 0 else 0

    return {
        "total_gt": total_gt,
        "matched": matched,
        "partial": partial,
        "wrong": wrong,
        "missing": missing,
        "accuracy": round(accuracy, 1),
        "coverage": round(coverage, 1),
        "fields_extracted": len([v for v in extracted.values() if v is not None and str(v).strip()]),
    }


def run_extraction(form_type: str, pdf_path: Path, config_name: str, config_flags: list) -> dict:
    """Run main.py with given flags and return result info."""
    output_dir = OUTPUT_BASE / config_name / f"form_{form_type}"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, str(ROOT / "main.py"),
        str(pdf_path),
        "--form-type", form_type,
        "--output-dir", str(output_dir),
    ] + config_flags

    print(f"    CMD: {' '.join(config_flags)}")
    t0 = time.time()

    # Configs using VLM models (--vlm-extract, --checkbox-crops, --multimodal) need longer
    uses_vlm = any(f in ("--vlm-extract", "--checkbox-crops", "--multimodal", "--vlm-crop-extract",
                         "--glm-ocr", "--nanonets-ocr") for f in config_flags)
    timeout_secs = 2400 if uses_vlm else 900
    timeout_label = "40 min" if uses_vlm else "15 min"

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_secs,
            cwd=str(ROOT),
        )
        elapsed = time.time() - t0

        # Find extracted JSON
        extracted_json = None
        for f in output_dir.rglob("*_extracted.json"):
            extracted_json = f
            break
        if not extracted_json:
            # Check if it was saved directly
            for f in output_dir.rglob("extracted.json"):
                extracted_json = f
                break

        if result.returncode != 0:
            print(f"    ERROR (exit {result.returncode}): {result.stderr[-200:]}")
            return {"error": result.stderr[-200:], "time": round(elapsed, 1)}

        return {
            "extracted_json": str(extracted_json) if extracted_json else None,
            "time": round(elapsed, 1),
            "fields_line": None,
        }

    except subprocess.TimeoutExpired:
        return {"error": f"TIMEOUT ({timeout_label})", "time": timeout_secs}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-vlm", action="store_true", help="Only run VLM configs (skip text-llm)")
    ap.add_argument("--only-config", type=str, help="Run only this config name")
    args = ap.parse_args()

    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    # Verify test forms exist
    for ft, paths in FORMS.items():
        if not paths["pdf"].exists():
            print(f"ERROR: PDF not found: {paths['pdf']}")
            return
        if not paths["gt"].exists():
            print(f"WARNING: GT not found for {ft}: {paths['gt']}")

    # Filter configs
    configs_to_run = CONFIGS
    if args.only_vlm:
        configs_to_run = {k: v for k, v in CONFIGS.items() if "vlm" in k}
    if args.only_config:
        configs_to_run = {k: v for k, v in CONFIGS.items() if k == args.only_config}

    print("=" * 80)
    print("  EXTRACTION CONFIGURATION COMPARISON TEST")
    print("=" * 80)
    print(f"  Forms: {', '.join(FORMS.keys())} (1 per type)")
    print(f"  Configs: {len(configs_to_run)}")
    print(f"  Total runs: {len(configs_to_run) * len(FORMS)}")
    print()

    # Load existing results if re-running partial
    report_path = OUTPUT_BASE / "comparison_report.json"
    if report_path.exists():
        results = json.loads(report_path.read_text())
    else:
        results = {}

    for config_name, config_flags in configs_to_run.items():
        print(f"\n{'='*70}")
        print(f"  CONFIG: {config_name}")
        print(f"  Flags: {' '.join(config_flags)}")
        print(f"{'='*70}")
        results[config_name] = {}

        for form_type, paths in FORMS.items():
            print(f"\n  [{form_type}] {paths['pdf'].name}")
            run_result = run_extraction(form_type, paths["pdf"], config_name, config_flags)

            if "error" in run_result:
                results[config_name][form_type] = {
                    "error": run_result["error"],
                    "time": run_result["time"],
                }
                continue

            # Compare against GT
            if run_result.get("extracted_json") and paths["gt"].exists():
                extracted_path = Path(run_result["extracted_json"])
                if extracted_path.exists():
                    comparison = compare_results(extracted_path, paths["gt"])
                    comparison["time"] = run_result["time"]
                    results[config_name][form_type] = comparison
                    print(f"    -> {comparison['accuracy']}% accuracy, {comparison['coverage']}% coverage, "
                          f"{comparison['fields_extracted']} fields, {run_result['time']:.0f}s")
                else:
                    results[config_name][form_type] = {
                        "error": "extracted JSON not found",
                        "time": run_result["time"],
                    }
            else:
                results[config_name][form_type] = {
                    "error": "no extracted JSON or GT",
                    "time": run_result["time"],
                }

    # ── Summary Report ──
    print("\n\n")
    print("=" * 100)
    print("  RESULTS SUMMARY")
    print("=" * 100)

    # Header
    header = f"{'Config':<28s}"
    for ft in FORMS:
        header += f"| {'ACORD '+ft:^22s}"
    header += f"| {'AVG':^14s}| {'Total Time':^10s}"
    print(header)
    print("-" * 100)

    # Rows
    for config_name in results:
        row = f"{config_name:<28s}"
        accuracies = []
        total_time = 0
        for ft in FORMS:
            r = results[config_name].get(ft, {})
            if "error" in r:
                row += f"| {'ERROR':^22s}"
            else:
                acc = r.get("accuracy", 0)
                cov = r.get("coverage", 0)
                t = r.get("time", 0)
                accuracies.append(acc)
                total_time += t
                row += f"| {acc:5.1f}% acc {cov:5.1f}% cov "
        avg = sum(accuracies) / len(accuracies) if accuracies else 0
        row += f"| {avg:5.1f}% avg | {total_time:7.0f}s "
        print(row)

    print("-" * 100)

    # Detailed per-form breakdown
    print("\n\nDETAILED BREAKDOWN:")
    print("-" * 100)
    for config_name in results:
        print(f"\n  {config_name}:")
        for ft in FORMS:
            r = results[config_name].get(ft, {})
            if "error" in r:
                print(f"    [{ft}] ERROR: {r.get('error', '?')}")
            else:
                print(f"    [{ft}] Accuracy: {r['accuracy']}% | Coverage: {r['coverage']}% | "
                      f"Matched: {r['matched']}/{r['total_gt']} | "
                      f"Partial: {r['partial']} | Wrong: {r['wrong']} | Missing: {r['missing']} | "
                      f"Extracted: {r['fields_extracted']} | Time: {r['time']:.0f}s")

    # Save
    report_path = OUTPUT_BASE / "comparison_report.json"
    report_path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"\n\nFull report saved to: {report_path}")


if __name__ == "__main__":
    main()
