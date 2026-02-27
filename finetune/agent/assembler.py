"""Conversation assembler for agent fine-tuning dataset.

Takes a ConversationScenario + optional skeleton and assembles a complete
training conversation in OpenAI chat format (list of messages with system,
user, assistant, and tool roles).

Handles:
- System prompt generation (once at position 0)
- User message rendering from templates
- Tool call injection with matching responses
- Assistant message rendering
- Difficulty/curriculum classification
- Sliding-window splitting for long conversations

Usage:
    from finetune.agent.assembler import assemble_conversation
    conv = assemble_conversation(scenario)
    # conv = {"messages": [...], "metadata": {...}}
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from finetune.agent.conversation_templates import (
    render_assistant_template,
    render_bulk_message,
    render_user_template,
)
from finetune.agent.scenario_generator import ConversationScenario
from finetune.agent.skeleton_builder import TurnSkeleton, build_skeleton
from finetune.agent.system_prompt_builder import build_training_system_prompt
from finetune.agent.tool_injector import inject_tool_calls


# ---------------------------------------------------------------------------
# Greeting message pools (no template topic matches perfectly)
# ---------------------------------------------------------------------------

_GREETING_USER_MESSAGES = [
    "Hi, I need help with commercial insurance",
    "Hello, I'm looking for insurance for my business",
    "Hey there, I need to get some insurance quotes",
    "Hi, can you help me with a commercial insurance application?",
    "Good morning, I need to set up insurance for my company",
    "Hello, I'd like to get commercial insurance",
    "Hi, I'm interested in getting insurance coverage for my business",
]


# ---------------------------------------------------------------------------
# Helpers: user message generation
# ---------------------------------------------------------------------------


def _render_user_message(
    turn: TurnSkeleton,
    scenario: ConversationScenario,
    rng: random.Random,
) -> str:
    """Render a user message for the given turn skeleton.

    Dispatches to the appropriate template based on the turn's action and phase.
    """
    action = turn.action
    seed = rng.randint(0, 2**31)

    # Greeting turns
    if action == "greet":
        return rng.choice(_GREETING_USER_MESSAGES)

    # Document upload
    if action == "process_document":
        from finetune.agent.conversation_templates import DOCUMENT_TYPE_DISPLAY
        upload_info = turn.user_fields.get("_document_upload", {})
        doc_type = upload_info.get("document_type", "document")
        display_name = DOCUMENT_TYPE_DISPLAY.get(doc_type, doc_type)
        return render_user_template("upload_document", seed=seed, document_type=display_name)

    # Bulk extract
    if action == "bulk_extract":
        return render_bulk_message(turn.user_fields, seed=seed)

    # Confirm data
    if turn.user_fields.get("confirmation"):
        return render_user_template("confirm_data", seed=seed)

    # Quote selection
    if action == "select_quote":
        carrier = "Progressive Commercial"
        if scenario.prior_insurance:
            carrier = scenario.prior_insurance[0].get("carrier_name", carrier)
        return render_user_template("select_quote", seed=seed, carrier=carrier)

    # Bind confirmation
    if turn.user_fields.get("bind_confirmation"):
        return render_user_template("confirm_binding", seed=seed)

    # Present quotes (user asking for quotes)
    if action == "present_quotes":
        return render_user_template("ask_for_quotes", seed=seed)

    # Deliver policy / complete forms (user doesn't say much)
    if action in ("deliver_policy", "complete_forms"):
        return render_user_template("confirm_data", seed=seed)

    # Present review (user triggers review)
    if action == "present_review":
        return render_user_template("confirm_data", seed=seed)

    # Fill forms (user confirms)
    if action == "fill_forms":
        return render_user_template("confirm_data", seed=seed)

    # Classify LOBs
    if action == "classify_lobs":
        lob_desc = ", ".join(scenario.lobs)
        return render_user_template(
            "provide_coverage_needs", seed=seed, coverage_type=lob_desc
        )

    # Analyze gaps (assistant-initiated, user says something generic)
    if action == "analyze_gaps":
        return render_user_template("confirm_data", seed=seed)

    # Save fields - pick template based on what fields are present
    if action == "save_fields" and turn.user_fields:
        return _render_field_based_user_message(turn, seed, rng)

    # Fallback: generic confirmation
    return render_user_template("confirm_data", seed=seed)


def _render_field_based_user_message(
    turn: TurnSkeleton,
    seed: int,
    rng: random.Random,
) -> str:
    """Render a user message based on the specific fields being provided."""
    fields = turn.user_fields

    # Business name
    if "business_name" in fields and len(fields) <= 2:
        kwargs: Dict[str, Any] = {"business_name": fields["business_name"]}
        return render_user_template("provide_business_name", seed=seed, **kwargs)

    # Address fields
    if any(k.startswith("mailing_") for k in fields):
        street = fields.get("mailing_street", "")
        city = fields.get("mailing_city", "")
        state = fields.get("mailing_state", "")
        zip_code = fields.get("mailing_zip", "")
        if street and city:
            return render_user_template(
                "provide_address",
                seed=seed,
                street=street,
                city=city,
                state=state,
                zip=zip_code,
            )

    # Entity type + tax ID
    if "entity_type" in fields and "tax_id" in fields:
        parts = []
        parts.append(
            render_user_template(
                "provide_entity_type",
                seed=seed,
                entity_type=fields["entity_type"],
            )
        )
        parts.append(
            render_user_template(
                "provide_tax_id",
                seed=seed + 1,
                tax_id=fields["tax_id"],
            )
        )
        return ". ".join(parts)

    # Contact info
    if "contact_phone" in fields and "contact_email" in fields:
        return render_user_template(
            "provide_contact",
            seed=seed,
            phone=fields["contact_phone"],
            email=fields["contact_email"],
        )

    # Vehicle fields
    if any(k.startswith("vehicle_") for k in fields):
        # Get the first vehicle's data
        parts = []
        for k, v in fields.items():
            parts.append(f"{k}: {v}")
        return "Here are the vehicle details: " + ", ".join(parts)

    # Driver fields
    if any(k.startswith("driver_") for k in fields):
        parts = []
        for k, v in fields.items():
            parts.append(f"{k}: {v}")
        return "Driver info: " + ", ".join(parts)

    # Effective date
    if "effective_date" in fields:
        return render_user_template(
            "provide_effective_date",
            seed=seed,
            date=fields["effective_date"],
        )

    # Revenue
    if "annual_revenue" in fields:
        return render_user_template(
            "provide_revenue",
            seed=seed,
            revenue=fields["annual_revenue"],
        )

    # Employee count
    if "employee_count" in fields:
        return render_user_template(
            "provide_employees",
            seed=seed,
            count=fields["employee_count"],
        )

    # Generic: list all fields as key-value pairs
    pairs = [f"{k}: {v}" for k, v in fields.items() if v]
    if pairs:
        return "Here's the info: " + ", ".join(pairs)

    return "Here's the information you need"


# ---------------------------------------------------------------------------
# Helpers: assistant message generation
# ---------------------------------------------------------------------------


def _render_assistant_message(
    turn: TurnSkeleton,
    scenario: ConversationScenario,
    form_state: dict,
    tool_interactions: list,
    rng: random.Random,
) -> str:
    """Render the assistant's content message for the given turn."""
    action = turn.action
    seed = rng.randint(0, 2**31)

    # Greeting
    if action == "greet":
        return render_assistant_template("greet_customer", seed=seed)

    # After saving fields: acknowledge and ask next
    if action in ("save_fields", "bulk_extract"):
        # Summarize what was saved
        saved_fields = []
        for interaction in tool_interactions:
            tc = interaction.get("tool_call", {})
            func = tc.get("function", {})
            if func.get("name") == "save_field":
                import json as _json

                try:
                    args = _json.loads(func.get("arguments", "{}"))
                    saved_fields.append(
                        (args.get("field_name", ""), args.get("value", ""))
                    )
                except (ValueError, KeyError):
                    pass

        if saved_fields:
            field_name, value = saved_fields[0]
            next_q = turn.assistant_should_ask
            return render_assistant_template(
                "acknowledge_and_ask_next",
                seed=seed,
                field=field_name,
                value=value,
                next_question=next_q,
            )
        # Fallback
        return render_assistant_template(
            "transition_to_next_phase",
            seed=seed,
            current_phase=turn.phase,
            next_topic=turn.assistant_should_ask,
        )

    # Document processing acknowledgement
    if action == "process_document":
        from finetune.agent.conversation_templates import DOCUMENT_TYPE_DISPLAY
        upload_info = turn.user_fields.get("_document_upload", {})
        doc_type = upload_info.get("document_type", "document")
        display_name = DOCUMENT_TYPE_DISPLAY.get(doc_type, doc_type)
        # Summarize extracted fields
        extracted = upload_info.get("extracted_fields", {})
        if extracted:
            summary_parts = [f"{k}: {v}" for k, v in list(extracted.items())[:5]]
            extracted_summary = ", ".join(summary_parts)
            if len(extracted) > 5:
                extracted_summary += f" (and {len(extracted) - 5} more fields)"
        else:
            extracted_summary = "document processed"
        return render_assistant_template(
            "acknowledge_document",
            seed=seed,
            document_type=display_name,
            extracted_summary=extracted_summary,
            next_question=turn.assistant_should_ask,
        )

    # Gap analysis
    if action == "analyze_gaps":
        # Pull gaps from the tool response if available
        gaps_list = []
        for interaction in tool_interactions:
            resp = interaction.get("tool_response", {})
            if resp.get("role") == "tool":
                import json as _json

                try:
                    content = _json.loads(resp.get("content", "{}"))
                    gaps_list.extend(content.get("missing_critical", []))
                    gaps_list.extend(content.get("missing_important", []))
                except (ValueError, KeyError):
                    pass
        gaps_str = ", ".join(gaps_list) if gaps_list else "a few remaining details"
        first_gap = gaps_list[0] if gaps_list else "the next item"
        return render_assistant_template(
            "present_gap_summary",
            seed=seed,
            gaps=gaps_str,
            first_gap=first_gap,
        )

    # Review
    if action == "present_review":
        summary_parts = []
        for fname, finfo in sorted(form_state.items()):
            val = finfo.get("value", "")
            if val:
                summary_parts.append(f"{fname}: {val}")
        summary = "; ".join(summary_parts[:10])
        if len(summary_parts) > 10:
            summary += f" (and {len(summary_parts) - 10} more fields)"
        return render_assistant_template(
            "present_review", seed=seed, summary=summary or "all collected data"
        )

    # Fill forms
    if action == "fill_forms":
        return render_assistant_template(
            "transition_to_next_phase",
            seed=seed,
            current_phase="form filling",
            next_topic="quoting",
        )

    # Complete forms
    if action == "complete_forms":
        return render_assistant_template(
            "transition_to_next_phase",
            seed=seed,
            current_phase="data collection",
            next_topic="quoting",
        )

    # Present quotes
    if action == "present_quotes":
        carrier = "Progressive Commercial"
        if scenario.prior_insurance:
            carrier = scenario.prior_insurance[0].get("carrier_name", carrier)
        premium = "15,000"
        count = 3
        quote_summary = (
            f"{carrier} at ${premium}/yr, plus {count - 1} other options"
        )
        return render_assistant_template(
            "present_quotes",
            seed=seed,
            count=count,
            quote_summary=quote_summary,
        )

    # Quote selection
    if action == "select_quote":
        carrier = "Progressive Commercial"
        if scenario.prior_insurance:
            carrier = scenario.prior_insurance[0].get("carrier_name", carrier)
        return render_assistant_template(
            "transition_to_next_phase",
            seed=seed,
            current_phase="quote selection",
            next_topic="binding",
        )

    # Submit bind request
    if action == "submit_bind_request":
        carrier = "Progressive Commercial"
        if scenario.prior_insurance:
            carrier = scenario.prior_insurance[0].get("carrier_name", carrier)
        bind_id = f"BR-{scenario.scenario_id.replace('scenario_', '')}"
        return render_assistant_template(
            "confirm_bind",
            seed=seed,
            bind_id=bind_id,
            carrier=carrier,
        )

    # Deliver policy
    if action == "deliver_policy":
        return (
            "Your policy documents are being prepared. You'll receive them via email "
            "within 2-3 business days. Thank you for choosing us for your commercial "
            "insurance needs! If you have any questions, don't hesitate to reach out."
        )

    # Classify LOBs
    if action == "classify_lobs":
        lobs_str = ", ".join(scenario.lobs)
        forms_str = ", ".join(str(f) for f in scenario.assigned_forms)
        return (
            f"Based on your needs, I've identified the following lines of business: "
            f"{lobs_str}. The required forms are: ACORD {forms_str}. "
            f"{turn.assistant_should_ask}"
        )

    # Fallback
    return render_assistant_template(
        "transition_to_next_phase",
        seed=seed,
        current_phase=turn.phase,
        next_topic=turn.assistant_should_ask,
    )


