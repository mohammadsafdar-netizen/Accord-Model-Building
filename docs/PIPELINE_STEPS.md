# Step-by-Step: What Happens When You Run the Pipeline

This describes the full flow when you run:

```bash
python test_pipeline.py --gpu --one-per-form --model qwen2.5:7b --vision --vision-model qwen3-vl:30b --vram-reserve 2
```

---

## Part 1: Test pipeline setup

1. **Parse arguments**  
   CLI parses `--gpu`, `--forms`, `--one-per-form`, `--model`, `--vision`, `--vision-model`, `--vram-reserve`, etc.

2. **Discover test data**  
   Scans `test_data/` for folders named like `*125*`, `*127*`, `*137*`. In each folder, finds every `*.pdf` and its matching `*.json` (ground truth).  
   If `--one-per-form`: keeps only the **first PDF per form type** (so 3 PDFs total: one 125, one 127, one 137).

3. **Load schemas**  
   Loads `schemas/125.json`, `schemas/127.json`, `schemas/137.json` (field names, categories, tooltips).

4. **Create shared engines**  
   - **OCREngine**: Docling + EasyOCR, DPI 300, GPU/CPU as requested; with `--gpu`, Docling runs on CPU and EasyOCR on GPU so VRAM is left for the LLM.  
   - **LLMEngine**: text model (e.g. `qwen2.5:7b`), and if `--vision`, vision model (e.g. `qwen3-vl:30b`).  
   - **SchemaRegistry**: holds the three form schemas.

5. **For each form type (125, 127, 137)**  
   For each PDF in that form’s list, the pipeline runs **one full extraction** (Part 2 below), then compares to ground truth and saves results (Part 3).

---

## Part 2: Single-PDF extraction (`extractor.extract()`)

For **one** PDF, this is the sequence inside the extractor.

### Step 0: Free GPU for OCR

- **LLMEngine.unload_model()**  
  Stops the text (and vision) model in Ollama and waits so GPU VRAM is freed for OCR.

---

### Step 1: OCR (`ocr.process()`)

1. **PDF → images**  
   Converts the PDF to images at 300 DPI; saves under `output_dir/images/`.

2. **Table-line removal**  
   Morphological ops on each image to remove table lines; saves “clean” images (e.g. `output_dir/images_clean/`).  
   These clean images are used for EasyOCR and later for the vision model.

3. **Docling OCR**  
   Runs Docling on the **original** page images.  
   - With `--gpu` and default settings: Docling runs on **CPU** so GPU is free for EasyOCR and the LLM.  
   - Produces **markdown per page** (tables, headings, paragraphs).  
   Docling is then unloaded from GPU (if it was on GPU) and the process waits so VRAM is released.

4. **EasyOCR**  
   Runs EasyOCR on the **clean** (line-removed) images.  
   - With `--gpu`: EasyOCR runs on **GPU**.  
   - Produces **text blocks with bounding boxes** (x, y, text, confidence) per page.  
   EasyOCR is then unloaded and the process waits again.

5. **Spatial index**  
   For each page, builds a **spatial index** from the bbox data:  
   - Rows and columns (by Y and X).  
   - Tables (grids of cells).  
   - **Label–value pairs** (e.g. `POLICY NUMBER -> BA-12345`).  
   These are used later for “below label” and table-aware extraction.

**Outputs:**  
`docling_pages`, `bbox_pages`, `spatial_indices`, `image_paths`, `clean_image_paths`, and derived full-document strings (e.g. `full_docling_text`, `format_bbox_as_rows`).

---

### Step 2: Form type and schema

- If **form_type** was not provided: it is **detected** from the PDF name or from Docling text (e.g. “ACORD 125”).  
- **Schema** for that form type (125, 127, or 137) is loaded from the registry (field list, categories, tooltips).

---

### Step 3: Prepare text and sections

- **Full OCR strings**  
  - `docling_text`: all Docling markdown concatenated.  
  - `bbox_text`: all pages’ bbox text with coordinates (e.g. `[y=..., x=...] text`).  
  - `lv_text`: label–value pairs per page, e.g. `LABEL -> value`.

- **Per-page**  
  - `page_docling`, `page_bbox_text`, `page_lv_text` for section- or page-scoped prompts.

- **Section detection (form sections)**  
  - Headers in the bbox are used to cluster blocks into **form sections** (e.g. “Policy”, “Named Insured”, “Driver Table”).  
  - Section IDs and crop boxes are saved to `output_dir/form_sections.json`.  
  - Later, some categories get **section-scoped** Docling/BBox text (only blocks in the relevant sections) to reduce noise.

- **Save intermediates**  
  - Saves Docling, bbox, bbox rows, label–value, and spatial summary under `output_dir/` for debugging.

---

### Step 4: Spatial pre-extraction

- **spatial_preextract(form_type, page_bbox)**  
  Uses **only** bbox positions and label–value geometry (no LLM):  
  - Finds labels like “DATE”, “CARRIER”, “NAIC CODE”, “POLICY NUMBER”, “AGENCY”, “PRODUCER”, “NAMED INSURED”, etc.  
  - Reads values **below** or **to the right** of those labels.  
  - Form-specific logic: e.g. 125 status row (Quote/Bound/Issue/Cancel/Renew/Change), effective date/time, underwriter, product code, LOB checkboxes; 127/137 header and driver/vehicle rows where applicable.  
