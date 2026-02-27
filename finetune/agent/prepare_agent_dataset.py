"""Dataset orchestrator CLI for agent fine-tuning.

Generates, validates, filters, and writes the full SFT + DPO dataset in
curriculum phases.  Can also re-validate existing output without regenerating.

Usage:
    .venv/bin/python finetune/agent/prepare_agent_dataset.py
    .venv/bin/python finetune/agent/prepare_agent_dataset.py --scenarios 1000
    .venv/bin/python finetune/agent/prepare_agent_dataset.py --validate-only
    .venv/bin/python finetune/agent/prepare_agent_dataset.py --output-dir finetune/data
    .venv/bin/python finetune/agent/prepare_agent_dataset.py --seed 123
    .venv/bin/python finetune/agent/prepare_agent_dataset.py --dpo-pairs 30
    .venv/bin/python finetune/agent/prepare_agent_dataset.py --window-size 10
    .venv/bin/python finetune/agent/prepare_agent_dataset.py --val-split 0.1
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from finetune.agent.assembler import (
    assemble_conversation,
    assemble_windowed_conversations,
)
from finetune.agent.build_agent_dpo_pairs import generate_dpo_pairs
from finetune.agent.scenario_generator import (
    ConversationScenario,
    generate_scenarios,
)
from finetune.agent.validate_dataset import validate_conversation, validate_dataset

# ---------------------------------------------------------------------------
# Quality thresholds
# ---------------------------------------------------------------------------

INCLUDE_THRESHOLD = 0.95
FLAG_THRESHOLD = 0.85

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write a list of dicts as one-JSON-per-line to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        for rec in records:
            fh.write(json.dumps(rec, separators=(",", ":"), default=str) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file back into a list of dicts."""
    records: list[dict] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Validate-only mode
# ---------------------------------------------------------------------------


