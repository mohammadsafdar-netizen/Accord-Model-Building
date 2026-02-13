# Best Project: OCR Fusion + Text LLM Pipeline

High-accuracy extraction pipeline for scanned ACORD forms **125**, **127**, and **137**.

## Architecture

```
Scanned PDF
    |
    v
+---------------------------+
|      OCR Engine           |
|  (ocr_engine.py)          |
|                           |
|  PDF -> 300 DPI Images    |
|  Table line removal       |
|  Docling  -> Markdown     |
|  EasyOCR  -> BBox X,Y     |
|  Spatial indexing          |
+---------------------------+
    |
    v
+---------------------------+
|      Extractor            |
|  (extractor.py)           |
|                           |
|  Form type detection      |
|  Schema + tooltips load   |
|  Category-by-category:    |
|    header -> insurer ->   |
|    producer -> insured -> |
|    policy -> drivers ->   |
|    vehicles -> coverage   |
|  Two-pass per category:   |
|    1. Docling-guided      |
|    2. BBox gap-fill       |
|  Verification + normalise |
+---------------------------+
    |
    v
  Structured JSON Output
```

### Key Design Decisions

- **Dual OCR Fusion**: Docling provides semantic structure (headings, tables, columns). EasyOCR provides spatial positions (X,Y bounding boxes). Combined, they resolve column alignment issues that plague driver tables.
- **Category-by-Category**: Extracts fields in focused batches (header, insurer, producer, etc.) to reduce LLM confusion. Each batch gets a targeted prompt with disambiguation rules.
- **Two-Pass Strategy**: First pass uses structured Docling text + tooltips. Second pass targets missed fields using BBox positional text.
- **Schema-Guided**: Field names and tooltips from ACORD PDF schemas drive extraction. The LLM knows exactly what each field should contain.
- **Future-Proof for Vision**: The `LLMEngine.generate_with_image()` stub allows plugging in a vision LLM later. Only 2 files need changes (llm_engine.py, extractor.py).

## Files

| File | Purpose |
|------|---------|
| `config.py` | Central paths and env (Eureka-friendly; see `docs/EUREKA.md`) |
| `main.py` | CLI entry point |
| `ocr_engine.py` | Dual OCR: Docling + EasyOCR + Surya/Paddle + spatial analysis |
| `llm_engine.py` | LLM interface: text now, vision hook for later |
| `extractor.py` | Core pipeline: category-by-category extraction |
| `prompts.py` | Prompt builders: form-specific, category-specific |
| `schema_registry.py` | Schema loading: fields, tooltips, categories |
| `compare.py` | Accuracy comparison against ground truth |
| `rag_examples.py` | RAG store: few-shot examples from ground truth (used when `--use-rag`) |
| `utils.py` | JSON cleanup, logging helpers |
| `test_pipeline.py` | End-to-end test for all 3 forms |
| `tests/` | Unit tests (`tests/unit/`) and E2E (`tests/integration/`, `-m e2e`); run with `pytest tests/` |
| `scripts/run_eureka.sh` | One-command run: tests, e2e, pipeline, or extract (see `docs/EUREKA.md`) |
| `schemas/125.json` | ACORD 125 field schema (548 fields) |
| `schemas/127.json` | ACORD 127 field schema (634 fields) |
| `schemas/137.json` | ACORD 137 field schema (102 fields) |
| `scripts/enrich_schemas.py` | Add tooltips (137) and format hints (125/127) to improve extraction |

Schemas define field names, types (text/checkbox/radio), tooltips (shown to the LLM), and categories. Better tooltips and consistent format hints (e.g. "Return 1 or Off" for checkboxes, "MM/DD/YYYY" for dates) improve accuracy and coverage. Run `python scripts/enrich_schemas.py` to (re)apply enrichment.

## Transferring This Project (Portable)

This project is **portable**: it uses no hardcoded absolute paths and works from any directory on any system.

**Clone or pull from GitHub (other machine):**

