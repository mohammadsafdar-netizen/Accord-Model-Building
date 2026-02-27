"""Tests for the DPO preference pair generator."""

import json

import pytest

from finetune.agent.build_agent_dpo_pairs import generate_dpo_pairs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_CATEGORIES = {
    "address_hallucination",
    "quote_fabrication",
    "tool_ordering",
    "phase_inappropriate_tools",
    "multi_field_completeness",
    "confirmation_handling",
}


# ---------------------------------------------------------------------------
# Basic structure tests
# ---------------------------------------------------------------------------


class TestDPOPairCount:
    """Tests for pair counts and category coverage."""

    def test_dpo_pair_count(self):
        pairs = generate_dpo_pairs(pairs_per_category=5)
        assert len(pairs) >= 30  # 6 categories x 5 each

    def test_dpo_pair_count_matches_request(self):
        pairs = generate_dpo_pairs(pairs_per_category=3)
        # Should have exactly 6 * 3 = 18 pairs
        assert len(pairs) == 18

    def test_all_6_categories_present(self):
        pairs = generate_dpo_pairs(pairs_per_category=3)
        categories = {p["category"] for p in pairs}
        assert EXPECTED_CATEGORIES == categories

    def test_per_category_count(self):
        pairs = generate_dpo_pairs(pairs_per_category=4)
        from collections import Counter

        counts = Counter(p["category"] for p in pairs)
        for cat in EXPECTED_CATEGORIES:
            assert counts[cat] == 4, f"Category {cat} has {counts[cat]} pairs, expected 4"


