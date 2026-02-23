"""Configuration and path setup for the Form Assignment & Pre-Filling module."""

import sys
from pathlib import Path

# Project root (parent of Custom_model_fa_pf/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Module paths
MODULE_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = ROOT / "schemas"
FORM_TEMPLATES_DIR = MODULE_DIR / "form_templates"
OUTPUT_DIR = MODULE_DIR / "output"

# Default settings
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_TIMEOUT = 300
DEFAULT_MAX_TOKENS = 4096
