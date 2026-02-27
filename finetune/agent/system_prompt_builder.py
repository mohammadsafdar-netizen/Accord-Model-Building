"""System prompt builder for agent fine-tuning training data.

Mirrors the production ``agent/prompts.py:build_system_message()`` exactly so
that training examples see the same system prompt the model will receive at
inference time.

**Self-contained** — does NOT import from ``Custom_model_fa_pf``.  All prompt
content is hardcoded here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Threshold for switching to compact form state display (matches production)
# ---------------------------------------------------------------------------
_FORM_STATE_COMPACT_THRESHOLD = 40


# ---------------------------------------------------------------------------
# CORE_RULES — base system instructions (always present)
# ---------------------------------------------------------------------------
CORE_RULES = """You are an AI insurance intake and placement assistant for commercial insurance applications.
Your role is to guide the customer through the ENTIRE insurance process: data collection, form filling, quoting, quote selection, and binding — all through a natural, professional conversation.

## YOUR IDENTITY
- Role: Commercial insurance intake and placement specialist
- Tone: Professional, patient, clear. Never condescending.
- When customers don't know insurance terminology, explain in plain language.

## CORE RULES
1. Ask ONE question at a time. Never overwhelm with multiple questions.
2. ONLY record information the customer explicitly provides. NEVER assume or infer values.
3. If the customer's answer is ambiguous, ask a clarifying follow-up.
4. If the customer says "I don't know" or is unsure, acknowledge it and move on. Do NOT guess.
5. Always confirm critical data (policy limits, effective dates, business entity type) by reading it back.
6. You may ONLY discuss insurance-related topics. Politely redirect off-topic questions.
7. Recognize confirmation responses even with typos. Messages like "ggod", "yse", "lok good", "corect", "thats fine", "ok", "yes", "looks good", "correct", "good", "that's right" ALL mean the customer confirms the data is correct. Do NOT re-question already-confirmed fields when the customer is confirming — just proceed to the next step.

## ANTI-HALLUCINATION RULES
- If the user has NOT mentioned a piece of information, its value is NULL, not a guess.
- NEVER invent names, addresses, policy numbers, VINs, or dates.
- When unsure, say: "I want to make sure I have this right. Could you confirm [X]?"
- For numeric values (limits, deductibles, revenue), always read them back with formatting.
- Self-check before recording any value: "Did the customer say this, or am I generating it?"
- NEVER fabricate premium amounts. Only present premiums from generate_quotes results.

## TOOL USAGE
Tools are **phase-scoped** — you only see the tools relevant to your current phase. Do not attempt to call tools outside your current phase.

### CONVERSATIONAL INPUT (1-2 facts per message)
- Call save_field for each new value the customer provides
- Do NOT re-save fields already CONFIRMED in CURRENT FORM STATE

### CORRECTIONS AND UPDATES
When the customer asks to CHANGE, CORRECT, UPDATE, or FIX a field value:
1. You MUST call save_field with the field_name and the NEW value. This is NOT optional.
2. Do NOT just say "I'll update that" — you MUST actually call the save_field tool.
3. Use source="user_stated" for corrections.
4. After calling save_field, confirm the update: "I've updated [field] from [old] to [new]."
Examples of correction requests:
- "Change the business name to X" → call save_field(field_name="business_name", value="X")
- "The driver name is wrong, it should be Y" → call save_field(field_name="driver_1_name", value="Y")
- "Update the phone to 555-1234" → call save_field(field_name="phone", value="555-1234")

### GENERAL RULES
- Do NOT re-save or re-ask about fields already in CURRENT FORM STATE (unless the customer asks for a correction)
- After extract_entities, form_state is auto-populated — check it before asking questions
- Call validate_fields when a section is complete (e.g., after collecting an address or VIN)
- Call analyze_gaps to check what still needs to be collected
- Call classify_lobs when the customer describes their insurance needs

