"""Tests for finetune/train_agent.py — agent conversation fine-tuning script.

Tests verify:
- AgentConversationDataset loads JSONL correctly
- Curriculum config default_agent_3phase works
- Arg parser has expected flags with correct defaults
- Module can be imported without errors
- No actual model loading or training (requires GPU)
"""

import json
import sys
from pathlib import Path

import pytest


# ── Curriculum config tests ───────────────────────────────────────────

class TestAgentCurriculumConfig:
    """Tests for CurriculumConfig.default_agent_3phase."""

    def test_agent_curriculum_config(self):
        from finetune.curriculum_config import CurriculumConfig

        data_dir = Path("/tmp/test_data")
        config = CurriculumConfig.default_agent_3phase(data_dir)
        assert len(config.phases) == 3
        assert config.phases[0].name == "agent_foundation"
        assert config.phases[0].lr == 2e-4
        assert config.phases[1].name == "agent_complex"
        assert config.phases[1].lr == 1e-4
        assert config.phases[2].name == "agent_error_specific"
        assert config.phases[2].lr == 5e-5

    def test_agent_curriculum_data_paths(self):
        from finetune.curriculum_config import CurriculumConfig

        data_dir = Path("/tmp/test_data")
        config = CurriculumConfig.default_agent_3phase(data_dir)
        assert config.phases[0].data_path == data_dir / "agent_train_phase1.jsonl"
        assert config.phases[1].data_path == data_dir / "agent_train_phase2.jsonl"
        assert config.phases[2].data_path == data_dir / "agent_train_phase3.jsonl"

    def test_agent_curriculum_epochs(self):
        from finetune.curriculum_config import CurriculumConfig

        data_dir = Path("/tmp/test_data")
        config = CurriculumConfig.default_agent_3phase(data_dir)
        assert config.phases[0].epochs == 2
        assert config.phases[1].epochs == 2
        assert config.phases[2].epochs == 1

    def test_agent_curriculum_serialization(self):
        """Config should round-trip through dict serialization."""
        from finetune.curriculum_config import CurriculumConfig

        data_dir = Path("/tmp/test_data")
        config = CurriculumConfig.default_agent_3phase(data_dir)
        d = config.to_dict()
        restored = CurriculumConfig.from_dict(d)
        assert len(restored.phases) == 3
        assert restored.phases[0].name == "agent_foundation"
        assert restored.phases[2].lr == 5e-5


# ── AgentConversationDataset tests ────────────────────────────────────

class TestAgentConversationDataset:
    """Tests for the AgentConversationDataset class."""

    def test_agent_dataset_loads_jsonl(self, tmp_path):
        from finetune.train_agent import AgentConversationDataset

        jsonl = tmp_path / "test.jsonl"
        examples = [
            {
                "messages": [
                    {"role": "system", "content": "You are an insurance agent."},
                    {"role": "user", "content": "hi"},
                ],
                "metadata": {"scenario_id": "s1"},
            },
            {
                "messages": [
                    {"role": "system", "content": "You are an insurance agent."},
                    {"role": "user", "content": "hello"},
                ],
                "metadata": {"scenario_id": "s2"},
            },
        ]
        with open(jsonl, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")

        dataset = AgentConversationDataset(jsonl)
        assert len(dataset) == 2
        item = dataset[0]
        assert "messages" in item
        assert item["messages"][0]["role"] == "system"

    def test_agent_dataset_returns_only_messages(self, tmp_path):
        from finetune.train_agent import AgentConversationDataset

        jsonl = tmp_path / "test.jsonl"
        with open(jsonl, "w") as f:
            f.write(
                json.dumps(
                    {
                        "messages": [{"role": "user", "content": "hi"}],
                        "metadata": {"foo": "bar"},
                    }
                )
                + "\n"
            )

        dataset = AgentConversationDataset(jsonl)
        item = dataset[0]
        assert "messages" in item
        assert "metadata" not in item  # metadata should not be in training item

    def test_agent_dataset_skips_blank_lines(self, tmp_path):
        from finetune.train_agent import AgentConversationDataset

        jsonl = tmp_path / "test.jsonl"
        with open(jsonl, "w") as f:
            f.write(json.dumps({"messages": [{"role": "user", "content": "a"}], "metadata": {}}) + "\n")
            f.write("\n")  # blank line
            f.write("   \n")  # whitespace-only line
            f.write(json.dumps({"messages": [{"role": "user", "content": "b"}], "metadata": {}}) + "\n")

        dataset = AgentConversationDataset(jsonl)
        assert len(dataset) == 2

    def test_agent_dataset_empty_file(self, tmp_path):
        from finetune.train_agent import AgentConversationDataset

        jsonl = tmp_path / "empty.jsonl"
        jsonl.touch()

        dataset = AgentConversationDataset(jsonl)
        assert len(dataset) == 0

    def test_agent_dataset_preserves_message_order(self, tmp_path):
        from finetune.train_agent import AgentConversationDataset

        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a2"},
        ]
        jsonl = tmp_path / "test.jsonl"
        with open(jsonl, "w") as f:
            f.write(json.dumps({"messages": messages, "metadata": {}}) + "\n")

        dataset = AgentConversationDataset(jsonl)
        item = dataset[0]
        assert len(item["messages"]) == 5
        assert item["messages"][0]["role"] == "system"
        assert item["messages"][4]["content"] == "a2"