```bash
# First time: clone the repo
git clone https://github.com/mohammadsafdar-netizen/Accord-Model-Building.git best_project
cd best_project

# If you already have the repo: pull latest
cd best_project   # or wherever you cloned it
git pull origin main
```

Then install deps and run (see **Quick Start** and **Basic Usage** below).

**To move without git (e.g. zip / USB):**

1. Copy the entire `best_project` folder.
2. On the new system, from inside `best_project`:
   ```bash
   pip install -r requirements.txt
   ```
3. **LangGraph app (optional):** If you use `langgraph_impl/`, create your env file:
   ```bash
   cp langgraph_impl/.env.example langgraph_impl/.env
   # Edit langgraph_impl/.env and set GROQ_API_KEY=your_key
   ```
4. Run from the project root as in **Basic Usage** and **Run Tests** below.

**To reduce transfer size**, you can omit (they can be regenerated):
- `test_output/` — recreated by `python test_pipeline.py`
- `langgraph_impl/logs/` — recreated when running the app
- `langgraph_impl/filled_forms/` — recreated when filling forms

Never commit or share `langgraph_impl/.env`; it may contain API keys. Use `.env.example` as a template.

## Quick Start

### Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure Ollama is running with a text model:
   ```bash
   ollama pull qwen2.5:7b
   ollama serve
   ```

3. **Required:** System dependency for PDF→image conversion (pdf2image uses poppler):
   ```bash
   sudo apt install poppler-utils   # Linux (Debian/Ubuntu)
   brew install poppler             # macOS
   ```
   If you see `PDFInfoNotInstalledError` or `No such file or directory: 'pdfinfo'`, install poppler-utils and ensure it’s in your PATH.

### Basic Usage

```bash
# Extract from a scanned PDF (auto-detect form type)
python main.py path/to/form.pdf

# Specify form type and model
python main.py path/to/form127.pdf --form-type 127 --model qwen2.5:7b

# With accuracy comparison
python main.py path/to/form127.pdf --ground-truth path/to/gt.json

# Use GPU for faster OCR
python main.py path/to/form.pdf --gpu

# Add a vision pass (VLM on form images for missing fields)
# Requires an Ollama vision model, e.g. llava:7b
ollama pull llava:7b
python main.py path/to/form.pdf --vision
python main.py path/to/form.pdf --vision --vision-model llava:13b

# Enable RAG (few-shot examples from ground truth for better accuracy)
python main.py path/to/form.pdf --use-rag
python main.py path/to/form.pdf --docling --text-llm --use-rag --rag-gt-dir ./test_data
```

### Configuration (Eureka / other machines)

Paths and defaults can be set via **environment variables** so the same code runs without changes:

- `BEST_PROJECT_ROOT` — Project root (default: auto)
- `BEST_PROJECT_TEST_DATA` — Test data dir (default: `<root>/test_data`)
- `BEST_PROJECT_OUTPUT` — Output dir (default: `<root>/test_output`)
- `BEST_PROJECT_SCHEMAS` — Schema JSON dir (default: `<root>/schemas`)
- `BEST_PROJECT_RAG_GT` — Ground-truth dir for RAG when `--use-rag` (default: same as TEST_DATA)
- `OLLAMA_URL` — Ollama API URL
- `USE_GPU=1` — Use GPU for OCR by default

See **`docs/EUREKA.md`** for full setup and **`scripts/run_eureka.sh`** for one-command test/run.

### Run Tests

**Unit tests (no GPU):**

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
# or: ./scripts/run_eureka.sh tests
```

**E2E / full pipeline (GPU + test_data):**

```bash
pytest tests/ -m e2e -v
# or: python test_pipeline.py --gpu
# or: ./scripts/run_eureka.sh pipeline
```

**Legacy single script:**

```bash
# Test all 3 forms
python test_pipeline.py

# Test specific forms
python test_pipeline.py --forms 127 137

