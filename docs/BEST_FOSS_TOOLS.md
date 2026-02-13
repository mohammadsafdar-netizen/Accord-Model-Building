# Best Free & Open-Source Tools (FOSS) per Step

This pipeline uses the best available free and open-source tools at each step. All are free to use and open-source.

---

## 1. PDF → Page images

| Tool | License | Why |
|------|--------|-----|
| **PyMuPDF (fitz)** (primary) | AGPL | Fast, single Python dependency, no system packages (e.g. poppler). Used when `pymupdf` is installed. |
| **pdf2image** (fallback) | MIT | Uses poppler; fallback if PyMuPDF is not installed. |

**Install (primary):** `pip install pymupdf`

---

## 2. Table-line removal (pre-OCR cleanup)

| Tool | License | Why |
|------|--------|-----|
| **OpenCV (cv2)** | Apache 2.0 | Industry standard for image ops; morphological open to remove horizontal/vertical lines. |

**Install:** `pip install opencv-python`

---

## 3. Document structure / semantic OCR

| Tool | License | Why |
|------|--------|-----|
| **Docling** | Apache 2.0 | Document understanding (DS4SD); outputs structured markdown, tables, layout. Best FOSS for form structure. |

**Install:** `pip install docling`  
**Use:** `--docling`

---

## 4. Bbox OCR (text + coordinates per block)

| Tool | License | Accuracy (typical) | Why |
|------|--------|--------------------|-----|
| **Surya** (default) | Apache 2.0 | ~97% | Best FOSS accuracy on documents/forms; layout-aware. |
| **PaddleOCR** | Apache 2.0 | ~96% | Strong alternative; good speed/accuracy balance. |
| **EasyOCR** | Apache 2.0 | Lower on forms | Fallback when Surya/Paddle not installed. |

**Default:** `--ocr-backend surya`  
**Override:** `--ocr-backend paddle` or `--ocr-backend easyocr` or `--ocr-backend none`

**Install (best):** `pip install surya-ocr`  
**Install (alternative):** `pip install paddleocr paddlepaddle`

---

## 5. Text LLM (extraction, gap-fill)

| Tool | License | Why |
|------|--------|-----|
| **Ollama** (local) | MIT | Run FOSS LLMs locally (Qwen, Llama, Mistral, etc.); no API keys. |
| **Models** | Various (MIT, Llama 2, etc.) | e.g. `qwen2.5:7b`, `llama3.2:3b`. |

**Use:** `--text-llm --model qwen2.5:7b`  
**Install:** [ollama.com](https://ollama.com) then `ollama pull qwen2.5:7b`

---

## 6. Vision LLM (VLM) for form images

| Tool | License | Why |
|------|--------|-----|
| **Ollama** + **LLaVA / Qwen-VL / Llava** | MIT / model license | Local vision-language models; no cloud. |

**Use:** `--vision --vision-model llava:7b`  
**Install:** `ollama pull llava:7b` (or another VLM)

---

## 7. JSON repair (LLM output)

| Tool | License | Why |
|------|--------|-----|
| **json_repair** | MIT | Fixes malformed JSON from LLM responses. |

**Install:** `pip install json_repair` (used by `llm_engine`)

---

## Recommended stack (copy-paste)

```bash
# PDF + OCR
pip install pymupdf opencv-python docling surya-ocr

# Optional: PaddleOCR instead of or alongside Surya
pip install paddleocr paddlepaddle

# LLM (run locally)
# Install Ollama from https://ollama.com then:
ollama pull qwen2.5:7b
ollama pull llava:7b   # if using --vision
```

**Run with best FOSS stack:**

```bash
python main.py path/to/form.pdf --form-type 125 --docling --gpu --text-llm
# Uses: PyMuPDF → OpenCV → Docling + Surya (default) → Ollama
```

To use PaddleOCR instead of Surya:

```bash
python main.py path/to/form.pdf --form-type 125 --docling --ocr-backend paddle --text-llm
```

---

## Summary table

| Step | Best FOSS tool | Flag / default |
|------|----------------|----------------|
| PDF → images | PyMuPDF | (auto) |
| Line removal | OpenCV | (auto) |
| Structure OCR | Docling | `--docling` |
| Bbox OCR | Surya | default `--ocr-backend surya` |
| Text LLM | Ollama + Qwen/Llama | `--text-llm --model qwen2.5:7b` |
| Vision LLM | Ollama + LLaVA | `--vision --vision-model llava:7b` |
| JSON repair | json_repair | (auto) |

All of the above are **free and open-source**.
