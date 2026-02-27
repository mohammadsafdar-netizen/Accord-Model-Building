"""Tests for the quality validators for agent fine-tuning dataset."""

import json

import pytest

from finetune.agent.validate_dataset import (
    ValidationScore,
    validate_conversation,
    validate_dataset,
)
from finetune.agent.scenario_generator import generate_scenarios
from finetune.agent.assembler import assemble_conversation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_good_conversation():
    """Assemble a valid conversation from the first scenario."""
    scenarios = generate_scenarios()
    s = scenarios[0]
    return assemble_conversation(s), s


def _make_conversation_with_hallucinated_address():
    """Create a conversation where assistant saves an address not from user."""
    conv, scenario = _make_good_conversation()
    msgs = conv["messages"]
    # Find a save_field tool call and change its value to something not in user messages
    for i, msg in enumerate(msgs):
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if tc["function"]["name"] == "save_field":
                    args = json.loads(tc["function"]["arguments"])
                    args["value"] = "9999 Fake Blvd, Nowhere, XX 00000"
                    tc["function"]["arguments"] = json.dumps(args)
                    break
            break
    return conv, scenario


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidateConversation:
    """Tests for validate_conversation()."""

    def test_validates_good_conversation(self):
        conv, scenario = _make_good_conversation()
        score = validate_conversation(conv, scenario)
        assert isinstance(score, ValidationScore)
        assert score.composite >= 0.85  # Good conversations should score well

    def test_structural_checks_pass_for_good_conversation(self):
        conv, scenario = _make_good_conversation()
        score = validate_conversation(conv, scenario)
        assert score.structural >= 0.8

    def test_rejects_hallucinated_address(self):
        conv, scenario = _make_conversation_with_hallucinated_address()
        score = validate_conversation(conv, scenario)
        assert score.anti_hallucination < 1.0  # Should detect the hallucination

    def test_validation_score_has_all_fields(self):
        conv, scenario = _make_good_conversation()
        score = validate_conversation(conv, scenario)
        assert hasattr(score, "structural")
        assert hasattr(score, "phase_consistency")
        assert hasattr(score, "anti_hallucination")
        assert hasattr(score, "tool_ordering")
        assert hasattr(score, "behavioral")
        assert hasattr(score, "form_state_consistency")
        assert hasattr(score, "composite")
        assert hasattr(score, "issues")

    def test_composite_is_weighted_average(self):
        conv, _ = _make_good_conversation()
        score = validate_conversation(conv)
        expected = (
            0.15 * score.structural
            + 0.15 * score.phase_consistency
            + 0.25 * score.anti_hallucination
            + 0.15 * score.tool_ordering
            + 0.20 * score.behavioral
            + 0.10 * score.form_state_consistency
        )
        assert abs(score.composite - expected) < 0.01

    def test_detects_broken_tool_call_id(self):
        conv, _ = _make_good_conversation()
        msgs = conv["messages"]
        # Break a tool response ID
        for msg in msgs:
            if msg.get("role") == "tool":
                msg["tool_call_id"] = "broken_id_xyz"
                break
        score = validate_conversation(conv)
        assert score.structural < 1.0

    def test_detects_wrong_role_sequence(self):
        conv, _ = _make_good_conversation()
        # Put two user messages in a row
        msgs = conv["messages"]
        for i in range(1, len(msgs)):
            if msgs[i].get("role") == "user":
                msgs.insert(i + 1, {"role": "user", "content": "Extra user message"})
                break
        score = validate_conversation(conv)
        assert score.structural < 1.0

    def test_all_scores_between_0_and_1(self):
        conv, scenario = _make_good_conversation()
        score = validate_conversation(conv, scenario)
        for field in [
            "structural",
            "phase_consistency",
            "anti_hallucination",
            "tool_ordering",
            "behavioral",
            "form_state_consistency",
            "composite",
        ]:
            val = getattr(score, field)
            assert 0.0 <= val <= 1.0, f"{field} = {val} is out of range"


