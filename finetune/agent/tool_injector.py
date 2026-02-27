"""
Deterministic tool call injector for agent fine-tuning dataset.

Takes a TurnSkeleton + accumulated form_state and produces OpenAI-format
tool call / tool response pairs, plus an updated form_state.

Self-contained: does NOT import from Custom_model_fa_pf. All normalization
logic, key aliases, and confidence scoring are hardcoded here so the
fine-tuning pipeline runs independently of the production agent.

Usage:
    from finetune.agent.tool_injector import inject_tool_calls
    interactions, new_form_state = inject_tool_calls(turn, form_state, scenario)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from finetune.agent.scenario_generator import ConversationScenario, LOB_FORMS
from finetune.agent.skeleton_builder import TurnSkeleton

# ---------------------------------------------------------------------------
# Key aliases — mirrors production agent/tools.py _KEY_ALIASES (102 entries)
# ---------------------------------------------------------------------------

KEY_ALIASES: Dict[str, str] = {
    # Business address variants
    "business_address_street": "mailing_street",
    "business_address_city": "mailing_city",
    "business_address_state": "mailing_state",
    "business_address_zip": "mailing_zip",
    "business_street": "mailing_street",
    "business_city": "mailing_city",
    "business_state": "mailing_state",
    "business_zip": "mailing_zip",
    "address_street": "mailing_street",
    "address_city": "mailing_city",
    "address_state": "mailing_state",
    "address_zip": "mailing_zip",
    # Employee variants
    "num_full_time_employees": "employee_count",
    "full_time_employees": "employee_count",
    "num_employees": "employee_count",
    "total_employees": "employee_count",
    "num_part_time_employees": "part_time_employees",
    # Monetary fields
    "subcontractor_costs": "subcontractor_cost",
    # Name variants
    "applicant_name": "contact_name",
    "owner_name": "contact_name",
    "insured_name": "contact_name",
    # Producer/agent variants
    "agent_name": "producer_contact_name",
    "agent_company": "producer_agency_name",
    "agent_address": "producer_street",
    "agent_address_street": "producer_street",
    "agent_address_city": "producer_city",
    "agent_address_state": "producer_state",
    "agent_address_zip": "producer_zip",
    "agent_phone": "producer_phone",
    "agent_email": "producer_email",
    "agent_producer_code": "producer_code",
    "agent_license_number": "producer_license_number",
    # Prior carrier variants
    "current_carrier": "prior_carrier_1_carrier",
    "prior_carrier": "prior_carrier_1_carrier",
    "current_policy_number": "prior_carrier_1_policy_number",
    "current_policy_effective_date": "prior_carrier_1_effective_date",
    "current_policy_expiration_date": "prior_carrier_1_expiration_date",
    "current_effective_date": "prior_carrier_1_effective_date",
    "current_expiration_date": "prior_carrier_1_expiration_date",
    "current_annual_premium": "prior_carrier_1_premium",
    "current_premium": "prior_carrier_1_premium",
    # Location/terminal variants
    "terminal_address_street": "location_1_street",
    "terminal_address_city": "location_1_city",
    "terminal_address_state": "location_1_state",
    "terminal_address_zip": "location_1_zip",
    "terminal_square_footage": "location_1_building_area",
    "terminal_construction_type": "location_1_construction_type",
    "terminal_year_built": "location_1_year_built",
    "terminal_occupancy": "location_1_occupancy",
    # main_terminal_* variants
    "main_terminal_address_street": "location_1_street",
    "main_terminal_address_city": "location_1_city",
    "main_terminal_address_state": "location_1_state",
    "main_terminal_address_zip": "location_1_zip",
    "main_terminal_square_footage": "location_1_building_area",
    "main_terminal_construction_type": "location_1_construction_type",
    "main_terminal_year_built": "location_1_year_built",
    "main_terminal_occupancy": "location_1_occupancy",
    # Policy dates
    "policy_effective_date": "effective_date",
    "policy_expiration_date": "expiration_date",
    "requested_effective_date": "effective_date",
    "requested_expiration_date": "expiration_date",
    "coverage_start_date": "effective_date",
    # Lienholder
    "lienholder_name": "additional_interest_1_name",
    "lienholder_account": "additional_interest_1_account_number",
    "lienholder_address_street": "additional_interest_1_street",
    "lienholder_address_city": "additional_interest_1_city",
    "lienholder_address_state": "additional_interest_1_state",
    "lienholder_address_zip": "additional_interest_1_zip",
}

# ---------------------------------------------------------------------------
# Monetary field keywords — used for value normalization
# ---------------------------------------------------------------------------

_MONETARY_KEYWORDS = {
    "annual_payroll", "annual_revenue", "subcontractor_cost", "premium",
    "cost_new", "stated_amount", "amount",
}

# ---------------------------------------------------------------------------
# Confidence source weights — mirrors production ConfidenceScorer
# ---------------------------------------------------------------------------

_SOURCE_WEIGHTS: Dict[str, float] = {
    "user_stated": 0.95,
    "user_confirmed": 1.00,
    "llm_inferred": 0.60,
    "validated_external": 0.98,
    "defaulted": 0.50,
    "ocr_extracted": 0.80,
    "document_ocr": 0.85,
    "extracted": 0.85,
}

# ---------------------------------------------------------------------------
# Critical/important field lists for gap analysis
# ---------------------------------------------------------------------------

_CRITICAL_FIELDS = [
    "business_name", "mailing_street", "mailing_city", "mailing_state",
    "mailing_zip", "entity_type", "tax_id", "effective_date",
    "expiration_date", "contact_name",
]

_IMPORTANT_FIELDS = [
    "nature_of_business", "operations_description", "employee_count",
    "annual_revenue", "years_in_business", "annual_payroll",
    "contact_phone", "contact_email",
]

# ---------------------------------------------------------------------------
# Helper: normalize key via aliases
# ---------------------------------------------------------------------------


def _resolve_alias(field_name: str) -> str:
    """Resolve a field name through KEY_ALIASES to its canonical form."""
    return KEY_ALIASES.get(field_name, field_name)


# ---------------------------------------------------------------------------
# Helper: normalize monetary values
# ---------------------------------------------------------------------------


def _normalize_value(field_name: str, value: str) -> str:
    """Normalize field values: strip $, commas from money; convert text numbers.

    Mirrors production agent/tools.py:_normalize_value exactly.
    """
    cleaned = value.strip()

    # Check if field name contains a monetary keyword
    is_monetary = any(kw in field_name.lower() for kw in _MONETARY_KEYWORDS)
    if is_monetary or (cleaned.startswith("$") and any(c.isdigit() for c in cleaned)):
        # Handle "$4.2 million" / "$4.2M"
        m = re.match(r'^\$?([\d,.]+)\s*(million|mil|m)$', cleaned, re.IGNORECASE)
        if m:
            num = float(m.group(1).replace(",", ""))
            return str(int(num * 1_000_000))
        # Handle "$1,850,000" or "$67,500"
        stripped = cleaned.lstrip("$").replace(",", "").strip()
        if stripped.replace(".", "").isdigit():
            try:
                f = float(stripped)
                return str(int(f)) if f == int(f) else stripped
            except ValueError:
                pass
            return stripped

    return cleaned


# ---------------------------------------------------------------------------
# Helper: score confidence
# ---------------------------------------------------------------------------


def _score_confidence(source: str = "user_stated") -> float:
    """Compute confidence score for a field source."""
    return _SOURCE_WEIGHTS.get(source, 0.50)


# ---------------------------------------------------------------------------
# Helper: generate tool call ID
# ---------------------------------------------------------------------------


def _make_call_id() -> str:
    """Generate a tool call ID: call_ + 8 hex chars."""
    return f"call_{uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Helper: build a single tool interaction dict
# ---------------------------------------------------------------------------


def _make_interaction(
    tool_name: str,
    arguments: dict,
    response_content: dict,
) -> dict:
    """Build an OpenAI-format tool call + response pair."""
    call_id = _make_call_id()
    return {
        "tool_call": {
            "id": call_id,
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": json.dumps(arguments, separators=(",", ":")),
            },
        },
        "tool_response": {
            "role": "tool",
            "tool_call_id": call_id,
            "content": json.dumps(response_content, separators=(",", ":")),
        },
    }


# ---------------------------------------------------------------------------
# Tool-specific injectors
# ---------------------------------------------------------------------------


def _inject_save_fields(
    turn: TurnSkeleton,
    form_state: dict,
) -> Tuple[List[dict], dict]:
    """Generate save_field interactions for each field in turn.user_fields.

    Skips fields that already exist in form_state with the same value.
    Returns (interactions, updated_form_state).
    """
    interactions: List[dict] = []
    new_state = dict(form_state)
    saved_field_names: List[str] = []

    for raw_name, raw_value in turn.user_fields.items():
        # Skip non-data fields (e.g. "confirmation", "bind_confirmation")
        if raw_name in ("confirmation", "bind_confirmation", "selected_quote",
                        "insurance_needs"):
            continue

        canonical = _resolve_alias(raw_name)
        normalized = _normalize_value(canonical, str(raw_value))
        source = "user_stated"
        confidence = _score_confidence(source)

        # Skip if already exists with same value
        existing = new_state.get(canonical)
        if existing and existing.get("value") == normalized:
            continue

        # Build tool call arguments (as the model would produce them)
        args = {
            "field_name": canonical,
            "value": normalized,
            "source": source,
            "status": "pending",
        }

        # Build response
        resp = {
            "status": "saved",
            "field_name": canonical,
            "value": normalized,
            "confidence": confidence,
        }

        interactions.append(_make_interaction("save_field", args, resp))
        saved_field_names.append(canonical)

        # Update form_state
        new_state[canonical] = {
            "value": normalized,
            "confidence": confidence,
            "source": source,
            "status": "confirmed",
        }

    return interactions, new_state, saved_field_names


def _inject_validate_fields(
    saved_field_names: List[str],
) -> dict:
    """Generate a validate_fields interaction for the given fields."""
    args = {"fields": sorted(saved_field_names)}
    resp = {
        "status": "valid",
        "fields_checked": sorted(saved_field_names),
        "issues": [],
    }
    return _make_interaction("validate_fields", args, resp)


def _inject_classify_lobs(
    scenario: ConversationScenario,
) -> dict:
    """Generate a classify_lobs interaction using scenario data."""
    description = scenario.business.get("operations_description", "")
    if not description:
        description = scenario.business.get("nature_of_business", "")

    args = {"description": description}
    resp = {
        "lobs": list(scenario.lobs),
        "reasoning": f"Based on operations: {description}",
    }
    return _make_interaction("classify_lobs", args, resp)


def _inject_assign_forms(
    scenario: ConversationScenario,
) -> dict:
    """Generate an assign_forms interaction using scenario data."""
    args = {"lobs": list(scenario.lobs)}

    # Build lob_form_mapping from scenario
    lob_form_mapping: Dict[str, List[str]] = {}
    for lob in scenario.lobs:
        lob_form_mapping[lob] = LOB_FORMS.get(lob, [])

    resp = {
        "assigned_forms": list(scenario.assigned_forms),
        "lob_form_mapping": lob_form_mapping,
    }
    return _make_interaction("assign_forms", args, resp)


def _inject_analyze_gaps(
    form_state: dict,
    scenario: ConversationScenario,
) -> dict:
    """Generate an analyze_gaps interaction."""
    args = {}  # No args in training data — state is injected

    # Calculate completeness
    all_expected = set(_CRITICAL_FIELDS + _IMPORTANT_FIELDS)
    filled = set(form_state.keys()) & all_expected
    total_expected = len(all_expected) if all_expected else 1
    completeness = round(len(filled) / total_expected * 100, 1)

    # Missing critical
    missing_critical = [f for f in _CRITICAL_FIELDS if f not in form_state]
    missing_important = [f for f in _IMPORTANT_FIELDS if f not in form_state]

    resp = {
        "completeness_pct": completeness,
        "missing_critical": missing_critical,
        "missing_important": missing_important,
    }
    return _make_interaction("analyze_gaps", args, resp)


def _inject_fill_forms(
    scenario: ConversationScenario,
) -> dict:
    """Generate a fill_forms interaction."""
    args = {}  # No args in training data — state is injected

    resp = {
        "status": "success",
        "forms_filled": list(scenario.assigned_forms),
        "output_directory": "/output/filled_forms",
    }
    return _make_interaction("fill_forms", args, resp)


def _inject_select_quote(
    turn: TurnSkeleton,
    scenario: ConversationScenario,
) -> dict:
    """Generate a select_quote interaction."""
    quote_id = turn.user_fields.get("selected_quote", "quote_1")
    payment_plan = scenario.policy.get("payment_plan", "annual")

    args = {
        "quote_id": quote_id,
        "payment_plan": payment_plan,
    }

    # Deterministic carrier and premium from scenario
    carrier = "Progressive Commercial"
    if scenario.prior_insurance:
        carrier = scenario.prior_insurance[0].get("carrier_name", carrier)
    total_premium = 15000  # Reasonable default
    if scenario.prior_insurance:
        try:
            total_premium = int(scenario.prior_insurance[0].get("premium", "15000"))
        except (ValueError, TypeError):
            pass

    resp = {
        "status": "selected",
        "quote_id": quote_id,
        "carrier": carrier,
        "total_premium": total_premium,
    }
    return _make_interaction("select_quote", args, resp)


def _inject_submit_bind_request(
    scenario: ConversationScenario,
) -> dict:
    """Generate a submit_bind_request interaction."""
    args = {}  # No args in training data — state is injected

    # Deterministic timestamp and ID from scenario_id
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bind_id = f"BR-{scenario.scenario_id.replace('scenario_', '')}"

    resp = {
        "status": "submitted",
        "bind_request_id": bind_id,
        "timestamp": timestamp,
    }
    return _make_interaction("submit_bind_request", args, resp)


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------


def inject_tool_calls(
    turn: TurnSkeleton,
    form_state: dict,
    scenario: ConversationScenario,
    seed: int = 42,
) -> Tuple[List[dict], dict]:
    """Generate tool calls and responses for a turn skeleton.

    Args:
        turn: The TurnSkeleton describing what should happen this turn.
        form_state: Current accumulated form state (field_name -> {value, confidence, ...}).
        scenario: The ConversationScenario providing ground truth data.
        seed: Random seed for reproducibility (unused currently, reserved for future).

    Returns:
        (tool_interactions, updated_form_state)
        where tool_interactions is a list of dicts with "tool_call" and "tool_response" keys.
    """
    if not turn.tools_to_call:
        return [], dict(form_state)

    interactions: List[dict] = []
    new_state = dict(form_state)
    saved_field_names: List[str] = []

    # Determine which tool types are requested this turn
    tool_set = set(turn.tools_to_call)
    has_save = "save_field" in tool_set
    has_validate = "validate_fields" in tool_set
    has_classify = "classify_lobs" in tool_set
    has_assign = "assign_forms" in tool_set
    has_gaps = "analyze_gaps" in tool_set
    has_fill = "fill_forms" in tool_set
    has_select = "select_quote" in tool_set
    has_bind = "submit_bind_request" in tool_set

    # 1. save_field — one per user field
    if has_save and turn.user_fields:
        save_interactions, new_state, saved_field_names = _inject_save_fields(
            turn, new_state,
        )
        interactions.extend(save_interactions)

    # 2. validate_fields — after saves
    if has_validate and saved_field_names:
        interactions.append(_inject_validate_fields(saved_field_names))

    # 3. classify_lobs
    if has_classify:
        interactions.append(_inject_classify_lobs(scenario))

    # 4. assign_forms — after classify_lobs
    if has_assign:
        interactions.append(_inject_assign_forms(scenario))

    # 5. analyze_gaps
    if has_gaps:
        interactions.append(_inject_analyze_gaps(new_state, scenario))

    # 6. fill_forms
    if has_fill:
        interactions.append(_inject_fill_forms(scenario))

    # 7. select_quote
    if has_select:
        interactions.append(_inject_select_quote(turn, scenario))

    # 8. submit_bind_request
    if has_bind:
        interactions.append(_inject_submit_bind_request(scenario))

    return interactions, new_state
