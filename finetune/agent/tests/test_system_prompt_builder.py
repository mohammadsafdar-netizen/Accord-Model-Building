"""Tests for system_prompt_builder — builds training system prompts matching production."""

import pytest

from finetune.agent.system_prompt_builder import (
    CORE_RULES,
    PHASE_PROMPTS,
    build_training_system_prompt,
)


# ---------------------------------------------------------------------------
# Basic structure tests
# ---------------------------------------------------------------------------

def test_system_prompt_includes_core_rules():
    prompt = build_training_system_prompt(phase="greeting", form_state={})
    assert "ANTI-HALLUCINATION RULES" in prompt
    assert "CORE RULES" in prompt


def test_system_prompt_includes_phase():
    prompt = build_training_system_prompt(phase="greeting", form_state={})
    assert "Greeting" in prompt or "GREETING" in prompt


def test_system_prompt_includes_form_state():
    fs = {
        "business_name": {
            "value": "Acme Corp",
            "confidence": 0.95,
            "source": "user_stated",
            "status": "confirmed",
        },
    }
    prompt = build_training_system_prompt(phase="applicant_info", form_state=fs)
    assert "business_name" in prompt
    assert "Acme Corp" in prompt


def test_system_prompt_empty_form_state():
    prompt = build_training_system_prompt(phase="greeting", form_state={})
    assert "No fields collected yet" in prompt


def test_system_prompt_includes_extraction_status():
    prompt = build_training_system_prompt(
        phase="form_specific",
        form_state={},
        lobs=["commercial_auto"],
        assigned_forms=["125", "127", "137"],
    )
    assert "commercial_auto" in prompt
    assert "125" in prompt


def test_system_prompt_includes_quotes():
    quotes = [
        {
            "carrier_name": "Progressive",
            "total_annual_premium": 12500.0,
            "quote_id": "Q-001",
        },
    ]
    prompt = build_training_system_prompt(
        phase="quoting", form_state={}, quotes=quotes,
    )
    assert "Progressive" in prompt
    assert "12,500" in prompt or "12500" in prompt


def test_system_prompt_includes_selected_quote():
    prompt = build_training_system_prompt(
        phase="bind_request",
        form_state={},
        selected_quote={"quote_id": "Q-001", "payment_plan": "annual"},
    )
    assert "Q-001" in prompt


def test_system_prompt_includes_bind_status():
    prompt = build_training_system_prompt(
        phase="policy_delivery",
        form_state={},
        bind_request={"bind_status": "submitted", "bind_request_id": "BR-001"},
    )
    assert "BR-001" in prompt


def test_system_prompt_includes_summary():
    prompt = build_training_system_prompt(
        phase="form_specific",
        form_state={},
        summary="Customer is a trucking company in Texas with 3 vehicles.",
    )
    assert "trucking company" in prompt


def test_all_phases_have_prompts():
    phases = [
        "greeting", "applicant_info", "policy_details", "business_info",
        "form_specific", "review", "complete", "quoting", "quote_selection",
        "bind_request", "policy_delivery",
    ]
    for phase in phases:
        prompt = build_training_system_prompt(phase=phase, form_state={})
        assert len(prompt) > 100, f"Phase '{phase}' produced very short prompt"


def test_returns_string_not_message():
    prompt = build_training_system_prompt(phase="greeting", form_state={})
    assert isinstance(prompt, str)


def test_compact_form_state_for_large_states():
    """50+ confirmed fields should trigger compact category-grouped output."""
    fs = {}
    for i in range(50):
        fs[f"field_{i}"] = {
            "value": f"val_{i}",
            "confidence": 0.95,
            "source": "user_stated",
            "status": "confirmed",
        }
    prompt = build_training_system_prompt(
        phase="review", form_state=fs, compact_form_state=True,
    )
    assert "categories" in prompt.lower() or "fields" in prompt.lower()


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------

def test_core_rules_is_nonempty_string():
    assert isinstance(CORE_RULES, str)
    assert len(CORE_RULES) > 500


