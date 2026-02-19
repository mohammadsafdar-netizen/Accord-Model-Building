# Running Faster on a 24GB VRAM GPU

On a 24GB GPU you can run more on device and reduce load/unload, so **the pipeline runs faster** than on 6-8GB.

---

## What runs faster

| Step | 6-8GB typical | 24GB |
|------|----------------|------|
| **Docling** | CPU (to free VRAM for EasyOCR + LLM) | **GPU** -> faster OCR |
| **EasyOCR / Surya** | GPU, then unload | GPU, less pressure to unload |
| **Unload wait** | 5-8 s between stages | Can use 2-4 s |
| **Text LLM (Ollama)** | GPU | GPU, same |
| **VLM** | Often 7B or skip | 7B finetuned + optional 30B |
| **Keep models loaded** | Swap frequently | Keep 2-3 models loaded |

So: **OCR is faster** (Docling on GPU, optional larger Surya batches), **less waiting** between stages, and you can keep models loaded longer.

---

## Recommended configuration for 24GB

**Optimal accuracy (all features):**

```bash
OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve

.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --docling --use-positional --use-templates \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --text-llm --smart-ensemble \
    --validate-fields --checkbox-crops --multimodal
```

**Batch testing:**

```bash
.venv/bin/python test_pipeline.py --gpu --one-per-form \
    --docling --use-positional --use-templates \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --text-llm --smart-ensemble \
    --validate-fields --checkbox-crops --multimodal
```

**Text LLM only (faster, lower accuracy):**

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu --docling --text-llm
```

---

## Environment / tuning

- **Ollama multi-model:**
  ```bash
  OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve
  ```
  This allows keeping VLM + text LLM + OCR model loaded simultaneously. With `--no-keep-models-loaded` disabled (default), models stay loaded between passes, saving ~40% time from avoided load/unload cycles.

- **Surya** (when using `--ocr-backend surya`):
  - `RECOGNITION_BATCH_SIZE=256` or `512` (default can be 512; reduce if OOM).
  - Larger batch = fewer steps = faster recognition.

- **Parallel VLM:**
  - Default: `--vlm-workers 3` with ThreadPoolExecutor for concurrent VLM calls.
  - Set `--vlm-workers` <= `OLLAMA_NUM_PARALLEL`.

- **Confidence routing:**
  - Default: enabled. Fields already extracted with high confidence (>= 0.90) are skipped in subsequent VLM/LLM passes.
  - Disable with `--no-confidence-routing` if you want all sources to contribute to all fields.

---

## Model recommendations for 24GB

| Model | Size | Purpose |
|-------|------|---------|
| `acord-vlm-7b` | ~5 GB (Q5_K_M) | Finetuned VLM for form extraction (recommended) |
| `qwen2.5:7b` | ~5 GB | Text LLM for category extraction |
| `qwen2.5:14b` | ~9 GB | Higher-quality text LLM (if VRAM allows) |
| `qwen3-vl:8b` | ~5 GB | General VLM (if finetuned model unavailable) |

With `OLLAMA_MAX_LOADED_MODELS=3`, you can keep `acord-vlm-7b` + `qwen2.5:7b` + one more model loaded simultaneously on 24GB.

---

## Summary

- **Yes, it will run faster on a 24GB VRAM GPU:** mainly from keeping models loaded, parallel VLM, Docling on GPU, and less unload wait.
- Use `--gpu` and set `OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4` for best performance.
- The finetuned `acord-vlm-7b` (~5 GB) fits comfortably alongside a 7B text model on 24GB.