# With a different model
python test_pipeline.py --model llama3.2:3b
```

## Supported Forms

| Form | Name | Fields | Key Data |
|------|------|--------|----------|
| ACORD 125 | Commercial Insurance Application | 548 | Insurer, producer, named insured, policy, lines of business, premises |
| ACORD 127 | Business Auto Section | 634 | Header, 13 drivers (A-M), vehicles (A-E), coverages, checkboxes |
| ACORD 137 | Commercial Auto Section | 102 | Named insured, policy, insurer, vehicle schedule (A-F), coverage symbols |

## Vision pass (VLM)

A **vision pass** runs after the text-based extraction and gap-fill. It uses an Ollama vision model (e.g. **llava:7b**) on the form page images to fill remaining missing fields.

- **CLI:** `--vision` and `--vision-model llava:7b` (default). Pull a vision model first: `ollama pull llava:7b`.
- **Flow:** OCR → category extraction → gap-fill → **vision pass** (VLM on first 1–2 pages, batched missing fields) → verification.
- You can switch to a larger model later (e.g. `--vision-model llava:13b` or another Ollama vision model) without code changes.
- **Describe-then-extract (optional):** `--vision-descriptions` crops each page into regions, uses a **small** VLM to describe each region, then sends the **crop images + descriptions** to the main VLM. Cropping is **dynamic layout-based** when OCR is available: EasyOCR spatial index (row clusters by vertical gap) or raw bbox clustering; otherwise falls back to a 2×2 grid. Use `--vision-describer-model llava:7b` for the describer. Example: `python main.py form.pdf --vision --vision-model qwen3-vl:30b --vision-descriptions --vision-describer-model llava:7b`

## Recommended setups by VRAM

The pipeline uses the GPU for **one stage at a time** (OCR → text LLM → vision LLM), with unloads between stages. So your VRAM must fit the **largest single model**, not all at once.

| VRAM | Text LLM (`--model`) | Vision (`--vision-model`) | Notes |
|------|----------------------|---------------------------|--------|
| **24 GB** | `qwen2.5:14b` (~9 GB) | `qwen3-vl:30b` (~20–24 GB) | Best quality: 14b text + 30B vision both fit. Optional text: `qwen2.5:32b` (~18 GB) if you skip vision or use a smaller VLM. |
| **20 GB** | `qwen2.5:14b` (~9 GB) | `llava:13b` or `qwen2-vl:7b` (~5–9 GB) | Best balance. For vision you can try `qwen3-vl:30b` (may need quantized tag, can OOM); if OOM use `llava:13b`. |
| **20 GB** (safer) | `qwen2.5:7b` (~5 GB) | `qwen3-vl:30b` or `llava:13b` | Use 7b text if you want to run 30B vision on 20 GB (tight; close other GPU apps). |
| **12 GB** | `qwen2.5:7b` | `llava:7b` or `qwen2-vl:7b` | Avoid 30B vision. |
| **8 GB** | `qwen2.5:7b` | `llava:7b` | Or run without `--vision`. |
| **6 GB** | `qwen2.5:7b` | No vision (or `llava:7b` if Ollama not loaded) | Use **CPU OCR**: `--ocr-backend easyocr` and do **not** pass `--gpu`, so only Ollama uses the GPU. Surya/Paddle will OOM. |

**Example for 24 GB (recommended):**
```bash
ollama pull qwen2.5:14b
ollama pull qwen3-vl:30b
python test_pipeline.py --forms 125 127 137 --gpu --one-per-form --vision --model qwen2.5:14b --vision-model "qwen3-vl:30b"
```

**Example for 20 GB (recommended):**
```bash
ollama pull qwen2.5:14b
ollama pull llava:13b
python test_pipeline.py --forms 125 127 137 --gpu --one-per-form --vision --model qwen2.5:14b --vision-model llava:13b
```

**Example for 20 GB (max vision, risk of OOM):**
```bash
python test_pipeline.py ... --model qwen2.5:7b --vision --vision-model "qwen3-vl:30b"
```

**Example for 6 GB (CPU OCR, GPU only for Ollama):**
```bash
# main.py: EasyOCR on CPU, Ollama 7b on GPU. Omit --gpu so Surya/Paddle are not used.
python main.py path/to/form125.pdf --form-type 125 --text-llm --ocr-backend easyocr

