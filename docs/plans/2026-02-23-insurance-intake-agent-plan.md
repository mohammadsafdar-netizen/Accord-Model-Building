# ACORD Insurance Intake Agent — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a conversational AI agent using LangGraph that drives insurance intake conversations, fills ACORD forms, validates data, and generates visual form guides.

**Architecture:** LangGraph StateGraph with 8 nodes (greet → understand → check_gaps → ask/validate/fill → review → guide), 10 agent tools wrapping existing pipeline modules, vLLM/Ollama as LLM backend, Rich CLI for testing.

**Tech Stack:** LangGraph 1.0.8, langchain-openai, langchain-core 1.2.12, vLLM 0.15.1, Rich 14.3.2, PyMuPDF (fitz), Pydantic, existing Custom_model_fa_pf modules

**Design doc:** `docs/plans/2026-02-23-insurance-intake-agent-design.md`

---

## Phase 1: Agent Core (State + Tools + Graph)

### Task 1: Install missing dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Install packages**

Run:
```bash
cd /home/inevoai/Development/Accord-Model-Building
uv pip install langchain-openai prompt-toolkit
```

Expected: packages install successfully. `langchain-openai` gives us `ChatOpenAI` (works with both vLLM and Ollama's OpenAI-compatible endpoint). `prompt-toolkit` gives us the interactive CLI input.

**Step 2: Verify imports**

Run:
```bash
.venv/bin/python -c "from langchain_openai import ChatOpenAI; from langchain_core.tools import tool; from langgraph.graph import StateGraph, START, END; from langgraph.prebuilt import ToolNode; from langgraph.checkpoint.memory import MemorySaver; print('All imports OK')"
```

Expected: `All imports OK`

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add langchain-openai and prompt-toolkit dependencies"
```

---

### Task 2: Create agent config

**Files:**
- Modify: `Custom_model_fa_pf/config.py`

**Step 1: Write the failing test**

Create `Custom_model_fa_pf/tests/test_agent_config.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /home/inevoai/Development/Accord-Model-Building && .venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_config.py -v`

Expected: FAIL with `ImportError: cannot import name 'AGENT_MODEL'`

**Step 3: Add config constants**

Add to bottom of `Custom_model_fa_pf/config.py`:

```python
# --- Agent configuration ---
LLM_BACKEND = "ollama"  # "vllm" or "ollama"
VLLM_BASE_URL = "http://localhost:8000/v1"
OLLAMA_OPENAI_URL = "http://localhost:11434/v1"  # Ollama's OpenAI-compatible endpoint

AGENT_MODEL = "qwen2.5:7b"  # Model name for agent LLM
AGENT_TEMPERATURE = 0.3
AGENT_MAX_TOKENS = 4096

MAX_CONVERSATION_TURNS = 30
MAX_TOOL_CALLS_PER_TURN = 5
SUMMARIZE_AFTER_TURNS = 20
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_config.py -v`

Expected: all 7 tests PASS

**Step 5: Commit**

```bash
git add Custom_model_fa_pf/config.py Custom_model_fa_pf/tests/test_agent_config.py
git commit -m "feat(agent): add agent configuration constants to config.py"
```

---

### Task 3: Create agent state module

**Files:**
- Create: `Custom_model_fa_pf/agent/__init__.py`
- Create: `Custom_model_fa_pf/agent/state.py`
- Create: `Custom_model_fa_pf/tests/test_agent_state.py`

**Step 1: Create agent package**

```bash
mkdir -p /home/inevoai/Development/Accord-Model-Building/Custom_model_fa_pf/agent
```

Create `Custom_model_fa_pf/agent/__init__.py`:
```python
"""LangGraph conversational intake agent."""
```

**Step 2: Write the failing test**

Create `Custom_model_fa_pf/tests/test_agent_state.py`:

```python
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
        from typing import get_type_hints, Annotated, get_args
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
```

**Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_state.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'Custom_model_fa_pf.agent.state'`

**Step 4: Implement state module**

Create `Custom_model_fa_pf/agent/state.py`:

```python
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
    }
```

**Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_state.py -v`

Expected: all 7 tests PASS

**Step 6: Commit**

```bash
git add Custom_model_fa_pf/agent/__init__.py Custom_model_fa_pf/agent/state.py Custom_model_fa_pf/tests/test_agent_state.py
git commit -m "feat(agent): add IntakeState and IntakePhase for LangGraph agent"
```

---

### Task 4: Create agent prompts module

**Files:**
- Create: `Custom_model_fa_pf/agent/prompts.py`
- Create: `Custom_model_fa_pf/tests/test_agent_prompts.py`

**Step 1: Write the failing test**

Create `Custom_model_fa_pf/tests/test_agent_prompts.py`:

```python
"""Tests for agent prompt templates."""

import json
import pytest
from Custom_model_fa_pf.agent.prompts import (
    INTAKE_SYSTEM_PROMPT,
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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_prompts.py -v`

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement prompts module**

Create `Custom_model_fa_pf/agent/prompts.py`:

```python
"""Prompt templates for the insurance intake agent."""

from langchain_core.messages import SystemMessage


INTAKE_SYSTEM_PROMPT = """You are an AI insurance intake assistant for commercial insurance applications.
Your role is to collect accurate information needed to complete ACORD forms through a natural, professional conversation.

## YOUR IDENTITY
- Role: Commercial insurance intake specialist
- Tone: Professional, patient, clear. Never condescending.
- When customers don't know insurance terminology, explain in plain language.

## CORE RULES
1. Ask ONE question at a time. Never overwhelm with multiple questions.
2. ONLY record information the customer explicitly provides. NEVER assume or infer values.
3. If the customer's answer is ambiguous, ask a clarifying follow-up.
4. If the customer says "I don't know" or is unsure, acknowledge it and move on. Do NOT guess.
5. Always confirm critical data (policy limits, effective dates, business entity type) by reading it back.
6. You may ONLY discuss insurance intake topics. Politely redirect off-topic questions.

## INFORMATION COLLECTION ORDER
Follow this sequence, asking about each area in turn:

### Phase 1: Applicant Information
- Full legal business name and DBA (if any)
- Business entity type (Corporation, LLC, Partnership, Individual, etc.)
- Mailing address (street, city, state, ZIP)
- Phone and email
- FEIN (ask if they'd like to provide now or later)

### Phase 2: Policy Details
- Type of insurance needed (auto, GL, WC, property, umbrella, etc.)
- Requested effective date and expiration date
- New policy or renewal? If renewal, current carrier and policy number.

### Phase 3: Business/Risk Information
- Nature of business / what they do
- Years in business
- Number of employees
- Annual revenue or payroll (if Workers Comp)

### Phase 4: Form-Specific Details
- Vehicles: year, make, model, VIN, use type, garaging address
- Drivers: name, DOB, license number and state, years of experience
- Locations: address, construction type, occupancy
- Coverage: limits, deductibles, specific coverage types

### Phase 5: Review & Confirmation
- Summarize ALL collected information clearly
- Ask customer to confirm or flag corrections
- Note any fields still missing

## ANTI-HALLUCINATION RULES
- If the user has NOT mentioned a piece of information, its value is NULL, not a guess.
- NEVER invent names, addresses, policy numbers, VINs, or dates.
- When unsure, say: "I want to make sure I have this right. Could you confirm [X]?"
- For numeric values (limits, deductibles, revenue), always read them back with formatting.
- Self-check before recording any value: "Did the customer say this, or am I generating it?"

## TOOL USAGE
- Call save_field after each confirmed piece of information.
- Call validate_fields when a section is complete (e.g., after collecting an address or VIN).
- Call analyze_gaps periodically to check what's still needed.
- Call classify_lobs early when the customer describes their business.
- Call extract_entities when the customer provides a block of information (like an email).
"""


def build_form_state_context(form_state: dict) -> str:
    """Build a human-readable summary of collected form fields."""
    if not form_state:
        return "No fields collected yet."

    lines = []
    confirmed = []
    pending = []
    empty = []

    for field_name, info in sorted(form_state.items()):
        status = info.get("status", "empty")
        value = info.get("value", "")
        confidence = info.get("confidence", 0.0)

        if status == "confirmed" and value:
            confirmed.append(f"  {field_name}: {value} (confidence: {confidence:.0%})")
        elif status == "pending":
            pending.append(f"  {field_name}: {value or '—'} (needs confirmation)")
        else:
            empty.append(f"  {field_name}")

    if confirmed:
        lines.append(f"CONFIRMED ({len(confirmed)}):")
        lines.extend(confirmed)
    if pending:
        lines.append(f"\nPENDING ({len(pending)}):")
        lines.extend(pending)
    if empty:
        lines.append(f"\nEMPTY ({len(empty)}):")
        lines.extend(empty[:10])  # Limit to avoid flooding context
        if len(empty) > 10:
            lines.append(f"  ... and {len(empty) - 10} more")

    return "\n".join(lines)


def build_system_message(form_state: dict, summary: str) -> SystemMessage:
    """Build the full system message with prompt + form state + summary."""
    parts = [INTAKE_SYSTEM_PROMPT]

    # Always inject form state
    state_ctx = build_form_state_context(form_state)
    parts.append(f"\n## CURRENT FORM STATE\n{state_ctx}")

    # Inject conversation summary only when it exists
    if summary.strip():
        parts.append(f"\n## CONVERSATION SUMMARY (earlier turns)\n{summary}")

    return SystemMessage(content="\n".join(parts))
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_prompts.py -v`

Expected: all 10 tests PASS

**Step 5: Commit**

```bash
git add Custom_model_fa_pf/agent/prompts.py Custom_model_fa_pf/tests/test_agent_prompts.py
git commit -m "feat(agent): add system prompt with anti-hallucination rules and form state context"
```

---

### Task 5: Create confidence scoring module

**Files:**
- Create: `Custom_model_fa_pf/agent/confidence.py`
- Create: `Custom_model_fa_pf/tests/test_confidence.py`

**Step 1: Write the failing test**

Create `Custom_model_fa_pf/tests/test_confidence.py`:

```python
"""Tests for confidence scoring and review routing."""

import pytest
from Custom_model_fa_pf.agent.confidence import (
    ConfidenceScorer,
    ConfidenceLevel,
    ReviewRouter,
    ReviewDecision,
)


class TestConfidenceLevel:
    def test_from_score_high(self):
        assert ConfidenceLevel.from_score(0.95) == ConfidenceLevel.HIGH

    def test_from_score_medium(self):
        assert ConfidenceLevel.from_score(0.80) == ConfidenceLevel.MEDIUM

    def test_from_score_low(self):
        assert ConfidenceLevel.from_score(0.55) == ConfidenceLevel.LOW

    def test_from_score_very_low(self):
        assert ConfidenceLevel.from_score(0.30) == ConfidenceLevel.VERY_LOW

    def test_boundary_090(self):
        assert ConfidenceLevel.from_score(0.90) == ConfidenceLevel.HIGH

    def test_boundary_070(self):
        assert ConfidenceLevel.from_score(0.70) == ConfidenceLevel.MEDIUM


class TestConfidenceScorer:
    def setup_method(self):
        self.scorer = ConfidenceScorer()

    def test_user_stated(self):
        score = self.scorer.score("business_name", "Acme LLC", source="user_stated")
        assert score == 0.95

    def test_user_confirmed(self):
        score = self.scorer.score("business_name", "Acme LLC", source="user_confirmed")
        assert score == 1.0

    def test_llm_inferred(self):
        score = self.scorer.score("entity_type", "LLC", source="llm_inferred")
        assert score == 0.60

    def test_validated_boosts(self):
        base = self.scorer.score("vin", "1HGCM82633A004352", source="user_stated")
        boosted = self.scorer.score(
            "vin", "1HGCM82633A004352", source="user_stated", validation_passed=True
        )
        assert boosted > base

    def test_validation_failed_penalizes(self):
        base = self.scorer.score("vin", "BADVIN", source="user_stated")
        penalized = self.scorer.score(
            "vin", "BADVIN", source="user_stated", validation_passed=False
        )
        assert penalized < base

    def test_score_clamped_to_0_1(self):
        score = self.scorer.score("x", "y", source="user_confirmed", validation_passed=True)
        assert 0.0 <= score <= 1.0

    def test_unknown_source_defaults(self):
        score = self.scorer.score("field", "val", source="unknown_source")
        assert 0.0 < score < 1.0


class TestReviewRouter:
    def setup_method(self):
        self.router = ReviewRouter()

    def test_all_high_confidence_auto_accept(self):
        scores = {"name": 0.95, "address": 0.92, "phone": 0.98}
        decision = self.router.route(scores)
        assert decision.action == "auto_process"

    def test_low_critical_field_requires_review(self):
        scores = {"business_name": 0.45, "address": 0.95}
        decision = self.router.route(scores)
        assert decision.action == "human_review_required"
        assert len(decision.flagged_fields) > 0

    def test_low_noncritical_field_optional_review(self):
        scores = {"sic_code": 0.50, "business_name": 0.95}
        decision = self.router.route(scores)
        assert decision.action in ("auto_process", "human_review_optional")

    def test_empty_scores_auto_process(self):
        decision = self.router.route({})
        assert decision.action == "auto_process"
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_confidence.py -v`

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement confidence module**

Create `Custom_model_fa_pf/agent/confidence.py`:

```python
"""Confidence scoring and human review routing for intake fields."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConfidenceLevel(str, Enum):
    HIGH = "high"          # >= 0.90
    MEDIUM = "medium"      # 0.70 - 0.89
    LOW = "low"            # 0.50 - 0.69
    VERY_LOW = "very_low"  # < 0.50

    @staticmethod
    def from_score(score: float) -> "ConfidenceLevel":
        if score >= 0.90:
            return ConfidenceLevel.HIGH
        elif score >= 0.70:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.50:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW


# Fields that MUST be correct — flag for review if low confidence.
CRITICAL_FIELDS = {
    "business_name", "business.business_name",
    "policy.effective_date", "policy.expiration_date",
    "vehicles[].vin", "vin",
    "tax_id", "business.tax_id", "fein",
    "drivers[].license_number", "license_number",
    "coverage.liability_limit",
}


class ConfidenceScorer:
    """Score field values based on source, validation, and patterns."""

    SOURCE_WEIGHTS = {
        "user_stated": 0.95,
        "user_confirmed": 1.00,
        "llm_inferred": 0.60,
        "validated_external": 0.98,
        "defaulted": 0.50,
        "ocr_extracted": 0.80,
    }
    DEFAULT_WEIGHT = 0.50

    def score(
        self,
        field_name: str,
        value: str,
        source: str = "user_stated",
        validation_passed: Optional[bool] = None,
    ) -> float:
        """Compute confidence score for a field value."""
        base = self.SOURCE_WEIGHTS.get(source, self.DEFAULT_WEIGHT)

        if validation_passed is True:
            base = min(base + 0.10, 1.0)
        elif validation_passed is False:
            base = max(base - 0.30, 0.10)

        return round(min(max(base, 0.0), 1.0), 2)


@dataclass
class ReviewDecision:
    action: str  # "auto_process", "human_review_required", "human_review_optional"
    flagged_fields: list = field(default_factory=list)
    message: str = ""


class ReviewRouter:
    """Route forms to auto-processing or human review based on confidence."""

    def __init__(
        self,
        auto_threshold: float = 0.90,
        review_threshold: float = 0.70,
    ):
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold

    def route(self, confidence_scores: dict) -> ReviewDecision:
        if not confidence_scores:
            return ReviewDecision(action="auto_process", message="No fields to review")

        flagged = []
        for field_name, score in confidence_scores.items():
            if score < self.review_threshold:
                flagged.append({"field": field_name, "confidence": score})

        if not flagged:
            return ReviewDecision(action="auto_process", message="All fields above threshold")

        critical_flags = [
            f for f in flagged
            if any(c in f["field"] for c in CRITICAL_FIELDS)
        ]

        if critical_flags:
            return ReviewDecision(
                action="human_review_required",
                flagged_fields=flagged,
                message=f"{len(critical_flags)} critical fields need review",
            )

        return ReviewDecision(
            action="human_review_optional",
            flagged_fields=flagged,
            message=f"{len(flagged)} non-critical fields flagged",
        )
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_confidence.py -v`

Expected: all 15 tests PASS

**Step 5: Commit**

```bash
git add Custom_model_fa_pf/agent/confidence.py Custom_model_fa_pf/tests/test_confidence.py
git commit -m "feat(agent): add confidence scoring and human review routing"
```

---

### Task 6: Create agent tools module

**Files:**
- Create: `Custom_model_fa_pf/agent/tools.py`
- Create: `Custom_model_fa_pf/tests/test_agent_tools.py`

This is the bridge between the LangGraph agent and the existing pipeline modules. Each tool wraps an existing function and returns a JSON string.

**Step 1: Write the failing test**

Create `Custom_model_fa_pf/tests/test_agent_tools.py`:

```python
"""Tests for agent tool definitions."""

import json
import pytest
from Custom_model_fa_pf.agent.tools import (
    get_all_tools,
    save_field_tool,
    validate_fields_tool,
    classify_lobs_tool,
    extract_entities_tool,
    assign_forms_tool,
    read_form_tool,
    map_fields_tool,
    analyze_gaps_tool,
)


class TestToolDefinitions:
    def test_all_tools_list(self):
        tools = get_all_tools()
        assert len(tools) >= 8
        names = [t.name for t in tools]
        assert "save_field" in names
        assert "validate_fields" in names
        assert "classify_lobs" in names

    def test_tools_have_descriptions(self):
        for tool in get_all_tools():
            assert tool.description, f"Tool {tool.name} has no description"
            assert len(tool.description) > 10

    def test_tools_have_args_schema(self):
        """Each tool should have typed arguments."""
        for tool in get_all_tools():
            schema = tool.args_schema
            assert schema is not None, f"Tool {tool.name} has no args schema"


class TestSaveFieldTool:
    def test_save_field_returns_json(self):
        result = save_field_tool.invoke(
            {"field_name": "business_name", "value": "Acme LLC", "source": "user_stated"}
        )
        parsed = json.loads(result)
        assert parsed["status"] == "saved"
        assert parsed["field_name"] == "business_name"
        assert parsed["value"] == "Acme LLC"
        assert "confidence" in parsed

    def test_save_field_empty_value(self):
        result = save_field_tool.invoke(
            {"field_name": "phone", "value": "", "source": "user_stated"}
        )
        parsed = json.loads(result)
        assert parsed["status"] == "skipped"


class TestValidateFieldsTool:
    def test_validate_vin_error(self):
        fields = json.dumps({"Vehicle_VIN_A": "SHORTVIN"})
        result = validate_fields_tool.invoke({"fields_json": fields})
        parsed = json.loads(result)
        assert parsed["error_count"] >= 1

    def test_validate_clean_fields(self):
        fields = json.dumps({"Policy_EffectiveDate_A": "03/01/2026"})
        result = validate_fields_tool.invoke({"fields_json": fields})
        parsed = json.loads(result)
        assert parsed["error_count"] == 0

    def test_validate_auto_correction(self):
        fields = json.dumps({"NamedInsured_TaxIdentifier_A": "123456789"})
        result = validate_fields_tool.invoke({"fields_json": fields})
        parsed = json.loads(result)
        assert "12-3456789" in json.dumps(parsed)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_tools.py -v`

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement tools module**

Create `Custom_model_fa_pf/agent/tools.py`:

```python
"""Agent tool definitions — bridge between LangGraph and existing pipeline modules."""

import json
import logging
from typing import Optional

from langchain_core.tools import tool

from Custom_model_fa_pf.agent.confidence import ConfidenceScorer

logger = logging.getLogger(__name__)
_scorer = ConfidenceScorer()


@tool
def save_field(field_name: str, value: str, source: str = "user_stated") -> str:
    """Record a confirmed field value from the customer.

    Call this after the customer provides a piece of information and you have
    confirmed it. The value is stored with a confidence score.

    Args:
        field_name: A descriptive field name (e.g., 'business_name', 'driver_a_dob')
        value: The field value as a string
        source: How the value was obtained ('user_stated', 'user_confirmed', 'llm_inferred')
    """
    if not value or not value.strip():
        return json.dumps({"status": "skipped", "field_name": field_name, "reason": "empty value"})

    confidence = _scorer.score(field_name, value, source=source)
    return json.dumps({
        "status": "saved",
        "field_name": field_name,
        "value": value.strip(),
        "source": source,
        "confidence": confidence,
    })


@tool
def validate_fields(fields_json: str) -> str:
    """Validate form field values against business rules.

    Checks VIN checksum, driver's license format by state, FEIN format,
    date ordering, phone format, and state/ZIP consistency. Returns errors,
    warnings, and auto-corrections.

    Args:
        fields_json: JSON string of {field_name: value} pairs to validate
    """
    from Custom_model_fa_pf.validation_engine import validate

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    result = validate(fields)
    return json.dumps(result.to_dict())


@tool
def classify_lobs(text: str) -> str:
    """Classify which lines of business are needed based on the customer's description.

    Analyzes the text to identify insurance types: Commercial Auto, General Liability,
    Workers Compensation, Commercial Property, Commercial Umbrella, BOP, Cyber.

    Args:
        text: Customer description of their business and insurance needs
    """
    from Custom_model_fa_pf.lob_classifier import classify, LOBClassification
    from Custom_model_fa_pf.agent._llm_provider import get_llm_engine

    llm = get_llm_engine()
    results = classify(text, llm)
    return json.dumps([r.to_dict() for r in results])


@tool
def extract_entities(text: str) -> str:
    """Extract structured insurance entities from text.

    Extracts business info, policy details, vehicles, drivers, coverage requests,
    locations, and loss history from the provided text.

    Args:
        text: Customer message containing insurance information
    """
    from Custom_model_fa_pf.entity_extractor import extract
    from Custom_model_fa_pf.agent._llm_provider import get_llm_engine

    llm = get_llm_engine()
    submission = extract(text, llm)
    return json.dumps(submission.to_dict())


@tool
def assign_forms(lobs_json: str) -> str:
    """Determine which ACORD forms are needed based on lines of business.

    Args:
        lobs_json: JSON array of LOB classification dicts from classify_lobs
    """
    from Custom_model_fa_pf.lob_classifier import LOBClassification
    from Custom_model_fa_pf.form_assigner import assign

    try:
        lob_dicts = json.loads(lobs_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    lobs = []
    for d in lob_dicts:
        lobs.append(LOBClassification(
            lob_id=d["lob_id"],
            confidence=d.get("confidence", 0.9),
            reasoning=d.get("reasoning", ""),
            display_name=d.get("display_name", ""),
        ))

    assignments = assign(lobs)
    return json.dumps([a.to_dict() for a in assignments])


@tool
def read_form(pdf_path: str) -> str:
    """Read a fillable PDF form and return all field names, types, and tooltips.

    Works with any AcroForm PDF. Returns a catalog of all fields organized
    by category (driver, vehicle, policy, etc.).

    Args:
        pdf_path: Path to the PDF file to read
    """
    from pathlib import Path
    from Custom_model_fa_pf.form_reader import read_pdf_form

    catalog = read_pdf_form(Path(pdf_path))
    summary = {
        "form_number": catalog.form_number,
        "total_fields": catalog.total_fields,
        "text_fields": len(catalog.text_fields),
        "checkbox_fields": len(catalog.checkbox_fields),
        "sections": [s.to_dict() for s in catalog.sections[:5]],  # Limit to avoid huge output
    }
    return json.dumps(summary)


@tool
def map_fields(form_number: str, entities_json: str) -> str:
    """Map extracted customer data to form fields using the 3-phase field mapper.

    Phase 1: Deterministic regex patterns (instant).
    Phase 2: Suffix-indexed array mapping for drivers/vehicles (instant).
    Phase 3: LLM batch mapping for remaining fields.

    Args:
        form_number: ACORD form number (e.g., '125', '127', '137')
        entities_json: JSON string of extracted entities (CustomerSubmission format)
    """
    from Custom_model_fa_pf.entity_schema import CustomerSubmission
    from Custom_model_fa_pf.form_reader import find_template, read_pdf_form
    from Custom_model_fa_pf import llm_field_mapper
    from Custom_model_fa_pf.agent._llm_provider import get_llm_engine

    try:
        entity_dict = json.loads(entities_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    entities = CustomerSubmission.from_llm_json(entity_dict)

    # Find and read the template
    template_path = find_template(form_number)
    if template_path is None:
        return json.dumps({"error": f"No template found for form {form_number}"})

    catalog = read_pdf_form(template_path)
    llm = get_llm_engine()

    result = llm_field_mapper.map_fields(
        entities=entities, catalog=catalog, llm_engine=llm
    )

    return json.dumps({
        "form_number": form_number,
        "total_mapped": result.total_mapped,
        "phase1_count": result.phase1_count,
        "phase2_count": result.phase2_count,
        "phase3_count": result.phase3_count,
        "mappings": result.mappings,
    })


@tool
def analyze_gaps(entities_json: str, assigned_forms_json: str, field_values_json: str) -> str:
    """Analyze which required fields are still missing or incomplete.

    Returns missing critical fields, missing important fields, completeness
    percentage, and suggested follow-up questions.

    Args:
        entities_json: JSON string of extracted entities
        assigned_forms_json: JSON array of form assignment dicts
        field_values_json: JSON of {form_number: {field_name: value}}
    """
    from Custom_model_fa_pf.entity_schema import CustomerSubmission
    from Custom_model_fa_pf.form_assigner import FormAssignment
    from Custom_model_fa_pf.gap_analyzer import analyze

    try:
        entities = CustomerSubmission.from_llm_json(json.loads(entities_json))
        assignments_dicts = json.loads(assigned_forms_json)
        field_values = json.loads(field_values_json)
    except (json.JSONDecodeError, Exception) as e:
        return json.dumps({"error": f"Parse error: {e}"})

    assignments = []
    for d in assignments_dicts:
        assignments.append(FormAssignment(
            form_number=d["form_number"],
            purpose=d.get("purpose", ""),
            schema_available=d.get("schema_available", False),
            lobs=d.get("lobs", []),
        ))

    report = analyze(entities, assignments, field_values)
    return json.dumps(report.to_dict())


# --- Tool aliases for test imports ---
save_field_tool = save_field
validate_fields_tool = validate_fields
classify_lobs_tool = classify_lobs
extract_entities_tool = extract_entities
assign_forms_tool = assign_forms
read_form_tool = read_form
map_fields_tool = map_fields
analyze_gaps_tool = analyze_gaps


def get_all_tools():
    """Return all agent tools for binding to the LLM."""
    return [
        save_field,
        validate_fields,
        classify_lobs,
        extract_entities,
        assign_forms,
        read_form,
        map_fields,
        analyze_gaps,
    ]
```

**Step 4: Create LLM provider helper**

Create `Custom_model_fa_pf/agent/_llm_provider.py`:

```python
"""Shared LLM engine provider for agent tools."""

import logging
from Custom_model_fa_pf.config import (
    DEFAULT_MODEL, DEFAULT_OLLAMA_URL,
)

logger = logging.getLogger(__name__)

_engine = None


def get_llm_engine():
    """Get or create the shared LLM engine for tool calls."""
    global _engine
    if _engine is None:
        from llm_engine import LLMEngine
        _engine = LLMEngine(
            model=DEFAULT_MODEL,
            base_url=DEFAULT_OLLAMA_URL,
            keep_models_loaded=True,
            structured_json=True,
        )
    return _engine


def reset_engine():
    """Reset the engine (for testing)."""
    global _engine
    _engine = None
```

**Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_tools.py -v`

Expected: all 11 tests PASS (the tools that call LLM like classify_lobs are not invoked in unit tests — only save_field and validate_fields which are pure functions)

**Step 6: Commit**

```bash
git add Custom_model_fa_pf/agent/tools.py Custom_model_fa_pf/agent/_llm_provider.py Custom_model_fa_pf/tests/test_agent_tools.py
git commit -m "feat(agent): add 8 agent tools wrapping existing pipeline modules"
```

---

### Task 7: Create agent graph module

**Files:**
- Create: `Custom_model_fa_pf/agent/nodes.py`
- Create: `Custom_model_fa_pf/agent/graph.py`
- Create: `Custom_model_fa_pf/tests/test_agent_graph.py`

**Step 1: Write the failing test**

Create `Custom_model_fa_pf/tests/test_agent_graph.py`:

```python
"""Tests for agent graph structure and compilation."""

import pytest
from Custom_model_fa_pf.agent.graph import create_graph, create_agent
from Custom_model_fa_pf.agent.state import IntakePhase


class TestGraphStructure:
    def test_graph_compiles(self):
        """Graph should compile without errors."""
        graph = create_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = create_graph()
        # LangGraph compiled graph stores nodes
        node_names = set(graph.nodes.keys())
        assert "greet" in node_names
        assert "understand" in node_names
        assert "check_gaps" in node_names
        assert "respond" in node_names

    def test_agent_creates_with_checkpointer(self):
        agent = create_agent()
        assert agent is not None


class TestRouting:
    def test_route_greeting_phase(self):
        from Custom_model_fa_pf.agent.nodes import route_after_gaps
        state = {
            "phase": IntakePhase.GREETING.value,
            "form_state": {},
            "entities": {},
            "lobs": [],
            "assigned_forms": [],
            "validation_issues": [],
            "conversation_turn": 0,
        }
        result = route_after_gaps(state)
        assert result == "respond"  # Not enough info yet, ask questions

    def test_route_to_review_when_complete(self):
        from Custom_model_fa_pf.agent.nodes import route_after_gaps
        state = {
            "phase": IntakePhase.REVIEW.value,
            "form_state": {"business_name": {"value": "Acme", "status": "confirmed"}},
            "entities": {"business": {"business_name": "Acme"}},
            "lobs": ["commercial_auto"],
            "assigned_forms": ["125", "127"],
            "validation_issues": [],
            "conversation_turn": 5,
        }
        result = route_after_gaps(state)
        assert result == "review"
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_graph.py -v`

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement nodes module**

Create `Custom_model_fa_pf/agent/nodes.py`:

```python
"""Node functions for the LangGraph intake agent."""

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage

from Custom_model_fa_pf.agent.state import IntakePhase, IntakeState
from Custom_model_fa_pf.agent.prompts import build_system_message

logger = logging.getLogger(__name__)


def greet_node(state: IntakeState) -> dict:
    """Welcome the customer and initiate the intake conversation."""
    greeting = (
        "Welcome! I'm here to help you with your commercial insurance application. "
        "I'll walk you through the process step by step.\n\n"
        "To get started, could you tell me your business name and what type of "
        "business you operate?"
    )
    return {
        "messages": [AIMessage(content=greeting)],
        "phase": IntakePhase.APPLICANT_INFO.value,
        "conversation_turn": state.get("conversation_turn", 0) + 1,
    }


def understand_node(state: IntakeState) -> dict:
    """Process the latest user message — extract entities and update state.

    This node reads the latest user message and updates form_state with
    any new information. It does NOT call the LLM directly — it uses
    the tool results that come back from the agent's tool calls.
    """
    # The understanding happens via tool calls in the agent node.
    # This node simply increments the conversation turn.
    return {
        "conversation_turn": state.get("conversation_turn", 0) + 1,
    }


def check_gaps_node(state: IntakeState) -> dict:
    """Analyze completeness and decide what to do next.

    This is a routing node — it doesn't modify state, just evaluates it.
    The actual routing decision is made by route_after_gaps().
    """
    # Count collected fields
    form_state = state.get("form_state", {})
    confirmed = sum(1 for f in form_state.values() if f.get("status") == "confirmed")
    total_expected = len(form_state) if form_state else 0

    logger.debug(f"Gap check: {confirmed}/{total_expected} fields confirmed, phase={state.get('phase')}")
    return {}  # Pure routing node — route_after_gaps does the logic


def route_after_gaps(state: IntakeState) -> str:
    """Conditional routing after gap analysis.

    Returns:
        "respond" — need more info, generate a follow-up question
        "validate" — have enough info, run validation
        "review" — all complete, show summary
    """
    phase = state.get("phase", IntakePhase.GREETING.value)

    # If we're in REVIEW phase, go to review
    if phase == IntakePhase.REVIEW.value:
        return "review"

    # If we're in COMPLETE phase, also go to review
    if phase == IntakePhase.COMPLETE.value:
        return "review"

    # Check if we have enough data to validate
    form_state = state.get("form_state", {})
    entities = state.get("entities", {})
    lobs = state.get("lobs", [])
    assigned_forms = state.get("assigned_forms", [])

    # If we have LOBs + assigned forms + substantial entities, try validation
    confirmed_count = sum(1 for f in form_state.values() if f.get("status") == "confirmed")
    has_lobs = len(lobs) > 0
    has_forms = len(assigned_forms) > 0
    has_entities = bool(entities.get("business", {}).get("business_name"))

    if has_lobs and has_forms and has_entities and confirmed_count >= 10:
        # Check validation issues
        issues = state.get("validation_issues", [])
        errors = [i for i in issues if i.get("severity") == "error"]
        if not errors:
            return "review"
        return "validate"

    # Default: need more info
    return "respond"


def respond_node(state: IntakeState) -> dict:
    """This is a placeholder — the actual response is generated by the LLM agent node.

    In the compiled graph, the agent node (with tool calling) handles response
    generation. This node is used as a pass-through for the routing logic.
    """
    return {}


def validate_node(state: IntakeState) -> dict:
    """Run validation on all collected field values."""
    from Custom_model_fa_pf.validation_engine import validate

    form_state = state.get("form_state", {})
    # Build a flat dict of field_name -> value for validation
    fields = {k: v.get("value", "") for k, v in form_state.items() if v.get("value")}

    if not fields:
        return {"validation_issues": []}

    result = validate(fields)
    issues = [issue.to_dict() for issue in result.issues]

    # Apply auto-corrections back to form_state
    updated_state = dict(form_state)
    for field_name, corrected_value in result.auto_corrections.items():
        if field_name in updated_state:
            updated_state[field_name] = {
                **updated_state[field_name],
                "value": result.corrected_values.get(field_name, updated_state[field_name].get("value")),
                "status": "confirmed",
            }

    return {
        "validation_issues": issues,
        "form_state": updated_state,
    }


def review_node(state: IntakeState) -> dict:
    """Generate a summary of all collected information for customer confirmation."""
    form_state = state.get("form_state", {})
    confirmed = {k: v for k, v in form_state.items() if v.get("status") == "confirmed"}

    lines = ["Here's a summary of everything I've collected:\n"]
    for field_name, info in sorted(confirmed.items()):
        lines.append(f"  - {field_name}: {info.get('value', '')}")

    issues = state.get("validation_issues", [])
    if issues:
        lines.append(f"\nValidation notes ({len(issues)}):")
        for issue in issues[:5]:
            lines.append(f"  - {issue.get('message', '')}")

    lines.append("\nDoes everything look correct? Let me know if you'd like to change anything.")

    return {
        "messages": [AIMessage(content="\n".join(lines))],
        "phase": IntakePhase.COMPLETE.value,
    }
```

**Step 4: Implement graph module**

Create `Custom_model_fa_pf/agent/graph.py`:

```python
"""LangGraph StateGraph definition for the insurance intake agent."""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from Custom_model_fa_pf.agent.state import IntakeState
from Custom_model_fa_pf.agent.nodes import (
    greet_node,
    understand_node,
    check_gaps_node,
    route_after_gaps,
    validate_node,
    review_node,
)
from Custom_model_fa_pf.agent.prompts import build_system_message
from Custom_model_fa_pf.agent.tools import get_all_tools
from Custom_model_fa_pf.config import (
    LLM_BACKEND,
    VLLM_BASE_URL,
    OLLAMA_OPENAI_URL,
    AGENT_MODEL,
    AGENT_TEMPERATURE,
    AGENT_MAX_TOKENS,
    MAX_TOOL_CALLS_PER_TURN,
)

logger = logging.getLogger(__name__)


def _get_chat_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance pointing at vLLM or Ollama."""
    base_url = VLLM_BASE_URL if LLM_BACKEND == "vllm" else OLLAMA_OPENAI_URL
    return ChatOpenAI(
        base_url=base_url,
        api_key="not-needed",
        model=AGENT_MODEL,
        temperature=AGENT_TEMPERATURE,
        max_tokens=AGENT_MAX_TOKENS,
    )


def _agent_node(state: IntakeState) -> dict:
    """Core agent node: builds context, calls LLM with tools bound."""
    llm = _get_chat_llm()
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)

    # Build system message with form state + summary
    system_msg = build_system_message(
        form_state=state.get("form_state", {}),
        summary=state.get("summary", ""),
    )

    # Prepend system message to the conversation
    messages = [system_msg] + list(state.get("messages", []))

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def _should_use_tools(state: IntakeState) -> str:
    """Check if the last AI message wants to call tools."""
    messages = state.get("messages", [])
    if not messages:
        return END

    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "check_gaps"


def create_graph():
    """Build and compile the LangGraph StateGraph."""
    tools = get_all_tools()

    workflow = StateGraph(IntakeState)

    # Nodes
    workflow.add_node("greet", greet_node)
    workflow.add_node("agent", _agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("understand", understand_node)
    workflow.add_node("check_gaps", check_gaps_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("review", review_node)
    workflow.add_node("respond", lambda state: {})  # Pass-through for routing

    # Edges: Initial greeting
    workflow.add_edge(START, "greet")
    workflow.add_edge("greet", END)  # First turn: greet and wait

    # After user responds, go to the agent (with tool calling)
    # Note: on subsequent invocations, we enter at "agent" by routing from START
    # Actually, LangGraph re-enters at the point after the last END.
    # For multi-turn, we use the pattern: user message -> agent -> tools loop -> check -> respond/review

    # Agent -> tool calling loop
    workflow.add_conditional_edges("agent", _should_use_tools, {
        "tools": "tools",
        "check_gaps": "check_gaps",
        END: END,
    })
    workflow.add_edge("tools", "agent")  # After tools, back to agent

    # Gap routing
    workflow.add_conditional_edges("check_gaps", route_after_gaps, {
        "respond": END,       # Agent already generated response, end turn
        "validate": "validate",
        "review": "review",
    })
    workflow.add_edge("validate", END)
    workflow.add_edge("review", END)

    return workflow.compile()


def create_agent(checkpointer=None):
    """Create a compiled agent with checkpointing for multi-turn conversations."""
    tools = get_all_tools()

    workflow = StateGraph(IntakeState)

    workflow.add_node("greet", greet_node)
    workflow.add_node("agent", _agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("check_gaps", check_gaps_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("review", review_node)

    workflow.add_edge(START, "greet")
    workflow.add_edge("greet", END)

    workflow.add_conditional_edges("agent", _should_use_tools, {
        "tools": "tools",
        "check_gaps": "check_gaps",
        END: END,
    })
    workflow.add_edge("tools", "agent")

    workflow.add_conditional_edges("check_gaps", route_after_gaps, {
        "respond": END,
        "validate": "validate",
        "review": "review",
    })
    workflow.add_edge("validate", END)
    workflow.add_edge("review", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)
```

**Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_agent_graph.py -v`

Expected: all 5 tests PASS

**Step 6: Commit**

```bash
git add Custom_model_fa_pf/agent/nodes.py Custom_model_fa_pf/agent/graph.py Custom_model_fa_pf/tests/test_agent_graph.py
git commit -m "feat(agent): add LangGraph StateGraph with nodes, routing, and tool calling"
```

---

### Task 8: Create CLI chat interface

**Files:**
- Create: `Custom_model_fa_pf/cli.py`
- Create: `Custom_model_fa_pf/tests/test_cli.py`

**Step 1: Write the failing test**

Create `Custom_model_fa_pf/tests/test_cli.py`:

```python
"""Tests for CLI chat interface."""

import pytest
from Custom_model_fa_pf.cli import format_agent_response, extract_text_from_messages


class TestFormatAgentResponse:
    def test_simple_text(self):
        result = format_agent_response("Hello, welcome to insurance intake.")
        assert "Hello" in result

    def test_strips_leading_whitespace(self):
        result = format_agent_response("  \n  Hello")
        assert result.startswith("Hello") or result.startswith("\n")


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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_cli.py -v`

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement CLI module**

Create `Custom_model_fa_pf/cli.py`:

```python
"""CLI chat interface for the insurance intake agent."""

import logging
import sys
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from Custom_model_fa_pf.agent.state import IntakePhase, create_initial_state
from Custom_model_fa_pf.agent.graph import create_agent

console = Console()
logger = logging.getLogger(__name__)


def format_agent_response(text: str) -> str:
    """Clean up agent response text for display."""
    return text.strip()


def extract_text_from_messages(messages: list) -> str:
    """Extract displayable text from a list of LangGraph messages.

    Skips tool call messages and tool results — only returns AI text responses.
    """
    texts = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            texts.append(msg.content)
    return "\n".join(texts)


def run_chat():
    """Run the interactive chat CLI."""
    console.print(Panel(
        "[bold]ACORD Insurance Intake Agent[/bold]\n"
        "Type your messages to interact with the agent.\n"
        "Commands: /quit, /status, /reset",
        title="Insurance Intake",
        border_style="blue",
    ))

    session_id = str(uuid.uuid4())[:8]
    agent = create_agent()
    config = {"configurable": {"thread_id": f"cli:{session_id}"}}

    # Initial greeting — invoke with empty input to trigger greet node
    initial_state = create_initial_state(session_id)
    try:
        result = agent.invoke(initial_state, config=config)
        greeting = extract_text_from_messages(result.get("messages", []))
        if greeting:
            console.print(Panel(
                Markdown(format_agent_response(greeting)),
                title="Agent",
                border_style="green",
            ))
    except Exception as e:
        console.print(f"[red]Error starting agent: {e}[/red]")
        return

    # Chat loop
    while True:
        try:
            user_input = console.input("[bold blue]You:[/bold blue] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.lower() == "/status":
            # Show current state
            state = agent.get_state(config)
            phase = state.values.get("phase", "unknown")
            form_state = state.values.get("form_state", {})
            confirmed = sum(1 for f in form_state.values() if f.get("status") == "confirmed")
            console.print(Panel(
                f"Phase: {phase}\nFields confirmed: {confirmed}\n"
                f"Session: {session_id}",
                title="Status",
                border_style="yellow",
            ))
            continue

        if user_input.lower() == "/reset":
            session_id = str(uuid.uuid4())[:8]
            config = {"configurable": {"thread_id": f"cli:{session_id}"}}
            initial_state = create_initial_state(session_id)
            result = agent.invoke(initial_state, config=config)
            greeting = extract_text_from_messages(result.get("messages", []))
            if greeting:
                console.print(Panel(
                    Markdown(format_agent_response(greeting)),
                    title="Agent",
                    border_style="green",
                ))
            continue

        # Send user message to agent
        try:
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
            )
            response = extract_text_from_messages(result.get("messages", []))
            if response:
                console.print(Panel(
                    Markdown(format_agent_response(response)),
                    title="Agent",
                    border_style="green",
                ))
            else:
                # Agent might have only made tool calls with no text response
                console.print("[dim]Agent is processing...[/dim]")

        except Exception as e:
            logger.exception("Agent error")
            console.print(f"[red]Error: {e}[/red]")


def main():
    """Entry point for the CLI."""
    import argparse
    parser = argparse.ArgumentParser(description="ACORD Insurance Intake Agent CLI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--debug", action="store_true", help="Debug logging")
    args = parser.parse_args()

    log_level = logging.WARNING
    if args.verbose:
        log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_chat()


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_cli.py -v`

Expected: all 5 tests PASS

**Step 5: Commit**

```bash
git add Custom_model_fa_pf/cli.py Custom_model_fa_pf/tests/test_cli.py
git commit -m "feat(agent): add Rich CLI chat interface with /status and /reset commands"
```

---

## Phase 2: Visual Form Guide

### Task 9: Create visual guide module

**Files:**
- Create: `Custom_model_fa_pf/visual_guide.py`
- Create: `Custom_model_fa_pf/tests/test_visual_guide.py`

**Step 1: Write the failing test**

Create `Custom_model_fa_pf/tests/test_visual_guide.py`:

```python
"""Tests for visual form guide generation."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from Custom_model_fa_pf.visual_guide import (
    generate_field_overlay,
    FieldHighlight,
)
from Custom_model_fa_pf.config import FORM_TEMPLATES_DIR


class TestFieldHighlight:
    def test_create_highlight(self):
        h = FieldHighlight(
            field_name="NamedInsured_FullName_A",
            value="Acme LLC",
            rect=(100.0, 200.0, 400.0, 220.0),
            page=0,
            status="confirmed",
        )
        assert h.color == (0, 200, 0, 80)  # Green for confirmed

    def test_pending_is_yellow(self):
        h = FieldHighlight(
            field_name="test", value="", rect=(0, 0, 100, 20),
            page=0, status="pending",
        )
        assert h.color == (255, 200, 0, 80)

    def test_error_is_red(self):
        h = FieldHighlight(
            field_name="test", value="BAD", rect=(0, 0, 100, 20),
            page=0, status="error",
        )
        assert h.color == (255, 0, 0, 80)


@pytest.mark.skipif(
    not FORM_TEMPLATES_DIR.exists(),
    reason="Template directory not found",
)
class TestGenerateOverlay:
    def test_generate_for_form_125(self):
        from Custom_model_fa_pf.form_reader import find_template, read_pdf_form

        path = find_template("125")
        if path is None:
            pytest.skip("Form 125 template not found")

        catalog = read_pdf_form(path)
        # Pick a few fields that have rects
        fields_with_rects = [
            f for f in catalog.fields.values() if f.rect is not None
        ][:5]

        highlights = [
            FieldHighlight(
                field_name=f.name,
                value="Test Value",
                rect=f.rect,
                page=f.page,
                status="confirmed",
            )
            for f in fields_with_rects
        ]

        images = generate_field_overlay(path, highlights)
        assert len(images) > 0
        # Each image should be a bytes object (PNG)
        for img_bytes in images.values():
            assert img_bytes[:4] == b'\x89PNG'
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_visual_guide.py -v`

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement visual guide module**

Create `Custom_model_fa_pf/visual_guide.py`:

```python
"""Visual form guide — annotated PDF images showing where data goes."""

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Status -> RGBA color
STATUS_COLORS = {
    "confirmed": (0, 200, 0, 80),       # Green
    "pending": (255, 200, 0, 80),        # Yellow
    "error": (255, 0, 0, 80),            # Red
    "empty": (200, 200, 200, 40),        # Light gray
}


@dataclass
class FieldHighlight:
    """A field to highlight on the form image."""
    field_name: str
    value: str
    rect: Tuple[float, float, float, float]  # x0, y0, x1, y1
    page: int
    status: str = "confirmed"

    @property
    def color(self) -> Tuple[int, int, int, int]:
        return STATUS_COLORS.get(self.status, STATUS_COLORS["empty"])


def generate_field_overlay(
    pdf_path: Path,
    highlights: List[FieldHighlight],
    dpi: int = 150,
) -> Dict[int, bytes]:
    """Generate annotated PNG images for each page of a PDF.

    Args:
        pdf_path: Path to the template PDF
        highlights: List of FieldHighlight to draw on the pages
        dpi: Resolution for rendering

    Returns:
        Dict of page_number -> PNG bytes
    """
    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return {}

    doc = fitz.open(str(pdf_path))
    page_highlights: Dict[int, List[FieldHighlight]] = {}

    for h in highlights:
        page_highlights.setdefault(h.page, []).append(h)

    result = {}
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render the page to a pixmap
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Draw highlights for this page
        for h in page_highlights.get(page_num, []):
            r, g, b, a = h.color
            # Scale rect coordinates to pixel space
            x0 = int(h.rect[0] * zoom)
            y0 = int(h.rect[1] * zoom)
            x1 = int(h.rect[2] * zoom)
            y1 = int(h.rect[3] * zoom)

            # Draw a semi-transparent rectangle using shape overlay
            # PyMuPDF pixmap doesn't support alpha blending directly,
            # so we use page annotations instead
            rect = fitz.Rect(h.rect)
            # Draw colored rectangle on the page before rendering
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(
                color=(r / 255, g / 255, b / 255),
                fill=(r / 255, g / 255, b / 255),
                fill_opacity=a / 255,
                width=0.5,
            )
            shape.commit()

        # Re-render with annotations
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert to PNG bytes
        result[page_num] = pix.tobytes("png")

    doc.close()
    return result
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_visual_guide.py -v`

Expected: PASS (unit tests pass; integration test passes if templates exist)

**Step 5: Commit**

```bash
git add Custom_model_fa_pf/visual_guide.py Custom_model_fa_pf/tests/test_visual_guide.py
git commit -m "feat: add visual form guide with color-coded field overlays"
```

---

## Phase 3: Integration Testing

### Task 10: Run full test suite

**Step 1: Run all existing tests to verify nothing is broken**

Run:
```bash
cd /home/inevoai/Development/Accord-Model-Building
.venv/bin/python -m pytest Custom_model_fa_pf/tests/ -v --tb=short
```

Expected: All existing tests pass. New tests pass (except those requiring LLM which will be skipped).

**Step 2: Test the CLI manually (requires Ollama running)**

Run:
```bash
.venv/bin/python -m Custom_model_fa_pf.cli --verbose
```

Expected: Agent greets you and you can type messages. Type `/quit` to exit.

**Step 3: Commit if any fixes were needed**

```bash
git add -A
git commit -m "test: verify full test suite passes with agent modules"
```

---

## Phase 4: Scanned Document Support (Future)

### Task 11: Wire parent project VLM extraction as scan_document tool

**Files:**
- Modify: `Custom_model_fa_pf/agent/tools.py` (add scan_document tool)
- Create: `Custom_model_fa_pf/tests/test_scan_tool.py`

**Depends on:** vLLM serving the finetuned model

**Step 1: Write the failing test**

```python
"""Tests for scan_document tool."""

import pytest
from Custom_model_fa_pf.agent.tools import scan_document_tool


class TestScanDocumentTool:
    def test_tool_exists(self):
        assert scan_document_tool is not None
        assert scan_document_tool.name == "scan_document"

    def test_nonexistent_file_returns_error(self):
        import json
        result = scan_document_tool.invoke({"image_path": "/nonexistent/file.pdf"})
        parsed = json.loads(result)
        assert "error" in parsed
```

**Step 2: Implement scan_document tool**

Add to `Custom_model_fa_pf/agent/tools.py`:

```python
@tool
def scan_document(image_path: str, form_type: str = "auto") -> str:
    """Extract field values from a scanned ACORD form image using OCR + finetuned VLM.

    Uses the parent project's extraction pipeline: Surya OCR -> VLM (Qwen3-VL finetuned
    on 8,403 ACORD form samples) -> structured field extraction.

    Args:
        image_path: Path to the scanned form image (PDF or image file)
        form_type: ACORD form number for schema ('auto' to detect, or '125', '127', etc.)
    """
    from pathlib import Path as PPath

    path = PPath(image_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {image_path}"})

    try:
        # Import from parent project
        from extractor import ACORDExtractor
        from llm_engine import LLMEngine

        llm = LLMEngine(
            model="acord-vlm",  # Finetuned VLM
            keep_models_loaded=True,
            structured_json=True,
        )
        extractor = ACORDExtractor(llm_engine=llm)
        results = extractor.extract(str(path), form_type=form_type if form_type != "auto" else None)

        return json.dumps({
            "status": "success",
            "fields_extracted": len(results),
            "fields": results,
        })
    except ImportError:
        return json.dumps({"error": "Parent project extraction pipeline not available"})
    except Exception as e:
        return json.dumps({"error": f"Extraction failed: {e}"})
```

**Step 3: Run tests, commit**

---

## Phase 5: API Updates (Future)

### Task 12: Add agent chat endpoint to API

**Files:**
- Modify: `Custom_model_fa_pf/api.py`

Add a WebSocket or SSE endpoint for real-time agent chat:

```python
@app.websocket("/api/v1/agent/chat")
async def agent_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time agent conversations."""
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    agent = create_agent()
    config = {"configurable": {"thread_id": f"ws:{session_id}"}}

    # Send initial greeting
    initial_state = create_initial_state(session_id)
    result = agent.invoke(initial_state, config=config)
    greeting = extract_text_from_messages(result.get("messages", []))
    await websocket.send_json({"type": "message", "content": greeting})

    # Chat loop
    while True:
        data = await websocket.receive_json()
        user_msg = data.get("content", "")
        result = agent.invoke(
            {"messages": [HumanMessage(content=user_msg)]},
            config=config,
        )
        response = extract_text_from_messages(result.get("messages", []))
        await websocket.send_json({"type": "message", "content": response})
```

---

## Summary of All Files

| # | File | Action | Task |
|---|------|--------|------|
| 1 | `requirements.txt` | MODIFY | Task 1 |
| 2 | `Custom_model_fa_pf/config.py` | MODIFY | Task 2 |
| 3 | `Custom_model_fa_pf/agent/__init__.py` | CREATE | Task 3 |
| 4 | `Custom_model_fa_pf/agent/state.py` | CREATE | Task 3 |
| 5 | `Custom_model_fa_pf/agent/prompts.py` | CREATE | Task 4 |
| 6 | `Custom_model_fa_pf/agent/confidence.py` | CREATE | Task 5 |
| 7 | `Custom_model_fa_pf/agent/tools.py` | CREATE | Task 6 |
| 8 | `Custom_model_fa_pf/agent/_llm_provider.py` | CREATE | Task 6 |
| 9 | `Custom_model_fa_pf/agent/nodes.py` | CREATE | Task 7 |
| 10 | `Custom_model_fa_pf/agent/graph.py` | CREATE | Task 7 |
| 11 | `Custom_model_fa_pf/cli.py` | CREATE | Task 8 |
| 12 | `Custom_model_fa_pf/visual_guide.py` | CREATE | Task 9 |
| 13 | `Custom_model_fa_pf/tests/test_agent_config.py` | CREATE | Task 2 |
| 14 | `Custom_model_fa_pf/tests/test_agent_state.py` | CREATE | Task 3 |
| 15 | `Custom_model_fa_pf/tests/test_agent_prompts.py` | CREATE | Task 4 |
| 16 | `Custom_model_fa_pf/tests/test_confidence.py` | CREATE | Task 5 |
| 17 | `Custom_model_fa_pf/tests/test_agent_tools.py` | CREATE | Task 6 |
| 18 | `Custom_model_fa_pf/tests/test_agent_graph.py` | CREATE | Task 7 |
| 19 | `Custom_model_fa_pf/tests/test_cli.py` | CREATE | Task 8 |
| 20 | `Custom_model_fa_pf/tests/test_visual_guide.py` | CREATE | Task 9 |

## Execution Order

Tasks 1-10 form Phase 1-3 (the core MVP). They should be executed in order since each builds on the previous. Tasks 11-12 are future phases that depend on external services (vLLM, WebSocket).

**Critical path:** Task 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10
