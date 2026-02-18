#!/usr/bin/env python3
"""Export fine-tuned LoRA model to GGUF and register with Ollama.

Steps:
1. Load base model + LoRA adapters
2. Save merged 16-bit model
3. Convert to GGUF BF16 using llama.cpp converter (with venv python)
4. Quantize to Q5_K_M using llama-quantize
5. Create Ollama Modelfile and register

Usage:
    .venv/bin/python finetune/export_ollama.py
    .venv/bin/python finetune/export_ollama.py --quant q5_k_m --name my-acord-vlm
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "finetune" / "output"
EXPORT_DIR = ROOT / "finetune" / "export"
LLAMA_CPP = ROOT / "llama.cpp"

SYSTEM_PROMPT = (
    "You are an expert ACORD insurance form data extractor. "
    "Given an image of an ACORD form page, extract the requested fields "
    "and return ONLY valid JSON with field names as keys and extracted values."
)


def parse_args():
    parser = argparse.ArgumentParser(description="Export fine-tuned model to Ollama")
    parser.add_argument(
        "--model", choices=["3b", "7b"], default="3b",
        help="Base model size used during training (default: 3b)",
    )
    parser.add_argument(
        "--quant", default="q5_k_m",
        help="GGUF quantization type (default: q5_k_m)",
    )
    parser.add_argument(
        "--name", default="acord-vlm",
        help="Ollama model name (default: acord-vlm)",
    )
    parser.add_argument(
        "--lora-dir", type=str, default=None,
        help="Path to LoRA adapter dir (default: finetune/output/final)",
    )
    return parser.parse_args()


def run_cmd(cmd, desc, cwd=None):
    """Run a shell command with the venv Python on PATH."""
    venv_bin = str(ROOT / ".venv" / "bin")
    env = os.environ.copy()
    env["PATH"] = venv_bin + ":" + env.get("PATH", "")

    print(f"  Running: {desc}...")
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd or str(ROOT), env=env,
    )
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode}):")
        print(f"    stderr: {result.stderr[-500:] if result.stderr else 'none'}")
        print(f"    stdout: {result.stdout[-500:] if result.stdout else 'none'}")
        sys.exit(1)
    return result


def main():
    args = parse_args()

    lora_dir = Path(args.lora_dir) if args.lora_dir else OUTPUT_DIR / "final"
    if not lora_dir.exists():
        print(f"ERROR: LoRA directory not found: {lora_dir}")
        print("  Run train.py first to generate LoRA adapters.")
        sys.exit(1)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    merged_dir = EXPORT_DIR / "merged_16bit"

    # ── Step 1: Merge LoRA → 16-bit safetensors ──
    if merged_dir.exists() and list(merged_dir.glob("*.safetensors")):
        print(f"Merged model already exists at {merged_dir}, skipping merge...")
    else:
        print(f"Loading base model + LoRA from {lora_dir}...")
        from unsloth import FastVisionModel

        model, tokenizer = FastVisionModel.from_pretrained(
            model_name=str(lora_dir),
            max_seq_length=4096,
            load_in_4bit=True,
        )

        print(f"Merging LoRA → 16-bit at {merged_dir}...")
        model.save_pretrained_merged(
            str(merged_dir),
            tokenizer,
            save_method="merged_16bit",
        )
        print(f"  Merged model saved ({sum(f.stat().st_size for f in merged_dir.glob('*.safetensors')) / 1e9:.1f} GB)")

        # Free GPU memory
        del model, tokenizer
        import torch
        torch.cuda.empty_cache()
        import gc
        gc.collect()

    # ── Step 2: Convert to BF16 GGUF ──
    converter = LLAMA_CPP / "unsloth_convert_hf_to_gguf.py"
    if not converter.exists():
        # Fallback to standard converter
        converter = LLAMA_CPP / "convert_hf_to_gguf.py"
    if not converter.exists():
        print(f"ERROR: No GGUF converter found in {LLAMA_CPP}")
        sys.exit(1)

    bf16_gguf = EXPORT_DIR / "acord-vlm-bf16.gguf"
    if bf16_gguf.exists():
        print(f"BF16 GGUF already exists at {bf16_gguf}, skipping conversion...")
    else:
        print(f"\nConverting to BF16 GGUF...")
        run_cmd(
            f"python {converter} "
            f"--outfile {bf16_gguf} "
            f"--outtype bf16 "
            f"--split-max-size 50G "
            f"{merged_dir}",
            desc="HF → BF16 GGUF conversion",
        )
        print(f"  BF16 GGUF: {bf16_gguf} ({bf16_gguf.stat().st_size / 1e9:.1f} GB)")

    # ── Step 3: Quantize to target quant ──
    quantizer = LLAMA_CPP / "llama-quantize"
    if not quantizer.exists():
        # Try build directory
        quantizer = LLAMA_CPP / "build" / "bin" / "llama-quantize"
    if not quantizer.exists():
        print(f"ERROR: llama-quantize not found in {LLAMA_CPP}")
        sys.exit(1)

    final_gguf = EXPORT_DIR / f"acord-vlm-{args.quant}.gguf"
    if args.quant.lower() == "bf16":
        final_gguf = bf16_gguf
        print(f"Skipping quantization (already BF16)")
    else:
        print(f"\nQuantizing BF16 → {args.quant}...")
        run_cmd(
            f"{quantizer} {bf16_gguf} {final_gguf} {args.quant.upper()}",
            desc=f"Quantize to {args.quant}",
        )
        print(f"  Quantized GGUF: {final_gguf} ({final_gguf.stat().st_size / 1e9:.1f} GB)")

        # Delete BF16 intermediate to save disk
        bf16_gguf.unlink()
        print(f"  Deleted BF16 intermediate to save disk")

    # ── Step 4: Clean up merged_16bit to save disk ──
    import shutil
    if merged_dir.exists() and final_gguf.exists():
        shutil.rmtree(merged_dir)
        print(f"  Deleted merged_16bit dir to save disk")

    # ── Step 5: Create Ollama Modelfile ──
    modelfile_path = EXPORT_DIR / "Modelfile"
    modelfile_content = f"""FROM ./{final_gguf.name}

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 4096

