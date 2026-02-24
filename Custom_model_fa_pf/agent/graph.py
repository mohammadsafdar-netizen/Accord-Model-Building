"""LangGraph StateGraph definition for the insurance intake agent."""

import logging
import time
from typing import Optional

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from Custom_model_fa_pf.agent.state import IntakeState
from Custom_model_fa_pf.agent.nodes import (
    greet_node,
    check_gaps_node,
    route_after_gaps,
    validate_node,
    review_node,
    reflect_node,
    summarize_node,
    process_tool_results_node,
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
    MAX_CONVERSATION_TURNS,
    MAX_TOOL_CALLS_PER_TURN,
    SUMMARIZE_AFTER_TURNS,
)

logger = logging.getLogger(__name__)

AGENT_MAX_RETRIES = 3


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
    """Core agent node: builds context, calls LLM with tools bound.

    Includes retry with exponential backoff (Pattern 11: Exception Handling).
    """
    llm = _get_chat_llm()
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)

    # Build system message with form state + summary + pipeline state
    system_msg = build_system_message(
        form_state=state.get("form_state", {}),
        summary=state.get("summary", ""),
        phase=state.get("phase", ""),
        quotes=state.get("quotes", []),
        selected_quote=state.get("selected_quote", {}),
        bind_request=state.get("bind_request", {}),
    )

    # Prepend system message to the conversation
    messages = [system_msg] + list(state.get("messages", []))

    last_error = None
    for attempt in range(1, AGENT_MAX_RETRIES + 1):
        try:
            response = llm_with_tools.invoke(messages)
            return {
                "messages": [response],
                "conversation_turn": state.get("conversation_turn", 0) + 1,
                "reflect_count": 0,  # Reset reflection count each turn
            }
        except Exception as exc:
            last_error = exc
            logger.warning(
                "LLM call failed (attempt %d/%d): %s",
                attempt, AGENT_MAX_RETRIES, exc,
            )
            if attempt < AGENT_MAX_RETRIES:
                time.sleep(2 ** attempt)

    # All retries exhausted — return graceful error message
    logger.error("Agent LLM call failed after %d retries: %s", AGENT_MAX_RETRIES, last_error)
    error_msg = AIMessage(content=(
        "I'm having trouble processing your request right now. "
        "Could you please try again in a moment?"
    ))
    return {
        "messages": [error_msg],
        "error_count": state.get("error_count", 0) + 1,
    }


def _should_use_tools(state: IntakeState) -> str:
    """Check if the last AI message wants to call tools.

    Enforces MAX_TOOL_CALLS_PER_TURN to prevent infinite tool loops.
    Counts agent→tools ROUND-TRIPS (not individual ToolMessages) so that
    a single batch of many tool calls (e.g. 27 save_fields) counts as 1 round.
    Routes to 'reflect' instead of directly to 'check_gaps' (Pattern 4).
    """
    messages = state.get("messages", [])
    if not messages:
        return END

    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        # Count round-trips: each AIMessage with tool_calls = 1 round
        from langchain_core.messages import ToolMessage
        rounds = 0
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                continue  # Skip individual tool results
            elif hasattr(msg, "tool_calls") and msg.tool_calls:
                rounds += 1  # Each AI tool-calling message = 1 round
            else:
                break
        if rounds >= MAX_TOOL_CALLS_PER_TURN:
            logger.warning(
                "Tool call limit reached (%d/%d rounds), routing to reflect",
                rounds, MAX_TOOL_CALLS_PER_TURN,
            )
            return "reflect"
        return "tools"
    return "reflect"


def _route_entry(state: IntakeState) -> str:
    """Route to greet on first turn, agent on subsequent turns.

    Enforces MAX_CONVERSATION_TURNS — routes to review when limit reached.
    Routes through summarize check for memory management (Pattern 8).
    """
    turn = state.get("conversation_turn", 0)
    if turn == 0:
        return "greet"
    if turn >= MAX_CONVERSATION_TURNS:
        logger.info("Conversation turn limit reached (%d), routing to review", turn)
        return "review"
    return "maybe_summarize"


