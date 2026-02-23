# ACORD Form Assignment & Pre-Filling CoPilot

Reads customer emails/messages, classifies the insurance line of business, assigns correct ACORD forms, and pre-fills fillable AcroPDF forms with extracted data.

## Architecture

```
Email/Message
    │
    ├──► Stage 1: LOB Classification (LLM)
    │        → commercial_auto, general_liability, etc.
    │
    ├──► Stage 2: Entity Extraction (LLM)
    │        → business info, vehicles, drivers, coverages
    │
    ▼
Stage 3: Form Assignment (rules)
    → Forms 125 + 127 + 137 for commercial auto
    │
    ▼
Stage 4: Field Mapping (static maps)
    → entity fields → PDF widget field names
    │
    ▼
Stage 5: PDF Filling (PyMuPDF)
    → pre-filled ACORD PDFs
    │
    ▼
Stage 6: Gap Analysis (optional, LLM)
    → missing fields + follow-up questions
```

## Supported Lines of Business

| LOB | Forms | Status |
|-----|-------|--------|
| Commercial Auto | 125 + 127 + 137 | Full pipeline |
| Commercial Umbrella | 125 + 163 | Full pipeline |
| General Liability | 125 + 126 | Form 125 only (no 126 schema) |
| Workers' Compensation | 125 + 130 | Form 125 only (no 130 schema) |
| Commercial Property | 125 + 140 | Form 125 only (no 140 schema) |

## Usage

```bash
# From inline text
python -m Custom_model_fa_pf.main --email "We need commercial auto insurance for our 3 trucks..."

# From file
python -m Custom_model_fa_pf.main --email-file customer_request.txt

# JSON only (no PDF filling)
python -m Custom_model_fa_pf.main --email "..." --json-only

# With gap analysis + verbose
python -m Custom_model_fa_pf.main --email "..." --show-gaps --verbose

# Custom model
python -m Custom_model_fa_pf.main --email "..." --model qwen3:8b
```

## Output

Results are saved to `output/submission_YYYYMMDD_HHMMSS/`:

```
submission.json              # Full results
classification.json          # LOB classification
extracted_entities.json      # Extracted entities
form_assignments.json        # Assigned forms
field_mappings/              # Per-form field values
filled_forms/                # Pre-filled PDFs
gap_report.json              # Missing info + follow-up questions
```

## Requirements

- Python 3.12+
- Ollama with qwen3:8b (or compatible model)
- PyMuPDF (`uv pip install PyMuPDF`)

## Testing

```bash
# Unit tests (no Ollama needed)
pytest Custom_model_fa_pf/tests/ -k "not integration"

# Integration tests (requires Ollama)
pytest Custom_model_fa_pf/tests/ -k integration
```
