"""Tests for agent prompt templates."""

import pytest
from Custom_model_fa_pf.agent.prompts import (
    INTAKE_SYSTEM_PROMPT,
    REFLECTION_PROMPT,
    SUMMARIZE_PROMPT,
    build_system_message,
    build_form_state_context,
)


class TestIntakeSystemPrompt:
    def test_prompt_is_string(self):
        assert isinstance(INTAKE_SYSTEM_PROMPT, str)
        assert len(INTAKE_SYSTEM_PROMPT) > 100

    def test_contains_identity(self):
        assert "insurance" in INTAKE_SYSTEM_PROMPT.lower()

    def test_contains_anti_hallucination(self):
        assert "NEVER" in INTAKE_SYSTEM_PROMPT
        assert "hallucin" in INTAKE_SYSTEM_PROMPT.lower() or "invent" in INTAKE_SYSTEM_PROMPT.lower()

    def test_contains_phase_instructions(self):
        assert "Applicant" in INTAKE_SYSTEM_PROMPT or "applicant" in INTAKE_SYSTEM_PROMPT
        assert "Policy" in INTAKE_SYSTEM_PROMPT

    def test_contains_tool_instructions(self):
        assert "save_field" in INTAKE_SYSTEM_PROMPT
        assert "validate_fields" in INTAKE_SYSTEM_PROMPT

    def test_contains_quoting_instructions(self):
        assert "build_quote_request" in INTAKE_SYSTEM_PROMPT
        assert "match_carriers" in INTAKE_SYSTEM_PROMPT
        assert "generate_quotes" in INTAKE_SYSTEM_PROMPT
        assert "compare_quotes" in INTAKE_SYSTEM_PROMPT
        assert "submit_bind_request" in INTAKE_SYSTEM_PROMPT

    def test_contains_quoting_phases(self):
        assert "Phase 6" in INTAKE_SYSTEM_PROMPT
        assert "Phase 7" in INTAKE_SYSTEM_PROMPT
        assert "Phase 8" in INTAKE_SYSTEM_PROMPT
        assert "Quoting" in INTAKE_SYSTEM_PROMPT
        assert "Binding" in INTAKE_SYSTEM_PROMPT


class TestBuildSystemMessage:
    def test_basic_message(self):
        msg = build_system_message(form_state={}, summary="")
        assert isinstance(msg.content, str)
        assert "insurance" in msg.content.lower()

    def test_includes_form_state(self):
        state = {"business_name": {"value": "Acme LLC", "status": "confirmed"}}
        msg = build_system_message(form_state=state, summary="")
        assert "Acme LLC" in msg.content

    def test_includes_summary(self):
        msg = build_system_message(form_state={}, summary="Customer is a trucking company.")
        assert "trucking company" in msg.content

    def test_no_summary_when_empty(self):
        msg = build_system_message(form_state={}, summary="")
        assert "CONVERSATION SUMMARY" not in msg.content

    def test_includes_phase(self):
        msg = build_system_message(form_state={}, summary="", phase="quoting")
        assert "quoting" in msg.content

    def test_includes_quotes(self):
        quotes = [{"carrier_name": "Progressive", "total_annual_premium": 15000, "quote_id": "Q1"}]
        msg = build_system_message(form_state={}, summary="", quotes=quotes)
        assert "Progressive" in msg.content
        assert "Q1" in msg.content

    def test_includes_selected_quote(self):
        selected = {"quote_id": "Q1", "payment_plan": "monthly"}
        msg = build_system_message(form_state={}, summary="", selected_quote=selected)
        assert "Q1" in msg.content
        assert "monthly" in msg.content

    def test_includes_bind_request(self):
        bind = {"bind_request_id": "BR-001", "bind_status": "pending_carrier_review"}
        msg = build_system_message(form_state={}, summary="", bind_request=bind)
        assert "BR-001" in msg.content
        assert "pending_carrier_review" in msg.content


class TestBuildFormStateContext:
    def test_empty_state(self):
        ctx = build_form_state_context({})
        assert "No fields collected yet" in ctx

    def test_with_fields(self):
        state = {
            "business_name": {"value": "Acme", "status": "confirmed", "confidence": 0.95},
            "effective_date": {"value": "", "status": "empty", "confidence": 0.0},
        }
        ctx = build_form_state_context(state)
        assert "Acme" in ctx
        assert "confirmed" in ctx.lower() or "CONFIRMED" in ctx


class TestReflectionPrompt:
    def test_is_string(self):
        assert isinstance(REFLECTION_PROMPT, str)
        assert len(REFLECTION_PROMPT) > 100

    def test_has_placeholders(self):
        assert "{response}" in REFLECTION_PROMPT
        assert "{form_state_summary}" in REFLECTION_PROMPT

    def test_contains_check_items(self):
        assert "Hallucinated" in REFLECTION_PROMPT
        assert "Multiple questions" in REFLECTION_PROMPT
        assert "Off-topic" in REFLECTION_PROMPT

    def test_contains_verdict_format(self):
        assert '"verdict": "pass"' in REFLECTION_PROMPT
        assert '"verdict": "revise"' in REFLECTION_PROMPT

    def test_format_works(self):
        """Prompt should format without errors."""
        formatted = REFLECTION_PROMPT.format(
            response="Hello, what is your business name?",
            form_state_summary="No fields collected yet.",
        )
        assert "Hello, what is your business name?" in formatted


class TestSummarizePrompt:
    def test_is_string(self):
        assert isinstance(SUMMARIZE_PROMPT, str)
        assert len(SUMMARIZE_PROMPT) > 100

    def test_has_placeholders(self):
        assert "{conversation_text}" in SUMMARIZE_PROMPT
        assert "{form_state_summary}" in SUMMARIZE_PROMPT

    def test_contains_instructions(self):
        assert "500 words" in SUMMARIZE_PROMPT
        assert "summary" in SUMMARIZE_PROMPT.lower()

    def test_format_works(self):
        formatted = SUMMARIZE_PROMPT.format(
            conversation_text="User: Hi\nAgent: Welcome!",
            form_state_summary="No fields collected yet.",
        )
        assert "User: Hi" in formatted