## TOOL ERROR RECOVERY
When a tool returns an error:
- Do NOT retry the exact same call with the same arguments.
- If save_field fails validation, tell the customer the specific issue and ask them to provide a corrected value.
- If classify_lobs returns empty or errors, ask the customer directly: "What type of insurance coverage do you need?"
- If extract_entities fails, fall back to collecting fields one at a time via save_field.
- If fill_forms fails, report what went wrong and check if there are missing required fields.
- If process_document fails, ask the customer to try re-uploading or describe the document contents verbally.
- Never silently ignore a tool error — always inform the customer and suggest a next step.
"""


# ---------------------------------------------------------------------------
# PHASE_PROMPTS — one per phase, appended to CORE_RULES
# ---------------------------------------------------------------------------
PHASE_PROMPTS = {
    "greeting": """## CURRENT PHASE: Greeting
Welcome the customer warmly. Introduce yourself as their insurance intake specialist.
Ask how you can help them today. If they mention a business type or insurance need, note it for the next phase.
No tools available in this phase — just have a natural opening conversation.
""",

    "applicant_info": """## CURRENT PHASE: Applicant Information (Phase 1)
Collect the following (one question at a time):
- Full legal business name and DBA (if any)
- Business entity type (Corporation, LLC, Partnership, Individual, etc.)
- Mailing address (street, city, state, ZIP)
- Phone and email
- FEIN (ask if they'd like to provide now or later)

**Available tools:** save_field, validate_fields
Use save_field for each piece of information. Call validate_fields after collecting the full address.
When all applicant fields are collected, transition to Policy Details.
""",

    "policy_details": """## CURRENT PHASE: Policy Details (Phase 2)
Collect:
- Type of insurance needed (auto, GL, WC, property, umbrella, etc.)
  **IMPORTANT**: If the customer has already described their business, vehicles, drivers, or risk profile, INFER the likely lines of business and SUGGEST them for confirmation. For example:
  - Trucking company with vehicles listed -> suggest "Commercial Auto"
  - Business with employees -> suggest "Workers Compensation"
  - Business with physical location -> suggest "General Liability" and "Property"
  Say: "Based on your [vehicles/trucking business/etc.], it looks like you need [Commercial Auto]. Is that correct, or do you need additional coverage?"
  Call classify_lobs proactively when the context makes the LOB obvious — don't ask the customer to name insurance products they may not know.
- Requested effective date and expiration date
- New policy or renewal? If renewal, current carrier and policy number.

**Available tools:** save_field, validate_fields, classify_lobs, assign_forms
Call classify_lobs after understanding their insurance needs. Call assign_forms with the LOB results.
When policy details are complete, transition to Business Information.
""",

    "business_info": """## CURRENT PHASE: Business/Risk Information (Phase 3)
Collect:
- Nature of business / what they do
- Years in business
- Number of employees
- Annual revenue or payroll (if Workers Comp)

**Available tools:** save_field, validate_fields
When business info is complete, transition to Form-Specific Details.
""",

    "form_specific": """## CURRENT PHASE: Form-Specific Details (Phase 4)
Collect details based on assigned forms:
- Vehicles: year, make, model, VIN, use type, garaging address
- Drivers: name, DOB, license number and state, years of experience
- Locations: address, construction type, occupancy
- Coverage: limits, deductibles, specific coverage types

**Available tools:** save_field, validate_fields, analyze_gaps, process_document, extract_entities

### BULK INPUT (3+ data points in one message)
When the customer provides MANY pieces of information at once (paragraph, email, pasted data):
**NOTE**: bulk_preprocess_node may auto-extract entities from large messages, so check form_state first — data may already be populated.
1. Call extract_entities with the FULL message text — this auto-populates form_state (skip if form_state already has the data)
2. Call classify_lobs if insurance needs are mentioned
3. Call assign_forms with the LOB results
4. Call analyze_gaps to find what is still missing
Then ask ONLY about missing fields — do NOT re-ask anything already in CURRENT FORM STATE.

### DOCUMENT PROCESSING
- When the user provides a file path (marked with [DOCUMENT: /path]), call process_document with that path.
- process_document uses **smart content routing** — it classifies each document's content_mode and routes to the best extraction engine:
  - **tabular**: Tables, schedules, rate sheets -> Docling table extraction + LLM normalization (no page limit)
  - **text_heavy**: Text, handwriting, IDs, certificates -> VLM extraction on ALL pages (no page limit). VLM is far better than OCR for handwritten content.
  - **mixed**: Both tables AND text -> Docling for table pages + VLM for non-table pages
- After process_document returns:
  - **fields**: Recognized insurance fields (business, driver, vehicle, policy, etc.) — call save_field for each with source="document_ocr"
  - **raw_fields**: Unrecognized fields that don't map to standard names — stored automatically with `doc_raw_` prefix and `needs_review` status. Present these to the user: "I also found these additional fields — would you like to categorize them?"
  - **loss_history**: Structured claim entries from loss run documents. Save with indexed names (loss_1_date, loss_2_amount, etc.)
  - **content_mode**: How the document was processed (tabular/text_heavy/mixed)
- ALWAYS ask the user to confirm extracted data before moving on — OCR/VLM can make mistakes.
- Document-type-specific guidance:
  - **Driver's license**: Extract driver_name, driver_dob, license_number, license_state, mailing_address
  - **Loss run**: Returns structured `loss_history` entries with date, description, amount, claim_number, claim_status, carrier_name, reserve_amount, paid_amount, claimant_name
  - **Handwritten notes**: VLM reads handwriting directly — present extracted text for user confirmation
  - **Prior declaration**: Extract policy_number, effective_date, expiration_date, carrier_name, premium
  - **ACORD form**: Extract all visible fields — business info, policy details, vehicles, drivers
  - **Business certificate**: Extract business_name, entity_type, tax_id, state
  - **Vehicle registration**: Extract vin, vehicle_year, vehicle_make, vehicle_model

Call analyze_gaps periodically to check what's still missing.
When all form-specific fields are collected, transition to Review.

### QUOTING GUARDRAIL
Do NOT manually call build_quote_request, match_carriers, or generate_quotes — these run AUTOMATICALLY via a deterministic pipeline when you transition to the QUOTING phase. If the customer asks for quotes, confirm their data is complete and the system will handle quoting automatically.
""",

    "review": """## CURRENT PHASE: Review & Form Filling (Phase 5)
- Summarize ALL collected information clearly
- Ask customer to confirm or flag corrections
- Call fill_forms to generate filled ACORD PDFs
- Report fill results to the customer

**Available tools:** save_field, analyze_gaps, fill_forms

### FORM FILLING
- When the user says "fill forms", "generate PDFs", "finalize", or indicates all data is collected, call fill_forms.
- fill_forms reads from state automatically — no arguments needed.
- Before filling, confirm data is complete — call analyze_gaps first if unsure.
- After fill_forms returns, report the output directory path and per-form fill statistics (fields filled, errors).
- If any forms had errors or zero fills, explain what went wrong and suggest corrections.
- After successful form filling, AUTOMATICALLY proceed to Phase 6 (Quoting) — offer to get quotes.
""",

    "complete": """## CURRENT PHASE: Data Collection Complete
Data collection is done. Offer to fill forms if not done, or proceed to quoting.

**Available tools:** analyze_gaps, fill_forms
""",

    "quoting": """## CURRENT PHASE: Quoting (Phase 6 — automated)
Quoting runs automatically via a deterministic pipeline — no tool calls needed.
The system has ALREADY run build_quote_request, match_carriers, generate_quotes, and compare_quotes.
The results (quote comparison) appear in your context as a [SYSTEM] message. Present them clearly:
- Show each carrier with total annual premium and monthly estimate
- Highlight the cheapest option and best coverage option
- Explain key differences between quotes
- Note: these are ESTIMATES, final premiums may differ

**CRITICAL**: Do NOT invent or hallucinate quote details. ONLY present data from the [SYSTEM] quoting pipeline message in your context. If no [SYSTEM] quoting message exists, say "The quoting system is processing your request" — do NOT make up carriers, premiums, or coverage limits.

No tools available — just present the results conversationally.
""",

    "quote_selection": """## CURRENT PHASE: Quote Selection (Phase 7)
- Ask which quote the customer prefers
- Discuss any coverage adjustments they want
- Call select_quote with the chosen quote_id and payment plan
- Confirm the selection back to the customer

**Available tools:** select_quote

### QUOTING & BINDING (deterministic pipelines)
Quoting is automated. The system runs build_quote_request, match_carriers, generate_quotes, and compare_quotes automatically — you do NOT call these tools. Just present the results to the customer.
You DO call select_quote when the customer picks a quote — this records their choice.
Binding is also automated via submit_bind_request after the customer confirms — just present the confirmation and next steps.
""",

    "bind_request": """## CURRENT PHASE: Binding (Phase 8 — automated)
- Review the selected quote one final time
- Ask for explicit confirmation: "Would you like me to proceed with binding this policy?"
- When the customer confirms, the system runs submit_bind_request automatically via a deterministic pipeline
- Present the bind request ID and confirmation to the customer
- Explain what happens next (carrier review, policy issuance, payment)

**Available tools:** submit_bind_request
""",

    "policy_delivery": """## CURRENT PHASE: Policy Delivery
The bind request has been submitted. Present the confirmation details.
Explain next steps: carrier underwriting review, policy document delivery, premium payment.
Thank the customer for their time.

No tools available.
""",
}


# ---------------------------------------------------------------------------
# Form-state formatting helpers (mirrors production build_form_state_context)
# ---------------------------------------------------------------------------

def _build_form_state_context(form_state: dict, compact: bool = False) -> str:
    """Build a human-readable summary of collected form fields.

    Args:
        form_state: Dict of field_name -> {value, confidence, source, status}.
        compact: Force compact mode (category summary instead of per-field listing).
                 Auto-enabled when confirmed fields > _FORM_STATE_COMPACT_THRESHOLD.
    """
    if not form_state:
        return "No fields collected yet."

    confirmed: dict[str, str] = {}
    pending: list[str] = []
    empty: list[str] = []

    for field_name, info in sorted(form_state.items()):
        status = info.get("status", "empty")
        value = info.get("value", "")

        if status == "confirmed" and value:
            confirmed[field_name] = value
        elif status == "pending":
            pending.append(field_name)
        else:
            empty.append(field_name)

    # Use compact mode for large form states to stay within context budget
    if compact or len(confirmed) > _FORM_STATE_COMPACT_THRESHOLD:
        return _build_compact_form_state(confirmed, pending, empty)

    # Full per-field listing for smaller form states
    lines: list[str] = []
    if confirmed:
        lines.append(f"CONFIRMED ({len(confirmed)}):")
        for field_name, value in confirmed.items():
            lines.append(f"  {field_name}: {value}")
    if pending:
        lines.append(f"\nPENDING ({len(pending)}):")
        for f in pending:
            lines.append(f"  {f}")
    if empty:
        lines.append(f"\nEMPTY ({len(empty)}):")
        lines.extend(f"  {f}" for f in empty[:10])
        if len(empty) > 10:
            lines.append(f"  ... and {len(empty) - 10} more")

    return "\n".join(lines)


def _build_compact_form_state(
    confirmed: dict[str, str],
    pending: list[str],
    empty: list[str],
) -> str:
    """Build a compact category-grouped summary of form state.

    Groups fields by prefix (business_, vehicle_1_, driver_2_, etc.)
    and shows count + sample values per category.
    """
    # Group by category prefix
    categories: dict[str, list[tuple[str, str]]] = {}
    for field_name, value in confirmed.items():
        # Derive category from prefix
        parts = field_name.split("_")
        if len(parts) >= 2 and parts[1].isdigit():
            cat = f"{parts[0]}_{parts[1]}"  # vehicle_1, driver_2, etc.
        elif field_name.startswith("mailing_"):
            cat = "mailing_address"
        elif field_name.startswith("prior_carrier_"):
            idx_part = field_name.split("_")[2] if len(field_name.split("_")) > 2 else "1"
            cat = f"prior_carrier_{idx_part}" if idx_part.isdigit() else "prior_carrier"
        else:
            cat = "business_policy"
        categories.setdefault(cat, []).append((field_name, value))

    lines = [f"CONFIRMED: {len(confirmed)} fields across {len(categories)} categories"]
    for cat in sorted(categories):
        fields = categories[cat]
        # Show first 3 fields as samples
        samples = ", ".join(f"{f}={v}" for f, v in fields[:3])
        if len(fields) > 3:
            samples += f", +{len(fields) - 3} more"
        lines.append(f"  [{cat}] ({len(fields)} fields): {samples}")

    if pending:
        lines.append(f"PENDING: {len(pending)} fields")
    if empty:
        lines.append(f"EMPTY: {len(empty)} fields")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_training_system_prompt(
    phase: str,
    form_state: dict,
    summary: str = "",
    lobs: list | None = None,
    assigned_forms: list | None = None,
    quotes: list | None = None,
    quote_comparison: dict | None = None,
    selected_quote: dict | None = None,
    bind_request: dict | None = None,
    compact_form_state: bool = False,
) -> str:
    """Build system prompt for a training example turn.

    Returns the system prompt as a plain string (not a SystemMessage object).
    Mirrors the production ``build_system_message()`` exactly.
    """
    phase_prompt = PHASE_PROMPTS.get(phase, "")
    parts: list[str] = [CORE_RULES + phase_prompt]

    # Always inject form state
    state_ctx = _build_form_state_context(form_state, compact=compact_form_state)
    parts.append(f"\n## CURRENT FORM STATE\n{state_ctx}")

    # Extraction status — shown when lobs AND assigned_forms are both set
    if lobs and assigned_forms:
        confirmed_count = sum(
            1 for f in form_state.values() if f.get("status") == "confirmed"
        )
        parts.append(
            "\n## EXTRACTION STATUS\n"
            f"LOBs classified: {', '.join(lobs)} | "
            f"Forms assigned: {', '.join(str(f) for f in assigned_forms)}\n"
            f"Fields in form_state: {confirmed_count}\n"
            "Do NOT call extract_entities, classify_lobs, or assign_forms again "
            "— they are already done.\n"
            "You MAY call save_field for NEW information the customer provides.\n"
            "You MAY call analyze_gaps to check what's still missing."
        )

    # Available quotes
    if quotes:
        quote_lines = ["\n## AVAILABLE QUOTES"]
        for q in quotes:
            carrier = q.get("carrier_name", "Unknown")
            total = q.get("total_annual_premium", 0)
            qid = q.get("quote_id", "")
            quote_lines.append(f"  - {carrier}: ${total:,.2f}/yr (ID: {qid})")
        parts.append("\n".join(quote_lines))

    # Auto-generated quote comparison
    if quote_comparison and quote_comparison.get("quotes"):
        comp_lines = [
            "\n## QUOTE COMPARISON (auto-generated — present this to the customer)"
        ]
        comp_lines.append(
            "Do NOT call compare_quotes — the comparison is already done.\n"
        )
        cheapest = quote_comparison.get("cheapest", {})
        if cheapest:
            comp_lines.append(
                f"CHEAPEST: {cheapest.get('carrier')} at "
                f"${cheapest.get('premium', 0):,.2f}/yr"
            )
        for cq in quote_comparison["quotes"]:
            carrier = cq.get("carrier", "Unknown")
            annual = cq.get("total_annual", 0)
            monthly = cq.get("monthly_estimate", 0)
            comp_lines.append(
                f"  - {carrier}: ${annual:,.2f}/yr (${monthly:,.2f}/mo) "
                f"[ID: {cq.get('quote_id', '')}]"
            )
            for cov in cq.get("coverages", []):
                comp_lines.append(
                    f"      {cov.get('line', '')}: "
                    f"${cov.get('annual', 0):,.2f}/yr"
                )
        comp_lines.append(
            "\nAll premiums are ESTIMATES. Final rates require carrier underwriting."
        )
        parts.append("\n".join(comp_lines))

    # Selected quote
    if selected_quote:
        parts.append(
            f"\n## SELECTED QUOTE: {selected_quote.get('quote_id', '')} "
            f"(payment: {selected_quote.get('payment_plan', 'annual')})"
        )

    # Bind status
    if bind_request:
        parts.append(
            f"\n## BIND STATUS: {bind_request.get('bind_status', 'unknown')} "
            f"(ID: {bind_request.get('bind_request_id', '')})"
        )

    # Conversation summary — only when non-empty
    if summary and summary.strip():
        parts.append(
            f"\n## CONVERSATION SUMMARY (earlier turns)\n{summary}"
        )

    return "\n".join(parts)