- Result is a dictionary of **high-confidence fields** (e.g. `Insurer_FullName_A`, `Policy_PolicyNumberIdentifier_A`, `Form_CompletionDate_A`).  
- These are saved to `output_dir/spatial_preextract.json` and **merged into** the main `extracted` dict so the LLM is not asked for them again.

---

### Step 5: Vision pass first (if `--vision` and vision model configured)

- **Unload text model** so the **vision model** (e.g. qwen3-vl:30b) can use the GPU.  
- **Checkbox-only pass:** Among fields still missing after spatial, checkbox/radio fields are sent to the VLM with form images; responses merged.  
- **General vision pass:** Remaining missing fields sent to the VLM; JSON merged. If vision model returns 404, both passes are skipped.  
- **Unload vision model** so the text model can run for the next steps.

---

### Step 6: Category-by-category TEXT LLM extraction

- **Extraction order** (by category): e.g. header → insurer → producer → named_insured → policy → coverage → location → loss_history → checkbox → general (and any others defined in the schema).  
- For **each category**:  
  - Fields **already** in `extracted` (from spatial pre-extract or vision) are **skipped**.  
  - Remaining fields get a **prompt** that includes:  
    - Form layout hint (125/127/137).  
    - Category hint (e.g. “insurer = carrier, not producer”).  
    - List of field names (and tooltips).  
    - **Docling** text (full or section-scoped).  
    - **BBox** text (full or section-scoped).  
    - Optional **label–value** lines.  
  - **LLM** (text model) returns a JSON of `{ field_name: value }`.  
  - Only keys **not already in extracted** are merged in.  
- **Drivers (127 only)**  
  - One sub-step: extract all driver rows (suffix _A … _M) using driver-specific prompts and bbox column/row positions.  
- **Vehicles (127 / 137)**  
  - One sub-step: extract vehicle-related fields per suffix (_A, _B, …) with vehicle prompts.

---

### Step 7: Gap-fill pass

- **Missing fields** after category extraction are collected.  
- A single **gap-fill** prompt is built with:  
  - BBox text (optionally section-scoped for the sections that contain those fields).  
  - Label–value text.  
- LLM returns JSON for as many of the missing fields as it can.  
- New values are merged into `extracted` (again only for keys not already present).

---

### Step 8: Verification and normalization

- **Verify with BBox**  
  - For each extracted value, checks whether that **exact string** (or a close variant) appears in the raw BBox text.  
  - Count of “verified” values is printed; used for monitoring, not for changing values.  
- **Normalise**  
  - Form-specific normalisation (e.g. dates, checkboxes 1/Off, trimming).  
- **Validate field names**  
  - Drops any key that is not in the schema (except spatially pre-extracted keys that are kept for GT alignment).  
- **Unload LLM**  
  - Text (and vision) model are stopped so GPU is free for the next PDF’s OCR.

---

### Step 9: Return result

---

**Order summary:** Spatial pre-extract → **Vision (VLM) first** → Text LLM by category → Driver/Vehicle → Gap-fill → Verify/normalise.

- Returns **extracted_fields** (final dict) and **metadata** (form_type, source_pdf, counts, time, model name).

---

## Part 3: After extraction (test pipeline)

For each PDF, **after** `extractor.extract()` returns:

1. **Save outputs**  
   - `extracted.json`: final field dictionary.  
   - `metadata.json`: form type, timing, model, etc.

2. **Compare to ground truth (if GT exists)**  
   - Load the PDF’s matching `.json` (GT).  
   - For **127**, GT is **flattened** (e.g. “Vehicle 1” / “Driver 1” → keys with suffix _A, _B, …) so keys match the schema.  
   - **compare_fields(extracted, gt_flat)** computes:  
     - **matched** (exact), **partial_match**, **wrong**, **missing**.  
     - **accuracy** = (matched + 0.5×partial) / total_gt.  
     - **exact_match_rate**, **coverage**.  
   - Checkbox/indicator fields get normalisation (e.g. 0/1 → false/true) before comparison.  
   - **comparison.json** is saved (per-field status: matched/partial/wrong/missing, expected vs extracted).

3. **Print report**  
   - Accuracy, coverage, matched/partial/wrong/missing, and optionally a short per-field summary.

4. **Cleanup and next PDF**  
   - OCR engine cleanup, `torch.cuda.empty_cache()`, short sleep.  
   - Then the next PDF (or next form type) runs from **Part 2** again.

---

## Part 4: End of run

- **Per-form-type summary**  
  - Aggregate accuracy, exact match, coverage, total matched/partial/wrong/missing, total time.  
  - Per-form accuracy list.  
- **Optional**  
  - Save a test summary JSON and/or final console summary.

---

## Summary flow (one PDF)

```
Start
  → Unload LLM (free GPU)
  → OCR: PDF → images → remove lines → Docling (→ unload) → EasyOCR (→ unload) → spatial index
  → Form type + schema
  → Section detection + save intermediates
  → Spatial pre-extract (label/position rules) → merge into extracted
  → [If vision] Unload text → VLM checkbox pass → VLM general pass → unload VLM
  → For each category: build prompt (Docling + BBox + sections) → text LLM → merge new fields
  → Driver extraction (127) → merge
  → Vehicle extraction (127/137) → merge
  → Gap-fill (missing fields) → merge
  → Verify vs BBox, normalise, validate field names, unload LLM
  → Return extracted + metadata
  → Save JSON, compare to GT, print report
End
```

That’s the full step-by-step of what happens when you run the pipeline.
