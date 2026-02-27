#!/usr/bin/env python3
"""Merge LoRA adapters into base model and export for vLLM serving.

This script takes a trained LoRA checkpoint (from train_agent.py) and:
1. Loads the base model + LoRA adapters
2. Merges LoRA weights into the base model
3. Saves as HuggingFace safetensors format
4. Prints the vLLM launch command

Usage:
    .venv/bin/python finetune/export_vllm.py
    .venv/bin/python finetune/export_vllm.py --checkpoint finetune/output/agent/final
    .venv/bin/python finetune/export_vllm.py --output finetune/export/merged_agent
    .venv/bin/python finetune/export_vllm.py --quantization awq  # Optional quantization
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHECKPOINT = ROOT / "finetune" / "output" / "agent" / "final"
DEFAULT_OUTPUT = ROOT / "finetune" / "export" / "merged_agent"
DEFAULT_BASE_MODEL = "Qwen/Qwen3-VL-8B-Instruct"


def parse_args():
    parser = argparse.ArgumentParser(description="Merge LoRA and export for vLLM")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=str(DEFAULT_CHECKPOINT),
        help="Path to LoRA checkpoint directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Output directory for merged model",
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default=DEFAULT_BASE_MODEL,
        help="Base model name or path",
    )
    parser.add_argument(
        "--max-seq-len",
        type=int,
        default=8192,
    )
    parser.add_argument(
        "--quantization",
        choices=["none", "awq", "gptq"],
        default="none",
        help="Post-merge quantization (default: none)",
    )
    return parser.parse_args()


def merge_and_export(
    checkpoint_dir: Path,
    output_dir: Path,
    base_model: str = DEFAULT_BASE_MODEL,
    max_seq_len: int = 8192,
    quantization: str = "none",
) -> dict:
    """Merge LoRA adapters and save merged model.

    Returns:
        dict with keys:
            output_dir: str -- path to merged model
            base_model: str -- base model name
            checkpoint: str -- path to LoRA checkpoint
            vllm_command: str -- vLLM launch command (empty on error)
            status: str -- "success" or "error"
            message: str -- human-readable status message
    """
    output_dir = Path(output_dir)
    checkpoint_dir = Path(checkpoint_dir)

    # Validate checkpoint exists
    if not checkpoint_dir.exists():
        return {
            "output_dir": str(output_dir),
            "base_model": base_model,
            "checkpoint": str(checkpoint_dir),
            "vllm_command": "",
            "status": "error",
            "message": f"Checkpoint not found: {checkpoint_dir}",
        }

    try:
        from unsloth import FastLanguageModel
    except ImportError:
        return {
            "output_dir": str(output_dir),
            "base_model": base_model,
            "checkpoint": str(checkpoint_dir),
            "vllm_command": "",
            "status": "error",
            "message": "Unsloth not installed. Run: uv pip install unsloth",
        }

    print(f"Loading base model: {base_model}")
    print(f"Loading LoRA adapters from: {checkpoint_dir}")

    model, tokenizer = FastLanguageModel.from_pretrained(
        str(checkpoint_dir),
        max_seq_length=max_seq_len,
        load_in_4bit=False,  # Load in full precision for merging
    )

    print("Merging LoRA adapters into base model...")
    model = model.merge_and_unload()

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving merged model to: {output_dir}")
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Build vLLM launch command
    vllm_cmd = (
        f"python -m vllm.entrypoints.openai.api_server \\\n"
        f"    --model {output_dir} \\\n"
        f"    --served-model-name insurance-agent \\\n"
        f"    --max-model-len {max_seq_len} \\\n"
        f"    --enable-auto-tool-choice \\\n"
        f"    --tool-call-parser hermes"
    )

    return {
        "output_dir": str(output_dir),
        "base_model": base_model,
        "checkpoint": str(checkpoint_dir),
        "vllm_command": vllm_cmd,
        "status": "success",
        "message": "Model merged and exported successfully",
    }


def print_vllm_command(output_dir: str, max_seq_len: int = 8192):
    """Print the vLLM launch command for the exported model."""
    print("\n" + "=" * 60)
    print("  vLLM Launch Command")
    print("=" * 60)
    print(
        f"\npython -m vllm.entrypoints.openai.api_server \\\n"
        f"    --model {output_dir} \\\n"
        f"    --served-model-name insurance-agent \\\n"
        f"    --max-model-len {max_seq_len} \\\n"
        f"    --enable-auto-tool-choice \\\n"
        f"    --tool-call-parser hermes\n"
    )
    print("=" * 60)


def main():
    args = parse_args()
    result = merge_and_export(
        checkpoint_dir=Path(args.checkpoint),
        output_dir=Path(args.output),
        base_model=args.base_model,
        max_seq_len=args.max_seq_len,
        quantization=args.quantization,
    )

    if result["status"] == "error":
        print(f"ERROR: {result['message']}")
        sys.exit(1)

    print(f"\n{result['message']}")
    print(f"  Output: {result['output_dir']}")
    print_vllm_command(result["output_dir"], args.max_seq_len)


if __name__ == "__main__":
    main()
