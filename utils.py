#!/usr/bin/env python3
"""
Utilities: JSON cleanup, logging, image helpers
================================================
Shared helper functions for the best_project pipeline.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Set up a nice console logger."""
    logger = logging.getLogger("best_project")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def clean_json_text(text: str) -> str:
    """Strip markdown code fences and clean up LLM-produced JSON."""
    text = text.strip()
    # Remove ```json ... ``` wrappers
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def prune_empty_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively remove keys with None / empty string / empty dict / empty list values."""
    pruned: Dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() in ("", "null", "None"):
            continue
        if isinstance(value, dict):
            inner = prune_empty_fields(value)
            if inner:
                pruned[key] = inner
            continue
        if isinstance(value, list):
            cleaned = [v for v in value if v is not None and v != ""]
            if cleaned:
                pruned[key] = cleaned
            continue
        pruned[key] = value
    return pruned


def save_json(data: Any, path: str | Path, indent: int = 2) -> None:
    """Save data to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent, default=str)


def load_json(path: str | Path) -> Any:
    """Load data from a JSON file."""
    with open(path) as f:
        return json.load(f)
