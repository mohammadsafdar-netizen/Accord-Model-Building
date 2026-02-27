"""Tests for the dataset orchestrator (prepare_agent_dataset.py)."""

import json
from pathlib import Path

import pytest

from finetune.agent.prepare_agent_dataset import prepare_dataset


def test_prepare_dataset_returns_report(tmp_path):
    """prepare_dataset returns a dict with expected keys."""
    result = prepare_dataset(
        scenarios=10,
        output_dir=tmp_path,
        seed=42,
        dpo_pairs_per_category=2,
    )
    assert isinstance(result, dict)
    assert result["scenarios_generated"] >= 10
    assert result["conversations_assembled"] >= 10
    assert "included" in result


def test_prepare_dataset_creates_output_files(tmp_path):
    """Output directory contains the expected JSONL and JSON files."""
    result = prepare_dataset(
        scenarios=10,
        output_dir=tmp_path,
        seed=42,
        dpo_pairs_per_category=2,
    )
    assert (tmp_path / "agent_train_phase1.jsonl").exists()
    assert (tmp_path / "agent_dpo.jsonl").exists()
    assert (tmp_path / "agent_quality_report.json").exists()
    assert (tmp_path / "agent_val.jsonl").exists()


def test_jsonl_files_are_valid(tmp_path):
    """Every line in every JSONL file is valid JSON."""
    prepare_dataset(
        scenarios=10,
        output_dir=tmp_path,
        seed=42,
        dpo_pairs_per_category=2,
    )
    for jsonl_file in tmp_path.glob("*.jsonl"):
        with open(jsonl_file) as f:
            for line in f:
                if line.strip():
                    json.loads(line)  # Should not raise


def test_quality_report_is_valid_json(tmp_path):
    """Quality report is valid JSON with expected top-level keys."""
    prepare_dataset(
        scenarios=10,
        output_dir=tmp_path,
        seed=42,
        dpo_pairs_per_category=2,
    )
    report_path = tmp_path / "agent_quality_report.json"
    report = json.loads(report_path.read_text())
    assert "total_scenarios" in report
    assert "avg_composite_score" in report
    assert "rejection_rate" in report


def test_val_set_is_subset(tmp_path):
    """Validation set has at least 1 example."""
    prepare_dataset(
        scenarios=20,
        output_dir=tmp_path,
        seed=42,
        dpo_pairs_per_category=2,
    )
    val_path = tmp_path / "agent_val.jsonl"
    val_count = sum(1 for line in open(val_path) if line.strip())
    assert val_count >= 1


def test_phase_files_have_correct_curriculum(tmp_path):
    """Each phase JSONL file only contains entries with the matching curriculum_phase."""
    prepare_dataset(
        scenarios=20,
        output_dir=tmp_path,
        seed=42,
        dpo_pairs_per_category=2,
    )
    for phase_num in [1, 2, 3]:
        path = tmp_path / f"agent_train_phase{phase_num}.jsonl"
        if path.exists():
            with open(path) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        assert data["metadata"]["curriculum_phase"] == phase_num


def test_dpo_file_has_chosen_rejected(tmp_path):
    """Every DPO line has 'chosen' and 'rejected' keys."""
    prepare_dataset(
        scenarios=10,
        output_dir=tmp_path,
        seed=42,
        dpo_pairs_per_category=2,
    )
    dpo_path = tmp_path / "agent_dpo.jsonl"
    with open(dpo_path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                assert "chosen" in data
                assert "rejected" in data


def test_validate_only_mode(tmp_path):
    """validate_only re-reads existing files without regenerating."""
    # First generate
    prepare_dataset(
        scenarios=10,
        output_dir=tmp_path,
        seed=42,
        dpo_pairs_per_category=2,
    )
    # Then validate-only (should not regenerate, just validate existing)
    result = prepare_dataset(
        scenarios=10,
        output_dir=tmp_path,
        seed=42,
        validate_only=True,
        dpo_pairs_per_category=2,
    )
    assert "included" in result
