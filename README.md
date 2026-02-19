# ACORD Form Extraction Pipeline

High-accuracy extraction pipeline for scanned ACORD insurance forms using OCR + LLM fusion.

## Supported Forms

| Form | Name | Fields | Key Data |
|------|------|--------|----------|
| ACORD 125 | Commercial Insurance Application | 548 | Insurer, producer, named insured, policy, lines of business, premises |
| ACORD 127 | Business Auto Section | 634 | Header, 13 drivers (A-M), vehicles (A-E), coverages, checkboxes |
| ACORD 137 | Commercial Auto Section | 403 | Named insured, policy, insurer, vehicle schedule (A-F), coverage symbols |
| ACORD 163 | Contractors Supplement | 518 | Contractor info, operations, equipment, subcontractors |

## Architecture

```
Scanned PDF
    |
    v
+-----------------------------------+
|         OCR Engine                 |
|  (ocr_engine.py)                  |
|                                   |
|  PDF -> 300 DPI Images            |
|  Optional: deskew + denoise       |
|  Optional: SIFT template align    |
|  Docling  -> Markdown / HTML      |
|  EasyOCR/Surya -> BBox X,Y       |
|  Spatial indexing + label-value   |
+-----------------------------------+
    |
    v
+-----------------------------------+
|         Extraction Pipeline        |
|  (extractor.py)                   |
|                                   |
|  1. Spatial pre-extract           |
|  2. Positional atlas matching     |
|  3. Template anchoring            |
|  4. Label-value pairing           |
|  5. Semantic matching (MiniLM)    |
|  6. VLM direct extract            |
|  7. Multimodal extract            |
|  8. Checkbox crop extract         |
|  9. VLM vision pass               |
| 10. Text LLM (category-by-cat)   |
| 11. Gap-fill pass                 |
| 12. Ensemble fusion               |
| 13. Cross-field validation        |
| 14. Normalize + verify            |
+-----------------------------------+
    |
    v
  Structured JSON Output
```

### Key Design Decisions

- **Dual OCR Fusion**: Docling provides semantic structure (headings, tables, columns). EasyOCR/Surya provides spatial positions (X,Y bounding boxes). Combined, they resolve column alignment issues that plague driver tables.
- **Category-by-Category**: Extracts fields in focused batches (header, insurer, producer, etc.) to reduce LLM confusion. Each batch gets a targeted prompt with disambiguation rules.
- **Multi-Source Ensemble**: Spatial, positional, template, VLM, and text LLM sources are fused with confidence-weighted ensemble. Smart ensemble applies field-type-aware weights (checkbox vs text vs numeric vs date).
- **Finetuned VLM**: A Qwen2.5-VL-7B model finetuned on 510 ACORD forms (`acord-vlm-7b`) provides direct page-image extraction with high accuracy.
- **Schema-Guided**: Field names, tooltips, and positions from ACORD PDF schemas drive extraction. The LLM knows exactly what each field should contain.

## Latest Accuracy Results

Using the recommended optimal configuration with finetuned VLM:

| Form | Accuracy | Coverage |
|------|----------|----------|
| ACORD 125 | 75.54% | 96.77% |
| ACORD 127 | 79.41% | 97.12% |
| ACORD 137 | 77.88% | 94.10% |
| ACORD 163 | 84.82% | 100.0% |
| **Average** | **79.41%** | **97.00%** |

## Quick Start

### Prerequisites

1. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```

2. Ensure Ollama is running with optimal settings:
   ```bash
   OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve
   ```

3. Pull required models:
   ```bash
   ollama pull qwen2.5:7b          # Text LLM
   # If using finetuned VLM (recommended):
   # See finetune/README.md to train and register acord-vlm-7b
   ```

4. System dependency for PDF-to-image conversion:
   ```bash
   sudo apt install poppler-utils   # Linux (Debian/Ubuntu)
   brew install poppler             # macOS
   ```

### Recommended Configuration (Optimal Accuracy)

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --docling --preprocess --use-positional \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --checkbox-crops --text-llm --use-rag \
    --smart-ensemble --no-confidence-routing \
    --validate-fields --no-semantic-matching
```

This configuration enables all major accuracy features: image preprocessing, positional atlas, finetuned VLM, checkbox crops, text LLM, RAG few-shot examples, smart ensemble fusion, full-field extraction (no confidence routing), and cross-field validation.

### Basic Usage

```bash
# Simple extraction (auto-detect form type)
.venv/bin/python main.py path/to/form.pdf

# Specify form type and model
.venv/bin/python main.py path/to/form127.pdf --form-type 127 --model qwen2.5:7b

# With accuracy comparison
.venv/bin/python main.py path/to/form127.pdf --ground-truth path/to/gt.json

# Use GPU for faster OCR
.venv/bin/python main.py path/to/form.pdf --gpu
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

### Ollama Environment

For multi-model pipelines (VLM + text LLM), set these before starting Ollama:

```bash
OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve
```

This allows keeping up to 3 models loaded simultaneously and running 4 parallel requests, which significantly speeds up ensemble pipelines.

### Run Tests

**Unit tests (no GPU):**

```bash
uv pip install -r requirements-dev.txt
pytest tests/ -v
```

**E2E / full pipeline (GPU + test_data):**

```bash
pytest tests/ -m e2e -v
# or full pipeline test:
.venv/bin/python test_pipeline.py --gpu --one-per-form \
    --docling --preprocess --use-positional \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --checkbox-crops --text-llm --use-rag \
    --smart-ensemble --no-confidence-routing \
    --validate-fields --no-semantic-matching
