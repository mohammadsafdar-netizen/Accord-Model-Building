"""Tests for agent state schema."""

import pytest
from Custom_model_fa_pf.agent.state import IntakePhase, IntakeState


class TestIntakePhase:
    def test_all_phases_exist(self):
        phases = [
            IntakePhase.GREETING,
            IntakePhase.APPLICANT_INFO,
            IntakePhase.POLICY_DETAILS,
            IntakePhase.BUSINESS_INFO,
            IntakePhase.FORM_SPECIFIC,
            IntakePhase.REVIEW,
            IntakePhase.COMPLETE,
        ]
        assert len(phases) == 7

    def test_phase_values_are_strings(self):
        assert IntakePhase.GREETING.value == "greeting"
        assert IntakePhase.COMPLETE.value == "complete"

    def test_phase_ordering(self):
        """Phases should be orderable by their position in the intake flow."""
        order = list(IntakePhase)
        assert order[0] == IntakePhase.GREETING
        assert order[-1] == IntakePhase.COMPLETE

    def test_next_phase(self):
        assert IntakePhase.next_phase(IntakePhase.GREETING) == IntakePhase.APPLICANT_INFO
        assert IntakePhase.next_phase(IntakePhase.REVIEW) == IntakePhase.COMPLETE
        assert IntakePhase.next_phase(IntakePhase.COMPLETE) == IntakePhase.COMPLETE


class TestIntakeState:
    def test_state_is_typed_dict(self):
        """IntakeState should be a TypedDict for LangGraph."""
        assert hasattr(IntakeState, "__annotations__")
        annotations = IntakeState.__annotations__
        assert "messages" in annotations
        assert "phase" in annotations
        assert "form_state" in annotations
        assert "session_id" in annotations

    def test_state_has_message_reducer(self):
        """The messages field should use add_messages reducer."""
        from typing import get_type_hints
        hints = get_type_hints(IntakeState, include_extras=True)
        msg_hint = hints["messages"]
        # Should be Annotated[list, add_messages]
        assert hasattr(msg_hint, "__metadata__") or "Annotated" in str(msg_hint)

    def test_default_state_values(self):
        """create_initial_state() should return a valid starting state."""
        from Custom_model_fa_pf.agent.state import create_initial_state
        state = create_initial_state("test-session-123")
        assert state["session_id"] == "test-session-123"
        assert state["phase"] == IntakePhase.GREETING.value
        assert state["messages"] == []
        assert state["form_state"] == {}
        assert state["entities"] == {}
        assert state["lobs"] == []
        assert state["assigned_forms"] == []
        assert state["conversation_turn"] == 0
        assert state["error_count"] == 0
        assert state["summary"] == ""
        assert state["reflect_count"] == 0

    def test_state_has_reflect_count(self):
        """IntakeState should have reflect_count for reflection pattern."""
        annotations = IntakeState.__annotations__
        assert "reflect_count" in annotations