def _route_after_reflect(state: IntakeState) -> str:
    """Route after reflection: revise (back to agent) or pass (to check_gaps).

    Limits revision to 1 attempt per turn to prevent infinite loops.
    """
    reflect_count = state.get("reflect_count", 0)
    messages = state.get("messages", [])

    # Check if the last message is a revision request (SystemMessage from reflect_node)
    if messages and reflect_count < 1:
        from langchain_core.messages import SystemMessage
        last = messages[-1]
        if isinstance(last, SystemMessage) and "REVISION NEEDED" in (last.content or ""):
            return "revise"

    return "pass"


def _should_summarize(state: IntakeState) -> str:
    """Check if conversation needs summarization before proceeding to agent.

    Triggers when conversation_turn >= SUMMARIZE_AFTER_TURNS and messages >= 20.
    """
    turn = state.get("conversation_turn", 0)
    messages = state.get("messages", [])

    if turn >= SUMMARIZE_AFTER_TURNS and len(messages) >= 20:
        return "summarize"
    return "agent"


def _build_graph(checkpointer=None):
    """Build the StateGraph (shared by create_graph and create_agent).

    Graph flow:
      START → _route_entry:
        turn=0 → greet → END
        turn>=MAX → review → END
        turn>0 → _should_summarize:
          needs_summary → summarize → agent
          no_summary → agent
      agent → _should_use_tools:
        "tools" → tools → process_tools → agent
        "reflect" → reflect → _route_after_reflect:
          "revise" → agent (max 1)
          "pass" → check_gaps
        END → END
      check_gaps → route_after_gaps → respond(END) / validate → END / review → END
    """
    tools = get_all_tools()

    workflow = StateGraph(IntakeState)

    # Nodes
    workflow.add_node("greet", greet_node)
    workflow.add_node("agent", _agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("maybe_summarize", lambda state: {})  # Pass-through for routing
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("check_gaps", check_gaps_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("review", review_node)

    # Entry: greet on first turn, maybe_summarize on subsequent, review if turn limit
    workflow.add_conditional_edges(START, _route_entry, {
        "greet": "greet",
        "maybe_summarize": "maybe_summarize",
        "review": "review",
    })
    workflow.add_edge("greet", END)  # First turn: greet and wait for user

    # Summarization check before agent
    workflow.add_conditional_edges("maybe_summarize", _should_summarize, {
        "summarize": "summarize",
        "agent": "agent",
    })
    workflow.add_edge("summarize", "agent")  # After summarization, proceed to agent

    # Agent -> tool calling or reflect
    workflow.add_conditional_edges("agent", _should_use_tools, {
        "tools": "tools",
        "reflect": "reflect",
        END: END,
    })
    workflow.add_node("process_tools", process_tool_results_node)
    workflow.add_edge("tools", "process_tools")  # After tools, process results
    workflow.add_edge("process_tools", "agent")  # Then back to agent

    # Reflection routing
    workflow.add_conditional_edges("reflect", _route_after_reflect, {
        "revise": "agent",
        "pass": "check_gaps",
    })

    # Gap routing
    workflow.add_conditional_edges("check_gaps", route_after_gaps, {
        "respond": END,       # Agent already generated response, end turn
        "validate": "validate",
        "review": "review",
    })
    workflow.add_edge("validate", END)
    workflow.add_edge("review", END)

    return workflow.compile(checkpointer=checkpointer)


def create_graph():
    """Build and compile the LangGraph StateGraph (no checkpointer)."""
    return _build_graph(checkpointer=None)


def create_agent(checkpointer=None):
    """Create a compiled agent with checkpointing for multi-turn conversations."""
    if checkpointer is None:
        checkpointer = MemorySaver()
    return _build_graph(checkpointer=checkpointer)
