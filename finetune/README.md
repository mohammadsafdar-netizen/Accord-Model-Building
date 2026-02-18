# ACORD VLM Fine-Tuning

Fine-tune Qwen2.5-VL on ACORD form extraction using Unsloth QLoRA.

## Quick Start

```bash
# 1. Install dependencies
uv pip install unsloth bitsandbytes datasets

# 2. Prepare dataset from existing forms + ground truth
.venv/bin/python finetune/prepare_dataset.py

# 3. Train (3B proof-of-concept, ~1-3 hours on RTX 3090)
.venv/bin/python finetune/train.py

# 4. Export to GGUF + register with Ollama
.venv/bin/python finetune/export_ollama.py

# 5. Test in pipeline
.venv/bin/python test_pipeline.py --gpu --one-per-form \
    --vlm-extract --vlm-extract-model acord-vlm \
    --text-llm --smart-ensemble
```

## Ollama Environment

For best performance, set these before starting Ollama:

```bash
OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve
```

## Training Options

```bash
# 7B model (needs ~18 GB VRAM)
.venv/bin/python finetune/train.py --model 7b

# Custom hyperparameters
.venv/bin/python finetune/train.py --epochs 5 --lr 1e-4 --lora-r 32

# Resume from checkpoint
.venv/bin/python finetune/train.py --resume
```

## Data Layout

```
finetune/
  data/
    train.jsonl    # Training examples
    val.jsonl      # Validation examples (held-out forms)
    images/        # Rendered page images (auto-generated)
  output/
    checkpoint-*/  # Training checkpoints
    final/         # Merged LoRA adapters
  export/
    *.gguf         # Quantized model
    Modelfile      # Ollama config
```

## Training Example Types

| Type | Description | Purpose |
|------|-------------|---------|
| `full_page` | All fields on a page | General extraction |
| `category_*` | Fields by category (header, driver, etc.) | Focused extraction |
| `checkbox` | Only checkbox fields (true/false) | Checkbox accuracy |

## Scaling to 400 Forms

When the full dataset arrives:

1. Place forms in `test_data/` following existing structure
2. Re-run `prepare_dataset.py` (will auto-render images)
3. Switch to 7B model: `--model 7b`
4. Consider more epochs: `--epochs 5`
