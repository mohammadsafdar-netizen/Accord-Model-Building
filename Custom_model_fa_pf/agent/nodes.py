"""Node functions for the LangGraph intake agent."""

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from Custom_model_fa_pf.agent.state import IntakePhase, IntakeState
from Custom_model_fa_pf.agent.prompts import (
    build_system_message,
    build_form_state_context,
    REFLECTION_PROMPT,
    SUMMARIZE_PROMPT,
)
from Custom_model_fa_pf.config import (
    LLM_BACKEND,
    VLLM_BASE_URL,
    OLLAMA_OPENAI_URL,
    AGENT_MODEL,
    AGENT_TEMPERATURE,
    AGENT_MAX_TOKENS,
    SUMMARIZE_AFTER_TURNS,
)

logger = logging.getLogger(__name__)


def _get_chat_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance for node-level LLM calls (reflect, summarize)."""
    base_url = VLLM_BASE_URL if LLM_BACKEND == "vllm" else OLLAMA_OPENAI_URL
    return ChatOpenAI(
        base_url=base_url,
        api_key="not-needed",
        model=AGENT_MODEL,
        temperature=AGENT_TEMPERATURE,
        max_tokens=AGENT_MAX_TOKENS,
    )


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


def process_tool_results_node(state: IntakeState) -> dict:
    """Process ToolMessages from save_field and update form_state accordingly.

    LangGraph ToolNode returns tool outputs as ToolMessages. This node
    scans recent ToolMessages for save_field results and writes them
    into form_state so the agent knows what's been collected.

    Also handles the case where smaller models write save_field(...) as plain
    text instead of using the proper tool calling format — parses those from
    the AI message content.
    """
    import re
    from langchain_core.messages import ToolMessage

    messages = state.get("messages", [])
    form_state = dict(state.get("form_state", {}))
    entities = state.get("entities", {})
    _new_uploads = []
    updated = False

    # 1. Process actual ToolMessages from LangGraph ToolNode
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                break
            continue

        try:
            data = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue

        # Skip non-dict results (e.g. lists from classify_lobs)
        if not isinstance(data, dict):
            continue

        # Process save_field results
        if data.get("status") == "saved" and data.get("field_name"):
            field_name = data["field_name"]
            form_state[field_name] = {
                "value": data.get("value", ""),
                "confidence": data.get("confidence", 0.0),
                "source": data.get("source", "user_stated"),
                "status": "confirmed",
            }
            updated = True
            logger.debug("Saved field from tool result: %s = %s", field_name, data.get("value"))

        # Process extract_entities results — update entities
        if "business" in data or "drivers" in data or "vehicles" in data:
            entities = data
            updated = True

        # Process fill_forms results — log fill stats
        if data.get("status") == "filled" and data.get("output_dir"):
            logger.info(
                "Forms filled: %d fields across %d forms → %s",
                data.get("total_fields_filled", 0),
                data.get("forms_count", 0),
                data.get("output_dir"),
            )
            for fr in data.get("fill_results", []):
                logger.info(
                    "  Form %s: %d filled, %d skipped, %d errors",
                    fr.get("form_number"), fr.get("filled_count", 0),
                    fr.get("skipped_count", 0), fr.get("error_count", 0),
                )

        # Process process_document results — track uploads
        if data.get("status") == "processed" and data.get("document_type"):
            from datetime import datetime
            _new_uploads.append({
                "file_path": data.get("file_path", ""),
                "document_type": data.get("document_type", "other"),
                "fields_count": len(data.get("fields", {})),
                "timestamp": datetime.now().isoformat(),
            })
            updated = True
            logger.info(
                "Tracked document upload: %s (%s, %d fields)",
                data.get("file_path"), data.get("document_type"),
                len(data.get("fields", {})),
            )

    # 2. Parse text-based tool calls from AI messages
    #    Small models sometimes write save_field("name", "value") as text
    for msg in reversed(messages[-5:]):  # Only check recent messages
        if not isinstance(msg, AIMessage) or not msg.content:
            continue
        if getattr(msg, "tool_calls", None):
            continue  # Real tool call, already handled above

        # Match patterns like: save_field("field_name", "value", "source")
        # or save_field("field_name", "value")
        pattern = r'save_field\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\'](?:\s*,\s*["\']([^"\']*)["\'])?\s*\)'
        matches = re.findall(pattern, msg.content)
        for match in matches:
            field_name = match[0]
            value = match[1]
            source = match[2] if match[2] else "user_stated"
            if value.strip():
                from Custom_model_fa_pf.agent.confidence import ConfidenceScorer
                scorer = ConfidenceScorer()
                confidence = scorer.score(field_name, value, source=source)
                form_state[field_name] = {
                    "value": value.strip(),
                    "confidence": confidence,
                    "source": source,
                    "status": "confirmed",
                }
                updated = True
                logger.info("Parsed text tool call: save_field(%s, %s)", field_name, value)

    result = {}
    if updated:
        result["form_state"] = form_state
        if entities != state.get("entities", {}):
            result["entities"] = entities
        if _new_uploads:
            uploaded = list(state.get("uploaded_documents", []))
            uploaded.extend(_new_uploads)
            result["uploaded_documents"] = uploaded
    return result


def check_gaps_node(state: IntakeState) -> dict:
    """Analyze completeness and decide what to do next.

    This is a routing node — it doesn't modify state, just evaluates it.
    The actual routing decision is made by route_after_gaps().
    """
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


def _parse_text_tool_calls(state: IntakeState) -> dict:
    """Parse save_field() calls written as text by smaller models.

    Small LLMs sometimes write tool invocations as plain text instead of
    using the proper function calling format. This function extracts those
    and updates form_state.
    """
    import re
    from Custom_model_fa_pf.agent.confidence import ConfidenceScorer

    messages = state.get("messages", [])
    form_state = dict(state.get("form_state", {}))
    updated = False

    for msg in reversed(messages[-5:]):
        if not isinstance(msg, AIMessage) or not msg.content:
            continue
        if getattr(msg, "tool_calls", None):
            continue

        pattern = r'save_field\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\'](?:\s*,\s*["\']([^"\']*)["\'])?\s*\)'
        matches = re.findall(pattern, msg.content)
        scorer = ConfidenceScorer()
        for match in matches:
            field_name = match[0]
            value = match[1]
            source = match[2] if match[2] else "user_stated"
            if value.strip():
                confidence = scorer.score(field_name, value, source=source)
                form_state[field_name] = {
                    "value": value.strip(),
                    "confidence": confidence,
                    "source": source,
                    "status": "confirmed",
                }
                updated = True
                logger.info("Parsed text tool call: save_field(%s, %s)", field_name, value)

    if updated:
        return {"form_state": form_state}
    return {}


def reflect_node(state: IntakeState) -> dict:
    """Critique the agent's last response before showing to user (Pattern 4: Reflection).

    Also parses any save_field() calls written as plain text by smaller models
    and updates form_state before reflection.

    Checks for hallucination, multiple questions, off-topic content, and incorrect
    confirmations. If issues found, sends revision feedback back to agent.
    """
    # First: parse any text-based tool calls and update form_state
    text_updates = _parse_text_tool_calls(state)

    messages = state.get("messages", [])
    if not messages:
        return text_updates

    last = messages[-1]
    # Only reflect on AI text responses, not tool calls or empty messages
    if not isinstance(last, AIMessage) or not last.content:
        return text_updates
    if getattr(last, "tool_calls", None):
        return text_updates  # Don't reflect on tool-calling messages

    # Merge current form_state with any text-parsed updates for reflection context
    merged_form_state = dict(state.get("form_state", {}))
    if "form_state" in text_updates:
        merged_form_state.update(text_updates["form_state"])

    llm = _get_chat_llm()
    prompt = REFLECTION_PROMPT.format(
        response=last.content,
        form_state_summary=build_form_state_context(merged_form_state),
    )

    try:
        result = llm.invoke([SystemMessage(content=prompt)])
        verdict = json.loads(result.content)
        if verdict.get("verdict") == "pass":
            logger.debug("Reflection passed for response")
            return text_updates  # Response is fine, pass through with form updates

        # Response needs revision — increment reflect_count and add feedback
        issues = verdict.get("issues", [])
        suggestion = verdict.get("suggestion", "Please revise your response.")
        logger.info("Reflection flagged issues: %s", issues)
        revision_result = {
            "messages": [SystemMessage(content=f"REVISION NEEDED: {suggestion}")],
            "reflect_count": state.get("reflect_count", 0) + 1,
        }
        # Merge text updates into revision result
        if "form_state" in text_updates:
            revision_result["form_state"] = text_updates["form_state"]
        return revision_result
    except (json.JSONDecodeError, Exception) as exc:
        logger.debug("Reflection failed (letting response through): %s", exc)
        return text_updates  # Reflection failed — let the response through with form updates


def summarize_node(state: IntakeState) -> dict:
    """Compress old messages into a summary when conversation gets long (Pattern 8: Memory).

    Keeps the last 6 messages for immediate context, summarizes everything else.
    Uses RemoveMessage to prune old messages from the add_messages reducer.
    """
    messages = state.get("messages", [])
    turn = state.get("conversation_turn", 0)

    if turn < SUMMARIZE_AFTER_TURNS or len(messages) < 20:
        return {}  # Not enough history to warrant summarization

    # Keep the last 6 messages for immediate context
    to_summarize = messages[:-6]
    if not to_summarize:
        return {}

    # Build conversation text from messages to summarize
    conversation_text = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Agent'}: {m.content}"
        for m in to_summarize
        if isinstance(m, (HumanMessage, AIMessage)) and m.content
    )

    if not conversation_text.strip():
        return {}

    llm = _get_chat_llm()
    prompt = SUMMARIZE_PROMPT.format(
        conversation_text=conversation_text,
        form_state_summary=build_form_state_context(state.get("form_state", {})),
    )

    try:
        result = llm.invoke([SystemMessage(content=prompt)])
        new_summary = result.content.strip()
        logger.info(
            "Summarized %d messages into %d chars",
            len(to_summarize), len(new_summary),
        )
    except Exception as exc:
        logger.warning("Summarization failed: %s", exc)
        return {}  # Summarization failed — keep full history

    # Use RemoveMessage to prune old messages from the state
    from langgraph.graph.message import RemoveMessage
    removals = [
        RemoveMessage(id=m.id)
        for m in to_summarize
        if hasattr(m, "id") and m.id
    ]

    return {
        "summary": new_summary,
        "messages": removals,  # add_messages reducer handles RemoveMessage
    }
