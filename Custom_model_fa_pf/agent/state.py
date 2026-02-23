"""Agent state schema for LangGraph intake agent."""

from enum import Enum
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class IntakePhase(str, Enum):
    """Phases of the insurance intake conversation."""

    GREETING = "greeting"
    APPLICANT_INFO = "applicant_info"
    POLICY_DETAILS = "policy_details"
    BUSINESS_INFO = "business_info"
    FORM_SPECIFIC = "form_specific"
    REVIEW = "review"
    COMPLETE = "complete"

    @staticmethod
    def next_phase(current: "IntakePhase") -> "IntakePhase":
        """Return the next phase in the intake flow."""
        order = list(IntakePhase)
        idx = order.index(current)
        return order[min(idx + 1, len(order) - 1)]


class IntakeState(TypedDict):
    """State that flows through the LangGraph agent.

    The messages field uses add_messages reducer — LangGraph appends
    new messages rather than overwriting the list.
    """

    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]
    summary: str  # Compressed older history

    # Intake progress
    phase: str  # IntakePhase value (stored as str for serialization)
    form_state: dict  # field_name -> {value, confidence, source, status}
    entities: dict  # Structured extracted entities (CustomerSubmission.to_dict())

    # Forms
    lobs: list  # LOB IDs (e.g., ["commercial_auto", "general_liability"])
    assigned_forms: list  # Form numbers (e.g., ["125", "127", "137"])

    # Quality
    confidence_scores: dict  # field_name -> float
    validation_issues: list  # List of validation issue dicts

    # Session metadata
    session_id: str
    conversation_turn: int
    error_count: int
    reflect_count: int  # Reflection revisions this turn (max 1)


def create_initial_state(session_id: str) -> dict:
    """Create a fresh initial state for a new intake session."""
    return {
        "messages": [],
        "summary": "",
        "phase": IntakePhase.GREETING.value,
        "form_state": {},
        "entities": {},
        "lobs": [],
        "assigned_forms": [],
        "confidence_scores": {},
        "validation_issues": [],
        "session_id": session_id,
        "conversation_turn": 0,
        "error_count": 0,
        "reflect_count": 0,
    }