# ---------------------------------------------------------------------------
# Difficulty / curriculum classification
# ---------------------------------------------------------------------------


def _classify_difficulty(
    scenario: ConversationScenario,
    skeleton: list[TurnSkeleton],
) -> tuple[str, int]:
    """Classify conversation difficulty and curriculum phase.

    Returns:
        (difficulty, curriculum_phase) where difficulty is "easy"/"medium"/"hard"
        and curriculum_phase is 1/2/3.
    """
    multi_lob = len(scenario.lobs) > 1
    is_conversational = scenario.delivery_style == "conversational"
    is_bulk = scenario.delivery_style == "bulk_email"
    is_mixed = scenario.delivery_style == "mixed"

    # Check for corrections
    has_corrections = any(
        t.action == "save_fields"
        and any(
            k in ("employee_count", "annual_revenue", "effective_date")
            for k in t.user_fields
        )
        and t.phase == "form_specific"
        and t.assistant_should_ask
        and "correction" in t.assistant_should_ask.lower()
        for t in skeleton
    )

    # Hard: multi-LOB + (bulk OR mixed), or has corrections with multi-LOB
    if multi_lob and (is_bulk or is_mixed):
        return "hard", 3
    if multi_lob and has_corrections:
        return "hard", 3

    # Easy: single LOB + conversational
    if not multi_lob and is_conversational:
        return "easy", 1

    # Medium: everything else (multi-LOB OR non-conversational)
    return "medium", 2


