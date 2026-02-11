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
| `main.py` | CLI entry point |
| `ocr_engine.py` | Dual OCR: Docling + EasyOCR + spatial analysis |
| `llm_engine.py` | LLM interface: text now, vision hook for later |
| `extractor.py` | Core pipeline: category-by-category extraction |
| `prompts.py` | Prompt builders: form-specific, category-specific |
| `schema_registry.py` | Schema loading: fields, tooltips, categories |
| `compare.py` | Accuracy comparison against ground truth |
| `utils.py` | JSON cleanup, logging helpers |
| `test_pipeline.py` | End-to-end test for all 3 forms |
| `schemas/125.json` | ACORD 125 field schema (548 fields) |
| `schemas/127.json` | ACORD 127 field schema (634 fields) |
| `schemas/137.json` | ACORD 137 field schema (102 fields) |

## Transferring This Project (Portable)

This project is **portable**: it uses no hardcoded absolute paths and works from any directory on any system.

**To move to another machine:**

1. Copy the entire `best_project` folder (e.g. zip, USB, or clone from git).
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

3. System dependency for pdf2image:
   ```bash
   sudo apt install poppler-utils   # Linux
   brew install poppler             # macOS
   ```

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
```

### Run Tests

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
