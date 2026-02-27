"""Quality validators for agent fine-tuning dataset.

Runs 6 independent validators on assembled conversations and produces a
composite quality score.  Used to filter training data before fine-tuning:
  >= 0.95  include
  0.85-0.95  flag for review
  < 0.85  reject

Usage:
    from finetune.agent.validate_dataset import validate_conversation, validate_dataset
    score = validate_conversation(conv, scenario)
    report = validate_dataset(conversations, scenarios)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from finetune.agent.scenario_generator import ConversationScenario
from finetune.agent.skeleton_builder import PHASE_ORDER, PHASE_TOOLS

# ---------------------------------------------------------------------------
# Valid tool names (superset of PHASE_TOOLS values)
# ---------------------------------------------------------------------------

VALID_TOOL_NAMES = {
    "save_field",
    "validate_fields",
    "classify_lobs",
    "assign_forms",
    "extract_entities",
    "analyze_gaps",
    "process_document",
    "fill_forms",
    "read_form",
    "map_fields",
    "match_carriers",
    "generate_quotes",
    "compare_quotes",
    "select_quote",
    "submit_bind_request",
    "build_quote_request",
}

# Weights per validator
_WEIGHTS = {
    "structural": 0.15,
    "phase_consistency": 0.15,
    "anti_hallucination": 0.25,
    "tool_ordering": 0.15,
    "behavioral": 0.20,
    "form_state_consistency": 0.10,
}


# ---------------------------------------------------------------------------
# ValidationScore dataclass
# ---------------------------------------------------------------------------


@dataclass
class ValidationScore:
    structural: float = 1.0
    phase_consistency: float = 1.0
    anti_hallucination: float = 1.0
    tool_ordering: float = 1.0
    behavioral: float = 1.0
    form_state_consistency: float = 1.0
    composite: float = 1.0
    issues: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(val: float) -> float:
    """Clamp a value between 0.0 and 1.0."""
    return max(0.0, min(1.0, val))


def _extract_tool_calls(messages: list[dict]) -> list[dict]:
    """Extract all tool_call dicts from assistant messages."""
    calls: list[dict] = []
    for msg in messages:
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                calls.append(tc)
    return calls


def _extract_tool_responses(messages: list[dict]) -> list[dict]:
    """Extract all tool-role messages."""
    return [m for m in messages if m.get("role") == "tool"]


def _parse_tool_args(tc: dict) -> dict:
    """Parse the arguments JSON from a tool call, returning {} on error."""
    raw = tc.get("function", {}).get("arguments", "{}")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _get_tool_name(tc: dict) -> str:
    """Get the tool function name from a tool call dict."""
    return tc.get("function", {}).get("name", "")


def _get_save_field_values(messages: list[dict]) -> list[tuple[str, str]]:
    """Return list of (field_name, value) from all save_field tool calls."""
    results: list[tuple[str, str]] = []
    for msg in messages:
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if _get_tool_name(tc) == "save_field":
                    args = _parse_tool_args(tc)
                    fn = args.get("field_name", "")
                    val = args.get("value", "")
                    if fn:
                        results.append((fn, val))
    return results


def _collect_user_text(messages: list[dict]) -> str:
    """Concatenate all user message content into a single lower-case string."""
    parts: list[str] = []
    for msg in messages:
        if msg.get("role") == "user" and msg.get("content"):
            parts.append(str(msg["content"]))
    return "\n".join(parts).lower()


def _collect_tool_response_text(messages: list[dict]) -> str:
    """Concatenate all tool response content into a single lower-case string."""
    parts: list[str] = []
    for msg in messages:
        if msg.get("role") == "tool" and msg.get("content"):
            parts.append(str(msg["content"]))
    return "\n".join(parts).lower()


# ---------------------------------------------------------------------------
# V1: Structural Validator
# ---------------------------------------------------------------------------


def _validate_structural(messages: list[dict]) -> tuple[float, list[str]]:
    """Check structural well-formedness.

    - system first
    - correct role sequence (no consecutive user messages, tool only after tool_calls)
    - tool_call_ids match between assistant tool_calls and tool responses
    - no 'state' key in tool call arguments
    - all tool names are valid

    Returns (score, issues).
    """
    score = 1.0
    issues: list[str] = []

    if not messages:
        issues.append("structural: empty message list")
        return 0.0, issues

    # Check system first
    if messages[0].get("role") != "system":
        score -= 0.2
        issues.append("structural: first message is not role=system")

    # Check messages are valid dicts with role
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            score -= 0.2
            issues.append(f"structural: message {i} is not a dict")
            continue
        if "role" not in msg:
            score -= 0.2
            issues.append(f"structural: message {i} missing 'role' key")

    # Collect all tool_call IDs from assistant messages
    expected_tool_call_ids: set[str] = set()
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tc_id = tc.get("id", "")
                if tc_id:
                    expected_tool_call_ids.add(tc_id)

    # Collect all tool response IDs
    actual_tool_response_ids: set[str] = set()
    for msg in messages:
        if msg.get("role") == "tool":
            resp_id = msg.get("tool_call_id", "")
            if resp_id:
                actual_tool_response_ids.add(resp_id)

    # Check that every tool response ID matches an expected tool_call ID
    orphan_ids = actual_tool_response_ids - expected_tool_call_ids
    if orphan_ids:
        score -= 0.2
        issues.append(
            f"structural: {len(orphan_ids)} tool response(s) with "
            f"unmatched tool_call_id"
        )

    # Check role sequence: no two consecutive user messages
    prev_role = None
    for i, msg in enumerate(messages):
        role = msg.get("role")
        if role == "user" and prev_role == "user":
            score -= 0.2
            issues.append(f"structural: consecutive user messages at index {i}")
            break  # count once
        # tool messages should only appear after an assistant with tool_calls
        if role == "tool" and prev_role not in ("assistant", "tool"):
            score -= 0.2
            issues.append(
                f"structural: tool message at index {i} not preceded by "
                f"assistant or tool"
            )
            break  # count once
        prev_role = role

    # Check no 'state' key in tool call arguments
    for msg in messages:
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                args = _parse_tool_args(tc)
                if "state" in args:
                    score -= 0.2
                    issues.append(
                        f"structural: 'state' key found in tool call "
                        f"arguments for {_get_tool_name(tc)}"
                    )
                    break
            else:
                continue
            break

    # Check all tool names are valid
    all_tool_calls = _extract_tool_calls(messages)
    for tc in all_tool_calls:
        name = _get_tool_name(tc)
        if name and name not in VALID_TOOL_NAMES:
            score -= 0.2
            issues.append(f"structural: invalid tool name '{name}'")
            break  # count once

    return _clamp(score), issues


# ---------------------------------------------------------------------------
# V2: Phase Consistency Validator
# ---------------------------------------------------------------------------


def _validate_phase_consistency(
    messages: list[dict],
    metadata: dict,
) -> tuple[float, list[str]]:
    """Check phase ordering and tool-phase compatibility.

    - phases in metadata follow PHASE_ORDER (no backward transitions)
    - tools used in each phase are valid per PHASE_TOOLS

    Returns (score, issues).
    """
    score = 1.0
    issues: list[str] = []

    phases = metadata.get("phases", [])
    if not phases:
        # No phase info: can't validate
        return 1.0, []

    # Check phase ordering (no backward jumps)
    phase_indices = {p: i for i, p in enumerate(PHASE_ORDER)}
    last_idx = -1
    for p in phases:
        idx = phase_indices.get(p, -1)
        if idx == -1:
            # Unknown phase: flag it
            score -= 0.2
            issues.append(f"phase_consistency: unknown phase '{p}'")
            continue
        if idx < last_idx:
            score -= 0.2
            issues.append(
                f"phase_consistency: backward transition to '{p}' "
                f"after reaching phase index {last_idx}"
            )
        last_idx = max(last_idx, idx)

    # Check tools used per phase. We need to correlate tool calls with phases.
    # Since metadata.tools_used is a flat list, and we don't have per-turn
    # phase info in the messages, we do a best-effort check: every tool in
    # metadata.tools_used should be valid for at least one of the listed phases.
    tools_used = set(metadata.get("tools_used", []))
    all_valid_tools: set[str] = set()
    for p in phases:
        all_valid_tools.update(PHASE_TOOLS.get(p, []))
    # Also include tools that are globally valid but not phase-specific
    all_valid_tools.update(VALID_TOOL_NAMES)

    invalid_phase_tools = tools_used - all_valid_tools
    if invalid_phase_tools:
        score -= 0.2
        issues.append(
            f"phase_consistency: tools not valid for any listed phase: "
            f"{invalid_phase_tools}"
        )

    return _clamp(score), issues


# ---------------------------------------------------------------------------
# V3: Anti-Hallucination Validator
# ---------------------------------------------------------------------------


def _validate_anti_hallucination(
    messages: list[dict],
    scenario: Optional[ConversationScenario] = None,
) -> tuple[float, list[str]]:
    """Check that save_field values trace to user messages or scenario data.

    - Every save_field value should appear (case-insensitive) in a prior user
      message or in the scenario entity data.
    - Address-like values not found in user text are flagged harder.

    Returns (score, issues).
    """
    score = 1.0
    issues: list[str] = []

    user_text = _collect_user_text(messages)
    tool_response_text = _collect_tool_response_text(messages)

    # Flatten scenario data into a single text blob for substring search
    scenario_text = ""
    if scenario:
        scenario_text = json.dumps(
            {
                "business": scenario.business,
                "policy": scenario.policy,
                "vehicles": scenario.vehicles,
                "drivers": scenario.drivers,
                "coverages": scenario.coverages,
                "locations": scenario.locations,
                "loss_history": scenario.loss_history,
                "prior_insurance": scenario.prior_insurance,
                "lobs": scenario.lobs,
            },
            default=str,
        ).lower()

    save_field_pairs = _get_save_field_values(messages)
    if not save_field_pairs:
        # No save_field calls: nothing to validate
        return 1.0, []

    for field_name, value in save_field_pairs:
        if not value:
            continue
        val_lower = str(value).lower().strip()

        # Skip very short values (single char, "yes", "no") — too generic
        if len(val_lower) <= 2:
            continue

        # Check if value appears in user messages
        found_in_user = val_lower in user_text
        # Check if value appears in scenario data
        found_in_scenario = val_lower in scenario_text if scenario_text else False
        # Check if value appears in tool responses (for derived values)
        found_in_tools = val_lower in tool_response_text

        if not (found_in_user or found_in_scenario or found_in_tools):
            # Harsher penalty for address-like hallucinations
            penalty = 0.3
            score -= penalty
            issues.append(
                f"anti_hallucination: save_field '{field_name}' value "
                f"'{value}' not found in user messages or scenario data"
            )

    return _clamp(score), issues


# ---------------------------------------------------------------------------
# V4: Tool Ordering Validator
# ---------------------------------------------------------------------------


def _validate_tool_ordering(messages: list[dict]) -> tuple[float, list[str]]:
    """Check that tools are called in a sensible order.

    - classify_lobs before assign_forms
    - analyze_gaps after some save_field calls
    - fill_forms after analyze_gaps or review phase
    - select_quote after quoting data available
    - submit_bind_request after select_quote

    Returns (score, issues).
    """
    score = 1.0
    issues: list[str] = []

    # Build an ordered list of tool calls
    tool_order: list[str] = []
    for msg in messages:
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                name = _get_tool_name(tc)
                if name:
                    tool_order.append(name)

    if not tool_order:
        return 1.0, []

    # Build index maps: first occurrence of each tool
    first_occurrence: dict[str, int] = {}
    for i, name in enumerate(tool_order):
        if name not in first_occurrence:
            first_occurrence[name] = i

    # classify_lobs must come before assign_forms
    if "classify_lobs" in first_occurrence and "assign_forms" in first_occurrence:
        if first_occurrence["classify_lobs"] > first_occurrence["assign_forms"]:
            score -= 0.25
            issues.append(
                "tool_ordering: classify_lobs called after assign_forms"
            )

    # analyze_gaps should come after at least one save_field
    if "analyze_gaps" in first_occurrence and "save_field" in first_occurrence:
        if first_occurrence["analyze_gaps"] < first_occurrence["save_field"]:
            score -= 0.25
            issues.append(
                "tool_ordering: analyze_gaps called before any save_field"
            )

    # fill_forms should come after analyze_gaps (if both present)
    if "fill_forms" in first_occurrence and "analyze_gaps" in first_occurrence:
        if first_occurrence["fill_forms"] < first_occurrence["analyze_gaps"]:
            score -= 0.25
            issues.append(
                "tool_ordering: fill_forms called before analyze_gaps"
            )

    # select_quote must come after some quoting-related context
    # (we check that select_quote is not the first tool)
    if "select_quote" in first_occurrence:
        if first_occurrence["select_quote"] == 0:
            score -= 0.25
            issues.append(
                "tool_ordering: select_quote called as first tool (no prior context)"
            )

    # submit_bind_request must come after select_quote
    if (
        "submit_bind_request" in first_occurrence
        and "select_quote" in first_occurrence
    ):
        if first_occurrence["submit_bind_request"] < first_occurrence["select_quote"]:
            score -= 0.25
            issues.append(
                "tool_ordering: submit_bind_request called before select_quote"
            )

    return _clamp(score), issues


# ---------------------------------------------------------------------------
# V5: Behavioral Validator
# ---------------------------------------------------------------------------


def _validate_behavioral(messages: list[dict]) -> tuple[float, list[str]]:
    """Check assistant behavioral quality.

    - Assistant content should ask at most ~2 question marks
    - No re-asking of confirmed fields
    - Corrections should trigger save_field

    Returns (score, issues).
    """
    score = 1.0
    issues: list[str] = []

    # Track saved/confirmed fields
    saved_fields: set[str] = set()
    confirmed_fields: set[str] = set()

    for i, msg in enumerate(messages):
        # Track save_field calls
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if _get_tool_name(tc) == "save_field":
                    args = _parse_tool_args(tc)
                    fn = args.get("field_name", "")
                    if fn:
                        saved_fields.add(fn)

        # Check assistant content messages
        if msg.get("role") == "assistant" and msg.get("content"):
            content = str(msg["content"])

            # Count question marks
            q_count = content.count("?")
            if q_count > 2:
                score -= 0.15
                issues.append(
                    f"behavioral: assistant message at index {i} has "
                    f"{q_count} questions (max 2)"
                )
                break  # count once to avoid over-penalizing

    # Check if user mentions "change" or "correction" and next assistant has save_field
    for i in range(len(messages) - 1):
        msg = messages[i]
        if msg.get("role") == "user" and msg.get("content"):
            text = str(msg["content"]).lower()
            if any(kw in text for kw in ["change", "correct", "update", "fix"]):
                # Look at the next assistant message
                next_msg = messages[i + 1] if i + 1 < len(messages) else None
                if next_msg and next_msg.get("role") == "assistant":
                    has_save = False
                    if next_msg.get("tool_calls"):
                        for tc in next_msg["tool_calls"]:
                            if _get_tool_name(tc) == "save_field":
                                has_save = True
                                break
                    # Also check the message after (some patterns have
                    # assistant content -> assistant tool_calls)
                    if not has_save and i + 2 < len(messages):
                        after = messages[i + 2]
                        if after.get("tool_calls"):
                            for tc in after["tool_calls"]:
                                if _get_tool_name(tc) == "save_field":
                                    has_save = True
                                    break

                    if not has_save:
                        score -= 0.15
                        issues.append(
                            f"behavioral: user requested correction at "
                            f"index {i} but no save_field followed"
                        )
                        break  # count once

    return _clamp(score), issues


# ---------------------------------------------------------------------------
# V6: Form State Consistency Validator
# ---------------------------------------------------------------------------


def _validate_form_state_consistency(
    messages: list[dict],
) -> tuple[float, list[str]]:
    """Check that form_state accumulation is consistent.

    - Every field that appeared in a save_field tool call should have a
      corresponding tool response confirming it was saved.
    - No phantom fields (tool responses claiming saves that weren't requested).

    Returns (score, issues).
    """
    score = 1.0
    issues: list[str] = []

    # Collect all save_field request field_names
    requested_saves: set[str] = set()
    for msg in messages:
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if _get_tool_name(tc) == "save_field":
                    args = _parse_tool_args(tc)
                    fn = args.get("field_name", "")
                    if fn:
                        requested_saves.add(fn)

    # Collect all confirmed saves from tool responses
    # We look at tool responses for save_field that have "status": "saved"
    confirmed_saves: set[str] = set()
    for msg in messages:
        if msg.get("role") == "tool" and msg.get("content"):
            try:
                content = json.loads(msg["content"])
                if isinstance(content, dict) and content.get("status") == "saved":
                    fn = content.get("field_name", "")
                    if fn:
                        confirmed_saves.add(fn)
            except (json.JSONDecodeError, TypeError):
                pass

    # Check for phantom fields: confirmed but never requested
    phantom = confirmed_saves - requested_saves
    for fn in phantom:
        score -= 0.25
        issues.append(
            f"form_state_consistency: phantom field '{fn}' "
            f"in tool response but not in any save_field request"
        )

    return _clamp(score), issues


# ---------------------------------------------------------------------------
# Main validate_conversation
# ---------------------------------------------------------------------------


def validate_conversation(
    conversation: dict,
    scenario: Optional[ConversationScenario] = None,
) -> ValidationScore:
    """Run all 6 validators on a conversation and return composite score.

    Args:
        conversation: {"messages": [...], "metadata": {...}} from assembler.
        scenario: If provided, used for anti-hallucination checks.

    Returns:
        ValidationScore with per-validator scores, composite, and issues.
    """
    messages = conversation.get("messages", [])
    metadata = conversation.get("metadata", {})

    all_issues: list[str] = []

    # V1: Structural
    s1, iss1 = _validate_structural(messages)
    all_issues.extend(iss1)

    # V2: Phase Consistency
    s2, iss2 = _validate_phase_consistency(messages, metadata)
    all_issues.extend(iss2)

    # V3: Anti-Hallucination
    s3, iss3 = _validate_anti_hallucination(messages, scenario)
    all_issues.extend(iss3)

    # V4: Tool Ordering
    s4, iss4 = _validate_tool_ordering(messages)
    all_issues.extend(iss4)

    # V5: Behavioral
    s5, iss5 = _validate_behavioral(messages)
    all_issues.extend(iss5)

    # V6: Form State Consistency
    s6, iss6 = _validate_form_state_consistency(messages)
    all_issues.extend(iss6)

    composite = (
        _WEIGHTS["structural"] * s1
        + _WEIGHTS["phase_consistency"] * s2
        + _WEIGHTS["anti_hallucination"] * s3
        + _WEIGHTS["tool_ordering"] * s4
        + _WEIGHTS["behavioral"] * s5
        + _WEIGHTS["form_state_consistency"] * s6
    )

    return ValidationScore(
        structural=s1,
        phase_consistency=s2,
        anti_hallucination=s3,
        tool_ordering=s4,
        behavioral=s5,
        form_state_consistency=s6,
        composite=_clamp(composite),
        issues=all_issues,
    )


# ---------------------------------------------------------------------------
# validate_dataset
# ---------------------------------------------------------------------------


def validate_dataset(
    conversations: list[dict],
    scenarios: Optional[list[ConversationScenario]] = None,
) -> dict:
    """Validate an entire dataset and return a quality report.

    Args:
        conversations: List of {"messages": [...], "metadata": {...}}.
        scenarios: Optional parallel list of scenarios for anti-hallucination.

    Returns:
        {
            "total": int,
            "included": int,    # score >= 0.95
            "flagged": int,     # 0.85 <= score < 0.95
            "rejected": int,    # score < 0.85
            "avg_composite": float,
            "avg_by_validator": {
                "structural": float,
                "phase_consistency": float,
                "anti_hallucination": float,
                "tool_ordering": float,
                "behavioral": float,
                "form_state_consistency": float,
            },
            "rejection_reasons": list[str],
        }
    """
    total = len(conversations)
    included = 0
    flagged = 0
    rejected = 0

    sum_composite = 0.0
    sum_by_validator: dict[str, float] = {
        "structural": 0.0,
        "phase_consistency": 0.0,
        "anti_hallucination": 0.0,
        "tool_ordering": 0.0,
        "behavioral": 0.0,
        "form_state_consistency": 0.0,
    }

    rejection_reasons: list[str] = []

    for i, conv in enumerate(conversations):
        scenario = scenarios[i] if scenarios and i < len(scenarios) else None
        score = validate_conversation(conv, scenario)

        sum_composite += score.composite
        sum_by_validator["structural"] += score.structural
        sum_by_validator["phase_consistency"] += score.phase_consistency
        sum_by_validator["anti_hallucination"] += score.anti_hallucination
        sum_by_validator["tool_ordering"] += score.tool_ordering
        sum_by_validator["behavioral"] += score.behavioral
        sum_by_validator["form_state_consistency"] += score.form_state_consistency

        if score.composite >= 0.95:
            included += 1
        elif score.composite >= 0.85:
            flagged += 1
        else:
            rejected += 1
            rejection_reasons.extend(score.issues)

    avg_composite = sum_composite / total if total > 0 else 0.0
    avg_by_validator = {
        k: v / total if total > 0 else 0.0 for k, v in sum_by_validator.items()
    }

    return {
        "total": total,
        "included": included,
        "flagged": flagged,
        "rejected": rejected,
        "avg_composite": avg_composite,
        "avg_by_validator": avg_by_validator,
        "rejection_reasons": rejection_reasons,
    }