# ---------------------------------------------------------------------------
# Main assembler
# ---------------------------------------------------------------------------


def assemble_conversation(
    scenario: ConversationScenario,
    skeleton: list[TurnSkeleton] | None = None,
    seed: int = 42,
) -> dict:
    """Assemble a complete training conversation from scenario + skeleton.

    If skeleton is None, build one using build_skeleton().

    Returns: {
        "messages": [...],  # OpenAI chat format messages
        "metadata": {
            "scenario_id": str,
            "phases": list[str],
            "tools_used": list[str],
            "difficulty": str,  # "easy", "medium", "hard"
            "curriculum_phase": int,  # 1, 2, or 3
            "turn_count": int,
            "delivery_style": str,
            "user_persona": str,
        }
    }
    """
    rng = random.Random(seed)

    if skeleton is None:
        skeleton = build_skeleton(scenario, seed=seed)

    # Build system prompt using the first turn's phase and empty form_state
    first_phase = skeleton[0].phase if skeleton else "greeting"
    system_content = build_training_system_prompt(
        phase=first_phase,
        form_state={},
        lobs=list(scenario.lobs),
        assigned_forms=list(scenario.assigned_forms),
    )

    messages: list[dict] = [{"role": "system", "content": system_content}]

    form_state: dict = {}
    phases_seen: list[str] = []
    tools_used: set[str] = set()

    for turn in skeleton:
        # Track phases
        if not phases_seen or phases_seen[-1] != turn.phase:
            phases_seen.append(turn.phase)

        # 1. User message
        user_content = _render_user_message(turn, scenario, rng)
        messages.append({"role": "user", "content": user_content})

        # 2. Tool call injection
        tool_interactions, new_form_state = inject_tool_calls(
            turn, form_state, scenario, seed=seed
        )
        form_state = new_form_state

        if tool_interactions:
            # Track which tools were used
            for interaction in tool_interactions:
                tc = interaction.get("tool_call", {})
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                if tool_name:
                    tools_used.add(tool_name)

            # 2a. Assistant message with tool_calls (content=None)
            tool_calls_list = [
                interaction["tool_call"] for interaction in tool_interactions
            ]
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls_list,
                }
            )

            # 2b. Tool response messages
            for interaction in tool_interactions:
                messages.append(interaction["tool_response"])

            # 2c. Assistant content message after tool responses
            assistant_content = _render_assistant_message(
                turn, scenario, form_state, tool_interactions, rng
            )
            messages.append({"role": "assistant", "content": assistant_content})
        else:
            # No tools: just assistant content
            assistant_content = _render_assistant_message(
                turn, scenario, form_state, [], rng
            )
            messages.append({"role": "assistant", "content": assistant_content})

    # Ensure the last message is assistant with content (not None)
    if messages[-1]["role"] != "assistant" or messages[-1].get("content") is None:
        messages.append(
            {
                "role": "assistant",
                "content": (
                    "Thank you for your time. Your insurance application has been "
                    "processed. If you have any further questions, please don't "
                    "hesitate to reach out."
                ),
            }
        )

    # Classify difficulty
    difficulty, curriculum_phase = _classify_difficulty(scenario, skeleton)

    metadata = {
        "scenario_id": scenario.scenario_id,
        "phases": phases_seen,
        "tools_used": sorted(tools_used),
        "difficulty": difficulty,
        "curriculum_phase": curriculum_phase,
        "turn_count": len(skeleton),
        "delivery_style": scenario.delivery_style,
        "user_persona": scenario.user_persona,
    }

    return {"messages": messages, "metadata": metadata}


