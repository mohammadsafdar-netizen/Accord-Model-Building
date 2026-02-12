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

### 3. Other speed flags (no accuracy loss)

- `--docling-gpu` – Run Docling on GPU (faster OCR, needs 24GB+ VRAM).
- `--unload-wait 5` – Shorter wait after model unload (e.g. 5s on 24GB).
- Checkbox VLM batch size is 18 by default (fewer round-trips than 10).

## Future: more parallelism

- **Multiple Ollama instances:** Run two section-extraction agents in parallel (e.g. producer on port 11434, policy on 11435) and merge. The graph can be extended with parallel extract nodes.
- **Multi-GPU:** One GPU for VLM, one for text LLM; graph nodes could run on different backends.