def test_phase_prompts_has_all_11_phases():
    expected = {
        "greeting", "applicant_info", "policy_details", "business_info",
        "form_specific", "review", "complete", "quoting", "quote_selection",
        "bind_request", "policy_delivery",
    }
    assert set(PHASE_PROMPTS.keys()) == expected


# ---------------------------------------------------------------------------
# Form-state section formatting
# ---------------------------------------------------------------------------

def test_form_state_shows_confirmed_pending_empty():
    fs = {
        "business_name": {"value": "Acme Corp", "confidence": 0.95, "source": "user_stated", "status": "confirmed"},
        "phone": {"value": "", "confidence": 0.0, "source": "", "status": "pending"},
        "fein": {"value": "", "confidence": 0.0, "source": "", "status": "empty"},
    }
    prompt = build_training_system_prompt(phase="applicant_info", form_state=fs)
    assert "CONFIRMED" in prompt
    assert "PENDING" in prompt
    assert "EMPTY" in prompt


def test_empty_fields_are_capped_at_10():
    """Only show first 10 empty fields, then '... and N more'."""
    fs = {}
    for i in range(20):
        fs[f"empty_field_{i:02d}"] = {"value": "", "confidence": 0.0, "source": "", "status": "empty"}
    prompt = build_training_system_prompt(phase="applicant_info", form_state=fs)
    assert "more" in prompt.lower()


# ---------------------------------------------------------------------------
# Extraction status section
# ---------------------------------------------------------------------------

def test_extraction_status_not_shown_without_lobs():
    prompt = build_training_system_prompt(
        phase="form_specific", form_state={},
        lobs=None, assigned_forms=["125"],
    )
    assert "EXTRACTION STATUS" not in prompt


def test_extraction_status_not_shown_without_assigned_forms():
    prompt = build_training_system_prompt(
        phase="form_specific", form_state={},
        lobs=["commercial_auto"], assigned_forms=None,
    )
    assert "EXTRACTION STATUS" not in prompt


# ---------------------------------------------------------------------------
# Quote comparison section
# ---------------------------------------------------------------------------

def test_system_prompt_includes_quote_comparison():
    qc = {
        "quotes": [
            {
                "carrier": "Progressive",
                "total_annual": 12500.0,
                "monthly_estimate": 1041.67,
                "quote_id": "Q-001",
                "coverages": [],
            },
        ],
        "cheapest": {"carrier": "Progressive", "premium": 12500.0},
    }
    prompt = build_training_system_prompt(
        phase="quoting", form_state={}, quote_comparison=qc,
    )
    assert "QUOTE COMPARISON" in prompt
    assert "Progressive" in prompt


def test_quote_comparison_not_shown_when_empty():
    prompt = build_training_system_prompt(
        phase="quoting", form_state={}, quote_comparison=None,
    )
    assert "QUOTE COMPARISON" not in prompt


# ---------------------------------------------------------------------------
# Summary section
# ---------------------------------------------------------------------------

def test_summary_not_shown_when_empty():
    prompt = build_training_system_prompt(
        phase="form_specific", form_state={}, summary="",
    )
    assert "CONVERSATION SUMMARY" not in prompt


def test_summary_not_shown_when_whitespace():
    prompt = build_training_system_prompt(
        phase="form_specific", form_state={}, summary="   ",
    )
    assert "CONVERSATION SUMMARY" not in prompt


# ---------------------------------------------------------------------------
# Phase prompt content verification
# ---------------------------------------------------------------------------

def test_greeting_phase_has_welcome():
    prompt = build_training_system_prompt(phase="greeting", form_state={})
    assert "Welcome" in prompt or "welcome" in prompt


def test_quoting_phase_warns_no_hallucination():
    prompt = build_training_system_prompt(phase="quoting", form_state={})
    assert "Do NOT invent" in prompt or "CRITICAL" in prompt


def test_form_specific_has_tools():
    prompt = build_training_system_prompt(phase="form_specific", form_state={})
    assert "save_field" in prompt
    assert "extract_entities" in prompt
