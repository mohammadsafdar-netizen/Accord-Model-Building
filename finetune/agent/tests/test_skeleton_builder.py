"""Tests for the conversation skeleton builder."""

import pytest
from finetune.agent.scenario_generator import generate_scenarios, ConversationScenario
from finetune.agent.skeleton_builder import build_skeleton, TurnSkeleton, PHASE_TOOLS, PHASE_ORDER


def _make_simple_scenario():
    """Create a minimal scenario for testing."""
    scenarios = generate_scenarios()
    # Find a single-LOB conversational scenario
    for s in scenarios:
        if len(s.lobs) == 1 and s.delivery_style == "conversational":
            return s
    return scenarios[0]


def _make_bulk_scenario():
    """Create a bulk-style scenario for testing."""
    scenarios = generate_scenarios()
    for s in scenarios:
        if s.delivery_style == "bulk_email":
            return s
    return scenarios[0]


def _make_mixed_scenario():
    """Create a mixed-style scenario for testing."""
    scenarios = generate_scenarios()
    for s in scenarios:
        if s.delivery_style == "mixed":
            return s
    return scenarios[0]


def test_skeleton_returns_list_of_turn_skeletons():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    assert isinstance(skeleton, list)
    assert all(isinstance(t, TurnSkeleton) for t in skeleton)
    assert len(skeleton) >= 8  # Minimum reasonable conversation


def test_skeleton_starts_with_greeting():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    assert skeleton[0].phase == "greeting"


def test_skeleton_phase_order():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    phases = [t.phase for t in skeleton]
    # Check monotonic (no backward transitions)
    for i in range(1, len(phases)):
        assert PHASE_ORDER.index(phases[i]) >= PHASE_ORDER.index(phases[i - 1]), \
            f"Backward transition: {phases[i - 1]} -> {phases[i]}"


def test_skeleton_includes_review():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    phases = [t.phase for t in skeleton]
    assert "review" in phases


def test_skeleton_tools_are_phase_scoped():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    for turn in skeleton:
        for tool in turn.tools_to_call:
            assert tool in PHASE_TOOLS[turn.phase], \
                f"Tool '{tool}' not allowed in phase '{turn.phase}'. Allowed: {PHASE_TOOLS[turn.phase]}"


def test_conversational_skeleton_length():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    assert 10 <= len(skeleton) <= 30


def test_bulk_skeleton_shorter():
    scenario = _make_bulk_scenario()
    skeleton = build_skeleton(scenario)
    assert 6 <= len(skeleton) <= 15


def test_skeleton_ends_with_policy_delivery():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    assert skeleton[-1].phase == "policy_delivery"


def test_skeleton_has_quoting_phase():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    phases = [t.phase for t in skeleton]
    assert "quoting" in phases
    assert "quote_selection" in phases


def test_greeting_turn_has_no_tools_and_no_fields():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    greeting = skeleton[0]
    assert greeting.tools_to_call == []
    assert greeting.user_fields == {}


def test_all_delivery_styles_produce_valid_skeletons():
    """All 3 delivery styles should produce phase-ordered, phase-scoped skeletons."""
    for style_finder in (_make_simple_scenario, _make_bulk_scenario, _make_mixed_scenario):
        scenario = style_finder()
        skeleton = build_skeleton(scenario)
        # Phase order
        phases = [t.phase for t in skeleton]
        for i in range(1, len(phases)):
            assert PHASE_ORDER.index(phases[i]) >= PHASE_ORDER.index(phases[i - 1]), \
                f"[{scenario.delivery_style}] Backward: {phases[i - 1]} -> {phases[i]}"
        # Phase-scoped tools
        for turn in skeleton:
            for tool in turn.tools_to_call:
                assert tool in PHASE_TOOLS[turn.phase], \
                    f"[{scenario.delivery_style}] Tool '{tool}' not in phase '{turn.phase}'"
        # Starts greeting, ends delivery
        assert phases[0] == "greeting"
        assert phases[-1] == "policy_delivery"


def test_skeleton_contains_business_name_field():
    """The skeleton should contain the scenario's business name somewhere."""
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    all_fields = {}
    for turn in skeleton:
        all_fields.update(turn.user_fields)
    assert "business_name" in all_fields
    assert all_fields["business_name"] == scenario.business["business_name"]


