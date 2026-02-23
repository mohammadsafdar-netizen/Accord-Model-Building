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


def extract_text_from_messages(messages: list, skip: int = 0) -> str:
    """Extract displayable text from a list of LangGraph messages.

    Skips tool call messages and tool results — only returns AI text responses.

    Args:
        messages: Full list of messages from the graph state.
        skip: Number of messages to skip from the start (already displayed).
    """
    texts = []
    for msg in messages[skip:]:
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

    # Track message count to only display new messages each turn
    msg_count = 0

    # Initial greeting — invoke with empty input to trigger greet node
    initial_state = create_initial_state(session_id)
    try:
        result = agent.invoke(initial_state, config=config)
        all_msgs = result.get("messages", [])
        greeting = extract_text_from_messages(all_msgs, skip=msg_count)
        msg_count = len(all_msgs)
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
            msg_count = 0
            initial_state = create_initial_state(session_id)
            result = agent.invoke(initial_state, config=config)
            all_msgs = result.get("messages", [])
            greeting = extract_text_from_messages(all_msgs, skip=msg_count)
            msg_count = len(all_msgs)
            if greeting:
                console.print(Panel(
                    Markdown(format_agent_response(greeting)),
                    title="Agent",
                    border_style="green",
                ))
            continue

        # Send user message to agent
        try:
            # Count messages before invoke to skip already-displayed ones
            # (+1 for the HumanMessage we're about to add)
            prev_count = msg_count

            result = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
            )
            all_msgs = result.get("messages", [])
            # Skip previous messages + the user message we just sent
            response = extract_text_from_messages(all_msgs, skip=prev_count + 1)
            msg_count = len(all_msgs)

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
