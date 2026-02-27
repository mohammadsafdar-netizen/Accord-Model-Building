"""Tests for the conversation assembler module."""

import json

import pytest

from finetune.agent.assembler import assemble_conversation, assemble_windowed_conversations
from finetune.agent.scenario_generator import generate_scenarios


def _get_scenario(delivery_style="conversational", multi_lob=False):
    scenarios = generate_scenarios()
    for s in scenarios:
        if s.delivery_style == delivery_style:
            if multi_lob and len(s.lobs) > 1:
                return s
            elif not multi_lob and len(s.lobs) == 1:
                return s
    return scenarios[0]


class TestAssembledConversationStructure:
    """Tests for basic conversation structure."""

    def test_assembled_conversation_has_messages_and_metadata(self):
        s = _get_scenario()
        conv = assemble_conversation(s)
        assert "messages" in conv
        assert "metadata" in conv
        assert isinstance(conv["messages"], list)
        assert isinstance(conv["metadata"], dict)

    def test_first_message_is_system(self):
        s = _get_scenario()
        conv = assemble_conversation(s)
        assert conv["messages"][0]["role"] == "system"
        assert len(conv["messages"][0]["content"]) > 100

    def test_second_message_is_user(self):
        s = _get_scenario()
        conv = assemble_conversation(s)
        assert conv["messages"][1]["role"] == "user"

    def test_last_message_is_assistant_with_content(self):
        s = _get_scenario()
        conv = assemble_conversation(s)
        assert conv["messages"][-1]["role"] == "assistant"
        assert conv["messages"][-1]["content"] is not None

    def test_system_message_only_at_position_zero(self):
        """System message should appear exactly once, at index 0."""
        s = _get_scenario()
        conv = assemble_conversation(s)
        system_msgs = [
            i for i, m in enumerate(conv["messages"]) if m["role"] == "system"
        ]
        assert system_msgs == [0]


class TestToolCallStructure:
    """Tests for tool call / tool response pairing."""

    def test_tool_calls_have_matching_responses(self):
        s = _get_scenario()
        conv = assemble_conversation(s)
        msgs = conv["messages"]
        for i, msg in enumerate(msgs):
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    # Find the matching tool response
                    found = False
                    for j in range(i + 1, min(i + 50, len(msgs))):
                        if (
                            msgs[j].get("role") == "tool"
                            and msgs[j].get("tool_call_id") == tc["id"]
                        ):
                            found = True
                            break
                    assert found, f"No tool response for call {tc['id']}"

    def test_tool_call_message_has_none_content(self):
        """Assistant messages with tool_calls should have content=None."""
        s = _get_scenario()
        conv = assemble_conversation(s)
        for msg in conv["messages"]:
            if msg.get("tool_calls"):
                assert msg["content"] is None

    def test_tool_response_content_is_json_string(self):
        s = _get_scenario()
        conv = assemble_conversation(s)
        for msg in conv["messages"]:
            if msg.get("role") == "tool":
                json.loads(msg["content"])  # Should be valid JSON

    def test_tool_call_has_required_fields(self):
        """Each tool_call must have id, type, and function keys."""
        s = _get_scenario()
        conv = assemble_conversation(s)
        for msg in conv["messages"]:
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    assert "id" in tc
                    assert tc["type"] == "function"
                    assert "function" in tc
                    assert "name" in tc["function"]
                    assert "arguments" in tc["function"]


class TestMetadata:
    """Tests for metadata fields."""

    def test_metadata_has_required_fields(self):
        s = _get_scenario()
        conv = assemble_conversation(s)
        meta = conv["metadata"]
        assert "scenario_id" in meta
        assert "difficulty" in meta
        assert meta["difficulty"] in ("easy", "medium", "hard")
        assert "curriculum_phase" in meta
        assert meta["curriculum_phase"] in (1, 2, 3)
        assert "phases" in meta
        assert "tools_used" in meta
        assert "turn_count" in meta
        assert "delivery_style" in meta
        assert "user_persona" in meta

    def test_easy_scenario_classification(self):
        s = _get_scenario(delivery_style="conversational", multi_lob=False)
        conv = assemble_conversation(s)
        assert conv["metadata"]["difficulty"] == "easy"
        assert conv["metadata"]["curriculum_phase"] == 1

    def test_hard_scenario_classification(self):
        s = _get_scenario(delivery_style="bulk_email", multi_lob=True)
        if s is not None:
            conv = assemble_conversation(s)
            assert conv["metadata"]["difficulty"] == "hard"
            assert conv["metadata"]["curriculum_phase"] == 3

    def test_metadata_scenario_id_matches(self):
        s = _get_scenario()
        conv = assemble_conversation(s)
        assert conv["metadata"]["scenario_id"] == s.scenario_id


class TestWindowedConversations:
    """Tests for the windowed conversation generator."""

    def test_windowed_conversations_returns_list(self):
        s = _get_scenario()
        windows = assemble_windowed_conversations(s, window_size=8, overlap=2)
        assert isinstance(windows, list)

    def test_each_window_starts_with_system(self):
        s = _get_scenario()
        windows = assemble_windowed_conversations(s, window_size=8, overlap=2)
        for w in windows:
            assert w["messages"][0]["role"] == "system"

    def test_each_window_ends_with_assistant(self):
        s = _get_scenario()
        windows = assemble_windowed_conversations(s, window_size=8, overlap=2)
        for w in windows:
            assert w["messages"][-1]["role"] == "assistant"
            assert w["messages"][-1]["content"] is not None

    def test_short_conversation_produces_single_window(self):
        """A conversation shorter than window_size should give one window."""
        s = _get_scenario(delivery_style="bulk_email")
        windows = assemble_windowed_conversations(s, window_size=50, overlap=2)
        assert len(windows) == 1


class TestMultiScenarioRobustness:
    """Run across multiple scenarios to check for crashes / invariant violations."""

    def test_no_none_content_in_final_assistant(self):
        """Every conversation must end with assistant message that has content."""
        scenarios = generate_scenarios()[:10]
        for s in scenarios:
            conv = assemble_conversation(s)
            assert conv["messages"][-1]["content"] is not None, (
                f"Scenario {s.scenario_id} ended with None content"
            )

    def test_all_delivery_styles_assemble(self):
        """Each delivery style should produce a valid conversation."""
        scenarios = generate_scenarios()
        seen_styles = set()
        for s in scenarios:
            if s.delivery_style not in seen_styles:
                seen_styles.add(s.delivery_style)
                conv = assemble_conversation(s)
                assert conv["messages"][0]["role"] == "system"
                assert conv["messages"][-1]["role"] == "assistant"
                assert conv["messages"][-1]["content"] is not None
            if len(seen_styles) >= 3:
                break

    def test_deterministic_with_same_seed(self):
        """Same scenario + seed should produce identical output."""
        s = _get_scenario()
        conv1 = assemble_conversation(s, seed=123)
        conv2 = assemble_conversation(s, seed=123)
        assert len(conv1["messages"]) == len(conv2["messages"])
        for m1, m2 in zip(conv1["messages"], conv2["messages"]):
            assert m1["role"] == m2["role"]
            assert m1.get("content") == m2.get("content")