# test_pipeline: same idea; first run can be slow (CPU OCR). Use --one-per-form to limit PDFs.
python test_pipeline.py --forms 125 --one-per-form --ocr-backend easyocr
```
If you have cached OCR from a previous run, re-running with the same output dir skips heavy OCR and only runs the LLM. The pipeline sets `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True` by default so Paddle (if installed) does not block startup.

## RAG (few-shot) feature

When enabled with **`--use-rag`**, the pipeline injects few-shot (field → value) examples from ground-truth JSONs into every extraction step that uses the text LLM:

- **Category extraction** (header, insurer, producer, named_insured, policy, etc.)
- **Driver rows** (Form 127)
- **Vehicle rows** (Forms 127 / 137)
- **Gap-fill** (second pass for missed fields)

Examples are loaded from a directory of ground-truth JSONs (by default `test_data/` or `BEST_PROJECT_RAG_GT`). The store is built once at startup; retrieval is in-memory and adds only a small number of lines per prompt. This improves accuracy (format and convention alignment) with minimal speed impact.

**Activate:**

```bash
# Single PDF
python main.py path/to/form.pdf --docling --text-llm --use-rag

# Full test pipeline
python test_pipeline.py --gpu --use-rag
```

**Custom RAG ground-truth path:** `--rag-gt-dir <path>` (main.py) or set `BEST_PROJECT_RAG_GT`. Directory layout: form subfolders (e.g. `ACORD_0125_*/`, `127/`, `137/`) containing `*.json` files with flat field → value. See `docs/RAG_DESIGN.md` for design details.

## Improving accuracy

- **Checkbox/indicator fields:** Comparison normalises values (1/On/True/Yes/Y → true, 0/Off/False/No/N → false). If your ground truth uses different conventions, ensure schemas and prompts ask for a format that normalises correctly (e.g. "Return 1 if checked, Off if not").
- **Schema vs ground truth:** Accuracy is computed only over fields that exist in both the schema and the ground truth JSON. If GT has many more keys (e.g. flattened or different naming), align schema field names with GT or normalise GT keys before comparison.
- **Vision (VLM) batches:** If the VLM often returns empty content (e.g. with qwen3-vl:30b on large batches), the pipeline falls back to streaming. You can reduce the vision batch size in `extractor.py` (`VISION_BATCH`) to ease load on the VLM and improve reliability.
- **Larger models:** Using a larger text model (e.g. `qwen2.5:14b`) and/or vision model (e.g. `qwen3-vl:30b`) usually improves extraction quality at the cost of speed and VRAM.
- **Schema enrichment:** Run `python scripts/enrich_schemas.py` so tooltips and format hints (dates, checkboxes, amounts) are present; the LLM uses these for extraction.
- **Describe-then-extract:** Using `--vision-descriptions` with Docling + EasyOCR regions often improves vision coverage; ensure Docling and EasyOCR complete successfully so region crops are meaningful.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `PDFInfoNotInstalledError` or `No such file or directory: 'pdfinfo'` | Install poppler: `sudo apt install poppler-utils` (Linux) or `brew install poppler` (macOS). Restart the terminal if needed so `pdfinfo` is in PATH. |
| `404` for `localhost:11434/api/generate` (or `/api/chat`, `/v1/chat/completions`) | The process on port 11434 is not exposing Ollama’s API. **Fix on that machine:** (1) Stop any service using 11434. (2) Start Ollama’s server: `ollama serve` (leave it running in a terminal, or use the official systemd service). (3) Check: `curl -s http://localhost:11434/api/tags` should return JSON with a `models` list. (4) If using Snap or a custom install, reinstall from [ollama.com](https://ollama.com/download/linux) so the HTTP API is available. |
