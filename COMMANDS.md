# Pipeline Commands Reference

All commands use `main.py` as the single entry point. Run from the project root.

---

## Recommended Optimal Configuration

The highest-accuracy configuration with all major features enabled:

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --docling --preprocess --use-positional \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --checkbox-crops --text-llm --use-rag \
    --smart-ensemble --no-confidence-routing \
    --validate-fields --no-semantic-matching
```

For batch testing:

```bash
.venv/bin/python test_pipeline.py --gpu --one-per-form \
    --docling --preprocess --use-positional \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --checkbox-crops --text-llm --use-rag \
    --smart-ensemble --no-confidence-routing \
    --validate-fields --no-semantic-matching
```

---

## Common Configurations

### Minimal (OCR only, no LLM)

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --docling
```

### Text LLM only

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu --docling --text-llm
```

### VLM only (direct page-image extraction)

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --vlm-extract --vlm-extract-model acord-vlm-7b
```

### VLM + Text LLM + Ensemble

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --docling --vlm-extract --vlm-extract-model acord-vlm-7b \
    --text-llm --smart-ensemble
```

### With ground truth comparison

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --docling --preprocess --use-positional \
    --vlm-extract --vlm-extract-model acord-vlm-7b \
    --checkbox-crops --text-llm --use-rag \
    --smart-ensemble --no-confidence-routing \
    --validate-fields --no-semantic-matching \
    --ground-truth path/to/gt.json
```

### Two-stage VLM-OCR (Nanonets)

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --nanonets-ocr --text-llm --smart-ensemble
```

### Two-stage VLM-OCR (GLM)

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --glm-ocr --text-llm --smart-ensemble
```

### With image preprocessing

```bash
.venv/bin/python main.py path/to/form.pdf --form-type 125 --gpu \
    --docling --preprocess --text-llm
```

---

## Quick Reference: All CLI Flags

### Form Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `pdf_path` | (required) | Path to the scanned PDF |
| `--form-type` | auto-detect | ACORD form type: `125`, `127`, `137`, `163` |
| `--model` | `qwen2.5:7b` | Ollama text LLM model |
| `--ollama-url` | `localhost:11434` | Ollama API base URL |
| `--output-dir` | auto | Output directory for results |
| `--ground-truth` | none | Ground truth JSON for accuracy comparison |
| `--schemas-dir` | `./schemas` | Directory containing schema JSON files |

### OCR & Preprocessing

| Flag | Default | Description |
|------|---------|-------------|
| `--docling` | off | Run Docling OCR for structure/markdown |
| `--ocr-backend` | `surya` | Bbox OCR: `none`, `easyocr`, `surya`, `paddle` |
| `--dpi` | `300` | Image DPI for PDF conversion |
| `--preprocess` | off | Deskew + denoise + binarize + CLAHE before OCR |
| `--docling-html` | off | Export Docling as HTML instead of markdown |
| `--align-to-template` | off | SIFT feature matching to align to template |
| `--gpu` | off | Use GPU for OCR |

### VLM / Vision Extraction

| Flag | Default | Description |
|------|---------|-------------|
| `--vlm-extract` | off | Direct VLM extraction from page images |
| `--vlm-extract-model` | `qwen3-vl:8b` | Ollama VLM model for `--vlm-extract` |
| `--multimodal` | off | Send image + OCR text to VLM together |
| `--checkbox-crops` | off | Tight VLM crops for checkbox fields |
| `--vlm-crop-extract` | off | Cropped VLM extraction by field clusters |
| `--vision` | off | Legacy VLM pass on form images |
| `--vision-model` | `qwen2.5vl:7b` | Ollama vision model for `--vision` |
| `--vision-descriptions` | off | Crop+describe regions, then extract |
| `--vision-describer-model` | same as vision | Small VLM for region descriptions |
| `--vision-checkboxes-only` | off | VLM only for checkbox fields |

### Text LLM Extraction

| Flag | Default | Description |
|------|---------|-------------|
| `--text-llm` | off | Run text LLM for category/driver/vehicle/gap-fill |

### VLM-OCR Two-Stage

| Flag | Default | Description |
|------|---------|-------------|
| `--glm-ocr` | off | GLM-OCR (0.9B) VLM OCR -> text LLM |
| `--nanonets-ocr` | off | Nanonets-OCR (3B) with checkbox Unicode -> text LLM |
| `--glm-ocr-model` | `glm-ocr` | Ollama model for GLM-OCR |
| `--nanonets-ocr-model` | `yasserrmd/Nanonets-OCR-s` | Ollama model for Nanonets-OCR |
| `--stage2-model` | same as `--model` | Text LLM override for stage 2 |

### Field Matching

| Flag | Default | Description |
|------|---------|-------------|
| `--no-semantic-matching` | enabled | Disable MiniLM semantic label matching |
| `--use-positional` | off | Enable positional atlas matching |
| `--use-templates` | off | Enable template anchoring |
| `--table-transformer` | off | ML-based table detection (DETR) |

### Multi-Source Fusion & Validation

| Flag | Default | Description |
|------|---------|-------------|
| `--ensemble` | off | Enable multi-source confidence-weighted fusion |
| `--smart-ensemble` | off | Field-type-aware ensemble (implies `--ensemble`) |
| `--validate-fields` | off | Cross-field validation (state/ZIP, dates, VIN, phone, NAIC) |
| `--dual-llm-validate` | off | Second LLM pass to verify + correct values |

### Performance & Optimization

| Flag | Default | Description |
|------|---------|-------------|
| `--no-keep-models-loaded` | keep loaded | Unload models between passes |
| `--no-parallel-vlm` | parallel | Disable concurrent VLM calls |
| `--vlm-workers` | `3` | Max concurrent VLM API calls |
| `--no-structured-json` | structured | Disable Ollama `format:json` |
| `--no-batch-categories` | batched | Extract each category separately |
| `--no-confidence-routing` | routing on | Extract all fields in every pass |
| `--confidence-threshold` | `0.90` | Confidence threshold for routing |
| `--timeout` | `300` | LLM request timeout in seconds |

### Data Sources

| Flag | Default | Description |
|------|---------|-------------|
| `--use-acroform` | off | Use AcroForm PDF fields (debug/testing only) |
| `--use-rag` | off | Few-shot RAG from ground truth |
| `--rag-gt-dir` | `test_data/` | Directory of ground-truth JSONs for RAG |
| `--use-knowledge-base` | off | Inject insurance knowledge context |

---

## Ollama Environment

For optimal performance with multi-model pipelines:

```bash
OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve
```

## Additional Flags for Accuracy Testing

| Flag | Expected Impact | Risk |
|------|----------------|------|
| `--preprocess` | Better OCR from deskew+denoise | Minimal, may slow slightly |
| `--dual-llm-validate` | Second LLM corrects errors | Adds ~30-60s per form |
| `--no-confidence-routing` | All sources contribute to all fields | May re-introduce VLM errors |
| `--nanonets-ocr` | Better OCR with checkbox Unicode | Needs model loaded |
