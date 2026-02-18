#!/usr/bin/env python3
"""Fine-tune Qwen2.5-VL on ACORD form extraction using Unsloth QLoRA.

Prerequisites:
    uv pip install unsloth bitsandbytes datasets

Usage:
    .venv/bin/python finetune/train.py                          # defaults (3B, 3 epochs)
    .venv/bin/python finetune/train.py --model 7b --epochs 5    # 7B model, 5 epochs
    .venv/bin/python finetune/train.py --resume                 # resume from last checkpoint
"""

import argparse
import json
import os
import sys
from pathlib import Path

from torch.utils.data import Dataset as TorchDataset
from PIL import Image

# ── Configuration ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "finetune" / "data"
OUTPUT_DIR = ROOT / "finetune" / "output"

MODEL_MAP = {
    "3b": "unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit",
    "7b": "unsloth/Qwen2.5-VL-7B-Instruct-bnb-4bit",
}

# Image resolution constraints (pixels = H * W, not side length)
# Qwen2.5-VL processes images in 28x28 patches
MIN_PIXELS = 256 * 28 * 28    # ~200K pixels
MAX_PIXELS = 768 * 28 * 28    # ~600K pixels


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune VLM on ACORD forms")
    parser.add_argument(
        "--model", choices=["3b", "7b"], default="3b",
        help="Model size (default: 3b for proof-of-concept)",
    )
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs (default: 3)")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate (default: 2e-4)")
    parser.add_argument("--batch-size", type=int, default=1, help="Per-device batch size (default: 1)")
    parser.add_argument("--grad-accum", type=int, default=8, help="Gradient accumulation steps (default: 8)")
    parser.add_argument("--max-seq-len", type=int, default=4096, help="Max sequence length (default: 4096)")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank (default: 16)")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha (default: 32)")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    return parser.parse_args()


class ACORDVisionDataset(TorchDataset):
    """PyTorch Dataset that loads JSONL training examples with images.

    Avoids PyArrow serialization issues with mixed content types in messages
    by loading images lazily and returning raw dicts for the data collator.
    """

    def __init__(self, jsonl_path: Path):
        self.examples = []
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    self.examples.append(json.loads(line))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        # Load images as PIL
        images = []
        for p in ex.get("images", []):
            if os.path.exists(p):
                images.append(Image.open(p).convert("RGB"))
            else:
                print(f"  WARNING: Image not found: {p}", file=sys.stderr)
        return {
            "messages": ex["messages"],
            "images": images,
        }


def main():
    args = parse_args()

    # ── Validate data exists ──
    train_path = DATA_DIR / "train.jsonl"
    val_path = DATA_DIR / "val.jsonl"
    if not train_path.exists():
        print("ERROR: Training data not found. Run prepare_dataset.py first.")
        print(f"  Expected: {train_path}")
        sys.exit(1)

    # ── Load raw data ──
    print("Loading datasets...")
    train_dataset = ACORDVisionDataset(train_path)
    val_dataset = ACORDVisionDataset(val_path) if val_path.exists() else None
    print(f"  Train: {len(train_dataset)} examples")
    print(f"  Val:   {len(val_dataset) if val_dataset else 0} examples")

    # ── Import Unsloth (heavy imports) ──
    print(f"\nLoading model: {MODEL_MAP[args.model]}...")
    from unsloth import FastVisionModel
    from unsloth.trainer import is_bfloat16_supported, UnslothVisionDataCollator

    model, tokenizer = FastVisionModel.from_pretrained(
        MODEL_MAP[args.model],
        max_seq_length=args.max_seq_len,
        load_in_4bit=True,
        use_gradient_checkpointing="unsloth",
    )

    # ── Apply LoRA adapters ──
    print("Applying LoRA adapters...")
    model = FastVisionModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        bias="none",
        use_rslora=False,
        finetune_vision_layers=True,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
    )

    # ── Configure training ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from trl import SFTConfig, SFTTrainer

    total_steps = (len(train_dataset) * args.epochs) // (args.batch_size * args.grad_accum)
    warmup_steps = max(1, total_steps // 10)

    training_args = SFTConfig(
        output_dir=str(OUTPUT_DIR),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        warmup_steps=warmup_steps,
        lr_scheduler_type="cosine",
        optim="adamw_8bit",
        weight_decay=0.01,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=1,
        save_strategy="epoch",
        save_total_limit=3,
        seed=args.seed,
        max_seq_length=args.max_seq_len,
        report_to="none",
        remove_unused_columns=False,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        dataloader_pin_memory=False,
    )

    # ── Create trainer ──
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=UnslothVisionDataCollator(model, tokenizer),
    )

    # ── Train ──
    print(f"\nStarting training:")
    print(f"  Model:    {MODEL_MAP[args.model]}")
    print(f"  LoRA:     r={args.lora_r}, alpha={args.lora_alpha}")
    print(f"  Epochs:   {args.epochs}")
    print(f"  Batch:    {args.batch_size} x {args.grad_accum} grad accum")
    print(f"  LR:       {args.lr}")
    print(f"  Steps:    ~{total_steps}")
    print(f"  Output:   {OUTPUT_DIR}")
    print()

    resume_from = None
    if args.resume:
        # Find latest checkpoint
        checkpoints = sorted(OUTPUT_DIR.glob("checkpoint-*"))
        if checkpoints:
            resume_from = str(checkpoints[-1])
            print(f"  Resuming from: {resume_from}")
        else:
            print("  No checkpoint found, starting fresh.")

    trainer.train(resume_from_checkpoint=resume_from)

    # ── Save final model ──
    final_dir = OUTPUT_DIR / "final"
    print(f"\nSaving final LoRA model to {final_dir}...")
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    # ── Evaluate on val set ──
    if val_dataset is not None and len(val_dataset) > 0:
        print("\nRunning validation...")
        metrics = trainer.evaluate()
        print(f"  Val loss: {metrics.get('eval_loss', 'N/A'):.4f}")

    print("\nTraining complete!")
    print(f"  LoRA adapters saved to: {final_dir}")
    print(f"  Next step: python finetune/export_ollama.py")


if __name__ == "__main__":
    main()
