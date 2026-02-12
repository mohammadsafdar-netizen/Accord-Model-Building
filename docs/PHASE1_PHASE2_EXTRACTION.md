# Phase 1 vs Phase 2 Extraction

## Overview

- **Phase 1**: Best extraction using **OCR + prefill + text-only LLM**. No vision model. Produces `extracted.json` from form text and layout.
- **Phase 2**: Add a **VLM** on top of Phase 1 to fill or correct missing fields, or to run a full vision-assisted pipeline.

---

## Phase 1 (text-only)

**Goal:** Get a solid first-pass JSON from the form using only:
1. **OCR**: Docling (structure) + EasyOCR or Surya (bbox) → spatial index, label–value pairs
2. **Prefill**: Spatial rules + label–value matching → prefilled form JSON
3. **Text LLM**: Category-by-category extraction + gap-fill for remaining nulls → `extracted.json`

**Run Phase 1:**

```bash
# Default: first PDF in test_data, form 125, EasyOCR, qwen2.5:7b
python run_phase1_extraction.py

# Full options
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 \
  --model qwen2.5:7b --gpu --ocr-backend surya --out phase1_output/myrun
```

**Faster (fewer LLM calls, ~2–5 min instead of 15+ min):**

```bash
# Fast path: 2–8 fill-nulls LLM calls instead of category-by-category (lower accuracy)
python run_phase1_fast.py --pdf path/to/form.pdf --form 125 --model qwen2.5:7b --out phase1_fast_out

# Or use main script with --fast (only 4 LLM chunks for a quick run)
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --fast --max-llm-chunks 4 --out phase1_fast_out
```

**Outputs (in `--out` dir):**

- `extracted.json` – Phase 1 extracted fields
- `extraction_metadata.json` – counts, sources, model, time
- OCR artifacts: `prefilled_form.json`, `label_value_pairs.json`, `prefill_sources.json`, `prefill_details.json`, `bbox_pages.json`, `docling_pages.json`, etc.

**When to use:** You want a fast, text-only first pass; you will add a VLM later or only for selected forms.

---

## Phase 2 (add VLM on top)

**Goal:** Use a vision model to fill or correct fields that Phase 1 missed or got wrong.

**Option A – Full pipeline with vision (Phase 1 + VLM in one run):**

```bash
python main.py path/to/form.pdf --vision --vision-model llava:7b
# or
python test_pipeline.py --gpu --vision --vision-model qwen2.5-vl:7b --forms 125
```

**Option B – Run Phase 1 first, then add VLM in a separate step (future):**  
You can load Phase 1 `extracted.json`, run the VLM only on missing or low-confidence fields, and merge. The current codebase runs Phase 1 + VLM in a single `main.py`/`test_pipeline.py` run when `--vision` is set; a “Phase 2 only” mode that reads Phase 1 JSON and runs only the VLM can be added later.

---

## Fill strategies (Phase 1)

- **Category + gap-fill (default):** The extractor runs category-by-category text LLM passes, then a gap-fill pass. Best balance of accuracy and coverage.
- **One-shot fill-nulls (optional):** For smaller schemas or when prefill is strong, you can use `build_fill_nulls_prompt()` (in `prompts.py`) to ask the text LLM to fill only the keys that are still null after prefill, in one or a few chunked calls. Not wired by default; can be added as `--fill-strategy fill_nulls` if needed.

---

## Summary

| Phase | What runs | Output |
|-------|-----------|--------|
| **Phase 1** | OCR → prefill → text LLM (category + gap-fill) | `extracted.json` (no VLM) |
| **Phase 2** | Phase 1 + VLM (checkboxes and/or general vision pass) | Same `extracted.json` with more fields from vision |

Use **Phase 1** for the best text-only JSON; add **Phase 2** (e.g. `--vision`) when you want the VLM to improve coverage or correctness.
