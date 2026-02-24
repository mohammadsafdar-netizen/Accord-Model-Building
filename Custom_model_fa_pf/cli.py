"""CLI chat interface for the insurance intake agent."""

import json
import logging
import os
import re
import sys
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from Custom_model_fa_pf.agent.state import IntakePhase, create_initial_state
from Custom_model_fa_pf.agent.graph import create_agent
from Custom_model_fa_pf.config import SUPPORTED_UPLOAD_EXTENSIONS

console = Console()
logger = logging.getLogger(__name__)

# Phase descriptions for human-friendly display
PHASE_DESCRIPTIONS = {
    "greeting": "Initial greeting",
    "applicant_info": "Collecting applicant information",
    "policy_details": "Gathering policy details",
    "business_info": "Learning about the business",
    "form_specific": "Filling form-specific fields",
    "review": "Reviewing collected information",
    "complete": "Intake complete",
}


def format_agent_response(text: str) -> str:
    """Clean up agent response text for display.

    Strips save_field() text that smaller models sometimes include
    in their conversational output instead of using proper tool calls.
    """
    import re
    # Remove lines that are just save_field(...) calls
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^save_field\(', stripped):
            continue  # Skip tool call text
        cleaned.append(line)
    return "\n".join(cleaned).strip()


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


def _truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _format_tool_args(args: dict) -> str:
    """Format tool call arguments as compact key: value lines."""
    lines = []
    for k, v in args.items():
        val_str = str(v)
        lines.append(f"  {k}: {_truncate(val_str, 120)}")
    return "\n".join(lines)


def _format_tool_result(content: str) -> str:
    """Format tool result content — try to parse as JSON for readability."""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            lines = []
            for k, v in parsed.items():
                val_str = str(v)
                lines.append(f"  {k}: {_truncate(val_str, 120)}")
            return "\n".join(lines)
        return _truncate(json.dumps(parsed, indent=2), 400)
    except (json.JSONDecodeError, TypeError):
        return _truncate(content, 400)


def display_verbose_messages(messages: list, skip: int, console: Console):
    """Display step-by-step details for all new messages when verbose mode is active.

    Shows tool calls, tool results, and reflection/system messages with Rich panels.
    """
    for msg in messages[skip:]:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                name = tc.get("name", "unknown")
                args = tc.get("args", {})
                console.print(Panel(
                    _format_tool_args(args),
                    title=f"TOOL CALL: {name}",
                    border_style="cyan",
                    padding=(0, 1),
                ))

        elif isinstance(msg, ToolMessage):
            name = getattr(msg, "name", "") or "tool"
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            # Use green border for document processing results
            border = "green" if name == "process_document" else "yellow"
            console.print(Panel(
                _format_tool_result(content),
                title=f"TOOL RESULT: {name}",
                border_style=border,
                padding=(0, 1),
            ))

        elif isinstance(msg, SystemMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            # Try to parse reflection JSON from content
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "verdict" in parsed:
                    verdict = parsed.get("verdict", "?")
                    issues = parsed.get("issues", [])
                    suggestion = parsed.get("suggestion", "")
                    lines = [f"  verdict: {verdict}"]
                    if issues:
                        lines.append(f"  issues: {', '.join(issues)}")
                    if suggestion:
                        lines.append(f"  suggestion: {_truncate(suggestion, 150)}")
                    display = "\n".join(lines)
                else:
                    display = _truncate(content, 400)
            except (json.JSONDecodeError, TypeError):
                display = _truncate(content, 400)

            console.print(Panel(
                display,
                title="REFLECTION",
                border_style="magenta",
                padding=(0, 1),
            ))


def display_state_status(agent, config, console: Console):
    """Print a compact status line showing phase, fields, LOBs, forms."""
    try:
        state = agent.get_state(config)
        vals = state.values

        phase = vals.get("phase", "unknown")
        form_state = vals.get("form_state", {})
        confirmed = sum(1 for f in form_state.values() if f.get("status") == "confirmed")
        lobs = vals.get("lobs", [])
        assigned = vals.get("assigned_forms", [])

        parts = [f"Phase: {phase}"]
        parts.append(f"Fields: {confirmed} confirmed")
        if lobs:
            lob_names = [l if isinstance(l, str) else l.get("lob_id", "?") for l in lobs]
            parts.append(f"LOBs: {', '.join(lob_names)}")
        if assigned:
            parts.append(f"Forms: {', '.join(str(f) for f in assigned)}")

        console.rule(f"[dim]{' | '.join(parts)}[/dim]", style="dim")
    except Exception:
        pass  # Don't crash on state read errors


def handle_fields_command(agent, config, console: Console):
    """Show all confirmed fields grouped by simple categories."""
    state = agent.get_state(config)
    vals = state.values
    form_state = vals.get("form_state", {})
    lobs = vals.get("lobs", [])
    assigned = vals.get("assigned_forms", [])

    confirmed = {k: v for k, v in form_state.items() if v.get("status") == "confirmed"}

    if not confirmed and not lobs:
        console.print(Panel(
            "[dim]No fields collected yet. Start the conversation![/dim]",
            title="Collected Fields",
            border_style="blue",
        ))
        return

    # Group fields by prefix heuristic
    groups: dict[str, list[tuple[str, str]]] = {}
    for field_name, info in sorted(confirmed.items()):
        value = info.get("value", "")
        # Derive category from field name prefix
        parts = field_name.split("_")
        if parts[0] in ("business", "company", "applicant", "entity"):
            cat = "BUSINESS"
        elif parts[0] in ("phone", "email", "contact", "fax"):
            cat = "CONTACT"
        elif parts[0] in ("policy", "effective", "expiration", "coverage"):
            cat = "POLICY"
        elif parts[0] in ("driver", "license"):
            cat = "DRIVERS"
        elif parts[0] in ("vehicle", "vin", "make", "model", "year"):
            cat = "VEHICLES"
        elif parts[0] in ("mailing", "location", "address", "city", "state", "zip"):
            cat = "ADDRESS"
        else:
            cat = "OTHER"
        groups.setdefault(cat, []).append((field_name, value))

    lines = []
    for cat in ["BUSINESS", "CONTACT", "ADDRESS", "POLICY", "DRIVERS", "VEHICLES", "OTHER"]:
        if cat not in groups:
            continue
        lines.append(f"[bold]{cat}[/bold]")
        for fname, fval in groups[cat]:
            lines.append(f"  {fname}: {fval}")

    if lobs:
        lob_names = [l if isinstance(l, str) else l.get("lob_id", "?") for l in lobs]
        lines.append(f"\n[bold]LOBs:[/bold] {', '.join(lob_names)}")
    if assigned:
        lines.append(f"[bold]Forms:[/bold] {', '.join(str(f) for f in assigned)}")

    console.print(Panel(
        "\n".join(lines),
        title=f"Collected Fields ({len(confirmed)} confirmed)",
        border_style="blue",
    ))


def handle_forms_command(agent, config, console: Console):
    """Show form assignment status and field mapping progress."""
    state = agent.get_state(config)
    vals = state.values
    assigned = vals.get("assigned_forms", [])
    form_state = vals.get("form_state", {})

    if not assigned:
        console.print(Panel(
            "[dim]No forms assigned yet — provide business info and LOBs first.[/dim]",
            title="Form Assignments",
            border_style="blue",
        ))
        return

    # Form purpose lookup
    form_purposes = {
        "125": "Commercial Insurance Application",
        "126": "Commercial General Liability Section",
        "127": "Commercial Auto Section",
        "137": "Commercial Auto Section (cont.)",
        "163": "Workers Compensation Application",
    }

    confirmed = {k: v for k, v in form_state.items() if v.get("status") == "confirmed"}

    lines = []
    for form_num in assigned:
        fnum = str(form_num)
        purpose = form_purposes.get(fnum, "ACORD Form")
        lines.append(f"[bold]Form {fnum}:[/bold] {purpose}")
        # Count fields that might belong to this form (heuristic — show total)
        lines.append(f"  {len(confirmed)} total confirmed fields in session")

    console.print(Panel(
        "\n".join(lines),
        title="Form Assignments",
        border_style="blue",
    ))


def handle_status_command(agent, config, session_id: str, console: Console):
    """Enhanced status display with phase, fields, LOBs, forms, validation."""
    state = agent.get_state(config)
    vals = state.values

    phase = vals.get("phase", "unknown")
    phase_desc = PHASE_DESCRIPTIONS.get(phase, "")
    form_state = vals.get("form_state", {})
    lobs = vals.get("lobs", [])
    assigned = vals.get("assigned_forms", [])
    validation_issues = vals.get("validation_issues", [])
    turn = vals.get("conversation_turn", 0)

    confirmed = {k: v for k, v in form_state.items() if v.get("status") == "confirmed"}
    pending = {k: v for k, v in form_state.items() if v.get("status") == "pending"}

    lines = []
    lines.append(f"[bold]Phase:[/bold] {phase}" + (f" — {phase_desc}" if phase_desc else ""))
    lines.append(f"[bold]Turn:[/bold] {turn}")
    lines.append(f"[bold]Session:[/bold] {session_id}")
    lines.append("")

    # Fields summary
    lines.append(f"[bold]Fields:[/bold] {len(confirmed)} confirmed, {len(pending)} pending")
    if confirmed:
        # Show up to 10 field names
        field_names = sorted(confirmed.keys())
        preview = field_names[:10]
        names_str = ", ".join(preview)
        if len(field_names) > 10:
            names_str += f", ... (+{len(field_names) - 10} more)"
        lines.append(f"  [dim]{names_str}[/dim]")

    # LOBs
    if lobs:
        lob_names = [l if isinstance(l, str) else l.get("lob_id", "?") for l in lobs]
        lines.append(f"\n[bold]LOBs:[/bold] {', '.join(lob_names)}")
    else:
        lines.append(f"\n[bold]LOBs:[/bold] [dim]not yet classified[/dim]")

    # Forms
    if assigned:
        lines.append(f"[bold]Forms:[/bold] {', '.join(str(f) for f in assigned)}")
    else:
        lines.append(f"[bold]Forms:[/bold] [dim]not yet assigned[/dim]")

    # Validation issues
    if validation_issues:
        lines.append(f"\n[bold yellow]Validation Issues ({len(validation_issues)}):[/bold yellow]")
        for issue in validation_issues[:5]:
            if isinstance(issue, dict):
                lines.append(f"  - {issue.get('message', issue.get('field', str(issue)))}")
            else:
                lines.append(f"  - {issue}")
        if len(validation_issues) > 5:
            lines.append(f"  ... +{len(validation_issues) - 5} more")

    console.print(Panel(
        "\n".join(lines),
        title="Status",
        border_style="yellow",
    ))


def _detect_document_path(text: str) -> str | None:
    """Detect a file path in user input that points to a supported document.

    Returns the resolved path if found and the file exists, else None.
    """
    # Match paths like /path/to/file.pdf, ~/docs/scan.png, ./file.jpg
    pattern = r'(?:^|\s)((?:[/~.]|[A-Za-z]:)[^\s,;]+\.(?:' + '|'.join(
        ext.lstrip('.') for ext in SUPPORTED_UPLOAD_EXTENSIONS
    ) + r'))(?:\s|$|[,;])'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        path = os.path.expanduser(match.group(1))
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None


def run_chat(verbose: bool = False):
    """Run the interactive chat CLI."""
    commands = "/quit, /status, /fields, /forms, /upload, /finalize, /reset"
    console.print(Panel(
        "[bold]ACORD Insurance Intake Agent[/bold]\n"
        "Type your messages to interact with the agent.\n"
        f"Commands: {commands}"
        + ("\n[dim]Verbose mode: ON[/dim]" if verbose else ""),
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
        if verbose:
            display_verbose_messages(all_msgs, msg_count, console)
        greeting = extract_text_from_messages(all_msgs, skip=msg_count)
        msg_count = len(all_msgs)
        if greeting:
            console.print(Panel(
                Markdown(format_agent_response(greeting)),
                title="Agent",
                border_style="green",
            ))
        if verbose:
            display_state_status(agent, config, console)
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
            handle_status_command(agent, config, session_id, console)
            continue

        if user_input.lower() == "/fields":
            handle_fields_command(agent, config, console)
            continue

        if user_input.lower() == "/forms":
            handle_forms_command(agent, config, console)
            continue

        if user_input.lower() == "/finalize":
            console.print("[cyan]Finalizing — generating filled ACORD forms...[/cyan]")
            user_input = (
                "Please finalize and fill all assigned ACORD forms with the collected data. "
                "Call fill_forms with the current entities and assigned forms."
            )

        if user_input.lower().startswith("/upload"):
            # Parse: /upload /path/to/file
            parts = user_input.split(None, 1)
            if len(parts) < 2 or not parts[1].strip():
                console.print("[yellow]Usage: /upload /path/to/document.pdf[/yellow]")
                continue
            raw_path = parts[1].strip()
            doc_path = os.path.expanduser(raw_path)
            if not os.path.isfile(doc_path):
                console.print(f"[red]File not found: {raw_path}[/red]")
                continue
            ext = os.path.splitext(doc_path)[1].lower()
            if ext not in SUPPORTED_UPLOAD_EXTENSIONS:
                console.print(
                    f"[red]Unsupported file type '{ext}'. "
                    f"Supported: {', '.join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))}[/red]"
                )
                continue
            doc_path = os.path.abspath(doc_path)
            console.print(f"[cyan]Processing document: {doc_path}[/cyan]")
            user_input = f"[DOCUMENT: {doc_path}] Please process this uploaded document and extract all insurance-relevant fields."

        if user_input.lower() == "/reset":
            session_id = str(uuid.uuid4())[:8]
            config = {"configurable": {"thread_id": f"cli:{session_id}"}}
            msg_count = 0
            initial_state = create_initial_state(session_id)
            result = agent.invoke(initial_state, config=config)
            all_msgs = result.get("messages", [])
            if verbose:
                display_verbose_messages(all_msgs, msg_count, console)
            greeting = extract_text_from_messages(all_msgs, skip=msg_count)
            msg_count = len(all_msgs)
            if greeting:
                console.print(Panel(
                    Markdown(format_agent_response(greeting)),
                    title="Agent",
                    border_style="green",
                ))
            if verbose:
                display_state_status(agent, config, console)
            continue

        # Auto-detect document paths in regular messages
        if not user_input.startswith("[DOCUMENT:"):
            detected = _detect_document_path(user_input)
            if detected:
                console.print(f"[cyan]Detected document: {detected}[/cyan]")
                user_input = f"[DOCUMENT: {detected}] {user_input}"

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

            # Verbose: show all internal steps before the final response
            if verbose:
                display_verbose_messages(all_msgs, prev_count + 1, console)

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

            # Verbose: show state after turn
            if verbose:
                display_state_status(agent, config, console)

        except Exception as e:
            logger.exception("Agent error")
            console.print(f"[red]Error: {e}[/red]")


def main():
    """Entry point for the CLI."""
    import argparse
    parser = argparse.ArgumentParser(description="ACORD Insurance Intake Agent CLI")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show tool calls, results, reflections, and state after each turn")
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

    run_chat(verbose=args.verbose)


if __name__ == "__main__":
    main()
