# ACORD VLM Fine-Tuning

Fine-tune Qwen2.5-VL-7B on ACORD form extraction using Unsloth QLoRA.

## Overview

- **Base model**: Qwen2.5-VL-7B (recommended for production accuracy)
- **Dataset**: 8,403 training / 80 validation examples from 510 forms across 4 form types (125, 127, 137, 163)
- **Output**: `acord-vlm-7b` — Q5_K_M quantized GGUF registered with Ollama

## Quick Start

```bash
# 1. Install dependencies
uv pip install unsloth bitsandbytes datasets

# 2. Prepare dataset from existing forms + ground truth
.venv/bin/python finetune/prepare_dataset.py

# 3. Train (7B model, ~4-6 hours on RTX 3090/4090)
.venv/bin/python finetune/train.py --model 7b

# 4. Export to GGUF + register with Ollama
.venv/bin/python finetune/export_ollama.py

# 5. Test in pipeline
.venv/bin/python test_pipeline.py --gpu --one-per-form \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --text-llm --smart-ensemble
```

## Ollama Environment

For best performance with multi-model pipelines, set these before starting Ollama:

```bash
OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve
```

## Training Options

```bash
# 3B model (lighter, ~2-3 hours, lower accuracy)
.venv/bin/python finetune/train.py --model 3b

# 7B model (recommended, ~4-6 hours)
.venv/bin/python finetune/train.py --model 7b

# Custom hyperparameters
.venv/bin/python finetune/train.py --model 7b --epochs 3 --lr 1e-4 --lora-r 32

# Resume from checkpoint
.venv/bin/python finetune/train.py --resume
```

### Overfitting Guidance

With the current dataset size (~8.4K training examples from 510 forms), stop training at **epoch 3**. Beyond that, validation loss typically plateaus or increases. Monitor `eval_loss` in the training logs and stop early if it starts rising.

## Data Layout

```
finetune/
  data/
    train.jsonl    # 8,403 training examples
    val.jsonl      # 80 validation examples (held-out forms)
    images/        # Rendered page images (auto-generated)
  output/
    checkpoint-*/  # Training checkpoints
    final/         # Merged LoRA adapters
  export/
    *.gguf         # Quantized model (Q5_K_M)
    Modelfile      # Ollama config
```

## Training Example Types

| Type | Description | Purpose |
|------|-------------|---------|
| `full_page` | All fields on a page | General extraction |
| `category_*` | Fields by category (header, driver, etc.) | Focused extraction |
| `checkbox` | Only checkbox fields (true/false) | Checkbox accuracy |

## Export & Registration

After training, export to GGUF and register with Ollama:

```bash
# Export merges LoRA adapters and quantizes to Q5_K_M
.venv/bin/python finetune/export_ollama.py

# The script automatically:
# 1. Merges LoRA weights into base model
# 2. Quantizes to Q5_K_M GGUF (~5 GB)
# 3. Creates Modelfile for Ollama
# 4. Registers as 'acord-vlm-7b' in Ollama
```

## Dataset Statistics

| Form Type | Forms | Training Examples |
|-----------|-------|-------------------|
| ACORD 125 | ~150 | ~2,500 |
| ACORD 127 | ~150 | ~2,500 |
| ACORD 137 | ~120 | ~1,900 |
| ACORD 163 | ~90 | ~1,500 |
| **Total** | **510** | **8,403 train / 80 val** |
