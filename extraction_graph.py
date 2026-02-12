#!/usr/bin/env python3
"""
LangGraph extraction pipeline: OCR (parallel) -> extraction.
============================================================
Runs OCR and extraction as graph nodes. OCR node uses parallel Docling+EasyOCR
when Docling=CPU and EasyOCR=GPU to reduce wall time. Extraction node runs
spatial + vision + text LLM + gap-fill.

Usage:
  from extraction_graph import build_extraction_graph, run_extraction
  result = run_extraction(pdf_path, form_type, output_dir, ocr_engine, llm_engine, registry, ...)

Requires: langgraph (pip install langgraph)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from ocr_engine import OCREngine, OCRResult


class ExtractionState(TypedDict, total=False):
    pdf_path: Path
    output_dir: Path
    form_type: Optional[str]
    ocr_result: Optional[OCRResult]
    extracted_fields: Dict[str, Any]
    metadata: Dict[str, Any]
    error: Optional[str]


def build_extraction_graph(ocr_engine: OCREngine, extractor: Any):
    """
    Build a LangGraph with:
      - ocr_node: run OCR (parallel Docling+EasyOCR when applicable)
      - extract_node: run extraction using ocr_result from state
    """
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError("langgraph is required. pip install langgraph")

    def ocr_node(state: ExtractionState) -> Dict[str, Any]:
        pdf_path = state["pdf_path"]
        output_dir = state["output_dir"]
        extractor.llm.unload_model()
        ocr_result = ocr_engine.process(pdf_path, output_dir)
        return {"ocr_result": ocr_result}

    def extract_node(state: ExtractionState) -> Dict[str, Any]:
        pdf_path = state["pdf_path"]
        output_dir = state["output_dir"]
        form_type = state.get("form_type")
        ocr_result = state.get("ocr_result")
        if ocr_result is None:
            return {"error": "Missing ocr_result in state"}
        result = extractor.extract(
            pdf_path=pdf_path,
            form_type=form_type,
            output_dir=output_dir,
            ocr_result=ocr_result,
        )
        return {
            "extracted_fields": result["extracted_fields"],
            "metadata": result["metadata"],
        }

    workflow = StateGraph(ExtractionState)
    workflow.add_node("ocr", ocr_node)
    workflow.add_node("extract", extract_node)
    workflow.set_entry_point("ocr")
    workflow.add_edge("ocr", "extract")
    workflow.add_edge("extract", END)
    return workflow.compile()


def run_extraction(
    pdf_path: Path,
    form_type: Optional[str],
    output_dir: Path,
    ocr_engine: OCREngine,
    extractor: Any,
    use_graph: bool = True,
) -> Dict[str, Any]:
    """
    Run extraction. If use_graph and langgraph available, run via LangGraph
    (OCR node then extract node; OCR uses parallel Docling+EasyOCR when enabled).
    Otherwise fall back to extractor.extract() (single call; parallel_ocr still used inside process).
    """
    if use_graph and LANGGRAPH_AVAILABLE:
        print("  [GRAPH] Running via LangGraph (ocr_node -> extract_node)")
        graph = build_extraction_graph(ocr_engine, extractor)
        state: ExtractionState = {
            "pdf_path": pdf_path,
            "output_dir": output_dir,
            "form_type": form_type,
        }
        for step in graph.stream(state):
            for key, value in step.items():
                state.update(value)
        if state.get("error"):
            return {
                "extracted_fields": {},
                "metadata": {"error": state["error"]},
            }
        return {
            "extracted_fields": state.get("extracted_fields", {}),
            "metadata": state.get("metadata", {}),
        }
    # Fallback: single call (still benefits from parallel_ocr inside ocr_engine.process)
    return extractor.extract(
        pdf_path=pdf_path,
        form_type=form_type,
        output_dir=output_dir,
        ocr_result=None,
    )
