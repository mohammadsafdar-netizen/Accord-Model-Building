"""
Conversation skeleton builder for agent fine-tuning dataset.

Given a ConversationScenario, produces a list[TurnSkeleton] that maps out
every turn of the synthetic conversation: which phase it belongs to, what
fields the user provides, which tools the assistant should call, the primary
action, and what the assistant should ask next.

Three delivery styles yield different skeleton shapes:
  - conversational  (15-25 turns): fields trickled in 1-2 at a time
  - bulk_email      (8-12 turns):  big initial dump, then gap-fill
  - mixed           (12-18 turns): partial conversational then bulk dump

Usage:
    from finetune.agent.skeleton_builder import build_skeleton
    skeleton = build_skeleton(scenario)  # list[TurnSkeleton]
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from finetune.agent.scenario_generator import ConversationScenario

# ---------------------------------------------------------------------------
# Phase constants (hardcoded from production agent/tools.py and agent/state.py)
# ---------------------------------------------------------------------------

PHASE_TOOLS: Dict[str, List[str]] = {
    "greeting":        [],
    "applicant_info":  ["save_field", "validate_fields"],
    "policy_details":  ["save_field", "validate_fields", "classify_lobs", "assign_forms"],
    "business_info":   ["save_field", "validate_fields"],
    "form_specific":   ["save_field", "validate_fields", "analyze_gaps", "process_document"],
    "review":          ["save_field", "analyze_gaps", "fill_forms"],
    "complete":        ["analyze_gaps", "fill_forms"],
    "quoting":         [],
    "quote_selection": ["select_quote"],
    "bind_request":    ["submit_bind_request"],
    "policy_delivery": [],
}

PHASE_ORDER: List[str] = [
    "greeting", "applicant_info", "policy_details", "business_info",
    "form_specific", "review", "complete", "quoting", "quote_selection",
    "bind_request", "policy_delivery",
]


# ---------------------------------------------------------------------------
# TurnSkeleton dataclass
# ---------------------------------------------------------------------------

@dataclass
class TurnSkeleton:
    phase: str                     # Current phase (e.g., "greeting", "applicant_info")
    user_fields: dict              # {field_name: value} provided by user in this turn
    tools_to_call: list            # Tool names to call (e.g., ["save_field", "validate_fields"])
    action: str                    # Primary action description
    assistant_should_ask: str      # What the assistant should ask next


# Type alias
ConversationSkeleton = List[TurnSkeleton]


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

def _flatten_business_fields(business: dict) -> Dict[str, str]:
    """Extract flat field dict from business entity."""
    fields: Dict[str, str] = {}
    fields["business_name"] = business.get("business_name", "")
    addr = business.get("mailing_address", {})
    fields["mailing_street"] = addr.get("line_one", "")
    fields["mailing_city"] = addr.get("city", "")
    fields["mailing_state"] = addr.get("state", "")
    fields["mailing_zip"] = addr.get("zip_code", "")
    fields["entity_type"] = business.get("entity_type", "")
    fields["tax_id"] = business.get("tax_id", "")
    fields["nature_of_business"] = business.get("nature_of_business", "")
    fields["operations_description"] = business.get("operations_description", "")
    fields["employee_count"] = business.get("employee_count", "")
    fields["annual_revenue"] = business.get("annual_revenue", "")
    fields["years_in_business"] = business.get("years_in_business", "")
    fields["annual_payroll"] = business.get("annual_payroll", "")
    # Contact info
    contacts = business.get("contacts", [])
    if contacts:
        c = contacts[0]
        fields["contact_name"] = c.get("full_name", "")
        fields["contact_phone"] = c.get("phone", "")
        fields["contact_email"] = c.get("email", "")
    return fields


def _flatten_policy_fields(policy: dict) -> Dict[str, str]:
    """Extract flat field dict from policy entity."""
    return {
        "effective_date": policy.get("effective_date", ""),
        "expiration_date": policy.get("expiration_date", ""),
    }


def _flatten_vehicle_fields(vehicles: list) -> Dict[str, str]:
    """Extract indexed vehicle fields: vehicle_1_year, vehicle_1_make, etc."""
    fields: Dict[str, str] = {}
    for i, v in enumerate(vehicles, start=1):
        prefix = f"vehicle_{i}_"
        fields[f"{prefix}year"] = v.get("year", "")
        fields[f"{prefix}make"] = v.get("make", "")
        fields[f"{prefix}model"] = v.get("model", "")
        fields[f"{prefix}vin"] = v.get("vin", "")
        if v.get("gvw"):
            fields[f"{prefix}gvw"] = v.get("gvw", "")
    return fields


def _flatten_driver_fields(drivers: list) -> Dict[str, str]:
    """Extract indexed driver fields: driver_1_name, driver_1_dob, etc."""
    fields: Dict[str, str] = {}
    for i, d in enumerate(drivers, start=1):
        prefix = f"driver_{i}_"
        fields[f"{prefix}name"] = d.get("full_name", "")
        fields[f"{prefix}dob"] = d.get("dob", "")
        fields[f"{prefix}license_number"] = d.get("license_number", "")
        fields[f"{prefix}license_state"] = d.get("license_state", "")
    return fields


def _flatten_coverage_fields(coverages: list) -> Dict[str, str]:
    """Extract indexed coverage fields."""
    fields: Dict[str, str] = {}
    for i, c in enumerate(coverages, start=1):
        prefix = f"coverage_{i}_"
        fields[f"{prefix}type"] = c.get("coverage_type", "")
        fields[f"{prefix}limit"] = c.get("limit", "")
        fields[f"{prefix}deductible"] = c.get("deductible", "")
        fields[f"{prefix}lob"] = c.get("lob", "")
    return fields


def _flatten_loss_history_fields(losses: list) -> Dict[str, str]:
    """Extract indexed loss history fields."""
    fields: Dict[str, str] = {}
    for i, lo in enumerate(losses, start=1):
        prefix = f"loss_{i}_"
        fields[f"{prefix}date"] = lo.get("date", "")
        fields[f"{prefix}amount"] = lo.get("amount", "")
        fields[f"{prefix}description"] = lo.get("description", "")
    return fields


def _flatten_prior_insurance_fields(priors: list) -> Dict[str, str]:
    """Extract indexed prior insurance fields."""
    fields: Dict[str, str] = {}
    for i, p in enumerate(priors, start=1):
        prefix = f"prior_{i}_"
        fields[f"{prefix}carrier"] = p.get("carrier_name", "")
        fields[f"{prefix}premium"] = p.get("premium", "")
    return fields


def _flatten_location_fields(locations: list) -> Dict[str, str]:
    """Extract indexed location fields."""
    fields: Dict[str, str] = {}
    for i, loc in enumerate(locations, start=1):
        prefix = f"location_{i}_"
        fields[f"{prefix}street"] = loc.get("street", "")
        fields[f"{prefix}city"] = loc.get("city", "")
        fields[f"{prefix}state"] = loc.get("state", "")
        fields[f"{prefix}zip"] = loc.get("zip", "")
        if loc.get("building_area"):
            fields[f"{prefix}building_area"] = loc.get("building_area", "")
        if loc.get("construction_type"):
            fields[f"{prefix}construction_type"] = loc.get("construction_type", "")
        if loc.get("year_built"):
            fields[f"{prefix}year_built"] = loc.get("year_built", "")
    return fields


def _flatten_all_fields(scenario: ConversationScenario) -> Dict[str, str]:
    """Flatten every entity in the scenario into a single field dict."""
    fields: Dict[str, str] = {}
    fields.update(_flatten_business_fields(scenario.business))
    fields.update(_flatten_policy_fields(scenario.policy))
    fields.update(_flatten_vehicle_fields(scenario.vehicles))
    fields.update(_flatten_driver_fields(scenario.drivers))
    fields.update(_flatten_coverage_fields(scenario.coverages))
    fields.update(_flatten_loss_history_fields(scenario.loss_history))
    fields.update(_flatten_prior_insurance_fields(scenario.prior_insurance))
    fields.update(_flatten_location_fields(scenario.locations))
    return fields


# ---------------------------------------------------------------------------
# Chunk helpers — split a dict into multiple dicts of N items each
# ---------------------------------------------------------------------------

def _chunk_dict(d: dict, chunk_size: int, rng: random.Random) -> List[dict]:
    """Split dict into chunks of approximately chunk_size entries."""
    items = list(d.items())
    rng.shuffle(items)
    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(dict(items[i:i + chunk_size]))
    return chunks


def _split_dict_ordered(d: dict, sizes: List[int]) -> List[dict]:
    """Split dict into sub-dicts of the specified sizes, in order."""
    items = list(d.items())
    result = []
    offset = 0
    for s in sizes:
        result.append(dict(items[offset:offset + s]))
        offset += s
    # Remaining
    if offset < len(items):
        if result:
            result[-1].update(dict(items[offset:]))
        else:
            result.append(dict(items[offset:]))
    return result


# ---------------------------------------------------------------------------
# Document upload turn helpers
# ---------------------------------------------------------------------------

_DOC_FOLLOW_UP: Dict[str, str] = {
    "loss_run": "Ask about prior insurance details or additional claims",
    "drivers_license": "Ask about additional driver details or next driver",
    "vehicle_registration": "Ask about additional vehicle details",
    "business_certificate": "Ask about business operations details",
    "prior_declaration": "Ask about prior policy coverage details",
    "acord_form": "Ask about form-specific details",
}


def _build_document_upload_turns(scenario: ConversationScenario) -> List[TurnSkeleton]:
    """Build TurnSkeleton entries for each document upload in the scenario."""
    turns: List[TurnSkeleton] = []
    for upload in getattr(scenario, "document_uploads", []):
        doc_type = upload.get("document_type", "other")
        follow_up = _DOC_FOLLOW_UP.get(doc_type, "Ask about remaining details")
        turns.append(TurnSkeleton(
            phase="form_specific",
            user_fields={"_document_upload": upload},
            tools_to_call=["process_document", "save_field"],
            action="process_document",
            assistant_should_ask=follow_up,
        ))
    return turns


# ---------------------------------------------------------------------------
# Skeleton builders per delivery style
# ---------------------------------------------------------------------------

def _build_conversational(scenario: ConversationScenario, rng: random.Random) -> List[TurnSkeleton]:
    """Build a conversational-style skeleton (15-25 turns)."""
    turns: List[TurnSkeleton] = []
    biz = scenario.business
    addr = biz.get("mailing_address", {})
    contacts = biz.get("contacts", [])
    contact = contacts[0] if contacts else {}

    # --- GREETING ---
    turns.append(TurnSkeleton(
        phase="greeting",
        user_fields={},
        tools_to_call=[],
        action="greet",
        assistant_should_ask="Ask how the assistant can help with insurance needs",
    ))

    # --- APPLICANT_INFO ---
    # Turn: business name
    turns.append(TurnSkeleton(
        phase="applicant_info",
        user_fields={"business_name": biz.get("business_name", "")},
        tools_to_call=["save_field"],
        action="save_fields",
        assistant_should_ask="Ask for the business mailing address",
    ))

    # Turn: address (4 fields)
    turns.append(TurnSkeleton(
        phase="applicant_info",
        user_fields={
            "mailing_street": addr.get("line_one", ""),
            "mailing_city": addr.get("city", ""),
            "mailing_state": addr.get("state", ""),
            "mailing_zip": addr.get("zip_code", ""),
        },
        tools_to_call=["save_field", "validate_fields"],
        action="save_fields",
        assistant_should_ask="Ask for entity type and federal tax ID",
    ))

    # Turn: entity type + FEIN
    turns.append(TurnSkeleton(
        phase="applicant_info",
        user_fields={
            "entity_type": biz.get("entity_type", ""),
            "tax_id": biz.get("tax_id", ""),
        },
        tools_to_call=["save_field"],
        action="save_fields",
        assistant_should_ask="Ask for primary contact information",
    ))

    # Turn: contact info
    contact_fields: Dict[str, str] = {}
    if contact:
        contact_fields["contact_name"] = contact.get("full_name", "")
        contact_fields["contact_phone"] = contact.get("phone", "")
        contact_fields["contact_email"] = contact.get("email", "")
    turns.append(TurnSkeleton(
        phase="applicant_info",
        user_fields=contact_fields,
        tools_to_call=["save_field", "validate_fields"],
        action="save_fields",
        assistant_should_ask="Ask about insurance needs and lines of business",
    ))

    # --- POLICY_DETAILS ---
    # Turn: describe insurance needs -> classify LOBs
    lob_description = ", ".join(scenario.lobs)
    turns.append(TurnSkeleton(
        phase="policy_details",
        user_fields={"insurance_needs": lob_description},
        tools_to_call=["save_field", "classify_lobs", "assign_forms"],
        action="classify_lobs",
        assistant_should_ask="Ask for desired effective date",
    ))

    # Turn: effective date
    turns.append(TurnSkeleton(
        phase="policy_details",
        user_fields={
            "effective_date": scenario.policy.get("effective_date", ""),
            "expiration_date": scenario.policy.get("expiration_date", ""),
        },
        tools_to_call=["save_field"],
        action="save_fields",
        assistant_should_ask="Ask about the nature of the business and operations",
    ))

    # --- BUSINESS_INFO ---
    # Turn: operations description
    turns.append(TurnSkeleton(
        phase="business_info",
        user_fields={
            "operations_description": biz.get("operations_description", ""),
            "nature_of_business": biz.get("nature_of_business", ""),
        },
        tools_to_call=["save_field"],
        action="save_fields",
        assistant_should_ask="Ask about employee count and annual revenue",
    ))

    # Turn: employee count + revenue
    turns.append(TurnSkeleton(
        phase="business_info",
        user_fields={
            "employee_count": biz.get("employee_count", ""),
            "annual_revenue": biz.get("annual_revenue", ""),
        },
        tools_to_call=["save_field", "validate_fields"],
        action="save_fields",
        assistant_should_ask="Ask about years in business and annual payroll",
    ))

    # Turn: years in business + payroll
    turns.append(TurnSkeleton(
        phase="business_info",
        user_fields={
            "years_in_business": biz.get("years_in_business", ""),
            "annual_payroll": biz.get("annual_payroll", ""),
        },
        tools_to_call=["save_field"],
        action="save_fields",
        assistant_should_ask="Ask about form-specific details",
    ))

    # --- FORM_SPECIFIC ---
    # Vehicle details (if commercial_auto)
    if scenario.vehicles:
        vehicle_fields = _flatten_vehicle_fields(scenario.vehicles)
        # Split vehicles into turns of 2-4 fields each
        veh_items = list(vehicle_fields.items())
        # Group by vehicle: each vehicle has ~4-5 fields
        fields_per_vehicle = 5 if any(v.get("gvw") for v in scenario.vehicles) else 4
        for vi, vehicle in enumerate(scenario.vehicles):
            prefix = f"vehicle_{vi + 1}_"
            vf = {k: v for k, v in vehicle_fields.items() if k.startswith(prefix)}
            # Split into 1-2 turns per vehicle
            if len(vf) > 3 and rng.random() < 0.6:
                items = list(vf.items())
                mid = len(items) // 2
                turns.append(TurnSkeleton(
                    phase="form_specific",
                    user_fields=dict(items[:mid]),
                    tools_to_call=["save_field"],
                    action="save_fields",
                    assistant_should_ask=f"Ask for remaining vehicle {vi + 1} details",
                ))
                turns.append(TurnSkeleton(
                    phase="form_specific",
                    user_fields=dict(items[mid:]),
                    tools_to_call=["save_field", "validate_fields"],
                    action="save_fields",
                    assistant_should_ask=f"Ask about {'next vehicle' if vi + 1 < len(scenario.vehicles) else 'driver details'}",
                ))
            else:
                turns.append(TurnSkeleton(
                    phase="form_specific",
                    user_fields=vf,
                    tools_to_call=["save_field", "validate_fields"],
                    action="save_fields",
                    assistant_should_ask=f"Ask about {'next vehicle' if vi + 1 < len(scenario.vehicles) else 'driver details'}",
                ))

    # Driver details (if commercial_auto)
    if scenario.drivers:
        driver_fields = _flatten_driver_fields(scenario.drivers)
        for di, driver in enumerate(scenario.drivers):
            prefix = f"driver_{di + 1}_"
            df = {k: v for k, v in driver_fields.items() if k.startswith(prefix)}
            if len(df) > 3 and rng.random() < 0.5:
                items = list(df.items())
                mid = len(items) // 2
                turns.append(TurnSkeleton(
                    phase="form_specific",
                    user_fields=dict(items[:mid]),
                    tools_to_call=["save_field"],
                    action="save_fields",
                    assistant_should_ask=f"Ask for remaining driver {di + 1} details",
                ))
                turns.append(TurnSkeleton(
                    phase="form_specific",
                    user_fields=dict(items[mid:]),
                    tools_to_call=["save_field", "validate_fields"],
                    action="save_fields",
                    assistant_should_ask=f"Ask about {'next driver' if di + 1 < len(scenario.drivers) else 'coverage details'}",
                ))
            else:
                turns.append(TurnSkeleton(
                    phase="form_specific",
                    user_fields=df,
                    tools_to_call=["save_field", "validate_fields"],
                    action="save_fields",
                    assistant_should_ask=f"Ask about {'next driver' if di + 1 < len(scenario.drivers) else 'coverage details'}",
                ))

    # Coverage details
    if scenario.coverages:
        cov_fields = _flatten_coverage_fields(scenario.coverages)
        # Provide coverages in 1-2 turns
        cov_items = list(cov_fields.items())
        if len(cov_items) > 6:
            mid = len(cov_items) // 2
            turns.append(TurnSkeleton(
                phase="form_specific",
                user_fields=dict(cov_items[:mid]),
                tools_to_call=["save_field"],
                action="save_fields",
                assistant_should_ask="Ask for remaining coverage details",
            ))
            turns.append(TurnSkeleton(
                phase="form_specific",
                user_fields=dict(cov_items[mid:]),
                tools_to_call=["save_field", "validate_fields"],
                action="save_fields",
                assistant_should_ask="Ask about loss history",
            ))
        else:
            turns.append(TurnSkeleton(
                phase="form_specific",
                user_fields=cov_fields,
                tools_to_call=["save_field", "validate_fields"],
                action="save_fields",
                assistant_should_ask="Ask about loss history",
            ))

    # Loss history (optional)
    if scenario.loss_history:
        loss_fields = _flatten_loss_history_fields(scenario.loss_history)
        turns.append(TurnSkeleton(
            phase="form_specific",
            user_fields=loss_fields,
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="Ask about prior insurance",
        ))

    # Prior insurance (optional)
    if scenario.prior_insurance:
        prior_fields = _flatten_prior_insurance_fields(scenario.prior_insurance)
        turns.append(TurnSkeleton(
            phase="form_specific",
            user_fields=prior_fields,
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="Ask about locations",
        ))

    # Locations (optional)
    if scenario.locations:
        loc_fields = _flatten_location_fields(scenario.locations)
        turns.append(TurnSkeleton(
            phase="form_specific",
            user_fields=loc_fields,
            tools_to_call=["save_field", "validate_fields"],
            action="save_fields",
            assistant_should_ask="Analyze gaps in the application",
        ))

    # Document uploads (before gap analysis)
    doc_turns = _build_document_upload_turns(scenario)
    turns.extend(doc_turns)

    # Analyze gaps
    turns.append(TurnSkeleton(
        phase="form_specific",
        user_fields={},
        tools_to_call=["analyze_gaps"],
        action="analyze_gaps",
        assistant_should_ask="Present gap analysis and ask user to confirm application for review",
    ))

    # --- REVIEW ---
    turns.append(TurnSkeleton(
        phase="review",
        user_fields={},
        tools_to_call=["analyze_gaps"],
        action="present_review",
        assistant_should_ask="Present application summary and ask user to confirm",
    ))

    # User confirms -> fill forms
    turns.append(TurnSkeleton(
        phase="review",
        user_fields={"confirmation": "yes"},
        tools_to_call=["fill_forms"],
        action="fill_forms",
        assistant_should_ask="Inform user forms are being filled and submitted for quoting",
    ))

    # --- COMPLETE ---
    turns.append(TurnSkeleton(
        phase="complete",
        user_fields={},
        tools_to_call=["fill_forms"],
        action="complete_forms",
        assistant_should_ask="Inform user that forms are complete and moving to quoting",
    ))

    # --- QUOTING ---
    turns.append(TurnSkeleton(
        phase="quoting",
        user_fields={},
        tools_to_call=[],
        action="present_quotes",
        assistant_should_ask="Present available quotes and ask user to select one",
    ))

    # --- QUOTE_SELECTION ---
    turns.append(TurnSkeleton(
        phase="quote_selection",
        user_fields={"selected_quote": "quote_1"},
        tools_to_call=["select_quote"],
        action="select_quote",
        assistant_should_ask="Confirm quote selection and ask if user wants to proceed with binding",
    ))

    # --- BIND_REQUEST ---
    turns.append(TurnSkeleton(
        phase="bind_request",
        user_fields={"bind_confirmation": "yes"},
        tools_to_call=["submit_bind_request"],
        action="submit_bind_request",
        assistant_should_ask="Confirm binding request submitted and provide next steps",
    ))

    # --- POLICY_DELIVERY ---
    turns.append(TurnSkeleton(
        phase="policy_delivery",
        user_fields={},
        tools_to_call=[],
        action="deliver_policy",
        assistant_should_ask="Provide policy documents and closing remarks",
    ))

    return turns


def _build_bulk_email(scenario: ConversationScenario, rng: random.Random) -> List[TurnSkeleton]:
    """Build a bulk-email-style skeleton (8-12 turns)."""
    turns: List[TurnSkeleton] = []

    # --- GREETING ---
    turns.append(TurnSkeleton(
        phase="greeting",
        user_fields={},
        tools_to_call=[],
        action="greet",
        assistant_should_ask="Ask how the assistant can help with insurance needs",
    ))

    # --- User dumps ALL info at once ---
    # Flatten everything into one big field dict
    all_fields = _flatten_all_fields(scenario)

    # The bulk dump goes into applicant_info phase (first data phase)
    # Since this is a bulk dump, we use save_field (which is in applicant_info)
    # extract_entities runs automatically via bulk_preprocess_node
    turns.append(TurnSkeleton(
        phase="applicant_info",
        user_fields=all_fields,
        tools_to_call=["save_field", "validate_fields"],
        action="bulk_extract",
        assistant_should_ask="Acknowledge receipt and ask about insurance needs",
    ))

    # --- POLICY_DETAILS: classify LOBs ---
    turns.append(TurnSkeleton(
        phase="policy_details",
        user_fields={"insurance_needs": ", ".join(scenario.lobs)},
        tools_to_call=["classify_lobs", "assign_forms"],
        action="classify_lobs",
        assistant_should_ask="Confirm LOBs and forms, ask about any missing information",
    ))

    # --- FORM_SPECIFIC: analyze gaps ---
    turns.append(TurnSkeleton(
        phase="form_specific",
        user_fields={},
        tools_to_call=["analyze_gaps"],
        action="analyze_gaps",
        assistant_should_ask="Present missing fields and ask user to fill gaps",
    ))

    # --- Gap-fill turns (1-3 turns with a few fields each) ---
    # Generate some "gap" fields that might be missing
    gap_fields_pool: Dict[str, str] = {}
    if scenario.coverages:
        gap_fields_pool.update(_flatten_coverage_fields(scenario.coverages))
    if scenario.loss_history:
        gap_fields_pool.update(_flatten_loss_history_fields(scenario.loss_history))
    if scenario.prior_insurance:
        gap_fields_pool.update(_flatten_prior_insurance_fields(scenario.prior_insurance))

    if gap_fields_pool:
        gap_chunks = _chunk_dict(gap_fields_pool, rng.randint(2, 4), rng)
        for i, chunk in enumerate(gap_chunks[:3]):  # Max 3 gap-fill turns
            turns.append(TurnSkeleton(
                phase="form_specific",
                user_fields=chunk,
                tools_to_call=["save_field", "validate_fields"],
                action="save_fields",
                assistant_should_ask="Ask about remaining gaps or proceed to review" if i < len(gap_chunks) - 1 else "Proceed to review",
            ))

    # Document uploads (after gap fill, before review)
    doc_turns = _build_document_upload_turns(scenario)
    turns.extend(doc_turns)

    # --- REVIEW ---
    turns.append(TurnSkeleton(
        phase="review",
        user_fields={"confirmation": "yes"},
        tools_to_call=["fill_forms"],
        action="fill_forms",
        assistant_should_ask="Confirm forms filled and proceed to quoting",
    ))

    # --- QUOTING ---
    turns.append(TurnSkeleton(
        phase="quoting",
        user_fields={},
        tools_to_call=[],
        action="present_quotes",
        assistant_should_ask="Present quotes and ask user to select one",
    ))

    # --- QUOTE_SELECTION ---
    turns.append(TurnSkeleton(
        phase="quote_selection",
        user_fields={"selected_quote": "quote_1"},
        tools_to_call=["select_quote"],
        action="select_quote",
        assistant_should_ask="Confirm selection and ask about binding",
    ))

    # --- BIND_REQUEST ---
    turns.append(TurnSkeleton(
        phase="bind_request",
        user_fields={"bind_confirmation": "yes"},
        tools_to_call=["submit_bind_request"],
        action="submit_bind_request",
        assistant_should_ask="Confirm bind request submitted",
    ))

    # --- POLICY_DELIVERY ---
    turns.append(TurnSkeleton(
        phase="policy_delivery",
        user_fields={},
        tools_to_call=[],
        action="deliver_policy",
        assistant_should_ask="Provide policy documents and closing remarks",
    ))

    return turns


def _build_mixed(scenario: ConversationScenario, rng: random.Random) -> List[TurnSkeleton]:
    """Build a mixed-style skeleton (12-18 turns)."""
    turns: List[TurnSkeleton] = []
    biz = scenario.business
    addr = biz.get("mailing_address", {})
    contacts = biz.get("contacts", [])
    contact = contacts[0] if contacts else {}

    # --- GREETING ---
    turns.append(TurnSkeleton(
        phase="greeting",
        user_fields={},
        tools_to_call=[],
        action="greet",
        assistant_should_ask="Ask how the assistant can help with insurance needs",
    ))

    # --- APPLICANT_INFO: partial info conversationally ---
    # Turn: business name + entity type
    turns.append(TurnSkeleton(
        phase="applicant_info",
        user_fields={
            "business_name": biz.get("business_name", ""),
            "entity_type": biz.get("entity_type", ""),
        },
        tools_to_call=["save_field"],
        action="save_fields",
        assistant_should_ask="Ask for business address",
    ))

    # Turn: address
    turns.append(TurnSkeleton(
        phase="applicant_info",
        user_fields={
            "mailing_street": addr.get("line_one", ""),
            "mailing_city": addr.get("city", ""),
            "mailing_state": addr.get("state", ""),
            "mailing_zip": addr.get("zip_code", ""),
        },
        tools_to_call=["save_field", "validate_fields"],
        action="save_fields",
        assistant_should_ask="Ask about insurance needs",
    ))

    # --- POLICY_DETAILS: classify LOBs ---
    turns.append(TurnSkeleton(
        phase="policy_details",
        user_fields={"insurance_needs": ", ".join(scenario.lobs)},
        tools_to_call=["save_field", "classify_lobs", "assign_forms"],
        action="classify_lobs",
        assistant_should_ask="Ask for effective date and remaining details",
    ))

    # Turn: effective date
    turns.append(TurnSkeleton(
        phase="policy_details",
        user_fields={
            "effective_date": scenario.policy.get("effective_date", ""),
        },
        tools_to_call=["save_field"],
        action="save_fields",
        assistant_should_ask="Ask for remaining business and operational details",
    ))

    # --- BUSINESS_INFO: user dumps remaining data in bulk ---
    # Gather remaining business fields + all form-specific data
    bulk_fields: Dict[str, str] = {}
    bulk_fields["tax_id"] = biz.get("tax_id", "")
    bulk_fields["operations_description"] = biz.get("operations_description", "")
    bulk_fields["nature_of_business"] = biz.get("nature_of_business", "")
    bulk_fields["employee_count"] = biz.get("employee_count", "")
    bulk_fields["annual_revenue"] = biz.get("annual_revenue", "")
    bulk_fields["years_in_business"] = biz.get("years_in_business", "")
    bulk_fields["annual_payroll"] = biz.get("annual_payroll", "")
    if contact:
        bulk_fields["contact_name"] = contact.get("full_name", "")
        bulk_fields["contact_phone"] = contact.get("phone", "")

    turns.append(TurnSkeleton(
        phase="business_info",
        user_fields=bulk_fields,
        tools_to_call=["save_field", "validate_fields"],
        action="bulk_extract",
        assistant_should_ask="Acknowledge the bulk data and ask about form-specific details",
    ))

    # --- FORM_SPECIFIC: remaining details ---
    # Vehicle + driver data if applicable
    form_specific_fields: Dict[str, str] = {}
    if scenario.vehicles:
        form_specific_fields.update(_flatten_vehicle_fields(scenario.vehicles))
    if scenario.drivers:
        form_specific_fields.update(_flatten_driver_fields(scenario.drivers))

    if form_specific_fields:
        # Split into 1-2 turns
        items = list(form_specific_fields.items())
        if len(items) > 8:
            mid = len(items) // 2
            turns.append(TurnSkeleton(
                phase="form_specific",
                user_fields=dict(items[:mid]),
                tools_to_call=["save_field"],
                action="save_fields",
                assistant_should_ask="Ask for remaining vehicle/driver details",
            ))
            turns.append(TurnSkeleton(
                phase="form_specific",
                user_fields=dict(items[mid:]),
                tools_to_call=["save_field", "validate_fields"],
                action="save_fields",
                assistant_should_ask="Ask about coverage details",
            ))
        else:
            turns.append(TurnSkeleton(
                phase="form_specific",
                user_fields=form_specific_fields,
                tools_to_call=["save_field", "validate_fields"],
                action="save_fields",
                assistant_should_ask="Ask about coverage details",
            ))

    # Coverage + loss + prior
    remaining_fields: Dict[str, str] = {}
    if scenario.coverages:
        remaining_fields.update(_flatten_coverage_fields(scenario.coverages))
    if scenario.loss_history:
        remaining_fields.update(_flatten_loss_history_fields(scenario.loss_history))
    if scenario.prior_insurance:
        remaining_fields.update(_flatten_prior_insurance_fields(scenario.prior_insurance))
    if scenario.locations:
        remaining_fields.update(_flatten_location_fields(scenario.locations))

    if remaining_fields:
        turns.append(TurnSkeleton(
            phase="form_specific",
            user_fields=remaining_fields,
            tools_to_call=["save_field", "validate_fields"],
            action="save_fields",
            assistant_should_ask="Analyze gaps in the application",
        ))

    # Document uploads (before gap analysis)
    doc_turns = _build_document_upload_turns(scenario)
    turns.extend(doc_turns)

    # Analyze gaps
    turns.append(TurnSkeleton(
        phase="form_specific",
        user_fields={},
        tools_to_call=["analyze_gaps"],
        action="analyze_gaps",
        assistant_should_ask="Present gap analysis and ask if there are corrections",
    ))

    # Gap-fill turn (optional, 1 turn)
    if rng.random() < 0.6:
        correction_field = rng.choice(["employee_count", "annual_revenue", "effective_date"])
        correction_value = "updated_value"
        if correction_field == "employee_count":
            correction_value = str(rng.randint(10, 500))
        elif correction_field == "annual_revenue":
            correction_value = str(rng.randint(500000, 50000000))
        elif correction_field == "effective_date":
            correction_value = scenario.policy.get("effective_date", "01/01/2026")
        turns.append(TurnSkeleton(
            phase="form_specific",
            user_fields={correction_field: correction_value},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="Confirm correction saved and proceed to review",
        ))

    # --- REVIEW ---
    turns.append(TurnSkeleton(
        phase="review",
        user_fields={},
        tools_to_call=["analyze_gaps"],
        action="present_review",
        assistant_should_ask="Present application summary and ask user to confirm",
    ))

    turns.append(TurnSkeleton(
        phase="review",
        user_fields={"confirmation": "yes"},
        tools_to_call=["fill_forms"],
        action="fill_forms",
        assistant_should_ask="Confirm forms are filled and proceed to quoting",
    ))

    # --- QUOTING ---
    turns.append(TurnSkeleton(
        phase="quoting",
        user_fields={},
        tools_to_call=[],
        action="present_quotes",
        assistant_should_ask="Present quotes and ask user to select one",
    ))

    # --- QUOTE_SELECTION ---
    turns.append(TurnSkeleton(
        phase="quote_selection",
        user_fields={"selected_quote": "quote_1"},
        tools_to_call=["select_quote"],
        action="select_quote",
        assistant_should_ask="Confirm selection and ask about binding",
    ))

    # --- BIND_REQUEST ---
    turns.append(TurnSkeleton(
        phase="bind_request",
        user_fields={"bind_confirmation": "yes"},
        tools_to_call=["submit_bind_request"],
        action="submit_bind_request",
        assistant_should_ask="Confirm bind request submitted",
    ))

    # --- POLICY_DELIVERY ---
    turns.append(TurnSkeleton(
        phase="policy_delivery",
        user_fields={},
        tools_to_call=[],
        action="deliver_policy",
        assistant_should_ask="Provide policy documents and closing remarks",
    ))

    return turns


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_skeleton(
    scenario: ConversationScenario,
    seed: int = 42,
) -> List[TurnSkeleton]:
    """
    Build a conversation skeleton from a scenario.

    Args:
        scenario: The ConversationScenario to build turns from.
        seed: Random seed for reproducibility.

    Returns:
        A list of TurnSkeleton instances representing the conversation.
    """
    rng = random.Random(seed)

    if scenario.delivery_style == "conversational":
        return _build_conversational(scenario, rng)
    elif scenario.delivery_style == "bulk_email":
        return _build_bulk_email(scenario, rng)
    elif scenario.delivery_style == "mixed":
        return _build_mixed(scenario, rng)
    else:
        # Default to conversational for unknown styles
        return _build_conversational(scenario, rng)
