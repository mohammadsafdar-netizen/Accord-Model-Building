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


REFLECTION_PROMPT = """Review this agent response for an insurance intake conversation.

RESPONSE TO REVIEW:
{response}

CURRENT FORM STATE:
{form_state_summary}

CHECK FOR:
1. Hallucinated data — does the response claim information the customer never provided?
2. Multiple questions — does it ask more than one question at a time?
3. Off-topic content — does it discuss anything other than insurance intake?
4. Incorrect confirmations — does it confirm values that don't match the form state?
5. Missing tool calls — should the agent have saved a field or run validation?

If ALL checks pass, respond with exactly: {{"verdict": "pass"}}
If ANY check fails, respond with: {{"verdict": "revise", "issues": ["issue1", ...], "suggestion": "how to fix"}}
Respond ONLY with valid JSON. No other text.
"""


SUMMARIZE_PROMPT = """Summarize this insurance intake conversation concisely.

CONVERSATION:
{conversation_text}

CURRENT FORM STATE:
{form_state_summary}

Create a brief summary that captures:
1. What information has been collected so far
2. What the customer's business is about
3. Any corrections or changes the customer requested
4. What was discussed most recently

Keep the summary under 500 words. Focus on facts, not conversation flow.
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
