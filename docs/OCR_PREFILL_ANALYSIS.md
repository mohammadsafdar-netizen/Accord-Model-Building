# OCR + Pre-fill Output Analysis

## Run summary (Form 125, one PDF)

- **OCR**: Docling (4 pages, ~44k chars) + EasyOCR (854 blocks) + spatial index (31+38+13+19 = 101 label-value pairs).
- **Spatial pre-extraction**: 44 fields (insurer, producer, policy, named insured, dates, premiums, line-of-business amounts, etc.).
- **Pre-fill**: 131 total (42 spatial + 89 from label-value matching).

## What works well

1. **Spatial**  
   Layout-based extraction gives correct schema keys and values for header/insurer/producer/policy/named insured, dates, and many premium/LOB fields. These are the most reliable and should stay as-is for the VLM.

2. **Label-value → schema**  
   When the OCR label clearly matches one schema field (e.g. "STREET" → street address, "BUSINESS PHONE #" → phone), pre-fill is correct. Same for NAICS, "NO. OF MEMBERS", etc., when pairing is correct.

3. **Artifacts**  
   - `empty_form.json`: all schema keys, values `null`.  
   - `prefilled_form.json`: spatial + label-value applied; remaining keys stay `null` for the VLM.  
   - `label_value_pairs.json`: raw pairs from OCR (each entry can include `confidence` from EasyOCR).  
   - `prefill_sources.json`: which fields came from "spatial" vs "label_value".  
   - `prefill_details.json`: per-field **source**, **basis**, and **confidence** (see below).

## Confidence and basis for filling

| Source        | Basis | Confidence |
|---------------|-------|------------|
| **spatial**   | Layout: label text is located in the bbox data within a known region (e.g. "CARRIER", "NAIC CODE"); the value is taken from an adjacent region defined by the form template (e.g. below the label, or to the right). Rules live in `spatial_extract.py` (e.g. `extract_125_header`, driver/vehicle tables). | Not stored (layout rules are high-confidence by design). |
| **label_value** | OCR produced a label–value pair (e.g. "STREET" → "123 Main St"); the label was matched to a schema field by **tooltip** (strong) or **field name** (moderate) in `_label_matches_field`. | Stored: **EasyOCR confidence** = `min(label block confidence, value block confidence)` from the pair. Written in `label_value_pairs.json` per pair and in `prefill_details.json` per filled field. |

- **What confidence is**: For **label_value** only, the number is the OCR engine’s per-block confidence (0–1) for the two blocks that form the pair. There is no separate “how sure we are this label maps to this schema field” score; match strength is reflected in **basis** (tooltip vs field_name).
- **Exactly how fields get filled**:  
  - **Spatial**: Script finds a label block (by text + x/y bounds), then reads the value from a fixed relative region (e.g. `_region_below_label`, or a column to the right). The value chosen is the “best” text in that region (longest, then highest OCR confidence).  
  - **Label_value**: Pairs come from the spatial index (Docling-guided + heuristic “value to the right of label”). Each pair’s label (normalized) is compared to each schema field’s tooltip and name; first match wins (longer field name preferred on ties). The pair’s value is written to that field; the pair’s confidence is stored in `prefill_details.json`.

## Issues observed

1. **Wrong pairings**  
   Some rows in `label_value_pairs.json` are still label↔value or column misalignments (e.g. "10000" as label, "MOTOR CARRIER" as value; or "LLC" → "NO. OF MEMBERS"). These come from the OCR pairing step; improving `_block_acceptable_as_value` and row/column logic will reduce this.

2. **Over-eager label→field match**  
   The matcher sometimes maps a label to a schema field that only shares a generic word (e.g. "Indicator", "Explanation"). So we get values like "202-456-1234" or "5045" on unrelated fields. **Mitigation**: Prefer tooltip-based match over name-only; require at least two significant words to match; or use a small allow-list of label snippets → schema keys for known form labels.

3. **Duplicate / repeated labels**  
   The same label (e.g. "NO. OF MEMBERS") can appear in multiple rows; we then assign the same value to multiple schema keys (e.g. _A, _B, _C). That can be correct for repeated sections but wrong when the value belongs to only one instance.

## Recommendation for VLM fill

- **Trust spatial** for pre-filled fields marked `"spatial"` in `prefill_sources.json`; the VLM can leave them or only correct obvious OCR errors.
- **Re-check label_value** pre-fills; the VLM should overwrite when the value clearly doesn’t fit the field (e.g. phone in a checkbox field).
- **Fill all remaining `null`** from context (other fields, label_value_pairs list, or images if using VLM).

So: use **prefilled_form.json** as the initial state, and let the VLM **fill nulls and correct** label_value-sourced fields where needed. This keeps the pipeline simple and makes it easy to add a dedicated “fill from prefilled” step later.
