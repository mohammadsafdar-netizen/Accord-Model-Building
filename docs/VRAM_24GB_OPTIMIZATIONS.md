# Running Faster on a 24GB VRAM GPU

On a 24GB GPU you can run more on device and reduce load/unload, so **the pipeline runs faster** than on 6–8GB.

---

## What runs faster

| Step | 6–8GB typical | 24GB |
|------|----------------|------|
| **Docling** | CPU (to free VRAM for EasyOCR + LLM) | **GPU** → faster OCR |
| **EasyOCR / Surya** | GPU, then unload | GPU, less pressure to unload |
| **Unload wait** | 5–8 s between stages | Can use 2–4 s |
| **Text LLM (Ollama)** | GPU | GPU, same |
| **VLM** | Often 7B or skip | 7B or 30B if you want |

So: **OCR is faster** (Docling on GPU, optional larger Surya batches), **less waiting** between stages, and you can keep models loaded longer.

---

## Recommended flags for 24GB

**Phase 1 (text-only) – fastest:**

```bash
# Docling on GPU, Surya for bbox, 7B text model
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --gpu \
  --ocr-backend surya

# With test_pipeline (batch): Docling on GPU
python test_pipeline.py --gpu --docling-gpu --forms 125 --model qwen2.5:7b
```

**Phase 1 fast path (few LLM calls):**

```bash
python run_phase1_fast.py --pdf path/to/form.pdf --form 125 --gpu \
  --ocr-backend surya --out phase1_fast_out
```

**Full pipeline with vision (24GB):**

```bash
# Docling on GPU; VLM 7B fits with text 7B unloaded between stages
python test_pipeline.py --gpu --docling-gpu --vision --vision-model llava:7b \
  --vision-checkboxes-only --forms 125
```

---

## Environment / tuning (optional)

- **Surya** (when using `--ocr-backend surya`):  
  - `RECOGNITION_BATCH_SIZE=256` or `512` (default can be 512; reduce if OOM).  
  - Larger batch = fewer steps = faster recognition.

- **Unload wait:**  
  - In code or via `--unload-wait 3` (test_pipeline) you can lower the wait after unloading OCR so the next model loads sooner (e.g. 3–4 s on 24GB).

- **Docling on GPU:**  
  - `--docling-gpu` in test_pipeline / main: Docling uses GPU instead of CPU → faster, uses more VRAM.

---

## Summary

- **Yes, it will run faster on a 24GB VRAM GPU:** mainly from Docling on GPU, less unload wait, and (if you use Surya) larger recognition batches.
- Use **`--gpu`** and **`--docling-gpu`** (where supported) for 24GB.
- Phase 1 fast path (**run_phase1_fast.py**) with **chunk-by-category** (default) improves accuracy vs fixed-size chunks and still uses few LLM calls.
