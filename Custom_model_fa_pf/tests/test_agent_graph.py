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
        assert "agent" in node_names
        assert "check_gaps" in node_names
        assert "tools" in node_names
        assert "reflect" in node_names
        assert "summarize" in node_names
        assert "maybe_summarize" in node_names

    def test_agent_creates_with_checkpointer(self):
        agent = create_agent()
        assert agent is not None


class TestEntryRouting:
    def test_first_turn_routes_to_greet(self):
        from Custom_model_fa_pf.agent.graph import _route_entry
        state = {"conversation_turn": 0}
        assert _route_entry(state) == "greet"

    def test_subsequent_turn_routes_to_maybe_summarize(self):
        from Custom_model_fa_pf.agent.graph import _route_entry
        state = {"conversation_turn": 1}
        assert _route_entry(state) == "maybe_summarize"

    def test_missing_turn_routes_to_greet(self):
        from Custom_model_fa_pf.agent.graph import _route_entry
        state = {}
        assert _route_entry(state) == "greet"

    def test_turn_limit_routes_to_review(self):
        """When conversation_turn >= MAX_CONVERSATION_TURNS, route to review."""
        from Custom_model_fa_pf.agent.graph import _route_entry
        from Custom_model_fa_pf.config import MAX_CONVERSATION_TURNS
        state = {"conversation_turn": MAX_CONVERSATION_TURNS}
        assert _route_entry(state) == "review"

    def test_turn_over_limit_routes_to_review(self):
        from Custom_model_fa_pf.agent.graph import _route_entry
        state = {"conversation_turn": 100}
        assert _route_entry(state) == "review"


class TestToolRouting:
    def test_should_use_tools_with_tool_calls(self):
        from Custom_model_fa_pf.agent.graph import _should_use_tools
        from langchain_core.messages import AIMessage
        msg = AIMessage(content="", tool_calls=[{"id": "1", "name": "save_field", "args": {}}])
        state = {"messages": [msg]}
        assert _should_use_tools(state) == "tools"

    def test_should_use_tools_without_tool_calls(self):
        """No tool calls → route to reflect."""
        from Custom_model_fa_pf.agent.graph import _should_use_tools
        from langchain_core.messages import AIMessage
        msg = AIMessage(content="Hello, what is your business name?")
        state = {"messages": [msg]}
        assert _should_use_tools(state) == "reflect"

    def test_should_use_tools_empty_messages(self):
        from Custom_model_fa_pf.agent.graph import _should_use_tools
        from langgraph.graph import END
        state = {"messages": []}
        assert _should_use_tools(state) == END

    def test_tool_call_limit_enforced(self):
        """After MAX_TOOL_CALLS_PER_TURN tool rounds, route to reflect."""
        from Custom_model_fa_pf.agent.graph import _should_use_tools
        from Custom_model_fa_pf.config import MAX_TOOL_CALLS_PER_TURN
        from langchain_core.messages import AIMessage, ToolMessage
        messages = []
        for i in range(MAX_TOOL_CALLS_PER_TURN):
            messages.append(AIMessage(
                content="", tool_calls=[{"id": str(i), "name": "save_field", "args": {}}]
            ))
            messages.append(ToolMessage(content='{"status":"ok"}', tool_call_id=str(i)))
        # Final AI message with tool call — should be blocked
        messages.append(AIMessage(
            content="", tool_calls=[{"id": "final", "name": "save_field", "args": {}}]
        ))
        state = {"messages": messages}
        assert _should_use_tools(state) == "reflect"


class TestReflectRouting:
    def test_pass_when_no_revision_needed(self):
        from Custom_model_fa_pf.agent.graph import _route_after_reflect
        from langchain_core.messages import AIMessage
        state = {"messages": [AIMessage(content="Your business name?")], "reflect_count": 0}
        assert _route_after_reflect(state) == "pass"

    def test_revise_when_revision_needed(self):
        from Custom_model_fa_pf.agent.graph import _route_after_reflect
        from langchain_core.messages import SystemMessage
        state = {
            "messages": [SystemMessage(content="REVISION NEEDED: Ask only one question.")],
            "reflect_count": 0,
        }
        assert _route_after_reflect(state) == "revise"

    def test_pass_when_max_revisions_reached(self):
        """Even with revision feedback, pass if reflect_count >= 1."""
        from Custom_model_fa_pf.agent.graph import _route_after_reflect
        from langchain_core.messages import SystemMessage
        state = {
            "messages": [SystemMessage(content="REVISION NEEDED: Ask only one question.")],
            "reflect_count": 1,
        }
        assert _route_after_reflect(state) == "pass"


class TestSummarizeRouting:
    def test_no_summarize_when_low_turns(self):
        from Custom_model_fa_pf.agent.graph import _should_summarize
        state = {"conversation_turn": 5, "messages": list(range(30))}
        assert _should_summarize(state) == "agent"

    def test_no_summarize_when_few_messages(self):
        from Custom_model_fa_pf.agent.graph import _should_summarize
        from Custom_model_fa_pf.config import SUMMARIZE_AFTER_TURNS
        state = {"conversation_turn": SUMMARIZE_AFTER_TURNS, "messages": list(range(10))}
        assert _should_summarize(state) == "agent"

    def test_summarize_when_conditions_met(self):
        from Custom_model_fa_pf.agent.graph import _should_summarize
        from Custom_model_fa_pf.config import SUMMARIZE_AFTER_TURNS
        state = {"conversation_turn": SUMMARIZE_AFTER_TURNS, "messages": list(range(25))}
        assert _should_summarize(state) == "summarize"


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
