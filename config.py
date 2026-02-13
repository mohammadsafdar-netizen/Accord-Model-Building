"""
Central configuration for best_project — paths and env for usability and Eureka.
================================================================================
All paths can be overridden via environment variables so the same code runs
on any machine (e.g. Eureka) without code changes.

Environment variables:
  BEST_PROJECT_ROOT     — Project root (default: directory containing this file)
  BEST_PROJECT_TEST_DATA — Test data directory (default: <root>/test_data)
  BEST_PROJECT_OUTPUT   — Default output directory (default: <root>/test_output)
  BEST_PROJECT_SCHEMAS  — Schema JSON directory (default: <root>/schemas)
  BEST_PROJECT_RAG_GT   — Directory of ground-truth JSONs for RAG (default: same as TEST_DATA)
  OLLAMA_URL            — Ollama API base URL (default: http://localhost:11434)
  USE_GPU               — Set to 1 to use GPU for OCR when not passing --gpu
"""

from __future__ import annotations

import os
from pathlib import Path

# Project root: env or directory containing this file
_ROOT = os.environ.get("BEST_PROJECT_ROOT")
if _ROOT:
    PROJECT_ROOT = Path(_ROOT).resolve()
else:
    PROJECT_ROOT = Path(__file__).resolve().parent

TEST_DATA_DIR = Path(
    os.environ.get("BEST_PROJECT_TEST_DATA", str(PROJECT_ROOT / "test_data"))
).resolve()

OUTPUT_DIR = Path(
    os.environ.get("BEST_PROJECT_OUTPUT", str(PROJECT_ROOT / "test_output"))
).resolve()

SCHEMAS_DIR = Path(
    os.environ.get("BEST_PROJECT_SCHEMAS", str(PROJECT_ROOT / "schemas"))
).resolve()

# RAG few-shot examples: directory of ground-truth JSONs (form subdirs with *.json)
RAG_GT_DIR = Path(
    os.environ.get("BEST_PROJECT_RAG_GT", str(TEST_DATA_DIR))
).resolve()

OLLAMA_URL_DEFAULT = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# When set to "1" or "true", CLI defaults to GPU for OCR (same as --gpu)
USE_GPU_DEFAULT = os.environ.get("USE_GPU", "").strip().lower() in ("1", "true", "yes")


def get_schemas_dir(override: Path | None = None) -> Path:
    """Return schemas directory (override or config)."""
    if override is not None:
        return Path(override)
    return SCHEMAS_DIR


def get_test_data_dir(override: Path | None = None) -> Path:
    """Return test data directory (override or config)."""
    if override is not None:
        return Path(override)
    return TEST_DATA_DIR


def get_output_dir(override: Path | None = None) -> Path:
    """Return default output directory (override or config)."""
    if override is not None:
        return Path(override)
    return OUTPUT_DIR


def get_rag_gt_dir(override: Path | None = None) -> Path:
    """Return directory of ground-truth JSONs for RAG (override or config)."""
    if override is not None:
        return Path(override)
    return RAG_GT_DIR
