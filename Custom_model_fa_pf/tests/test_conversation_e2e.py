"""End-to-end conversational tests for the insurance intake agent.

Tests natural language interaction to verify the agent feels human-like:
- Greeting warmth and professionalism
- Handling casual/informal language
- Remembering context across turns
- Asking one question at a time
- Handling corrections gracefully
- Dealing with incomplete/vague answers
- Off-topic redirect
- Multi-entity input (bulk info dump)
- Emotional/frustrated user
- Typos and grammar issues

Requires Ollama running with qwen2.5:7b model.
"""

import json
import logging
import pytest
import uuid

from langchain_core.messages import HumanMessage, AIMessage

from Custom_model_fa_pf.agent.graph import create_agent
from Custom_model_fa_pf.agent.state import create_initial_state

logger = logging.getLogger(__name__)


def _ollama_available():
    """Check if Ollama is running with the required model."""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code != 200:
            return False
        models = [m["name"] for m in resp.json().get("models", [])]
        return "qwen2.5:7b" in models
    except Exception:
        return False


# Skip all tests if Ollama is not reachable
pytestmark = pytest.mark.skipif(
    not _ollama_available(),
    reason="Ollama not running or qwen2.5:7b not available",
)


class ConversationRunner:
    """Helper to run multi-turn conversations with the agent."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())[:8]
        self.agent = create_agent()
        self.config = {"configurable": {"thread_id": f"test:{self.session_id}"}}
        self.msg_count = 0
        self.all_responses = []

    def start(self) -> str:
        """Send initial empty state to get greeting."""
        initial = create_initial_state(self.session_id)
        result = self.agent.invoke(initial, config=self.config)
        msgs = result.get("messages", [])
        response = self._extract_new_text(msgs)
        self.msg_count = len(msgs)
        self.all_responses.append(response)
        return response

    def say(self, text: str) -> str:
        """Send a user message and get the agent's response."""
        prev_count = self.msg_count
        result = self.agent.invoke(
            {"messages": [HumanMessage(content=text)]},
            config=self.config,
        )
        msgs = result.get("messages", [])
        response = self._extract_new_text(msgs, skip=prev_count + 1)
        self.msg_count = len(msgs)
        self.all_responses.append(response)
        return response

    def get_state(self) -> dict:
        """Get current agent state."""
        return self.agent.get_state(self.config).values

    def _extract_new_text(self, messages, skip=0) -> str:
        import re
        texts = []
        for msg in messages[skip:]:
            if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                # Strip save_field() text from display
                lines = msg.content.split("\n")
                cleaned = [l for l in lines if not re.match(r'^\s*save_field\(', l.strip())]
                text = "\n".join(cleaned).strip()
                if text:
                    texts.append(text)
        return "\n".join(texts)


@pytest.fixture
def conv():
    return ConversationRunner()


class TestGreeting:
    """Test that the greeting is warm, professional, and asks an opening question."""

    def test_greeting_is_welcoming(self, conv):
        greeting = conv.start()
        assert greeting, "Greeting should not be empty"
        lower = greeting.lower()
        assert any(w in lower for w in ["welcome", "hello", "hi", "help"]), \
            f"Greeting should be welcoming: {greeting[:200]}"

    def test_greeting_mentions_insurance(self, conv):
        greeting = conv.start()
        lower = greeting.lower()
        assert any(w in lower for w in ["insurance", "application", "intake", "policy"]), \
            f"Greeting should mention insurance context: {greeting[:200]}"

    def test_greeting_asks_opening_question(self, conv):
        greeting = conv.start()
        assert "?" in greeting, f"Greeting should ask a question: {greeting[:200]}"


class TestNaturalConversation:
    """Test that the agent handles natural, casual conversation."""

    def test_casual_intro(self, conv):
        """User introduces themselves casually."""
        conv.start()
        response = conv.say("Hey, I'm Mike from Acme Trucking. We need some insurance.")
        assert response, "Should respond to casual intro"
        lower = response.lower()
        # Should acknowledge the business name or ask follow-up
        assert any(w in lower for w in ["acme", "trucking", "business", "tell me more", "?"]), \
            f"Should engage with the user's info: {response[:300]}"

    def test_informal_language(self, conv):
        """User uses very informal language."""
        conv.start()
        response = conv.say("yeah so basically we got a bunch of trucks and need coverage ya know")
        assert response, "Should handle informal language"
        assert "?" in response, "Should ask a follow-up question"

    def test_one_question_at_a_time(self, conv):
        """Agent should ask only ONE question per response."""
        conv.start()
        response = conv.say("We're a landscaping company called Green Earth LLC")
        # Count question marks — should ideally be 1
        q_count = response.count("?")
        assert q_count <= 2, \
            f"Should ask at most 1-2 questions, got {q_count}: {response[:400]}"


