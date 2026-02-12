# Accuracy and Credibility

How extraction **accuracy** is measured and how **credibility** of results is supported (verification, sources, audit).

---

## 1. Accuracy (when ground truth exists)

Accuracy is computed only when you run with **ground truth** (e.g. `test_pipeline.py` with PDFs that have a matching `.json` GT file, or `main.py --ground-truth <path>`).

### Metrics (see `compare.py`)

| Metric | Definition |
|--------|------------|
| **Total GT fields** | Number of non-empty fields in the ground truth (after flattening for form 127). |
| **Matched** | Extracted value equals GT after normalisation (exact match). |
| **Partial match** | GT value is contained in extracted or vice versa (e.g. substring). |
| **Wrong** | Extracted value present but different from GT (not partial). |
| **Missing** | GT has a value but extraction has nothing for that field. |
| **Accuracy** | `(matched + 0.5 × partial_match) / total_gt × 100`. Partial counts as half right. |
| **Exact match rate** | `matched / total_gt × 100`. |
| **Coverage** | `(total_gt - missing) / total_gt × 100`. Share of GT fields that were filled at all. |

### Normalisation (before comparing)

- **Checkboxes/indicators:** GT and extracted are normalised to `true`/`false` (e.g. 1/0, "1"/"Off", "yes"/"no").
- **Dates:** Parsed and compared as YYYY-MM-DD when possible.
- **Times (e.g. EffectiveTime):** Compared as 4-digit HHMM.
- **Amounts/limits:** Currency and commas stripped; compared as digits.
- **Area/count:** Numeric strings with commas normalised (e.g. 100,000 vs 100000).

So **accuracy** is a **relative** measure: it tells you how well extraction matches a specific GT, not “truth” in the abstract. GT quality and schema/GT key alignment matter.

### Where results are stored

- **Per-run:** `test_output/form_<125|127|137>/<stem>/comparison.json` — full `field_results` with per-field `status` (matched/partial/wrong/missing), `expected`, and `extracted`.
- **Summary:** Printed report and optional test summary JSON (aggregate accuracy, exact match, coverage, matched/partial/wrong/missing counts).

---

## 2. Credibility (trust and audit)

Credibility is supported by **how** we produce values and **whether** we can cross-check them.

### 2.1 Source of each value

Each extracted field is produced by one of:

| Source | Meaning | Typical reliability |
|--------|--------|----------------------|
| **spatial** | Value came from **spatial pre-extraction**: label + position rules on BBox OCR (no LLM). | Highest: rule-based, same logic every time. |
| **vision** | Value came from the **vision model** (VLM) looking at form images. | Model-dependent; good for checkboxes and layout when VLM is strong. |
| **text_llm** | Value came from the **text LLM** (category, driver, or vehicle prompts) using OCR text. | Depends on OCR quality and prompt; section-scoping helps. |
| **gap_fill** | Value came from the **gap-fill** pass over remaining missing fields. | Same as text LLM but with a single, broad prompt. |

When **field_sources** (and optionally **field_verified**) are saved (see below), you can:

- Prefer or flag fields by source (e.g. treat **spatial** as highest credibility).
- Audit which fields came from vision vs text vs gap-fill for tuning or review.

### 2.2 BBox verification

After extraction we **cross-check** each value against the raw BBox OCR text:

- If the **exact string** (normalised) appears in the OCR text → counted as **verified**.
- If not, we still keep the value but it is **unverified** (could be paraphrased, inferred, or wrong).

So:

- **fields_verified** (count) = number of extracted values that appear literally in the OCR.
- **field_verified** (per field) = whether that field’s value was found in BBox.

High verified count → more values are grounded in OCR; low → more model inference (or OCR missing the text).

### 2.3 Schema validation

Only field names that exist in the form schema are kept. Spatially extracted keys that match GT but not schema are preserved so comparison against GT is still fair. So:

- Output is constrained to known fields (and allowed “extra” spatial keys for evaluation).
- Invalid or hallucinated **field names** are removed; **values** are not re-checked beyond verification.

### 2.4 Saved outputs for audit

- **extracted.json** — Final field → value map.
- **metadata.json** — Form type, PDF path, counts, timing, model; can include **field_sources** and **field_verified** when enabled.
- **comparison.json** (if GT provided) — Per-field status (matched/partial/wrong/missing) and expected vs extracted.
- **spatial_preextract.json** — Which values came from spatial rules (subset of field_sources).
- **form_sections.json** — Section boundaries used for section-scoped prompts.

Together these support **reproducibility** and **auditability** of accuracy and credibility.

---

## 3. How to improve accuracy and credibility

- **OCR:** Better scans and resolution (e.g. 300 DPI), table-line removal, and dual OCR (Docling + BBox) improve both accuracy and verification rate.
- **Spatial rules:** More fields in spatial pre-extract → more high-credibility (spatial) values and fewer model errors for those fields.
- **Prompts and schema:** Align schema and prompts with form layout and GT naming; use section-scoped context where it helps.
- **Vision:** When the VLM is reliable, vision-first fills checkboxes and layout-heavy fields; text LLM then fills the rest.
- **GT and comparison:** Use comparison.json to find systematic wrong/missing patterns; fix prompts, spatial rules, or schema. Re-run and compare again to measure improvement.

---

## 4. Summary

- **Accuracy** = how well extraction matches your ground truth (matched/partial/wrong/missing and derived %).
- **Credibility** = source of each value (spatial > vision > text_llm > gap_fill), BBox verification (value seen in OCR), schema validation, and saved outputs for audit.
- Use **field_sources** and **field_verified** (when available) to prioritise or review fields by reliability and to explain results to users or auditors.
