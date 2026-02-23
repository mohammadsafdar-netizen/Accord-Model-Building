"""Tests for agent configuration constants."""

from Custom_model_fa_pf.config import (
    AGENT_MODEL,
    AGENT_TEMPERATURE,
    AGENT_MAX_TOKENS,
    VLLM_BASE_URL,
    OLLAMA_OPENAI_URL,
    LLM_BACKEND,
    MAX_CONVERSATION_TURNS,
    MAX_TOOL_CALLS_PER_TURN,
    SUMMARIZE_AFTER_TURNS,
)


def test_agent_model_is_string():
    assert isinstance(AGENT_MODEL, str)
    assert len(AGENT_MODEL) > 0


def test_temperature_range():
    assert 0.0 <= AGENT_TEMPERATURE <= 1.0


def test_max_tokens_positive():
    assert AGENT_MAX_TOKENS > 0


def test_backend_valid():
    assert LLM_BACKEND in ("vllm", "ollama")


def test_urls_are_strings():
    assert VLLM_BASE_URL.startswith("http")
    assert OLLAMA_OPENAI_URL.startswith("http")


def test_turn_limits():
    assert MAX_CONVERSATION_TURNS > 0
    assert MAX_TOOL_CALLS_PER_TURN > 0
    assert SUMMARIZE_AFTER_TURNS > 0
