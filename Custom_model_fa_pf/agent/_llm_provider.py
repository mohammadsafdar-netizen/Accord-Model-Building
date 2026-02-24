"""Shared LLM engine provider for agent tools."""

import logging
from Custom_model_fa_pf.config import (
    AGENT_MODEL, AGENT_VLM_MODEL, DEFAULT_OLLAMA_URL,
)

logger = logging.getLogger(__name__)

_engine = None
_vlm_engine = None


def get_llm_engine():
    """Get or create the shared LLM engine for tool calls.

    Uses AGENT_MODEL (same model as the agent's ChatOpenAI) to ensure
    the model is available in Ollama.
    """
    global _engine
    if _engine is None:
        from llm_engine import LLMEngine
        _engine = LLMEngine(
            model=AGENT_MODEL,
            base_url=DEFAULT_OLLAMA_URL,
            keep_models_loaded=True,
            structured_json=True,
        )
    return _engine


def get_vlm_engine():
    """Get or create a VLM-enabled LLM engine for document processing.

    Lazy-loaded on first use — avoids loading the VLM model at startup.
    Uses AGENT_VLM_MODEL (qwen3-vl:8b) for direct image→JSON extraction.
    """
    global _vlm_engine
    if _vlm_engine is None:
        from llm_engine import LLMEngine
        logger.info("Loading VLM engine with model=%s", AGENT_VLM_MODEL)
        _vlm_engine = LLMEngine(
            model=AGENT_MODEL,
            base_url=DEFAULT_OLLAMA_URL,
            vlm_extract_model=AGENT_VLM_MODEL,
            keep_models_loaded=True,
            structured_json=True,
            max_tokens=8192,
        )
    return _vlm_engine


def reset_engine():
    """Reset all engines (for testing)."""
    global _engine, _vlm_engine
    _engine = None
    _vlm_engine = None