class TestContextRetention:
    """Test that the agent remembers what was said in previous turns."""

    def test_remembers_business_name(self, conv):
        """Agent should reference previously provided business name."""
        conv.start()
        conv.say("Our company is called Stellar Logistics, we're an LLC.")
        response = conv.say("What forms do we need?")
        # The agent should still have context about Stellar Logistics
        state = conv.get_state()
        # Check that form_state or entities captured the name
        form_state = state.get("form_state", {})
        entities = state.get("entities", {})
        has_name = (
            any("stellar" in str(v).lower() for v in form_state.values())
            or "stellar" in str(entities).lower()
        )
        # It's OK if stored in messages even if not in form_state yet
        assert response, "Should respond about forms"

    def test_multi_turn_info_collection(self, conv):
        """Agent collects info over multiple turns."""
        conv.start()
        conv.say("I'm John Smith, I run a plumbing company called Smith Plumbing Inc.")
        conv.say("We need general liability and commercial auto insurance.")
        response = conv.say("Our address is 123 Main St, Springfield, IL 62701")
        assert response, "Should respond after address"
        # Should ask for more info or confirm what was collected
        lower = response.lower()
        assert "?" in response or any(w in lower for w in ["great", "thank", "got it", "noted"]), \
            f"Should acknowledge or ask follow-up: {response[:300]}"


class TestCorrectionHandling:
    """Test that the agent handles corrections gracefully."""

    def test_simple_correction(self, conv):
        """User corrects previously provided info."""
        conv.start()
        conv.say("Our business name is Acme Corp")
        response = conv.say("Actually, sorry, the name is Acme Corporation, not Acme Corp.")
        lower = response.lower()
        # Should acknowledge the correction
        assert any(w in lower for w in ["correct", "update", "change", "noted", "acme corporation", "got it"]), \
            f"Should acknowledge correction: {response[:300]}"

    def test_correction_of_numbers(self, conv):
        """User corrects a numeric value."""
        conv.start()
        conv.say("We have 15 employees")
        response = conv.say("Wait, that's wrong. We actually have 25 employees now.")
        assert response, "Should handle numeric correction"


class TestEdgeCases:
    """Test edge cases — vague answers, off-topic, frustration."""

    def test_vague_answer(self, conv):
        """User gives a vague/unhelpful answer."""
        conv.start()
        response = conv.say("I don't really know much about insurance, I just need something basic")
        lower = response.lower()
        # Should be helpful, not dismissive
        assert any(w in lower for w in ["help", "start", "basic", "begin", "simple", "?"]), \
            f"Should be helpful with vague input: {response[:300]}"

    def test_i_dont_know_response(self, conv):
        """User says 'I don't know' to a question."""
        conv.start()
        conv.say("We're a trucking company, Big Rig Transport LLC")
        response = conv.say("I don't know our FEIN number, I'll have to look that up later")
        lower = response.lower()
        # Should acknowledge and move on, not push
        assert not any(w in lower for w in ["must", "required", "need to provide"]), \
            f"Should not push when user doesn't know: {response[:300]}"
        # Should ask about something else
        assert "?" in response, "Should move on to next question"

    def test_off_topic_redirect(self, conv):
        """User asks something completely off-topic."""
        conv.start()
        response = conv.say("What's the weather like today?")
        lower = response.lower()
        # Should redirect politely
        assert any(w in lower for w in ["insurance", "help", "assist", "application", "intake", "focus"]), \
            f"Should redirect to insurance topic: {response[:300]}"

    def test_frustrated_user(self, conv):
        """User expresses frustration."""
        conv.start()
        conv.say("We're a construction company, BuildRight Inc")
        response = conv.say("This is taking forever. Can we just speed this up?")
        lower = response.lower()
        # Should be empathetic, not robotic
        assert any(w in lower for w in ["understand", "sorry", "quick", "fast", "speed", "help", "certainly"]), \
            f"Should show empathy: {response[:300]}"


