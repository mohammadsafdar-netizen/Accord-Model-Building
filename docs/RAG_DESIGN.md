# RAG in the Extraction Pipeline

## Where RAG can fit

| Place | What to retrieve | Accuracy | Speed | Complexity |
|-------|-------------------|----------|--------|------------|
| **Few-shot examples** (recommended) | Past correct extractions (field → value) from ground truth or validated data | ✅ High | Neutral | Low |
| **Document chunks** | Only the most relevant Docling/bbox chunks per field instead of full section | Maybe | ✅ Fewer tokens | Medium |
| **Schema/tooltips** | Extra ACORD guidelines or internal docs by field/category | Maybe | Slight cost (more tokens) | Medium |

---

## 1. Example-based RAG (recommended) — **accuracy**

**Idea:** Build a small store of “correct” field extractions from ground-truth JSONs (e.g. in `test_data/`). When extracting a category, **retrieve 2–5 example (field, value) pairs** for that form type and category and add them to the prompt as few-shot examples.

**Why it helps accuracy:**

- Reduces ambiguity (e.g. date format, checkbox 1/Off, NAIC vs policy number).
- Gives the model a clear pattern of what “good” looks like for that form/category.
- No change to OCR or pipeline flow; only the prompt gains a short “Examples:” block.

**Speed:** Slightly more tokens per prompt; retrieval is cheap (in-memory or small vector store). Net: **neutral or small cost**, worth it for accuracy.

**Implementation:** Integrated in `rag_examples.py`. Enable with **`--use-rag`**; GT path from `--rag-gt-dir` or `BEST_PROJECT_RAG_GT` (default: test_data). Used in category extraction, driver, vehicle, and gap-fill prompts.

---

## 2. Document-chunk RAG — **speed (and possibly accuracy)**

**Idea:** Instead of sending the full section Docling + bbox text, **retrieve only chunks that are relevant** to the requested field names (e.g. by keyword/embedding over sentences or paragraphs). Send those chunks in the prompt.

**Why it might help:**

- **Speed:** Shorter prompts → fewer input tokens, possibly fewer LLM calls if we can batch more fields when context is smaller.
- **Accuracy:** Less noise; the model sees only the part of the page that likely contains the value. Risk: the chunk containing the value might be missed if retrieval is wrong.

**Implementation:** Would require chunking Docling text, indexing (e.g. by field names/tooltips or embeddings), and retrieve(chunk_index, field_names) before `build_extraction_prompt`. Not implemented by default; consider if sections are very long.

---

## 3. External knowledge RAG — **accuracy (edge cases)**

**Idea:** Retrieve from ACORD guidelines, internal playbooks, or FAQ (e.g. “What is NAIC code?”) and append to the prompt.

**Why it might help:** Handles rare or confusing fields. **Cost:** Building and maintaining the knowledge base; more tokens per request.

---

## Summary

- **Best first step:** Add **example-based RAG** (few-shot from ground truth). Improves **accuracy** with low complexity and minimal speed impact.
- **Later:** Document-chunk RAG can improve **speed** (and maybe accuracy) for very long forms; external knowledge RAG for edge cases.

The `rag_examples` module and **`--use-rag`** flag implement (1) and are integrated across category, driver, vehicle, and gap-fill steps.
