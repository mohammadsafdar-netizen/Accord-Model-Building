#!/usr/bin/env python3
"""Fine-tune Qwen3-VL-8B for insurance agent conversations using Unsloth QLoRA.

This script trains on text-only conversation data (no images).
Uses FastLanguageModel instead of FastVisionModel since agent
conversations are pure text with tool calls.

Prerequisites:
    uv pip install unsloth bitsandbytes datasets trl

Usage:
    .venv/bin/python finetune/train_agent.py
    .venv/bin/python finetune/train_agent.py --epochs 5 --lr 1e-4
    .venv/bin/python finetune/train_agent.py --curriculum
    .venv/bin/python finetune/train_agent.py --resume
"""

import argparse
import json
import sys
from pathlib import Path

from torch.utils.data import Dataset as TorchDataset

# ── Configuration ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "finetune" / "data"
OUTPUT_DIR = ROOT / "finetune" / "output" / "agent"

AGENT_MODEL = "unsloth/Qwen3-VL-8B-Instruct-bnb-4bit"


def parse_args():
    """Parse command-line arguments for agent fine-tuning."""
    parser = argparse.ArgumentParser(
        description="Fine-tune agent on conversation data"
    )
    parser.add_argument(
        "--epochs", type=int, default=2,
        help="Training epochs (default: 2)",
    )
    parser.add_argument(
        "--lr", type=float, default=2e-4,
        help="Learning rate (default: 2e-4)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1,
        help="Per-device batch size (default: 1)",
    )
    parser.add_argument(
        "--grad-accum", type=int, default=8,
        help="Gradient accumulation steps (default: 8)",
    )
    parser.add_argument(
        "--max-seq-len", type=int, default=8192,
        help="Max sequence length (default: 8192, longer for conversations)",
    )
    parser.add_argument(
        "--lora-r", type=int, default=32,
        help="LoRA rank (default: 32, higher for tool-calling precision)",
    )
    parser.add_argument(
        "--lora-alpha", type=int, default=64,
        help="LoRA alpha (default: 64, 2x lora-r)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--curriculum", action="store_true",
        help="Enable multi-phase curriculum training (foundation -> complex -> error-specific)",
    )
    parser.add_argument(
        "--curriculum-config", type=str, default=None,
        help="Path to curriculum config JSON (default: built-in 3-phase agent config)",
    )
    return parser.parse_args()


class AgentConversationDataset(TorchDataset):
    """PyTorch Dataset for agent conversation JSONL files.

    Unlike ACORDVisionDataset, this loads text-only conversations
    (no images). Each JSONL line has {"messages": [...], "metadata": {...}}.

    Only the "messages" field is returned for training; metadata is
    used during dataset preparation but not during training.
    """

    def __init__(self, jsonl_path: Path):
        self.examples = []
        with open(jsonl_path) as f:
            for line in f:
                if line.strip():
                    self.examples.append(json.loads(line))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return {"messages": self.examples[idx]["messages"]}


