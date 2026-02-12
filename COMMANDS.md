# Full pipeline commands (all features off by default)

Use these from the `best_project` directory. Replace `path/to/form.pdf` with your PDF and `125` with `127` or `137` if needed.

---

## run_phase1_extraction.py

**Docling only** (structure OCR, no bbox, no LLM, no VLM — images + empty/minimal extraction):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling
```

**Docling + EasyOCR** (prefill from spatial + label-value only):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend easyocr
```

**Docling + Surya (Marker)** (prefill from spatial + label-value only):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend surya
```

**Docling + text LLM** (no bbox, no VLM — needs Docling text for LLM):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --text-llm
```

**Docling + VLM only** (no bbox OCR, no text LLM):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --vision
```

**Docling + EasyOCR + text LLM** (no VLM):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend easyocr --text-llm
```

**Docling + Surya + text LLM** (no VLM):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend surya --text-llm
```

**Docling + EasyOCR + VLM** (no text LLM):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend easyocr --vision
```

**Docling + Surya + VLM** (no text LLM):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend surya --vision
```

**Full pipeline** (Docling + bbox + text LLM + VLM):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend surya --text-llm --vision
```
or with EasyOCR:
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend easyocr --text-llm --vision
```

**With GPU, custom output, ground truth, DPI:**
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend surya --text-llm --vision --gpu --out ./my_out --ground-truth path/to/gt.json --dpi 200
```

**VLM-only with custom vision model and batch size:**
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --vision --vision-model qwen2-vl:7b --vision-batch-size 12
```

**Fast path** (fewer LLM calls; needs --docling and --ocr-backend for fill-nulls):
```bash
python run_phase1_extraction.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend surya --text-llm --fast --max-llm-chunks 4
```

---

## main.py

**Docling only:**
```bash
python main.py path/to/form.pdf --form-type 125 --docling
```

**Docling + EasyOCR + text LLM:**
```bash
python main.py path/to/form.pdf --form-type 125 --docling --ocr-backend easyocr --text-llm
```

**Docling + Surya + text LLM:**
```bash
python main.py path/to/form.pdf --form-type 125 --docling --ocr-backend surya --text-llm
```

**Docling + VLM only:**
```bash
python main.py path/to/form.pdf --form-type 125 --docling --vision
```

**Full pipeline:**
```bash
python main.py path/to/form.pdf --form-type 125 --docling --ocr-backend surya --text-llm --vision
```

**With GPU and ground truth:**
```bash
python main.py path/to/form.pdf --form-type 125 --docling --ocr-backend surya --text-llm --vision --gpu --ground-truth path/to/gt.json
```

---

## run_phase1_fast.py (standalone)

Requires either `--docling` or `--form`; bbox defaults to none.

**Docling + Surya + fill-nulls LLM:**
```bash
python run_phase1_fast.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend surya
```

**Docling + EasyOCR + fill-nulls LLM:**
```bash
python run_phase1_fast.py --pdf path/to/form.pdf --form 125 --docling --ocr-backend easyocr
```

---

## Quick reference

| Feature    | Phase 1 flag       | main.py flag        |
|-----------|--------------------|----------------------|
| Docling   | `--docling`        | `--docling`          |
| EasyOCR   | `--ocr-backend easyocr` | `--ocr-backend easyocr` |
| Surya     | `--ocr-backend surya`   | `--ocr-backend surya`   |
| VLM       | `--vision`         | `--vision`            |
| Text LLM  | `--text-llm`       | `--text-llm`         |

Without `--docling` you must pass `--form 125` (or `127`/`137`).
