#!/usr/bin/env python3
"""
VLM-OCR Engine: Two-stage extraction using VLM-based OCR models
================================================================
Stage 1: Send page images to a VLM-OCR model (GLM-OCR or Nanonets-OCR-s)
         via Ollama → get structured text (markdown / HTML) per page.
Stage 2: Feed that structured text to a text LLM with ACORD schema prompts
         → get JSON field values.  (Stage 2 is handled by the caller.)

Supported backends:
  - glm-ocr    : ~0.9B, native Ollama.  Two prompts per page (Text + Table).
  - nanonets-ocr : ~3B (Qwen2.5-VL fine-tune), community Ollama ports.
                    Rich markdown with ☐/☑ checkboxes, HTML tables, <signature> tags.

Usage:
    from vlm_ocr_engine import VLMOCREngine, NanonetsOutputParser
    engine = VLMOCREngine(llm_engine, backend="glm-ocr", model="glm-ocr")
    pages = engine.ocr_pages(image_paths)   # List[str]
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# GLM-OCR prompts
# ---------------------------------------------------------------------------

GLM_TEXT_PROMPT = "Text Recognition:"
GLM_TABLE_PROMPT = "Table Recognition:"

# ---------------------------------------------------------------------------
# Nanonets-OCR prompt  (mirrors the official model card)
# ---------------------------------------------------------------------------

NANONETS_PROMPT = (
    "Extract the text from the above document as if you were reading it naturally. "
    "Return the tables in html format. "
    "Return the equations in LaTeX representation. "
    "If there is an image in the document and image caption is not present, add a small "
    "description of the image inside the <img></img> tag; otherwise, add the image caption "
    "inside <img></img>. "
    "Watermarks should be wrapped in brackets. Ex: <watermark>OFFICIAL COPY</watermark>. "
    "Page numbers should be wrapped in brackets. Ex: <page_number>14</page_number> or <page_number>9/22</page_number>. "
    "Prefer using ☐ and ☑ for check boxes."
)


# ===================================================================
# VLMOCREngine
# ===================================================================

class VLMOCREngine:
    """Send page images to a VLM-OCR model via Ollama and retrieve structured text."""

    def __init__(
        self,
        llm_engine: Any,          # LLMEngine instance
        backend: str,             # "glm-ocr" or "nanonets-ocr"
        model: str,               # Ollama model name (e.g. "glm-ocr", "yasserrmd/Nanonets-OCR-s")
    ):
        self.llm = llm_engine
        self.backend = backend
        self.model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ocr_pages(
        self,
        image_paths: List[Path],
        parallel: bool = True,
        max_workers: int = 3,
    ) -> List[str]:
        """Run VLM-OCR on each page image.  Returns structured text per page."""
        if not parallel or len(image_paths) <= 1:
            return [self._ocr_single_page(p) for p in image_paths]

        results: List[Optional[str]] = [None] * len(image_paths)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_idx = {
                pool.submit(self._ocr_single_page, p): idx
                for idx, p in enumerate(image_paths)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    print(f"    [VLM-OCR] Page {idx} failed: {exc}")
                    results[idx] = ""
        return [r or "" for r in results]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ocr_single_page(self, image_path: Path) -> str:
        """OCR a single page image via the configured VLM-OCR backend."""
        if self.backend == "glm-ocr":
            return self._ocr_glm(image_path)
        elif self.backend == "nanonets-ocr":
            return self._ocr_nanonets(image_path)
        else:
            raise ValueError(f"Unknown VLM-OCR backend: {self.backend}")

    def _ocr_glm(self, image_path: Path) -> str:
        """GLM-OCR: two calls – Text Recognition + Table Recognition."""
        text_out = self._call_vlm_ocr(GLM_TEXT_PROMPT, image_path)
        table_out = self._call_vlm_ocr(GLM_TABLE_PROMPT, image_path)

        parts = []
        if text_out and text_out.strip():
            parts.append("--- TEXT CONTENT ---")
            parts.append(text_out.strip())
        if table_out and table_out.strip():
            parts.append("\n--- TABLE CONTENT ---")
            parts.append(table_out.strip())
        return "\n".join(parts)

    def _ocr_nanonets(self, image_path: Path) -> str:
        """Nanonets-OCR: single call with the detailed prompt."""
        return self._call_vlm_ocr(NANONETS_PROMPT, image_path)

    def _call_vlm_ocr(self, prompt: str, image_path: Path) -> str:
        """Call the VLM-OCR model via LLMEngine.generate_vlm_ocr (no format:json)."""
        return self.llm.generate_vlm_ocr(
            prompt=prompt,
            image_path=image_path,
            temperature=0.0,
            max_tokens=8192,
        )


# ===================================================================
# Nanonets output parser
# ===================================================================

class NanonetsOutputParser:
    """Parse Nanonets-OCR structured markdown output.

    Extracts:
      - Checkbox states:  ☑ → "1",  ☐ → "Off"
      - Converts symbols to text markers for downstream LLM consumption.
    """

    # Pattern: checkbox symbol followed by label text (rest of line)
    _CHECKBOX_RE = re.compile(r'([☐☑✓✗✘☒])\s*(.+?)(?:\n|$)')

    _CHECKED_SYMBOLS = frozenset('☑✓☒')
    _UNCHECKED_SYMBOLS = frozenset('☐✗✘')

    @staticmethod
    def extract_checkbox_states(text: str) -> Dict[str, str]:
        """Find checkbox patterns like '☑ Some Label' → {"Some Label": "1"}.

        Returns:
            {label_text: "1" or "Off"}
        """
        results: Dict[str, str] = {}
        for m in NanonetsOutputParser._CHECKBOX_RE.finditer(text):
            symbol = m.group(1)
            label = m.group(2).strip()
            if not label:
                continue
            if symbol in NanonetsOutputParser._CHECKED_SYMBOLS:
                results[label] = "1"
            else:
                results[label] = "Off"
        return results

    @staticmethod
    def convert_checkboxes_to_text(text: str) -> str:
        """Replace Unicode checkbox symbols with text markers for LLM.

        ☑/✓/☒  →  [CHECKED]
        ☐/✗/✘  →  [UNCHECKED]
        """
        for sym in NanonetsOutputParser._CHECKED_SYMBOLS:
            text = text.replace(sym, "[CHECKED]")
        for sym in NanonetsOutputParser._UNCHECKED_SYMBOLS:
            text = text.replace(sym, "[UNCHECKED]")
        return text