def _validate_only(output_dir: Path) -> dict:
    """Re-read existing JSONL files and validate them without regenerating.

    Returns a result dict compatible with the normal pipeline output.
    """
    conversations: list[dict] = []
    for phase_num in [1, 2, 3]:
        phase_path = output_dir / f"agent_train_phase{phase_num}.jsonl"
        if phase_path.exists():
            conversations.extend(_read_jsonl(phase_path))

    val_path = output_dir / "agent_val.jsonl"
    if val_path.exists():
        conversations.extend(_read_jsonl(val_path))

    # Validate all conversations (without scenario cross-check since we
    # don't have the original scenarios serialised on disk).
    report = validate_dataset(conversations, scenarios=None)

    return {
        "scenarios_generated": 0,
        "conversations_assembled": len(conversations),
        "included": report["included"],
        "flagged": report["flagged"],
        "rejected": report["rejected"],
        "phase1_count": 0,
        "phase2_count": 0,
        "phase3_count": 0,
        "val_count": 0,
        "dpo_pairs": 0,
        "quality_report": report,
        "output_files": [],
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def prepare_dataset(
    scenarios: int = 520,
    output_dir: Path | None = None,
    seed: int = 42,
    validate_only: bool = False,
    dpo_pairs_per_category: int = 20,
    window_size: int = 10,
    val_split: float = 0.1,
) -> dict:
    """Run the full dataset preparation pipeline.

    Returns a summary dict with counts and paths.
    """
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent.parent / "data"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Validate-only shortcut
    # ------------------------------------------------------------------
    if validate_only:
        return _validate_only(output_dir)

    # ------------------------------------------------------------------
    # 1. Generate scenarios
    # ------------------------------------------------------------------
    scenario_list: list[ConversationScenario] = generate_scenarios(seed=seed)

    # Trim to requested count (generate_scenarios always produces 520+)
    if len(scenario_list) > scenarios:
        scenario_list = scenario_list[:scenarios]

    # ------------------------------------------------------------------
    # 2. Assemble conversations
    # ------------------------------------------------------------------
    all_conversations: list[dict] = []
    # Parallel list to keep scenario references for anti-hallucination checks
    all_scenarios: list[ConversationScenario] = []

    for sc in scenario_list:
        conv = assemble_conversation(sc, seed=seed)
        all_conversations.append(conv)
        all_scenarios.append(sc)

        # For conversations > 15 turns, also generate windowed versions
        turn_count = conv["metadata"].get("turn_count", 0)
        if turn_count > 15:
            windows = assemble_windowed_conversations(
                sc, window_size=window_size, overlap=2, seed=seed,
            )
            # Skip the first window (it overlaps fully with the base conv)
            for w in windows[1:]:
                all_conversations.append(w)
                all_scenarios.append(sc)

    # ------------------------------------------------------------------
    # 3. Validate all conversations
    # ------------------------------------------------------------------
    scores = []
    for i, conv in enumerate(all_conversations):
        sc = all_scenarios[i] if i < len(all_scenarios) else None
        score = validate_conversation(conv, sc)
        scores.append(score)

    # ------------------------------------------------------------------
    # 4. Filter by quality
    # ------------------------------------------------------------------
    included_convs: list[dict] = []
    included_scenarios: list[ConversationScenario] = []
    flagged_count = 0
    rejected_count = 0

    for conv, score in zip(all_conversations, scores):
        if score.composite >= INCLUDE_THRESHOLD:
            included_convs.append(conv)
            included_scenarios.append(
                all_scenarios[all_conversations.index(conv)]
                if conv in all_conversations
                else all_scenarios[0]
            )
        elif score.composite >= FLAG_THRESHOLD:
            # Flagged conversations are still included but counted separately
            flagged_count += 1
            included_convs.append(conv)
            included_scenarios.append(
                all_scenarios[all_conversations.index(conv)]
                if conv in all_conversations
                else all_scenarios[0]
            )
        else:
            rejected_count += 1

    # ------------------------------------------------------------------
    # 5. Split into curriculum phases
    # ------------------------------------------------------------------
    phase_buckets: dict[int, list[dict]] = {1: [], 2: [], 3: []}
    for conv in included_convs:
        cp = conv.get("metadata", {}).get("curriculum_phase", 2)
        phase_buckets.setdefault(cp, []).append(conv)

    # ------------------------------------------------------------------
    # 6. Split validation set (stratified random holdout)
    # ------------------------------------------------------------------
    rng = random.Random(seed)
    train_phase: dict[int, list[dict]] = {1: [], 2: [], 3: []}
    val_set: list[dict] = []

    for phase_num in [1, 2, 3]:
        bucket = list(phase_buckets[phase_num])
        rng.shuffle(bucket)
        n_val = max(1, int(len(bucket) * val_split)) if bucket else 0
        val_set.extend(bucket[:n_val])
        train_phase[phase_num] = bucket[n_val:]

    # ------------------------------------------------------------------
    # 7. Generate DPO pairs
    # ------------------------------------------------------------------
    dpo_pairs = generate_dpo_pairs(
        scenarios=scenario_list,
        pairs_per_category=dpo_pairs_per_category,
        seed=seed,
    )

    # ------------------------------------------------------------------
    # 8. Write output files
    # ------------------------------------------------------------------
    output_files: list[str] = []

    for phase_num in [1, 2, 3]:
        path = output_dir / f"agent_train_phase{phase_num}.jsonl"
        _write_jsonl(path, train_phase[phase_num])
        output_files.append(str(path))

    dpo_path = output_dir / "agent_dpo.jsonl"
    _write_jsonl(dpo_path, dpo_pairs)
    output_files.append(str(dpo_path))

    val_path = output_dir / "agent_val.jsonl"
    _write_jsonl(val_path, val_set)
    output_files.append(str(val_path))

    # Aggregate quality statistics
    total_conversations = len(all_conversations)
    avg_composite = (
        sum(s.composite for s in scores) / len(scores) if scores else 0.0
    )
    avg_by_validator = {}
    for vname in [
        "structural",
        "phase_consistency",
        "anti_hallucination",
        "tool_ordering",
        "behavioral",
        "form_state_consistency",
    ]:
        avg_by_validator[vname] = (
            sum(getattr(s, vname) for s in scores) / len(scores)
            if scores
            else 0.0
        )

    quality_report = {
        "total_scenarios": len(scenario_list),
        "total_conversations": total_conversations,
        "included": len(included_convs),
        "flagged": flagged_count,
        "rejected": rejected_count,
        "rejection_rate": (
            rejected_count / total_conversations
            if total_conversations > 0
            else 0.0
        ),
        "avg_composite_score": round(avg_composite, 4),
        "avg_by_validator": {k: round(v, 4) for k, v in avg_by_validator.items()},
        "phase_distribution": {
            f"phase{pn}": len(train_phase[pn]) + sum(
                1
                for c in val_set
                if c.get("metadata", {}).get("curriculum_phase") == pn
            )
            for pn in [1, 2, 3]
        },
        "dpo_pairs": len(dpo_pairs),
        "val_set_size": len(val_set),
    }

    report_path = output_dir / "agent_quality_report.json"
    report_path.write_text(json.dumps(quality_report, indent=2, default=str))
    output_files.append(str(report_path))

    # ------------------------------------------------------------------
    # 9. Build return dict
    # ------------------------------------------------------------------
    return {
        "scenarios_generated": len(scenario_list),
        "conversations_assembled": total_conversations,
        "included": len(included_convs),
        "flagged": flagged_count,
        "rejected": rejected_count,
        "phase1_count": len(train_phase[1]),
        "phase2_count": len(train_phase[2]),
        "phase3_count": len(train_phase[3]),
        "val_count": len(val_set),
        "dpo_pairs": len(dpo_pairs),
        "quality_report": quality_report,
        "output_files": output_files,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare agent fine-tuning dataset",
    )
    parser.add_argument("--scenarios", type=int, default=520)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--dpo-pairs", type=int, default=20)
    parser.add_argument("--window-size", type=int, default=10)
    parser.add_argument("--val-split", type=float, default=0.1)
    args = parser.parse_args()

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path(__file__).resolve().parent.parent / "data"
    )

    result = prepare_dataset(
        scenarios=args.scenarios,
        output_dir=output_dir,
        seed=args.seed,
        validate_only=args.validate_only,
        dpo_pairs_per_category=args.dpo_pairs,
        window_size=args.window_size,
        val_split=args.val_split,
    )

    print("\nDataset preparation complete!")
    print(f"  Scenarios: {result['scenarios_generated']}")
    print(f"  Conversations: {result['conversations_assembled']}")
    print(f"  Included: {result['included']}")
    print(f"  Flagged: {result['flagged']}")
    print(f"  Rejected: {result['rejected']}")
    print(f"  Phase 1 (train): {result['phase1_count']}")
    print(f"  Phase 2 (train): {result['phase2_count']}")
    print(f"  Phase 3 (train): {result['phase3_count']}")
    print(f"  Validation set: {result['val_count']}")
    print(f"  DPO pairs: {result['dpo_pairs']}")
    for f in result.get("output_files", []):
        print(f"  Output: {f}")


if __name__ == "__main__":
    main()
