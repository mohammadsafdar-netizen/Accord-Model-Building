"""
Conversation message templates for agent fine-tuning dataset.

Provides USER_TEMPLATES and ASSISTANT_TEMPLATES dicts (topic -> list of
template strings with {slot} placeholders), plus render functions that
pick a random variant and fill in the slots.

Usage:
    from finetune.agent.conversation_templates import (
        render_user_template, render_assistant_template, render_bulk_message,
    )
    msg = render_user_template("provide_business_name", seed=42,
                               business_name="Acme Corp")
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# User message templates — topic -> list of template strings
# ---------------------------------------------------------------------------

USER_TEMPLATES: Dict[str, List[str]] = {
    # --- Business identity ---
    "provide_business_name": [
        "My business is {business_name}",
        "The company name is {business_name}",
        "We're {business_name}",
        "It's {business_name}",
        "Business name: {business_name}",
        "Our company is called {business_name}",
        "{business_name} is the business name",
    ],
    "provide_address": [
        "{street}, {city}, {state} {zip}",
        "We're located at {street} in {city}, {state} {zip}",
        "Our address is {street}, {city} {state} {zip}",
        "The mailing address is {street}, {city}, {state} {zip}",
        "{street}\n{city}, {state} {zip}",
        "Address: {street}, {city}, {state} {zip}",
    ],
    "provide_entity_type": [
        "We're an {entity_type}",
        "It's a {entity_type}",
        "{entity_type}",
        "The entity type is {entity_type}",
        "We are organized as an {entity_type}",
    ],
    "provide_tax_id": [
        "Our FEIN is {tax_id}",
        "Tax ID: {tax_id}",
        "{tax_id}",
        "The federal tax ID is {tax_id}",
        "FEIN: {tax_id}",
    ],
    "provide_contact": [
        "You can reach me at {phone}, email is {email}",
        "Phone: {phone}, Email: {email}",
        "Best number is {phone} and email {email}",
        "Call me at {phone} or email {email}",
        "{phone} for phone, {email} for email",
    ],

    # --- Vehicles / Drivers ---
    "provide_vehicle": [
        "We have a {year} {make} {model}, VIN {vin}",
        "{year} {make} {model} - VIN: {vin}",
        "Vehicle: {year} {make} {model}, VIN is {vin}",
        "One of our trucks is a {year} {make} {model} with VIN {vin}",
        "Add a {year} {make} {model}. VIN: {vin}",
    ],
    "provide_driver": [
        "{name}, born {dob}, license {license_number} in {license_state}",
        "Driver: {name}, DOB {dob}, {license_state} license #{license_number}",
        "{name} - DOB: {dob}, DL: {license_number} ({license_state})",
        "Name: {name}, date of birth {dob}, license number {license_number}, state {license_state}",
        "We have a driver named {name}, born on {dob}, with {license_state} license {license_number}",
    ],

    # --- Coverage / Policy ---
    "provide_coverage_needs": [
        "We need {coverage_type} insurance",
        "Looking for {coverage_type} coverage",
        "I need to get {coverage_type}",
        "We're interested in {coverage_type} insurance",
        "Can you quote {coverage_type} for us?",
    ],
    "provide_effective_date": [
        "We need coverage starting {date}",
        "Effective date should be {date}",
        "Start date: {date}",
        "We'd like the policy to start on {date}",
        "Can we have it effective {date}?",
    ],

    # --- Loss history ---
    "provide_loss_history_none": [
        "No claims or losses",
        "Clean record, no losses",
        "We haven't had any claims",
        "No loss history to report",
        "Zero claims in the past 5 years",
    ],
    "provide_loss_history_with_claims": [
        "We had a {description} on {date} for ${amount}",
        "There was a claim - {description}, {date}, about ${amount}",
        "One claim: {description} on {date}, ${amount}",
        "We filed a claim for {description} dated {date}, cost was ${amount}",
        "Loss: {description}, date {date}, amount ${amount}",
    ],

    # --- Financial / Operations ---
    "provide_revenue": [
        "Annual revenue is about ${revenue}",
        "We do about ${revenue} a year",
        "Revenue: ${revenue}",
        "Our annual gross revenue is ${revenue}",
        "Roughly ${revenue} in annual sales",
    ],
    "provide_employees": [
        "We have {count} employees",
        "{count} full-time employees",
        "About {count} people",
        "Employee count is {count}",
        "There are {count} employees total",
    ],
    "provide_years_in_business": [
        "Been in business {years} years",
        "We started {years} years ago",
        "{years} years",
        "We've been operating for {years} years",
        "About {years} years in business",
    ],

    # --- Confirmations / Corrections ---
    "confirm_data": [
        "Yes that's correct",
        "Looks good",
        "Yep that's right",
        "correct",
        "yse thats correct",
        "lok good",
        "go ahead",
        "Yes, everything looks good",
        "That's all right",
        "Confirmed",
    ],
    "request_correction": [
        "Actually the {field} should be {value}",
        "Wait, change {field} to {value}",
        "That's wrong - {field} is {value}",
        "Correction: {field} needs to be {value}",
        "No, {field} is actually {value}",
    ],

    # --- Quoting / Binding ---
    "ask_for_quotes": [
        "Can you get me some quotes?",
        "Let's see what quotes are available",
        "Ready for quotes",
        "Go ahead and run quotes",
        "I'd like to see pricing",
    ],
    "select_quote": [
        "I'll go with {carrier}",
        "Let's go with the {carrier} quote",
        "Select {carrier}",
        "We want the {carrier} option",
        "{carrier} looks best, let's go with that",
    ],
    "confirm_binding": [
        "Yes, go ahead and bind it",
        "Bind the policy",
        "Yes please proceed with binding",
        "Go ahead and bind",
        "Let's bind it",
    ],

    # --- Bulk info (paragraph-style) ---
    "provide_bulk_info": [
        "Here's everything: {info}",
        "Let me give you all the details at once. {info}",
        "Okay so here's what I have: {info}",
        "All the info: {info}",
        "I'll send you everything - {info}",
    ],
}


# ---------------------------------------------------------------------------
# Assistant message templates — topic -> list of template strings
# ---------------------------------------------------------------------------

ASSISTANT_TEMPLATES: Dict[str, List[str]] = {
    "greet_customer": [
        "Welcome! I'm your insurance intake specialist. How can I help you today?",
        "Hello! I'd be happy to help you with your commercial insurance needs. What can I do for you?",
        "Hi there! I can help you with commercial insurance. Let's get started - what type of coverage are you looking for?",
        "Good day! I'm here to assist with your commercial insurance application. What brings you in today?",
    ],
    "acknowledge_and_ask_next": [
        "Great, I've recorded {field} as {value}. {next_question}",
        "Got it - {field}: {value}. {next_question}",
        "Thank you. I have {field} as {value}. {next_question}",
        "Noted, {field} is {value}. {next_question}",
        "Perfect, I've saved {field} as {value}. {next_question}",
    ],
    "confirm_field": [
        "Just to confirm, {field} is {value}, correct?",
        "I have {field} as {value}. Is that right?",
        "Let me verify - {field}: {value}. Does that look correct?",
        "So {field} is {value}? Please confirm.",
    ],
    "present_gap_summary": [
        "Based on what we have so far, I still need: {gaps}. Let's start with {first_gap}.",
        "I'm still missing a few things: {gaps}. Can we start with {first_gap}?",
        "To complete your application, I need: {gaps}. Let's tackle {first_gap} first.",
        "Here's what's still outstanding: {gaps}. Shall we start with {first_gap}?",
    ],
    "present_review": [
        "Here's a summary of everything we've collected: {summary}. Does everything look correct?",
        "Let me review what we have: {summary}. Please confirm this is all accurate.",
        "Before we proceed, here's your application summary: {summary}. Anything need to be changed?",
        "I'd like to review the information: {summary}. Is everything correct?",
    ],
    "present_quotes": [
        "I've received {count} quotes for your review: {quote_summary}. Which would you prefer?",
        "Here are {count} quotes: {quote_summary}. Would you like to go with one of these?",
        "Your quotes are ready! {count} options available: {quote_summary}. Which one interests you?",
        "I have {count} quote options for you: {quote_summary}. Let me know which one you'd like.",
    ],
    "ask_for_quote_selection": [
        "Would you like to go with one of these options? You can also ask me to explain the differences.",
        "Which quote would you prefer? I can provide more details on any of them.",
        "Ready to select a quote? Just let me know which carrier you'd like to go with.",
    ],
    "confirm_bind": [
        "I've submitted your bind request (ID: {bind_id}). Your {carrier} policy is being processed. You'll receive your policy documents soon.",
        "Bind request submitted! Reference: {bind_id}. {carrier} is processing your policy. Documents will be sent shortly.",
        "Done! Bind request {bind_id} has been submitted to {carrier}. Expect your policy documents within a few business days.",
        "Your bind request is confirmed (ID: {bind_id}). {carrier} will issue your policy documents shortly.",
    ],
    "ask_business_name": [
        "Let's start with your business name. What is the full legal name of your company?",
        "First, I'll need your business name. What is the legal name of your company?",
        "What is your company's full legal business name?",
    ],
    "ask_address": [
        "What is your business mailing address?",
        "Can you provide your business mailing address including street, city, state, and ZIP?",
        "I'll need your mailing address. What is the street address, city, state, and ZIP code?",
    ],
    "ask_coverage_needs": [
        "What type of insurance coverage are you looking for?",
        "What lines of insurance do you need? For example, commercial auto, general liability, workers' comp?",
        "What kind of commercial insurance are you interested in?",
    ],
    "ask_vehicle_info": [
        "Could you tell me about your vehicles? I'll need the year, make, model, and VIN for each.",
        "Let's get your vehicle information. What's the year, make, model, and VIN of the first vehicle?",
        "I need details on your vehicles. Can you provide year, make, model, and VIN number?",
    ],
    "ask_driver_info": [
        "Now I'll need information about your drivers. Can you give me the first driver's name, date of birth, and license details?",
        "Let's move on to driver information. Who's the first driver? I'll need their name, DOB, and license number.",
        "I need driver details now. Can you provide the name, date of birth, license number, and license state for each driver?",
    ],
    "transition_to_next_phase": [
        "Excellent, I have all the {current_phase} information. Let me move on to {next_topic}.",
        "Great, {current_phase} is complete. Now let's cover {next_topic}.",
        "That wraps up {current_phase}. Moving on to {next_topic}.",
        "Perfect, {current_phase} details are all set. Next up: {next_topic}.",
    ],
}


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------


def render_user_template(topic: str, seed: Optional[int] = None, **kwargs: Any) -> str:
    """Pick a random user template for *topic* and fill {slot} placeholders.

    Parameters
    ----------
    topic : str
        Key into USER_TEMPLATES.
    seed : int, optional
        If provided, makes template selection deterministic.
    **kwargs
        Values for {slot} placeholders in the chosen template.

    Returns
    -------
    str
        The rendered message.

    Raises
    ------
    KeyError
        If *topic* is not in USER_TEMPLATES.
    """
    templates = USER_TEMPLATES[topic]
    rng = random.Random(seed)
    template = rng.choice(templates)
    return template.format(**kwargs)


def render_assistant_template(topic: str, seed: Optional[int] = None, **kwargs: Any) -> str:
    """Pick a random assistant template for *topic* and fill {slot} placeholders.

    Parameters
    ----------
    topic : str
        Key into ASSISTANT_TEMPLATES.
    seed : int, optional
        If provided, makes template selection deterministic.
    **kwargs
        Values for {slot} placeholders in the chosen template.

    Returns
    -------
    str
        The rendered message.

    Raises
    ------
    KeyError
        If *topic* is not in ASSISTANT_TEMPLATES.
    """
    templates = ASSISTANT_TEMPLATES[topic]
    rng = random.Random(seed)
    template = rng.choice(templates)
    return template.format(**kwargs)


# ---------------------------------------------------------------------------
# Bulk message rendering
# ---------------------------------------------------------------------------

# Maps flat field keys to (topic, template_kwargs_builder) so we know which
# user template to use for each field category.

_FIELD_TO_TOPIC: Dict[str, str] = {
    "business_name": "provide_business_name",
    "entity_type": "provide_entity_type",
    "tax_id": "provide_tax_id",
    "revenue": "provide_revenue",
    "employees": "provide_employees",
    "count": "provide_employees",
    "years": "provide_years_in_business",
    "years_in_business": "provide_years_in_business",
}

# Fields that belong to composite templates (address, contact) — grouped.
_ADDRESS_KEYS = {"street", "city", "state", "zip"}
_CONTACT_KEYS = {"phone", "email"}


def render_bulk_message(fields: Dict[str, Any], seed: Optional[int] = None) -> str:
    """Combine multiple user templates into a natural paragraph.

    Parameters
    ----------
    fields : dict
        Maps field names to their values. Recognised keys:
        business_name, street/city/state/zip, entity_type, tax_id,
        phone/email, revenue, employees/count, years/years_in_business.
    seed : int, optional
        If provided, makes rendering deterministic.

    Returns
    -------
    str
        A multi-sentence paragraph combining the relevant templates.
    """
    rng = random.Random(seed)
    parts: List[str] = []

    # Track which fields we've consumed
    remaining = dict(fields)

    # 1. Business name
    if "business_name" in remaining:
        tpl = rng.choice(USER_TEMPLATES["provide_business_name"])
        parts.append(tpl.format(business_name=remaining.pop("business_name")))

    # 2. Entity type
    if "entity_type" in remaining:
        tpl = rng.choice(USER_TEMPLATES["provide_entity_type"])
        parts.append(tpl.format(entity_type=remaining.pop("entity_type")))

    # 3. Address (if all required keys present)
    if _ADDRESS_KEYS.issubset(remaining.keys()):
        tpl = rng.choice(USER_TEMPLATES["provide_address"])
        parts.append(tpl.format(
            street=remaining.pop("street"),
            city=remaining.pop("city"),
            state=remaining.pop("state"),
            zip=remaining.pop("zip"),
        ))

    # 4. Tax ID
    if "tax_id" in remaining:
        tpl = rng.choice(USER_TEMPLATES["provide_tax_id"])
        parts.append(tpl.format(tax_id=remaining.pop("tax_id")))

    # 5. Contact (if both phone and email present)
    if _CONTACT_KEYS.issubset(remaining.keys()):
        tpl = rng.choice(USER_TEMPLATES["provide_contact"])
        parts.append(tpl.format(
            phone=remaining.pop("phone"),
            email=remaining.pop("email"),
        ))

    # 6. Revenue
    if "revenue" in remaining:
        tpl = rng.choice(USER_TEMPLATES["provide_revenue"])
        parts.append(tpl.format(revenue=remaining.pop("revenue")))

    # 7. Employees
    count_key = "employees" if "employees" in remaining else ("count" if "count" in remaining else None)
    if count_key:
        tpl = rng.choice(USER_TEMPLATES["provide_employees"])
        parts.append(tpl.format(count=remaining.pop(count_key)))

    # 8. Years in business
    years_key = "years_in_business" if "years_in_business" in remaining else ("years" if "years" in remaining else None)
    if years_key:
        tpl = rng.choice(USER_TEMPLATES["provide_years_in_business"])
        parts.append(tpl.format(years=remaining.pop(years_key)))

    # Join with sentence-style separators
    return ". ".join(parts) if parts else ""
