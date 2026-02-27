"""Tests for finetune/export_vllm.py -- vLLM export/merge script.

Tests verify:
- Module can be imported without errors
- parse_args() has correct defaults
- merge_and_export() returns error for missing checkpoint (no Unsloth needed)
- print_vllm_command() produces correct command with tool-calling flags
- Result dict has expected structure
- Default paths reference expected directories
- No actual model loading or merging (requires GPU)
"""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest


# -- Module import tests -----------------------------------------------------

class TestExportVllmModule:
    """Tests for module-level attributes and importability."""

    def test_export_vllm_can_be_imported(self):
        import finetune.export_vllm as ev

        assert hasattr(ev, "merge_and_export")
        assert hasattr(ev, "parse_args")
        assert hasattr(ev, "print_vllm_command")

    def test_has_main(self):
        from finetune.export_vllm import main

        assert callable(main)

    def test_default_paths(self):
        from finetune.export_vllm import (
            DEFAULT_BASE_MODEL,
            DEFAULT_CHECKPOINT,
            DEFAULT_OUTPUT,
        )

        assert "agent" in str(DEFAULT_CHECKPOINT)
        assert "merged_agent" in str(DEFAULT_OUTPUT)
        assert "Qwen3-VL-8B" in DEFAULT_BASE_MODEL


# -- Arg parser tests --------------------------------------------------------

class TestExportVllmArgParser:
    """Tests for parse_args defaults and flags."""

    def test_parse_args_defaults(self):
        from finetune.export_vllm import parse_args

        old_argv = sys.argv
        sys.argv = ["export_vllm.py"]
        try:
            args = parse_args()
            assert args.max_seq_len == 8192
            assert args.quantization == "none"
            assert "Qwen3-VL-8B" in args.base_model
        finally:
            sys.argv = old_argv

    def test_parse_args_custom_checkpoint(self):
        from finetune.export_vllm import parse_args

        old_argv = sys.argv
        sys.argv = ["export_vllm.py", "--checkpoint", "/tmp/my_lora"]
        try:
            args = parse_args()
            assert args.checkpoint == "/tmp/my_lora"
        finally:
            sys.argv = old_argv

    def test_parse_args_custom_output(self):
        from finetune.export_vllm import parse_args

        old_argv = sys.argv
        sys.argv = ["export_vllm.py", "--output", "/tmp/my_output"]
        try:
            args = parse_args()
            assert args.output == "/tmp/my_output"
        finally:
            sys.argv = old_argv

    def test_parse_args_quantization_choices(self):
        from finetune.export_vllm import parse_args

        old_argv = sys.argv
        sys.argv = ["export_vllm.py", "--quantization", "awq"]
        try:
            args = parse_args()
            assert args.quantization == "awq"
        finally:
            sys.argv = old_argv

    def test_parse_args_custom_seq_len(self):
        from finetune.export_vllm import parse_args

        old_argv = sys.argv
        sys.argv = ["export_vllm.py", "--max-seq-len", "16384"]
        try:
            args = parse_args()
            assert args.max_seq_len == 16384
        finally:
            sys.argv = old_argv


# -- merge_and_export tests --------------------------------------------------

class TestMergeAndExport:
    """Tests for merge_and_export() -- no GPU or Unsloth required."""

    def test_missing_checkpoint_returns_error(self, tmp_path):
        from finetune.export_vllm import merge_and_export

        result = merge_and_export(
            checkpoint_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
        )
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_result_structure_on_error(self, tmp_path):
        from finetune.export_vllm import merge_and_export

        result = merge_and_export(
            checkpoint_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
        )
        assert "output_dir" in result
        assert "base_model" in result
        assert "checkpoint" in result
        assert "vllm_command" in result
        assert "status" in result
        assert "message" in result

    def test_error_result_has_empty_vllm_command(self, tmp_path):
        from finetune.export_vllm import merge_and_export

        result = merge_and_export(
            checkpoint_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
        )
        assert result["vllm_command"] == ""

    def test_error_result_preserves_paths(self, tmp_path):
        from finetune.export_vllm import merge_and_export

        ckpt = tmp_path / "nonexistent"
        out = tmp_path / "output"
        result = merge_and_export(checkpoint_dir=ckpt, output_dir=out)
        assert result["output_dir"] == str(out)
        assert result["checkpoint"] == str(ckpt)

    def test_default_base_model_in_result(self, tmp_path):
        from finetune.export_vllm import DEFAULT_BASE_MODEL, merge_and_export

        result = merge_and_export(
            checkpoint_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
        )
        assert result["base_model"] == DEFAULT_BASE_MODEL

    def test_custom_base_model_in_result(self, tmp_path):
        from finetune.export_vllm import merge_and_export

        result = merge_and_export(
            checkpoint_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
            base_model="my-custom-model",
        )
        assert result["base_model"] == "my-custom-model"


# -- print_vllm_command tests ------------------------------------------------

class TestPrintVllmCommand:
    """Tests for print_vllm_command() output."""

    def test_vllm_command_has_tool_choice(self):
        from finetune.export_vllm import print_vllm_command

        f = io.StringIO()
        with redirect_stdout(f):
            print_vllm_command("/tmp/test_model")
        output = f.getvalue()
        assert "--enable-auto-tool-choice" in output
        assert "--tool-call-parser hermes" in output

    def test_vllm_command_has_model_path(self):
        from finetune.export_vllm import print_vllm_command

        f = io.StringIO()
        with redirect_stdout(f):
            print_vllm_command("/tmp/test_model")
        output = f.getvalue()
        assert "--model /tmp/test_model" in output

    def test_vllm_command_has_served_model_name(self):
        from finetune.export_vllm import print_vllm_command

        f = io.StringIO()
        with redirect_stdout(f):
            print_vllm_command("/tmp/test_model")
        output = f.getvalue()
        assert "--served-model-name insurance-agent" in output

    def test_vllm_command_has_max_model_len(self):
        from finetune.export_vllm import print_vllm_command

        f = io.StringIO()
        with redirect_stdout(f):
            print_vllm_command("/tmp/test_model", max_seq_len=4096)
        output = f.getvalue()
        assert "--max-model-len 4096" in output

    def test_vllm_command_default_seq_len(self):
        from finetune.export_vllm import print_vllm_command

        f = io.StringIO()
        with redirect_stdout(f):
            print_vllm_command("/tmp/test_model")
        output = f.getvalue()
        assert "--max-model-len 8192" in output