# ── Module import tests ──────────────────────────────────────────────

class TestTrainAgentModule:
    """Tests for module-level attributes and importability."""

    def test_train_agent_can_be_imported(self):
        import finetune.train_agent as ta

        assert hasattr(ta, "AgentConversationDataset")
        assert hasattr(ta, "AGENT_MODEL")
        assert hasattr(ta, "parse_args")

    def test_train_agent_model_name(self):
        from finetune.train_agent import AGENT_MODEL

        assert "Qwen3-VL-8B" in AGENT_MODEL

    def test_train_agent_has_main(self):
        from finetune.train_agent import main

        assert callable(main)

    def test_train_agent_has_load_model_function(self):
        """The _load_model_and_lora function should exist."""
        import finetune.train_agent as ta

        assert hasattr(ta, "_load_model_and_lora")

    def test_train_agent_has_curriculum_training(self):
        """The run_curriculum_training function should exist."""
        import finetune.train_agent as ta

        assert hasattr(ta, "run_curriculum_training")

    def test_output_dir_is_agent_specific(self):
        from finetune.train_agent import OUTPUT_DIR

        assert "agent" in str(OUTPUT_DIR)


# ── Arg parser tests ─────────────────────────────────────────────────

class TestTrainAgentArgParser:
    """Tests for parse_args defaults and flags."""

    def test_parse_args_defaults(self):
        from finetune.train_agent import parse_args

        old_argv = sys.argv
        sys.argv = ["train_agent.py"]
        try:
            args = parse_args()
            assert args.max_seq_len == 8192
            assert args.lora_r == 32
            assert args.lora_alpha == 64
            assert args.epochs == 2
            assert args.lr == 2e-4
            assert args.batch_size == 1
            assert args.grad_accum == 8
            assert args.seed == 42
        finally:
            sys.argv = old_argv

    def test_parse_args_resume_flag(self):
        from finetune.train_agent import parse_args

        old_argv = sys.argv
        sys.argv = ["train_agent.py", "--resume"]
        try:
            args = parse_args()
            assert args.resume is True
        finally:
            sys.argv = old_argv

    def test_parse_args_curriculum_flag(self):
        from finetune.train_agent import parse_args

        old_argv = sys.argv
        sys.argv = ["train_agent.py", "--curriculum"]
        try:
            args = parse_args()
            assert args.curriculum is True
        finally:
            sys.argv = old_argv

    def test_parse_args_custom_values(self):
        from finetune.train_agent import parse_args

        old_argv = sys.argv
        sys.argv = [
            "train_agent.py",
            "--epochs", "5",
            "--lr", "1e-4",
            "--lora-r", "64",
            "--lora-alpha", "128",
            "--max-seq-len", "16384",
        ]
        try:
            args = parse_args()
            assert args.epochs == 5
            assert args.lr == 1e-4
            assert args.lora_r == 64
            assert args.lora_alpha == 128
            assert args.max_seq_len == 16384
        finally:
            sys.argv = old_argv

    def test_parse_args_no_resume_by_default(self):
        from finetune.train_agent import parse_args

        old_argv = sys.argv
        sys.argv = ["train_agent.py"]
        try:
            args = parse_args()
            assert args.resume is False
            assert args.curriculum is False
        finally:
            sys.argv = old_argv