def _load_model_and_lora(args):
    """Load Qwen3-VL-8B with FastLanguageModel and apply LoRA.

    Returns (model, tokenizer).

    Raises ImportError with a helpful message if Unsloth is not installed.
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print(
            "ERROR: Unsloth is not installed. Install it with:\n"
            "  uv pip install unsloth bitsandbytes\n",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nLoading model: {AGENT_MODEL}...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        AGENT_MODEL,
        max_seq_length=args.max_seq_len,
        load_in_4bit=True,
        use_gradient_checkpointing="unsloth",
    )

    print("Applying LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
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
    )

    return model, tokenizer


def run_curriculum_training(model, tokenizer, args, config):
    """Run multi-phase curriculum training for agent conversations.

    Each phase creates a fresh SFTConfig + SFTTrainer with phase-specific
    lr/epochs. The model stays in memory across phases (LoRA weights accumulate).
    Phases whose data files don't exist are skipped with a warning.
    """
    from trl import SFTConfig, SFTTrainer
    from unsloth.trainer import is_bfloat16_supported

    val_path = DATA_DIR / "agent_val.jsonl"
    val_dataset = AgentConversationDataset(val_path) if val_path.exists() else None

    print(f"\n{'='*60}")
    print(f"  AGENT CURRICULUM TRAINING - {len(config.phases)} phases")
    print(f"{'='*60}")

    for phase_idx, phase in enumerate(config.phases):
        print(f"\n{'-'*60}")
        print(f"  Phase {phase_idx + 1}/{len(config.phases)}: {phase.name}")
        print(f"  Data:   {phase.data_path}")
        print(f"  Epochs: {phase.epochs}")
        print(f"  LR:     {phase.lr}")
        print(f"{'-'*60}")

        if not phase.data_path.exists():
            print(f"  WARNING: Data file not found, skipping phase: {phase.data_path}")
            continue

        train_dataset = AgentConversationDataset(phase.data_path)
        if len(train_dataset) == 0:
            print(f"  WARNING: Empty dataset, skipping phase: {phase.data_path}")
            continue

        print(f"  Loaded {len(train_dataset)} training examples")

        phase_output_dir = OUTPUT_DIR / f"phase_{phase_idx}_{phase.name}"
        phase_output_dir.mkdir(parents=True, exist_ok=True)

        total_steps = (len(train_dataset) * phase.epochs) // (args.batch_size * args.grad_accum)
        warmup_steps = max(1, int(total_steps * phase.warmup_ratio))

        training_args = SFTConfig(
            output_dir=str(phase_output_dir),
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            learning_rate=phase.lr,
            num_train_epochs=phase.epochs,
            warmup_steps=warmup_steps,
            lr_scheduler_type="cosine",
            optim="adamw_8bit",
            weight_decay=0.01,
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=1,
            save_strategy="epoch",
            save_total_limit=2,
            seed=args.seed,
            max_seq_length=args.max_seq_len,
            report_to="none",
            remove_unused_columns=False,
            dataset_text_field="",
            dataset_kwargs={"skip_prepare_dataset": True},
            dataloader_pin_memory=False,
        )

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
        )

        trainer.train()

        # Save phase checkpoint
        final_dir = phase_output_dir / "final"
        print(f"  Saving phase checkpoint to {final_dir}...")
        model.save_pretrained(str(final_dir))
        tokenizer.save_pretrained(str(final_dir))

        # Evaluate
        if val_dataset is not None and len(val_dataset) > 0:
            metrics = trainer.evaluate()
            print(f"  Phase {phase.name} val loss: {metrics.get('eval_loss', 'N/A'):.4f}")

    # Save final combined model
    final_dir = OUTPUT_DIR / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving final curriculum model to {final_dir}...")
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    print("\nAgent curriculum training complete!")


def main():
    """Entry point for agent fine-tuning."""
    args = parse_args()

    # ── Curriculum mode ──
    if args.curriculum:
        # Import from finetune package when run as module, or directly when run as script
        try:
            from finetune.curriculum_config import CurriculumConfig
        except ImportError:
            from curriculum_config import CurriculumConfig

        if args.curriculum_config:
            config = CurriculumConfig.from_json(Path(args.curriculum_config))
        else:
            config = CurriculumConfig.default_agent_3phase(DATA_DIR)

        model, tokenizer = _load_model_and_lora(args)
        run_curriculum_training(model, tokenizer, args, config)
        return

    # ── Standard single-phase training ──

    # ── Validate data exists ──
    train_path = DATA_DIR / "agent_train.jsonl"
    val_path = DATA_DIR / "agent_val.jsonl"
    if not train_path.exists():
        print("ERROR: Agent training data not found. Run prepare_agent_dataset.py first.")
        print(f"  Expected: {train_path}")
        sys.exit(1)

    # ── Load raw data ──
    print("Loading datasets...")
    train_dataset = AgentConversationDataset(train_path)
    val_dataset = AgentConversationDataset(val_path) if val_path.exists() else None
    print(f"  Train: {len(train_dataset)} examples")
    print(f"  Val:   {len(val_dataset) if val_dataset else 0} examples")

    model, tokenizer = _load_model_and_lora(args)

    # ── Configure training ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from trl import SFTConfig, SFTTrainer
        from unsloth.trainer import is_bfloat16_supported
    except ImportError:
        print(
            "ERROR: Required packages not installed. Install with:\n"
            "  uv pip install unsloth bitsandbytes trl\n",
            file=sys.stderr,
        )
        sys.exit(1)

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

    # ── Create trainer (no vision data collator needed for text-only) ──
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )

    # ── Train ──
    print(f"\nStarting agent training:")
    print(f"  Model:    {AGENT_MODEL}")
    print(f"  LoRA:     r={args.lora_r}, alpha={args.lora_alpha}")
    print(f"  Epochs:   {args.epochs}")
    print(f"  Batch:    {args.batch_size} x {args.grad_accum} grad accum")
    print(f"  LR:       {args.lr}")
    print(f"  Seq len:  {args.max_seq_len}")
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
    final_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving final LoRA model to {final_dir}...")
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    # ── Evaluate on val set ──
    if val_dataset is not None and len(val_dataset) > 0:
        print("\nRunning validation...")
        metrics = trainer.evaluate()
        print(f"  Val loss: {metrics.get('eval_loss', 'N/A'):.4f}")

    print("\nAgent training complete!")
    print(f"  LoRA adapters saved to: {final_dir}")
    print(f"  Next step: python finetune/export_ollama.py")


if __name__ == "__main__":
    main()