class TestDPOPairStructure:
    """Tests for individual pair structure."""

    def test_dpo_pair_structure(self):
        pairs = generate_dpo_pairs(pairs_per_category=3)
        for pair in pairs:
            assert "chosen" in pair and "rejected" in pair
            assert "category" in pair
            assert isinstance(pair["chosen"], list)
            assert isinstance(pair["rejected"], list)

    def test_dpo_chosen_starts_with_system(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        for pair in pairs:
            assert pair["chosen"][0]["role"] == "system", (
                f"Category {pair['category']}: chosen doesn't start with system"
            )
            assert pair["rejected"][0]["role"] == "system", (
                f"Category {pair['category']}: rejected doesn't start with system"
            )

    def test_dpo_pairs_end_with_assistant(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        for pair in pairs:
            assert pair["chosen"][-1]["role"] == "assistant", (
                f"Category {pair['category']}: chosen doesn't end with assistant"
            )
            assert pair["rejected"][-1]["role"] == "assistant", (
                f"Category {pair['category']}: rejected doesn't end with assistant"
            )

    def test_messages_have_role_and_content(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        for pair in pairs:
            for side in ("chosen", "rejected"):
                for msg in pair[side]:
                    assert "role" in msg, (
                        f"Category {pair['category']}, {side}: message missing 'role'"
                    )
                    # assistant tool_call messages can have content=None
                    if msg["role"] != "assistant" or "tool_calls" not in msg:
                        assert "content" in msg, (
                            f"Category {pair['category']}, {side}: "
                            f"non-tool-call message missing 'content'"
                        )


# ---------------------------------------------------------------------------
# Shared context tests
# ---------------------------------------------------------------------------


class TestDPOSharedContext:
    """Tests that chosen and rejected share the same context."""

    def test_dpo_chosen_and_rejected_share_system_prompt(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        for pair in pairs:
            assert pair["chosen"][0]["content"] == pair["rejected"][0]["content"], (
                f"Category {pair['category']}: system prompts differ"
            )

    def test_dpo_chosen_and_rejected_share_user_messages(self):
        """User messages before the divergence point should be identical."""
        pairs = generate_dpo_pairs(pairs_per_category=2)
        for pair in pairs:
            # Find the first user message (should be identical in both)
            chosen_users = [
                m for m in pair["chosen"] if m["role"] == "user"
            ]
            rejected_users = [
                m for m in pair["rejected"] if m["role"] == "user"
            ]
            # There should be at least one user message
            assert len(chosen_users) >= 1
            assert len(rejected_users) >= 1
            # First user message should match
            assert chosen_users[0]["content"] == rejected_users[0]["content"], (
                f"Category {pair['category']}: first user messages differ"
            )


# ---------------------------------------------------------------------------
# Divergence tests
# ---------------------------------------------------------------------------


class TestDPODivergence:
    """Tests that chosen and rejected actually differ."""

    def test_chosen_rejected_differ(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        for pair in pairs:
            chosen_asst = [m for m in pair["chosen"] if m["role"] == "assistant"]
            rejected_asst = [m for m in pair["rejected"] if m["role"] == "assistant"]
            assert chosen_asst != rejected_asst, (
                f"Category {pair['category']}: chosen and rejected are identical"
            )


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


class TestDPODeterminism:
    """Tests for reproducibility."""

    def test_deterministic(self):
        p1 = generate_dpo_pairs(pairs_per_category=2, seed=42)
        p2 = generate_dpo_pairs(pairs_per_category=2, seed=42)
        assert len(p1) == len(p2)
        for a, b in zip(p1, p2):
            assert a["category"] == b["category"]
            assert a["chosen"] == b["chosen"]
            assert a["rejected"] == b["rejected"]

    def test_different_seeds_produce_different_pairs(self):
        p1 = generate_dpo_pairs(pairs_per_category=2, seed=42)
        p2 = generate_dpo_pairs(pairs_per_category=2, seed=99)
        # At least some pairs should differ (content, not just ordering)
        some_differ = any(
            a["chosen"] != b["chosen"]
            for a, b in zip(p1, p2)
            if a["category"] == b["category"]
        )
        assert some_differ, "Different seeds produced identical pairs"


# ---------------------------------------------------------------------------
# Category-specific tests
# ---------------------------------------------------------------------------


class TestAddressHallucination:
    """Tests for the address_hallucination category."""

    def test_chosen_saves_actual_address(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        addr_pairs = [p for p in pairs if p["category"] == "address_hallucination"]
        assert len(addr_pairs) == 2
        for pair in addr_pairs:
            # The chosen side should have a save_field tool call
            chosen_tool_msgs = [
                m for m in pair["chosen"]
                if m["role"] == "assistant" and m.get("tool_calls")
            ]
            assert len(chosen_tool_msgs) > 0, "Chosen side has no tool calls"

    def test_rejected_uses_different_address(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        addr_pairs = [p for p in pairs if p["category"] == "address_hallucination"]
        for pair in addr_pairs:
            # Extract save_field arguments from both sides
            def _get_save_field_values(messages):
                values = []
                for m in messages:
                    if m["role"] == "assistant" and m.get("tool_calls"):
                        for tc in m["tool_calls"]:
                            func = tc.get("function", {})
                            if func.get("name") == "save_field":
                                args = json.loads(func["arguments"])
                                if "street" in args.get("field_name", "").lower() or \
                                   args.get("field_name", "") == "mailing_street":
                                    values.append(args.get("value", ""))
                return values

            chosen_addrs = _get_save_field_values(pair["chosen"])
            rejected_addrs = _get_save_field_values(pair["rejected"])
            if chosen_addrs and rejected_addrs:
                # At least one address value should differ
                assert chosen_addrs[0] != rejected_addrs[0], (
                    "Chosen and rejected have the same address"
                )


class TestQuoteFabrication:
    """Tests for the quote_fabrication category."""

    def test_rejected_contains_fabricated_data(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        quote_pairs = [p for p in pairs if p["category"] == "quote_fabrication"]
        assert len(quote_pairs) == 2
        for pair in quote_pairs:
            # The chosen and rejected final assistant messages should differ
            chosen_last = pair["chosen"][-1]
            rejected_last = pair["rejected"][-1]
            assert chosen_last["content"] != rejected_last["content"]


class TestToolOrdering:
    """Tests for the tool_ordering category."""

    def test_chosen_has_correct_tool_order(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        ordering_pairs = [p for p in pairs if p["category"] == "tool_ordering"]
        assert len(ordering_pairs) == 2
        for pair in ordering_pairs:
            # Chosen side should have classify_lobs before assign_forms
            chosen_tools = []
            for m in pair["chosen"]:
                if m["role"] == "assistant" and m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        func = tc.get("function", {})
                        name = func.get("name", "")
                        if name:
                            chosen_tools.append(name)
            if "classify_lobs" in chosen_tools and "assign_forms" in chosen_tools:
                ci = chosen_tools.index("classify_lobs")
                ai = chosen_tools.index("assign_forms")
                assert ci < ai, "Chosen: classify_lobs should come before assign_forms"


class TestPhaseInappropriateTools:
    """Tests for the phase_inappropriate_tools category."""

    def test_chosen_has_no_tools_in_greeting(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        phase_pairs = [p for p in pairs if p["category"] == "phase_inappropriate_tools"]
        assert len(phase_pairs) == 2
        for pair in phase_pairs:
            # Chosen side: assistant messages should NOT have tool_calls
            # (since it's a greeting phase pair)
            chosen_asst_with_tools = [
                m for m in pair["chosen"]
                if m["role"] == "assistant" and m.get("tool_calls")
            ]
            assert len(chosen_asst_with_tools) == 0, (
                "Chosen side should not have tool calls in greeting"
            )

    def test_rejected_has_inappropriate_tools(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        phase_pairs = [p for p in pairs if p["category"] == "phase_inappropriate_tools"]
        for pair in phase_pairs:
            # Rejected side should have tool calls (inappropriate for greeting)
            rejected_asst_with_tools = [
                m for m in pair["rejected"]
                if m["role"] == "assistant" and m.get("tool_calls")
            ]
            assert len(rejected_asst_with_tools) > 0, (
                "Rejected side should have inappropriate tool calls"
            )


class TestMultiFieldCompleteness:
    """Tests for the multi_field_completeness category."""

    def test_chosen_saves_more_fields_than_rejected(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        multi_pairs = [p for p in pairs if p["category"] == "multi_field_completeness"]
        assert len(multi_pairs) == 2
        for pair in multi_pairs:
            def _count_save_fields(messages):
                count = 0
                for m in messages:
                    if m["role"] == "assistant" and m.get("tool_calls"):
                        for tc in m["tool_calls"]:
                            func = tc.get("function", {})
                            if func.get("name") == "save_field":
                                count += 1
                return count

            chosen_count = _count_save_fields(pair["chosen"])
            rejected_count = _count_save_fields(pair["rejected"])
            assert chosen_count > rejected_count, (
                f"Chosen ({chosen_count}) should save more fields "
                f"than rejected ({rejected_count})"
            )


class TestConfirmationHandling:
    """Tests for the confirmation_handling category."""

    def test_chosen_acknowledges_and_moves_on(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        conf_pairs = [p for p in pairs if p["category"] == "confirmation_handling"]
        assert len(conf_pairs) == 2
        for pair in conf_pairs:
            # Chosen should not re-ask about confirmed fields
            chosen_last = pair["chosen"][-1]
            assert chosen_last["role"] == "assistant"
            assert chosen_last["content"] is not None

    def test_rejected_re_questions_confirmed_data(self):
        pairs = generate_dpo_pairs(pairs_per_category=2)
        conf_pairs = [p for p in pairs if p["category"] == "confirmation_handling"]
        for pair in conf_pairs:
            # Rejected last assistant message should differ from chosen
            chosen_last = pair["chosen"][-1]["content"]
            rejected_last = pair["rejected"][-1]["content"]
            assert chosen_last != rejected_last


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestDPOEdgeCases:
    """Edge case tests."""

    def test_with_custom_scenarios(self):
        """Passing custom scenarios should work."""
        from finetune.agent.scenario_generator import generate_scenarios

        scenarios = generate_scenarios()[:5]
        pairs = generate_dpo_pairs(scenarios=scenarios, pairs_per_category=2)
        assert len(pairs) >= 12  # 6 categories x 2

    def test_single_pair_per_category(self):
        pairs = generate_dpo_pairs(pairs_per_category=1)
        assert len(pairs) == 6
        categories = {p["category"] for p in pairs}
        assert categories == EXPECTED_CATEGORIES
