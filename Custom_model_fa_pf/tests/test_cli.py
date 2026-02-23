"""Tests for CLI chat interface."""

import pytest
from Custom_model_fa_pf.cli import format_agent_response, extract_text_from_messages


class TestFormatAgentResponse:
    def test_simple_text(self):
        result = format_agent_response("Hello, welcome to insurance intake.")
        assert "Hello" in result

    def test_strips_leading_whitespace(self):
        result = format_agent_response("  \n  Hello")
        assert result.startswith("Hello")


class TestExtractTextFromMessages:
    def test_extract_ai_message(self):
        from langchain_core.messages import AIMessage
        messages = [AIMessage(content="Hello there")]
        text = extract_text_from_messages(messages)
        assert "Hello there" in text

    def test_skip_tool_messages(self):
        from langchain_core.messages import AIMessage, ToolMessage
        messages = [
            AIMessage(content="", tool_calls=[{"id": "1", "name": "save_field", "args": {}}]),
            ToolMessage(content='{"status":"ok"}', tool_call_id="1"),
            AIMessage(content="Got it, saved."),
        ]
        text = extract_text_from_messages(messages)
        assert "Got it, saved." in text
        assert "status" not in text  # Tool message content excluded

    def test_empty_messages(self):
        text = extract_text_from_messages([])
        assert text == ""

    def test_skip_previous_messages(self):
        from langchain_core.messages import AIMessage, HumanMessage
        messages = [
            AIMessage(content="Old greeting"),
            HumanMessage(content="user said something"),
            AIMessage(content="New response"),
        ]
        # Skip first 2 messages (old greeting + user message)
        text = extract_text_from_messages(messages, skip=2)
        assert "New response" in text
        assert "Old greeting" not in text