# ---------------------------------------------------------------------------
# Windowed conversation assembler
# ---------------------------------------------------------------------------


def _estimate_tokens(messages: list[dict]) -> int:
    """Estimate token count from messages using json.dumps for accuracy.

    This matches how tokenizers see the data: all JSON structure, keys,
    values, and formatting contribute to token count. Uses ~4 chars/token
    as a conservative estimate for English + JSON.
    """
    import json as _json
    total = 0
    for msg in messages:
        # Count the full serialized message including all structure
        total += len(_json.dumps(msg, ensure_ascii=False)) // 4
    return total


def assemble_windowed_conversations(
    scenario: ConversationScenario,
    window_size: int = 10,
    overlap: int = 2,
    seed: int = 42,
    max_tokens: int = 7000,
) -> list[dict]:
    """Create overlapping windowed training examples from long conversations.

    Each window gets a fresh system prompt with accumulated form_state up to
    that point in the conversation. Windows are capped at both window_size
    turns AND max_tokens (estimated), whichever is smaller.

    For conversations shorter than window_size turns, returns a single window
    containing the full conversation.

    Args:
        scenario: The ConversationScenario to assemble.
        window_size: Maximum number of turns per window.
        overlap: Number of overlapping turns between consecutive windows.
        seed: Random seed for reproducibility.
        max_tokens: Soft token cap per window (estimated). Defaults to 7000
            to stay safely under the 8192 training seq_len.

    Returns:
        A list of conversation dicts, each with "messages" and "metadata".
    """
    rng = random.Random(seed)

    skeleton = build_skeleton(scenario, seed=seed)

    # If short enough, just return the full conversation as a single window
    if len(skeleton) <= window_size:
        conv = assemble_conversation(scenario, skeleton=skeleton, seed=seed)
        return [conv]

    # First, do a full pass to compute form_state at each turn boundary
    form_states_at_turn: list[dict] = [{}]  # form_state BEFORE each turn
    form_state: dict = {}
    for turn in skeleton:
        _, new_form_state = inject_tool_calls(turn, form_state, scenario, seed=seed)
        form_state = new_form_state
        form_states_at_turn.append(dict(form_state))

    # Build windows
    windows: list[dict] = []
    step = max(1, window_size - overlap)
    start = 0

    while start < len(skeleton):
        end = min(start + window_size, len(skeleton))
        window_skeleton = skeleton[start:end]

        # Form state accumulated up to the start of this window
        accumulated_form_state = form_states_at_turn[start]

        # Build system prompt with accumulated form_state
        first_phase = window_skeleton[0].phase if window_skeleton else "greeting"
        system_content = build_training_system_prompt(
            phase=first_phase,
            form_state=accumulated_form_state,
            lobs=list(scenario.lobs),
            assigned_forms=list(scenario.assigned_forms),
        )

        messages: list[dict] = [{"role": "system", "content": system_content}]

        # Reset form_state for this window to the accumulated state
        window_form_state = dict(accumulated_form_state)
        phases_seen: list[str] = []
        tools_used: set[str] = set()
        window_rng = random.Random(seed + start)

        actual_turns_used = 0
        for turn in window_skeleton:
            if not phases_seen or phases_seen[-1] != turn.phase:
                phases_seen.append(turn.phase)

            # User message
            user_content = _render_user_message(turn, scenario, window_rng)
            messages.append({"role": "user", "content": user_content})

            # Tool calls
            tool_interactions, new_form_state = inject_tool_calls(
                turn, window_form_state, scenario, seed=seed
            )
            window_form_state = new_form_state

            if tool_interactions:
                for interaction in tool_interactions:
                    tc = interaction.get("tool_call", {})
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    if tool_name:
                        tools_used.add(tool_name)

                tool_calls_list = [
                    interaction["tool_call"] for interaction in tool_interactions
                ]
                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls_list,
                    }
                )

                for interaction in tool_interactions:
                    messages.append(interaction["tool_response"])

                assistant_content = _render_assistant_message(
                    turn, scenario, window_form_state, tool_interactions, window_rng
                )
                messages.append({"role": "assistant", "content": assistant_content})
            else:
                assistant_content = _render_assistant_message(
                    turn, scenario, window_form_state, [], window_rng
                )
                messages.append({"role": "assistant", "content": assistant_content})

            actual_turns_used += 1

            # Token-aware early stop: if we've exceeded the budget, stop
            # adding more turns to this window. Need at least 2 turns for
            # meaningful training signal (user + assistant with tool calls).
            if _estimate_tokens(messages) >= max_tokens and actual_turns_used >= 2:
                break

        # Ensure last message is assistant with content
        if (
            messages[-1]["role"] != "assistant"
            or messages[-1].get("content") is None
        ):
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "Thank you for your patience. Let me continue helping you "
                        "with your insurance application."
                    ),
                }
            )

        used_skeleton = window_skeleton[:actual_turns_used]
        difficulty, curriculum_phase = _classify_difficulty(scenario, used_skeleton)

        metadata = {
            "scenario_id": scenario.scenario_id,
            "phases": phases_seen,
            "tools_used": sorted(tools_used),
            "difficulty": difficulty,
            "curriculum_phase": curriculum_phase,
            "turn_count": actual_turns_used,
            "delivery_style": scenario.delivery_style,
            "user_persona": scenario.user_persona,
            "window_index": len(windows),
            "window_start_turn": start,
            "window_end_turn": start + actual_turns_used,
        }

        windows.append({"messages": messages, "metadata": metadata})

        actual_end = start + actual_turns_used
        if actual_end >= len(skeleton):
            break
        # Advance by actual turns used minus overlap
        start += max(1, actual_turns_used - overlap)

    return windows
