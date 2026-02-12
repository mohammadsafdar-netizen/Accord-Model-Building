# Label-Value → Empty JSON → LLM Fill Pipeline

## Design goal

1. **Iteratively improve label-value pair creation** using Docling + EasyOCR + spatial analysis.
2. **Produce a form-specific empty JSON** (schema keys with `null` values) for the detected form type.
3. **LLM’s only job: fill the JSON** from the label-value pairs (and optional OCR context). This single task is easier to evaluate and to **finetune** a model for later.

---

## Pipeline phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Phase 1: Label-Value Pair Creation (iterative, no LLM)                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input:  PDF → images (300 DPI, table-line removal)                          │
│  Step A: Docling OCR → structure (tables, key_value_items, markdown)         │
│  Step B: EasyOCR → bounding boxes + text per block                           │
│  Step C: Fuse: Docling structure + EasyOCR bbox + spatial rules              │
│          → list of (label_text, value_text, optional bbox, source)           │
│  Output: label_value_pairs (and optionally bbox/source per pair)             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Phase 2: Form-Specific Empty JSON                                            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input:  Form type (125 / 127 / 137) + schema registry                        │
│  Step:   Build JSON object with every schema field key → null (or default)   │
│  Output: empty_form.json (same keys as schema, values null)                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Phase 3: LLM Fills JSON                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input:  empty_form.json + label_value_pairs (+ optional docling/bbox text)  │
│  Step:   Single LLM task: "Given these label-value pairs, fill the JSON      │
│          keys. Use exact schema keys. Output only valid JSON."                │
│  Output: filled_form.json (ready for validation / finetuning targets)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

Benefits of this split:

- **Label-value** can be improved with better OCR fusion and rules without touching the LLM.
- **Empty JSON** is deterministic from schema; easy to version and test.
- **LLM fill** is one clear task → easier to prompt, evaluate, and finetune (e.g. SFT on “pairs → filled JSON”).

---

## Docling vs EasyOCR: roles and usage

### Docling (document understanding)

| Aspect | Details |
|--------|--------|
| **Role** | Layout, structure, reading order, tables, **key-value pairs**. |
| **Output we use** | Markdown per page (tables as `\|...\|`, headings), optional `document.key_value_items` and `document.tables` when API exists. |
| **Strengths** | Tables with rows/columns, key-value detection, hierarchy (sections, groups). Good for “what is a label” vs “what is a value” from layout. |
| **Limitations** | Coordinates may differ from image pixels; we fuse with EasyOCR for precise bbox. |
| **Best practice** | Prefer native `key_value_items` and table export when available; fall back to markdown parsing. |

Docling’s **DoclingDocument** (v2) has:

- `texts`, `tables`, `pictures`, **`key_value_items`**
- `body` / `furniture` / `groups` for structure
- Bounding boxes via item provenance (`prov`)

We currently use only `export_to_markdown()` and bbox from `iterate_items()`. Adding extraction of `key_value_items` and `tables` (when present) will make label-value creation **easier and more accurate** without changing the rest of the pipeline.

### EasyOCR (text + bbox)

| Aspect | Details |
|--------|--------|
| **Role** | Per-block text and **pixel-level bounding boxes** for alignment. |
| **Output** | List of (bbox, text, confidence) per page. We convert to (x, y, x_min, y_min, x_max, y_max). |
| **Strengths** | Reliable bbox; good for “same row” / “to the right of” rules. No column merging when `paragraph=False`. |
| **Limitations** | No notion of “label” vs “value”; we infer via heuristics and Docling. |
| **Best practice** | Use `paragraph=False` (default) for forms. Optionally tune `width_ths` if columns merge; prefer post-processing by (x, y) for tables. |

So:

- **Docling** = “what are the logical label-value and table structures?”
- **EasyOCR** = “where is each text fragment on the page (bbox)?”
- **Fusion** = Match Docling’s labels/values to EasyOCR blocks by text + position (same row, value to the right), and apply acceptance rules (no label-as-value, no legal boilerplate).

---

## Making the pipeline easier to run and maintain

1. **Single config per form type**  
   Form type → schema path, empty JSON template path, and (later) any form-specific label-value rules. Keeps pipeline code form-agnostic.

2. **Explicit artifacts**  
   - `label_value_pairs.json` (list of `{label, value, page?, source?}`)  
   - `empty_form_125.json` (or 127/137)  
   - `filled_form.json` (LLM output)  
   This makes debugging and finetuning data generation straightforward.

3. **Docling native when available**  
   If `result.document.key_value_items` or `result.document.tables` exist, use them first; then supplement with markdown-based parsing and EasyOCR pairing. One function (e.g. `extract_docling_pairs(result)`) that returns a list of (label, value) keeps the rest of the code unchanged.

4. **Stricter label-value acceptance**  
   Already added: reject value blocks that end with `:`, are pure symbols, or are long legal text; reject label blocks that are boilerplate. Keeps pairs clean for the LLM and for training data.

5. **Optional “LLM fill only” mode**  
   If label-value pairs and empty JSON are precomputed (or from another tool), the pipeline can run only Phase 3 (LLM fill). That supports batch jobs and finetuning workflows.

---

## Finetuning later

- **Training data**: (label_value_pairs, empty_json) → filled_json (ground truth from manual or existing pipeline).
- **Task**: Given pairs + empty JSON, predict filled JSON (or only changed keys).
- **Model**: Encoder-only or encoder-decoder; can start from the same base as the current LLM. The input is structured (pairs + schema keys), so the task is simpler than “full page → JSON.”

---

## Implementation status

- **Phase 1**: OCR engine + spatial index + Docling-guided and heuristic pairing, with acceptance filters. **Done:** Docling native `key_value_items` and `tables` extraction when available (`extract_docling_native_pairs`); merged with markdown-derived pairs per page. Optional export of label-value pairs to JSON for artifacts.
- **Phase 2**: **Done.** `form_json_builder.build_empty_form_json(registry, form_type)` builds a form-specific JSON with all schema keys and `null` (or defaults). Use `save_empty_form_json()` to write `empty_form_125.json` etc.
- **Phase 3**: New path: “fill JSON” prompt + LLM that takes label-value pairs + empty JSON and outputs filled JSON (to be wired in extractor or a dedicated fill step).
