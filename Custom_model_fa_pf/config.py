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

# --- Agent configuration ---
LLM_BACKEND = "ollama"  # "vllm" or "ollama"
VLLM_BASE_URL = "http://localhost:8000/v1"
OLLAMA_OPENAI_URL = "http://localhost:11434/v1"  # Ollama's OpenAI-compatible endpoint

AGENT_MODEL = "qwen2.5:7b"  # Model name for agent LLM
AGENT_TEMPERATURE = 0.3
AGENT_MAX_TOKENS = 4096

AGENT_VLM_MODEL = "qwen3-vl:8b"
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}
SUPPORTED_DOC_EXTENSIONS = {".pdf"}
SUPPORTED_UPLOAD_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_DOC_EXTENSIONS

MAX_CONVERSATION_TURNS = 30
MAX_TOOL_CALLS_PER_TURN = 5
SUMMARIZE_AFTER_TURNS = 20
