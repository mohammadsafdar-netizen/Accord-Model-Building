# LangGraph Extraction Pipeline & Speed Options

## Reducing run time

### 1. Parallel OCR (default on)

When **Docling runs on CPU** and **EasyOCR on GPU**, both run **in parallel**. Wall time for OCR is roughly **max(Docling, EasyOCR)** instead of Docling + EasyOCR.

- **Default:** `parallel_ocr=True` (parallel when Docling=CPU, EasyOCR=GPU).
- Disable with: `--no-parallel-ocr` (sequential OCR).

### 2. LangGraph pipeline (`--use-graph`)

The extraction pipeline can run as a **LangGraph** with two nodes:

1. **ocr_node** – Unloads LLM, runs `ocr.process()` (which uses parallel Docling+EasyOCR when enabled).
2. **extract_node** – Runs spatial pre-extract, vision, text LLM, gap-fill using the OCR result.

Same accuracy as the non-graph path; the graph gives a clear split (OCR vs extraction) and a place to add more parallelism later (e.g. multiple workers).

**Requires:** `pip install langgraph`

**Usage:**

```bash
python test_pipeline.py --gpu --one-per-form --use-graph
```

### 3. VLM time (main bottleneck)

The **vision language model (VLM)** is usually the slowest part: many sequential API calls (checkbox batches + general pass).

- **`--vision-checkboxes-only`** – **Biggest VLM time saver.** Run only the checkbox vision pass; skip the general vision pass. Text LLM fills the rest. Cuts VLM time roughly in half (or more on large forms).
- **`--vision-batch-size N`** – Fields per VLM call in the **general** vision pass (default: **12**). Higher = fewer calls (e.g. `--vision-batch-size 15` with default `--vision-max-tokens 16384`).
- **`--vision-max-tokens N`** – Max tokens per VLM response (default: **16384**). Reduces "Batch response empty" truncation and allows larger batch sizes. Use 8192 only if your VLM has strict limits.

Checkbox pass uses batch size 18 (or 20 with `--vision-fast`); general pass uses 12 by default. Increasing general batch to 15 can save ~20% of general-pass VLM calls.

### 4. Other speed flags (no accuracy loss)

- `--docling-gpu` – Run Docling on GPU (faster OCR, needs 24GB+ VRAM).
- `--unload-wait 5` – Shorter wait after model unload (e.g. 5s on 24GB).

## Future: more parallelism

- **Multiple Ollama instances:** Run two section-extraction agents in parallel (e.g. producer on port 11434, policy on 11435) and merge. The graph can be extended with parallel extract nodes.
- **Multi-GPU:** One GPU for VLM, one for text LLM; graph nodes could run on different backends.
