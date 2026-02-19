# Running on Eureka

This guide covers setting up and running the ACORD extraction pipeline on the **Eureka** machine for usability and testing.

---

## Quick answer: pull and run

**Yes — test docs and everything are in the repo.** If you pull the repo on Eureka and have dependencies + Ollama ready, you can run the full pipeline with one command.

1. **Clone/pull the repo** (includes `test_data/` with PDFs + ground-truth JSON, and `schemas/`).
2. **One-time:** install deps and Ollama (see below).
3. **Run:**
   ```bash
   cd Accord-Model-Building
   .venv/bin/python test_pipeline.py --gpu
   ```
   That runs the full pipeline (Docling + bbox OCR + text LLM) on all discovered forms in `test_data/`, compares to ground truth, and writes results to `test_output/`.  
   **Note:** `test_pipeline.py` has no `--text-llm` or `--docling` flags; it always uses Docling and the text LLM.

No extra download of test docs is needed **if** `test_data/` and `schemas/` are committed in your repo (they are not in `.gitignore`). If your repo omits `test_data/` (e.g. large files not pushed), copy it onto Eureka or set `BEST_PROJECT_TEST_DATA` to its path.

### Recommended: Full pipeline with finetuned VLM

For the highest accuracy, use the finetuned `acord-vlm-7b` model with the full pipeline:

1. **Pull required models** (once):
   ```bash
   ollama pull qwen2.5:7b          # Text LLM
   # acord-vlm-7b is registered via finetune/export_ollama.py
   ```

2. **Set Ollama environment for multi-model:**
   ```bash
   OLLAMA_MAX_LOADED_MODELS=3 OLLAMA_NUM_PARALLEL=4 ollama serve
   ```

3. **Run with optimal config:**
   ```bash
   .venv/bin/python test_pipeline.py --gpu --one-per-form \
       --docling --preprocess --use-positional \
       --vlm-extract --vlm-extract-model acord-vlm-7b \
       --checkbox-crops --text-llm --use-rag \
       --smart-ensemble --no-confidence-routing \
       --validate-fields --no-semantic-matching
   ```

This achieves ~79% average accuracy across all 4 form types (125, 127, 137, 163).

### RAG (few-shot examples)

To improve extraction accuracy using few-shot examples from ground truth in `test_data/`:

```bash
python test_pipeline.py --gpu --use-rag
```

This builds an in-memory store from all GT JSONs under `test_data/` and injects example field→value pairs into each category prompt. See `docs/RAG_DESIGN.md` for details.

---

## 1. One-time setup on Eureka

```bash
# Clone or copy the project to Eureka
cd /path/on/eureka
# e.g. git clone ... Accord-Model-Building && cd Accord-Model-Building

# Create virtualenv and install deps (Python 3.12)
python3 -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt   # for pytest
```

---

## 2. Configuration via environment (no code changes)

Set these on Eureka so paths and defaults match the machine:

| Variable | Meaning | Default |
|----------|---------|--------|
| `BEST_PROJECT_ROOT` | Project root | Directory containing `config.py` |
| `BEST_PROJECT_TEST_DATA` | Test PDFs + ground truth JSON | `<root>/test_data` |
| `BEST_PROJECT_OUTPUT` | Where to write test_output | `<root>/test_output` |
| `BEST_PROJECT_SCHEMAS` | Schema JSONs (125, 127, 137, 163) | `<root>/schemas` |
| `OLLAMA_URL` | Ollama API URL | `http://localhost:11434` |
| `USE_GPU` | Use GPU for OCR by default | Set to `1` on Eureka |

Example for Eureka (e.g. in `~/.bashrc` or a `.env` in the project):

```bash
export BEST_PROJECT_ROOT=/path/to/Accord-Model-Building
export BEST_PROJECT_TEST_DATA=$BEST_PROJECT_ROOT/test_data
export BEST_PROJECT_OUTPUT=$BEST_PROJECT_ROOT/test_output
export USE_GPU=1
export OLLAMA_URL=http://localhost:11434
```

---

## 3. Running tests

**Unit tests only (no GPU, no test data):**

```bash
cd /path/to/Accord-Model-Building
source .venv/bin/activate
pytest tests/ -v
# or
./scripts/run_eureka.sh tests
```

**E2E tests (needs test_data; optional GPU):**

```bash
pytest tests/ -m e2e -v
# or
./scripts/run_eureka.sh e2e
```

**Full pipeline (all forms in test_data, GPU + Docling + LLM):**

```bash
./scripts/run_eureka.sh pipeline
# or directly:
python test_pipeline.py --gpu
```

**Single PDF extraction:**

```bash
./scripts/run_eureka.sh extract /path/to/form125.pdf --form-type 125
# or
python main.py /path/to/form125.pdf --form-type 125 --docling --gpu --text-llm
```

---

## 4. Layout (usability)

- **`config.py`** — Central paths and env; used by `main.py`, `test_pipeline.py`, and tests.
- **`tests/`** — Unit tests (`tests/unit/`) and E2E tests (`tests/integration/`, marked `e2e`). Run from project root.
- **`scripts/run_eureka.sh`** — Convenience runner: `tests`, `e2e`, `pipeline`, or `extract <pdf>`.
- **`pytest.ini`** — By default runs unit tests only (`-m "not e2e"`). Use `-m e2e` to run E2E on Eureka.

---

## 5. Checklist for Eureka

- [ ] Python 3.12+ and venv
- [ ] `uv pip install -r requirements.txt` and `requirements-dev.txt`
- [ ] Ollama installed and running (`ollama serve`), models pulled (e.g. `ollama pull qwen2.5:7b`)
- [ ] `test_data/` populated with PDFs and matching `.json` ground truth (see README)
- [ ] Optional: set `BEST_PROJECT_*` and `USE_GPU=1` in env
- [ ] Run unit tests: `pytest tests/ -v`
- [ ] Run full pipeline: `./scripts/run_eureka.sh pipeline` or `python test_pipeline.py --gpu`
