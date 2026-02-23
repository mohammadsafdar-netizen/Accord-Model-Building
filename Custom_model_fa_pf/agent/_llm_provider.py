"""Shared LLM engine provider for agent tools."""

import logging
from Custom_model_fa_pf.config import (
    AGENT_MODEL, DEFAULT_OLLAMA_URL,
)

logger = logging.getLogger(__name__)

_engine = None


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


def reset_engine():
    """Reset the engine (for testing)."""
    global _engine
    _engine = None