```

## Files

| File | Purpose |
|------|---------|
| `config.py` | Central paths and env (Eureka-friendly; see `docs/EUREKA.md`) |
| `main.py` | CLI entry point |
| `ocr_engine.py` | Dual OCR: Docling + EasyOCR/Surya/Paddle + spatial analysis |
| `llm_engine.py` | LLM interface: text, vision, VLM with Ollama |
| `extractor.py` | Core pipeline orchestrator: multi-pass extraction |
| `prompts.py` | Prompt builders: form-specific, category-specific |
| `schema_registry.py` | Schema loading: fields, tooltips, categories, positions |
| `compare.py` | Accuracy comparison against ground truth |
| `ensemble.py` | Multi-source confidence-weighted fusion (smart ensemble) |
| `positional_matcher.py` | Geometric OCR-to-field matching from positional atlas |
| `semantic_matcher.py` | MiniLM embedding-based label-to-field matching |
| `image_preprocessor.py` | Deskew + denoise + binarize + CLAHE preprocessing |
| `image_aligner.py` | SIFT feature matching + homography warp to template |
| `field_validator.py` | Cross-field validation (state/ZIP, dates, VIN, phone, NAIC) |
| `vlm_ocr_engine.py` | VLM-OCR two-stage: GLM-OCR / Nanonets-OCR + text LLM |
| `table_detector.py` | ML-based table detection using DETR models |
| `template_registry.py` | Template anchoring: standardized field regions with DPI scaling |
| `spatial_extract.py` | Spatial pre-extraction: label + position rules (no LLM) |
| `rag_examples.py` | RAG store: few-shot examples from ground truth |
| `utils.py` | JSON cleanup, logging helpers |
| `test_pipeline.py` | End-to-end test for all form types |
| `tests/` | Unit tests (`tests/unit/`) and E2E (`tests/integration/`) |
| `scripts/run_eureka.sh` | One-command run for Eureka machine |
| `schemas/125.json` | ACORD 125 field schema (548 fields) |
| `schemas/127.json` | ACORD 127 field schema (634 fields) |
| `schemas/137.json` | ACORD 137 field schema (403 fields) |
| `schemas/163.json` | ACORD 163 field schema (518 fields) |
| `finetune/` | VLM fine-tuning pipeline (Qwen2.5-VL-7B) |

## Recommended Setups by VRAM

The pipeline uses GPU for **one stage at a time** (OCR -> VLM -> text LLM), with unloads between stages unless `--no-keep-models-loaded` is off (default: models stay loaded for speed).

| VRAM | Text LLM (`--model`) | VLM (`--vlm-extract-model`) | Notes |
|------|----------------------|---------------------------|--------|
| **24 GB** | `qwen2.5:14b` | `acord-vlm-7b` + `qwen3-vl:30b` | Best: finetuned VLM + large text model. With `OLLAMA_MAX_LOADED_MODELS=3`, both fit. |
| **16-20 GB** | `qwen2.5:7b` | `acord-vlm-7b` | Finetuned VLM (~5 GB Q5_K_M) + 7B text fits comfortably. |
| **12 GB** | `qwen2.5:7b` | `acord-vlm-7b` | Both fit with keep-models-loaded. |
| **8 GB** | `qwen2.5:7b` | Skip VLM or `acord-vlm-7b` (tight) | Use `--no-keep-models-loaded` to swap between models. |

**Example (24 GB, optimal):**
```bash
OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve
.venv/bin/python main.py form.pdf --form-type 125 --gpu \
    --docling --preprocess --use-positional \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --checkbox-crops --text-llm --use-rag \
    --smart-ensemble --no-confidence-routing \
    --validate-fields --no-semantic-matching
```

## RAG (Few-Shot) Feature

When enabled with **`--use-rag`**, the pipeline injects few-shot (field -> value) examples from ground-truth JSONs into every extraction prompt. Examples are loaded from a directory of ground-truth JSONs (by default `test_data/` or `BEST_PROJECT_RAG_GT`). See `docs/RAG_DESIGN.md` for design details.

```bash
.venv/bin/python main.py path/to/form.pdf --docling --text-llm --use-rag
```

## Improving Accuracy

- **Finetuned VLM**: The `acord-vlm-7b` model (Qwen2.5-VL-7B finetuned on 510 ACORD forms) significantly improves extraction accuracy. See `finetune/README.md`.
- **Smart Ensemble**: `--smart-ensemble` applies field-type-aware confidence weights, prioritizing reliable sources per field type.
- **Cross-field Validation**: `--validate-fields` catches inconsistencies (state/ZIP mismatches, date ordering, VIN checksums).
- **Checkbox Crops**: `--checkbox-crops` uses tight VLM crops with CLAHE enhancement for checkbox detection.
- **Multimodal**: `--multimodal` sends both image and OCR text to VLM for higher-confidence extraction.
- **Schema Enrichment**: Run `python scripts/enrich_schemas.py` to add tooltips and format hints.
- **Preprocessing**: `--preprocess` applies deskew + denoise for better OCR on poor scans.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `PDFInfoNotInstalledError` | Install poppler: `sudo apt install poppler-utils` (Linux) or `brew install poppler` (macOS) |
| Ollama `404` errors | Ensure Ollama is running: `ollama serve`. Check: `curl -s http://localhost:11434/api/tags` |
| OOM during VLM | Use `--no-keep-models-loaded` to unload between passes, or use smaller models |
| Slow pipeline | Set `OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4` and restart Ollama |