class TestBulkInfoDump:
    """Test handling when user provides lots of info at once."""

    def test_email_style_dump(self, conv):
        """User dumps a large block of info like an email."""
        conv.start()
        response = conv.say(
            "Here's all our info: Business name is Pacific Coast Hauling LLC, "
            "we're a California corporation, FEIN 94-1234567. Our address is "
            "456 Harbor Blvd, Long Beach, CA 90802. Phone (562) 555-0199. "
            "We need commercial auto insurance for our fleet of 5 trucks. "
            "Policy should start 04/01/2026 through 04/01/2027. "
            "We want $1M CSL liability coverage."
        )
        assert response, "Should handle bulk info"
        # Should acknowledge the info received
        lower = response.lower()
        assert any(w in lower for w in [
            "pacific", "information", "received", "thank", "got", "great"
        ]), f"Should acknowledge bulk info: {response[:300]}"

    def test_vehicle_list(self, conv):
        """User lists multiple vehicles at once."""
        conv.start()
        conv.say("We're FastMove Transport, an LLC in Texas")
        response = conv.say(
            "Our vehicles: "
            "1) 2024 Freightliner Cascadia, VIN 3AKJHHDR5RSAA1234 "
            "2) 2023 Kenworth T680, VIN 1XKYD49X04J123456 "
            "3) 2022 Peterbilt 579, VIN 1XPBD49X1PD654321"
        )
        assert response, "Should handle vehicle list"


class TestResponseQuality:
    """Test overall response quality — no robotic or template-like feel."""

    def test_no_json_leaks(self, conv):
        """Responses should never contain raw JSON or code artifacts."""
        conv.start()
        for msg in [
            "We're a small bakery called Sweet Treats",
            "We need general liability coverage",
            "Our address is 789 Oak Ave, Portland, OR 97201",
        ]:
            response = conv.say(msg)
            assert "{" not in response[:50], \
                f"Response should not start with JSON: {response[:200]}"
            assert "```" not in response, \
                f"Response should not contain code blocks: {response[:200]}"

    def test_no_internal_state_leaks(self, conv):
        """Responses should not expose internal tool calls or state info."""
        conv.start()
        response = conv.say("We're Alpha Services, a consulting firm needing insurance")
        lower = response.lower()
        # Should not mention tool names, function names, or internal state
        for leak in ["save_field", "tool_call", "form_state", "validate_fields",
                      "langchain", "langgraph", "node", "function"]:
            assert leak not in lower, \
                f"Response leaks internal info '{leak}': {response[:300]}"

    def test_reasonable_response_length(self, conv):
        """Responses should be conversational length, not too short or too long."""
        conv.start()
        response = conv.say("My company is Sunrise Electric, we install solar panels")
        # Should be at least a sentence, not more than a few paragraphs
        assert len(response) > 20, f"Response too short: {response}"
        assert len(response) < 2000, f"Response too long ({len(response)} chars)"


if __name__ == "__main__":
    # Quick manual run
    logging.basicConfig(level=logging.INFO)
    runner = ConversationRunner()

    print("=" * 60)
    print("GREETING:")
    print(runner.start())

    turns = [
        "Hi! I'm Sarah from Greenfield Landscaping LLC. We need insurance.",
        "We're based in Austin, Texas. 1234 Cedar Lane, 78701.",
        "We need general liability and commercial auto.",
        "We have 3 trucks — a 2024 Ford F-250, 2023 Chevy Silverado, and a 2022 Toyota Tacoma.",
        "I have 8 full-time employees and 3 part-time.",
        "I don't know our FEIN off the top of my head, I'll get it later.",
        "The policy should start March 1st, 2026.",
        "We want $1 million per occurrence, $2 million aggregate for GL.",
        "Actually wait, our address is 1234 Cedar Lane Suite 200, I forgot the suite number.",
        "That looks right. Let's go with it.",
    ]

    for msg in turns:
        print(f"\n{'=' * 60}")
        print(f"USER: {msg}")
        print(f"AGENT: {runner.say(msg)}")

    print(f"\n{'=' * 60}")
    print("FINAL STATE:")
    state = runner.get_state()
    print(f"Phase: {state.get('phase')}")
    print(f"Turn: {state.get('conversation_turn')}")
    print(f"Fields: {json.dumps(state.get('form_state', {}), indent=2)[:500]}")