def test_skeleton_contains_vehicle_fields_for_auto_lob():
    """Scenarios with commercial_auto should have vehicle fields."""
    scenarios = generate_scenarios()
    auto_scenario = None
    for s in scenarios:
        if "commercial_auto" in s.lobs and s.vehicles and s.delivery_style == "conversational":
            auto_scenario = s
            break
    if auto_scenario is None:
        pytest.skip("No commercial_auto conversational scenario found")
    skeleton = build_skeleton(auto_scenario)
    all_fields = {}
    for turn in skeleton:
        all_fields.update(turn.user_fields)
    assert any(k.startswith("vehicle_1_") for k in all_fields), \
        f"Expected vehicle_1_* fields, got: {sorted(all_fields.keys())}"


def test_skeleton_deterministic_with_same_seed():
    """Same scenario + same seed should produce identical skeletons."""
    scenario = _make_simple_scenario()
    s1 = build_skeleton(scenario, seed=42)
    s2 = build_skeleton(scenario, seed=42)
    assert len(s1) == len(s2)
    for t1, t2 in zip(s1, s2):
        assert t1.phase == t2.phase
        assert t1.user_fields == t2.user_fields
        assert t1.tools_to_call == t2.tools_to_call
        assert t1.action == t2.action


def test_skeleton_different_seeds_may_differ():
    """Different seeds should (usually) produce different skeletons."""
    scenario = _make_simple_scenario()
    s1 = build_skeleton(scenario, seed=42)
    s2 = build_skeleton(scenario, seed=999)
    # At minimum the overall structure is the same (both valid), but details may differ
    assert len(s1) >= 8
    assert len(s2) >= 8


def test_mixed_skeleton_length():
    scenario = _make_mixed_scenario()
    skeleton = build_skeleton(scenario)
    assert 8 <= len(skeleton) <= 22


def test_bulk_skeleton_has_bulk_turn():
    """Bulk style should have a turn where many fields are provided at once."""
    scenario = _make_bulk_scenario()
    skeleton = build_skeleton(scenario)
    # Find the largest user_fields turn
    max_fields = max(len(t.user_fields) for t in skeleton)
    assert max_fields >= 5, f"Bulk style should have a turn with 5+ fields, max was {max_fields}"


def test_bind_request_phase_present():
    scenario = _make_simple_scenario()
    skeleton = build_skeleton(scenario)
    phases = [t.phase for t in skeleton]
    assert "bind_request" in phases


# ---------------------------------------------------------------------------
# Document upload turns
# ---------------------------------------------------------------------------


def _make_scenario_with_uploads():
    """Find a scenario that has document_uploads."""
    scenarios = generate_scenarios()
    for s in scenarios:
        if s.document_uploads:
            return s
    # Fallback: should not happen with 500+ scenarios at 40%
    pytest.skip("No scenario with document_uploads found")


def test_skeleton_includes_document_upload_turns():
    """Scenarios with document_uploads should produce process_document turns."""
    scenario = _make_scenario_with_uploads()
    skeleton = build_skeleton(scenario)
    doc_turns = [t for t in skeleton if t.action == "process_document"]
    assert len(doc_turns) >= 1
    for dt in doc_turns:
        assert "process_document" in dt.tools_to_call
        assert dt.phase == "form_specific"


def test_document_upload_turns_have_upload_data():
    """Document upload turns should carry _document_upload in user_fields."""
    scenario = _make_scenario_with_uploads()
    skeleton = build_skeleton(scenario)
    doc_turns = [t for t in skeleton if t.action == "process_document"]
    for dt in doc_turns:
        assert "_document_upload" in dt.user_fields
        upload = dt.user_fields["_document_upload"]
        assert "document_type" in upload
        assert "file_path" in upload
        assert "extracted_fields" in upload


def test_document_upload_turns_count_matches_scenario():
    """Number of process_document turns should match document_uploads count."""
    scenario = _make_scenario_with_uploads()
    skeleton = build_skeleton(scenario)
    doc_turns = [t for t in skeleton if t.action == "process_document"]
    assert len(doc_turns) == len(scenario.document_uploads)


def test_document_upload_turns_are_phase_scoped():
    """Document upload turns should only use tools allowed in form_specific."""
    scenario = _make_scenario_with_uploads()
    skeleton = build_skeleton(scenario)
    doc_turns = [t for t in skeleton if t.action == "process_document"]
    for dt in doc_turns:
        for tool in dt.tools_to_call:
            assert tool in PHASE_TOOLS["form_specific"], (
                f"Tool '{tool}' not allowed in form_specific phase"
            )
