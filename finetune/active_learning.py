#!/usr/bin/env python3
"""Active learning loop orchestrator.

Runs one iteration of the active learning cycle:
  1. Ingest new corrections → corrections.jsonl
  2. Mine hard examples from latest test run → hard_examples.jsonl (optional)
  3. Merge all data → train_merged.jsonl
  4. Incremental SFT: resume from last checkpoint, 1 epoch, lr=5e-5
  5. Build preference pairs from corrections → preference_pairs.jsonl (optional)
  6. DPO training (optional)
  7. Export to Ollama via export_ollama.py

Each iteration is tracked in finetune/logs/iterations.json.

Usage:
    .venv/bin/python finetune/active_learning.py
    .venv/bin/python finetune/active_learning.py --skip-mining --skip-dpo
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Project root
ROOT = Path(__file__).resolve().parent.parent
FINETUNE_DIR = ROOT / "finetune"
DATA_DIR = FINETUNE_DIR / "data"
OUTPUT_DIR = FINETUNE_DIR / "output"
LOGS_DIR = FINETUNE_DIR / "logs"
CORRECTIONS_DIR = FINETUNE_DIR / "corrections"
PYTHON = str(ROOT / ".venv" / "bin" / "python")

ITERATIONS_FILE = LOGS_DIR / "iterations.json"


def _run_script(script: str, args: List[str] = None, description: str = "") -> bool:
    """Run a Python script as a subprocess. Returns True on success."""
    cmd = [PYTHON, str(FINETUNE_DIR / script)] + (args or [])
    print(f"\n  [{description or script}]")
    print(f"  Command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode != 0:
            print(f"  WARNING: {script} exited with code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"  ERROR: Failed to run {script}: {e}")
        return False


def _count_jsonl(path: Path) -> int:
    """Count lines in a JSONL file."""
    if not path.exists():
        return 0
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def _merge_jsonl_files(output_path: Path, *input_paths: Path) -> int:
    """Merge multiple JSONL files into one, deduplicating by content hash."""
    seen = set()
    total = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as out:
        for path in input_paths:
            if not path.exists():
                continue
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Simple dedup by content hash
                    key = hash(line)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.write(line + "\n")
                    total += 1

    return total


def load_iterations() -> List[Dict[str, Any]]:
    """Load iteration history."""
    if ITERATIONS_FILE.exists():
        return json.loads(ITERATIONS_FILE.read_text())
    return []


def save_iteration(iteration: Dict[str, Any]) -> None:
    """Append an iteration record."""
    iterations = load_iterations()
    iterations.append(iteration)
    ITERATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ITERATIONS_FILE.write_text(json.dumps(iterations, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Run one active learning iteration",
    )
    parser.add_argument(
        "--corrections-dir", type=Path, default=CORRECTIONS_DIR,
        help=f"Directory containing correction manifests (default: {CORRECTIONS_DIR})",
    )
    parser.add_argument(
        "--skip-mining", action="store_true",
        help="Skip hard example mining step",
    )
    parser.add_argument(
        "--skip-dpo", action="store_true",
        help="Skip DPO training step",
    )
    parser.add_argument(
        "--skip-export", action="store_true",
        help="Skip Ollama export step",
    )
    parser.add_argument(
        "--incremental-epochs", type=int, default=1,
        help="Epochs for incremental SFT (default: 1)",
    )
    parser.add_argument(
        "--incremental-lr", type=float, default=5e-5,
        help="Learning rate for incremental SFT (default: 5e-5)",
    )
    parser.add_argument(
        "--model", choices=["3b", "7b"], default="7b",
        help="Model size (default: 7b)",
    )
    args = parser.parse_args()

    iterations = load_iterations()
    iteration_num = len(iterations) + 1
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"  ACTIVE LEARNING — Iteration {iteration_num}")
    print(f"  {datetime.now().isoformat()}")
    print(f"{'='*60}")

    iteration_record = {
        "iteration": iteration_num,
        "timestamp": datetime.now().isoformat(),
        "steps": {},
    }

    # ── Step 1: Ingest corrections ──
    print(f"\n{'─'*60}")
    print(f"  Step 1: Ingest corrections")
    print(f"{'─'*60}")

    corrections_exist = (
        args.corrections_dir.exists()
        and list(args.corrections_dir.glob("*.json"))
    )

    if corrections_exist:
        n_manifests = len(list(args.corrections_dir.glob("*.json")))
        success = _run_script(
            "ingest_corrections.py",
            ["--corrections-dir", str(args.corrections_dir)],
            "Ingest corrections",
        )
        corrections_count = _count_jsonl(DATA_DIR / "corrections.jsonl")
        iteration_record["steps"]["ingest_corrections"] = {
            "success": success,
            "manifests": n_manifests,
            "examples_total": corrections_count,
        }
    else:
        print("  No correction manifests found, skipping")
        iteration_record["steps"]["ingest_corrections"] = {"skipped": True}

    # ── Step 2: Mine hard examples (optional) ──
    print(f"\n{'─'*60}")
    print(f"  Step 2: Mine hard examples")
    print(f"{'─'*60}")

    if args.skip_mining:
        print("  Skipped (--skip-mining)")
        iteration_record["steps"]["mine_hard"] = {"skipped": True}
    else:
        success = _run_script(
            "mine_hard_examples.py",
            ["--output", str(DATA_DIR / "hard_examples.jsonl")],
            "Mine hard examples",
        )
        hard_count = _count_jsonl(DATA_DIR / "hard_examples.jsonl")
        iteration_record["steps"]["mine_hard"] = {
            "success": success,
            "examples": hard_count,
        }

    # ── Step 3: Merge all data ──
    print(f"\n{'─'*60}")
    print(f"  Step 3: Merge training data")
    print(f"{'─'*60}")

    merged_path = DATA_DIR / "train_merged.jsonl"
    sources = [
        DATA_DIR / "train.jsonl",
        DATA_DIR / "hard_examples.jsonl",
        DATA_DIR / "corrections.jsonl",
    ]
    existing_sources = [s for s in sources if s.exists()]
    print(f"  Merging {len(existing_sources)} data sources:")
    for s in existing_sources:
        count = _count_jsonl(s)
        print(f"    {s.name}: {count} examples")

    total_merged = _merge_jsonl_files(merged_path, *sources)
    print(f"  Merged total: {total_merged} examples → {merged_path.name}")
    iteration_record["steps"]["merge"] = {
        "sources": [s.name for s in existing_sources],
        "total_merged": total_merged,
    }

    # ── Step 4: Incremental SFT ──
    print(f"\n{'─'*60}")
    print(f"  Step 4: Incremental SFT training")
    print(f"{'─'*60}")

    # Use curriculum with just one phase pointing at merged data
    curriculum_config = {
        "phases": [{
            "name": "incremental",
            "data_path": str(merged_path),
            "epochs": args.incremental_epochs,
            "lr": args.incremental_lr,
            "warmup_ratio": 0.1,
        }],
    }
    curriculum_path = FINETUNE_DIR / "logs" / "incremental_curriculum.json"
    curriculum_path.parent.mkdir(parents=True, exist_ok=True)
    curriculum_path.write_text(json.dumps(curriculum_config, indent=2))

    # Check for existing checkpoint to resume from
    last_checkpoint = OUTPUT_DIR / "final"
    train_args = [
        "--model", args.model,
        "--curriculum",
        "--curriculum-config", str(curriculum_path),
    ]
    if last_checkpoint.exists():
        train_args.append("--resume")

    success = _run_script("train.py", train_args, "Incremental SFT")
    iteration_record["steps"]["incremental_sft"] = {
        "success": success,
        "epochs": args.incremental_epochs,
        "lr": args.incremental_lr,
        "merged_examples": total_merged,
    }

    # ── Step 5: Build preference pairs (optional) ──
    print(f"\n{'─'*60}")
    print(f"  Step 5: Build preference pairs")
    print(f"{'─'*60}")

    if args.skip_dpo:
        print("  Skipped (--skip-dpo)")
        iteration_record["steps"]["preference_pairs"] = {"skipped": True}
    else:
        # Build from both test output errors and correction manifests
        success = _run_script(
            "build_preference_pairs.py",
            ["--include-partial"],
            "Build preference pairs from test errors",
        )
        pref_count = _count_jsonl(DATA_DIR / "preference_pairs.jsonl")

        # Also build from corrections
        if corrections_exist:
            corr_pref_count = _count_jsonl(DATA_DIR / "correction_preferences.jsonl")
            # Merge correction preferences into main preference file
            if (DATA_DIR / "correction_preferences.jsonl").exists():
                _merge_jsonl_files(
                    DATA_DIR / "preference_pairs_merged.jsonl",
                    DATA_DIR / "preference_pairs.jsonl",
                    DATA_DIR / "correction_preferences.jsonl",
                )
                pref_count = _count_jsonl(DATA_DIR / "preference_pairs_merged.jsonl")

        iteration_record["steps"]["preference_pairs"] = {
            "success": success,
            "pairs": pref_count,
        }

    # ── Step 6: DPO training (optional) ──
    print(f"\n{'─'*60}")
    print(f"  Step 6: DPO training")
    print(f"{'─'*60}")

    if args.skip_dpo:
        print("  Skipped (--skip-dpo)")
        iteration_record["steps"]["dpo"] = {"skipped": True}
    else:
        # Use merged preferences if available
        pref_path = DATA_DIR / "preference_pairs_merged.jsonl"
        if not pref_path.exists():
            pref_path = DATA_DIR / "preference_pairs.jsonl"

        if pref_path.exists() and _count_jsonl(pref_path) > 0:
            success = _run_script(
                "train_dpo.py",
                [
                    "--model", args.model,
                    "--preference-data", str(pref_path),
                    "--sft-checkpoint", str(OUTPUT_DIR / "final"),
                ],
                "DPO training",
            )
            iteration_record["steps"]["dpo"] = {"success": success}
        else:
            print("  No preference pairs available, skipping DPO")
            iteration_record["steps"]["dpo"] = {"skipped": True, "reason": "no_data"}

    # ── Step 7: Export to Ollama (optional) ──
    print(f"\n{'─'*60}")
    print(f"  Step 7: Export to Ollama")
    print(f"{'─'*60}")

    if args.skip_export:
        print("  Skipped (--skip-export)")
        iteration_record["steps"]["export"] = {"skipped": True}
    else:
        # Use DPO output if available, otherwise SFT output
        lora_dir = OUTPUT_DIR / "dpo" / "final"
        if not lora_dir.exists():
            lora_dir = OUTPUT_DIR / "final"

        if lora_dir.exists():
            success = _run_script(
                "export_ollama.py",
                ["--lora-dir", str(lora_dir)],
                "Export to Ollama",
            )
            iteration_record["steps"]["export"] = {"success": success}
        else:
            print("  No model checkpoint found, skipping export")
            iteration_record["steps"]["export"] = {"skipped": True, "reason": "no_checkpoint"}

    # ── Finalize ──
    elapsed = time.time() - start_time
    iteration_record["elapsed_seconds"] = round(elapsed, 1)
    save_iteration(iteration_record)

    print(f"\n{'='*60}")
    print(f"  ACTIVE LEARNING — Iteration {iteration_num} complete")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Log: {ITERATIONS_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