SYSTEM \"\"\"{SYSTEM_PROMPT}\"\"\"
"""
    modelfile_path.write_text(modelfile_content)
    print(f"  Modelfile created: {modelfile_path}")

    # ── Step 6: Register with Ollama ──
    print(f"\nRegistering with Ollama as '{args.name}'...")
    try:
        result = subprocess.run(
            ["ollama", "create", args.name, "-f", str(modelfile_path)],
            cwd=str(EXPORT_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            print(f"  Model registered: {args.name}")
            print(f"\n  Test with:")
            print(f"    ollama run {args.name}")
            print(f"\n  Use in pipeline:")
            print(f"    .venv/bin/python test_pipeline.py --gpu --one-per-form \\")
            print(f"        --vlm-extract --vlm-extract-model {args.name} \\")
            print(f"        --text-llm --smart-ensemble")
        else:
            print(f"  WARNING: Ollama registration failed:")
            print(f"    stdout: {result.stdout}")
            print(f"    stderr: {result.stderr}")
            print(f"\n  Manual registration:")
            print(f"    cd {EXPORT_DIR}")
            print(f"    ollama create {args.name} -f Modelfile")
    except FileNotFoundError:
        print("  WARNING: 'ollama' command not found.")
        print(f"\n  Manual registration:")
        print(f"    cd {EXPORT_DIR}")
        print(f"    ollama create {args.name} -f Modelfile")
    except subprocess.TimeoutExpired:
        print("  WARNING: Ollama registration timed out (>5 min).")
        print(f"  Try manually: cd {EXPORT_DIR} && ollama create {args.name} -f Modelfile")

    print("\nExport complete!")


if __name__ == "__main__":
    main()