class TestValidateDataset:
    """Tests for validate_dataset()."""

    def test_validate_dataset(self):
        scenarios = generate_scenarios()[:5]
        convs = [assemble_conversation(s) for s in scenarios]
        report = validate_dataset(convs, scenarios)
        assert "total" in report
        assert report["total"] == 5
        assert "avg_composite" in report
        assert "included" in report
        assert "rejected" in report

    def test_validate_dataset_categories_sum(self):
        """included + flagged + rejected should equal total."""
        scenarios = generate_scenarios()[:3]
        convs = [assemble_conversation(s) for s in scenarios]
        report = validate_dataset(convs, scenarios)
        assert (
            report["included"] + report["flagged"] + report["rejected"]
            == report["total"]
        )

    def test_validate_dataset_avg_by_validator(self):
        """Report should include per-validator averages."""
        scenarios = generate_scenarios()[:3]
        convs = [assemble_conversation(s) for s in scenarios]
        report = validate_dataset(convs, scenarios)
        assert "avg_by_validator" in report
        for key in [
            "structural",
            "phase_consistency",
            "anti_hallucination",
            "tool_ordering",
            "behavioral",
            "form_state_consistency",
        ]:
            assert key in report["avg_by_validator"]
            val = report["avg_by_validator"][key]
            assert 0.0 <= val <= 1.0

    def test_validate_dataset_no_scenarios(self):
        """Should work when scenarios are not provided."""
        scenarios = generate_scenarios()[:3]
        convs = [assemble_conversation(s) for s in scenarios]
        report = validate_dataset(convs)
        assert report["total"] == 3


class TestEdgeCases:
    """Edge case tests for validators."""

    def test_empty_conversation(self):
        """A conversation with just a system message should not crash."""
        conv = {
            "messages": [{"role": "system", "content": "You are an assistant."}],
            "metadata": {"phases": ["greeting"]},
        }
        score = validate_conversation(conv)
        assert isinstance(score, ValidationScore)
        # It won't score perfectly but should not crash
        assert 0.0 <= score.composite <= 1.0

    def test_no_tool_calls_conversation(self):
        """A minimal greeting-only conversation with no tool calls."""
        conv = {
            "messages": [
                {"role": "system", "content": "You are an assistant."},
                {"role": "user", "content": "Hi there"},
                {"role": "assistant", "content": "Hello! How can I help?"},
            ],
            "metadata": {"phases": ["greeting"]},
        }
        score = validate_conversation(conv)
        assert isinstance(score, ValidationScore)
        assert 0.0 <= score.composite <= 1.0

    def test_invalid_tool_name_penalized(self):
        """Using an unknown tool name should penalize structural score."""
        conv = {
            "messages": [
                {"role": "system", "content": "You are an assistant."},
                {"role": "user", "content": "Hi there"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "tc_1",
                            "function": {
                                "name": "nonexistent_tool",
                                "arguments": "{}",
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "tc_1",
                    "content": '{"status": "ok"}',
                },
                {"role": "assistant", "content": "Done."},
            ],
            "metadata": {"phases": ["greeting"]},
        }
        score = validate_conversation(conv)
        assert score.structural < 1.0

    def test_state_key_in_tool_args_penalized(self):
        """Having 'state' key in tool call arguments should penalize structural."""
        conv = {
            "messages": [
                {"role": "system", "content": "You are an assistant."},
                {"role": "user", "content": "My name is Acme LLC"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "tc_1",
                            "function": {
                                "name": "save_field",
                                "arguments": json.dumps(
                                    {
                                        "field_name": "business_name",
                                        "value": "Acme LLC",
                                        "state": {"some": "data"},
                                    }
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "tc_1",
                    "content": json.dumps(
                        {"status": "saved", "field_name": "business_name"}
                    ),
                },
                {"role": "assistant", "content": "Got it, saved."},
            ],
            "metadata": {"phases": ["applicant_info"]},
        }
        score = validate_conversation(conv)
        assert score.structural < 1.0
