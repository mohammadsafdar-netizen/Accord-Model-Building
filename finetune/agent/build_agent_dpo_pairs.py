"""DPO preference pair generator for agent fine-tuning.

Generates chosen/rejected conversation pairs for Direct Preference
Optimization (DPO) training across 6 anti-hallucination categories:

1. address_hallucination   - chosen saves actual address; rejected invents one
2. quote_fabrication       - chosen presents tool-provided data; rejected invents
3. tool_ordering           - chosen uses correct tool sequence; rejected skips
4. phase_inappropriate_tools - chosen defers tools to correct phase; rejected doesn't
5. multi_field_completeness  - chosen saves ALL fields; rejected misses some
6. confirmation_handling     - chosen accepts confirmation; rejected re-questions

Usage:
    from finetune.agent.build_agent_dpo_pairs import generate_dpo_pairs
    pairs = generate_dpo_pairs(pairs_per_category=20)
"""

from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Optional
from uuid import uuid4

from finetune.agent.scenario_generator import (
    ConversationScenario,
    generate_scenarios,
    CARRIER_NAMES,
    FIRST_NAMES,
    LAST_NAMES,
    STREET_NAMES,
    STATE_CITY_ZIP,
)
from finetune.agent.system_prompt_builder import (
    build_training_system_prompt,
    PHASE_PROMPTS,
)
from finetune.agent.conversation_templates import (
    render_user_template,
    render_assistant_template,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_CATEGORIES: List[str] = [
    "address_hallucination",
    "quote_fabrication",
    "tool_ordering",
    "phase_inappropriate_tools",
    "multi_field_completeness",
    "confirmation_handling",
]

# Bank of fake addresses for rejected hallucination pairs
_FAKE_ADDRESSES: List[Dict[str, str]] = [
    {"street": "742 Evergreen Terrace", "city": "Springfield", "state": "IL", "zip": "62704"},
    {"street": "1600 Pennsylvania Ave NW", "city": "Washington", "state": "DC", "zip": "20500"},
    {"street": "221B Baker Street", "city": "London", "state": "NY", "zip": "10001"},
    {"street": "350 Fifth Avenue", "city": "New York", "state": "NY", "zip": "10118"},
    {"street": "1 Infinite Loop", "city": "Cupertino", "state": "CA", "zip": "95014"},
    {"street": "4 Privet Drive", "city": "Little Whinging", "state": "CT", "zip": "06001"},
    {"street": "9876 Sunset Blvd", "city": "Los Angeles", "state": "CA", "zip": "90028"},
    {"street": "500 Oracle Parkway", "city": "Redwood City", "state": "CA", "zip": "94065"},
    {"street": "1 Microsoft Way", "city": "Redmond", "state": "WA", "zip": "98052"},
    {"street": "2300 Traverwood Dr", "city": "Ann Arbor", "state": "MI", "zip": "48105"},
    {"street": "100 Universal City Plaza", "city": "Universal City", "state": "CA", "zip": "91608"},
    {"street": "12 Grimmauld Place", "city": "Boston", "state": "MA", "zip": "02101"},
    {"street": "7890 Industrial Pkwy", "city": "Phoenix", "state": "AZ", "zip": "85001"},
    {"street": "456 Oak Lane", "city": "Portland", "state": "OR", "zip": "97201"},
    {"street": "321 Pine Street", "city": "San Francisco", "state": "CA", "zip": "94102"},
    {"street": "888 Market Street", "city": "Denver", "state": "CO", "zip": "80201"},
    {"street": "55 Water Street", "city": "Miami", "state": "FL", "zip": "33101"},
    {"street": "1234 Elm Ave", "city": "Austin", "state": "TX", "zip": "78701"},
    {"street": "999 Main Boulevard", "city": "Seattle", "state": "WA", "zip": "98101"},
    {"street": "2468 Commerce Drive", "city": "Atlanta", "state": "GA", "zip": "30301"},
    {"street": "1357 Liberty Road", "city": "Chicago", "state": "IL", "zip": "60601"},
    {"street": "7777 Lucky Lane", "city": "Las Vegas", "state": "NV", "zip": "89101"},
    {"street": "4040 Tech Center", "city": "Dallas", "state": "TX", "zip": "75201"},
    {"street": "1010 Innovation Way", "city": "Nashville", "state": "TN", "zip": "37201"},
]

# Fabricated carrier/premium data for rejected quote fabrication pairs
_FABRICATED_QUOTES: List[Dict[str, Any]] = [
    {"carrier": "Allstate Commercial", "premium": 8500},
    {"carrier": "GEICO Business", "premium": 7200},
    {"carrier": "Farmers Insurance", "premium": 9800},
    {"carrier": "USAA Commercial", "premium": 11500},
    {"carrier": "Erie Insurance", "premium": 6750},
    {"carrier": "American Family", "premium": 10200},
    {"carrier": "Auto-Owners Insurance", "premium": 8900},
    {"carrier": "Cincinnati Insurance", "premium": 7600},
    {"carrier": "Chubb Commercial", "premium": 13200},
    {"carrier": "Hanover Insurance", "premium": 9400},
    {"carrier": "Markel Insurance", "premium": 11800},
    {"carrier": "RLI Corp", "premium": 6900},
    {"carrier": "Sentry Insurance", "premium": 8200},
    {"carrier": "West Bend Mutual", "premium": 7100},
    {"carrier": "Selective Insurance", "premium": 10500},
    {"carrier": "Donegal Insurance", "premium": 9100},
    {"carrier": "Westfield Insurance", "premium": 8800},
    {"carrier": "Church Mutual", "premium": 7500},
    {"carrier": "Grinnell Mutual", "premium": 6400},
    {"carrier": "Acuity Insurance", "premium": 7800},
]

# Re-questioning phrases for rejected confirmation handling
_RE_QUESTION_PHRASES: List[str] = [
    "Wait, before we move on, can you double-check the business name? I want to make sure I have it right.",
    "Actually, let me verify something. You mentioned the address earlier - is it still {field}: {value}? Sometimes people give a different one.",
    "Hold on, I want to circle back. Are you sure about the entity type you provided? Just want to be thorough.",
    "Before continuing, I noticed you said {field} is {value}. Can you confirm that's correct one more time?",
    "I just want to go back and make sure - the {field} you gave was {value}, right? I want to be absolutely certain.",
    "Let me double-check one thing. You said {field} was {value}. Is that definitely right?",
    "Sorry, I want to verify again - is {field} really {value}? I want to make sure we have accurate data.",
    "One more thing before we move forward - you're absolutely sure {field} is {value}?",
    "I know you already confirmed this, but could you check the {field} one more time? I have {value}.",
    "Quick question - I have {field} as {value}. Can you verify that again?",
]


# ---------------------------------------------------------------------------
# Helper: make tool call ID
# ---------------------------------------------------------------------------


def _make_call_id() -> str:
    """Generate a deterministic tool call ID from the RNG."""
    return f"call_{uuid4().hex[:8]}"


def _make_call_id_from_rng(rng: random.Random) -> str:
    """Generate a tool call ID using a seeded RNG for determinism."""
    hex_chars = "0123456789abcdef"
    suffix = "".join(rng.choice(hex_chars) for _ in range(8))
    return f"call_{suffix}"


# ---------------------------------------------------------------------------
# Helper: build a tool call message
# ---------------------------------------------------------------------------


def _make_tool_call_msg(
    tool_name: str,
    arguments: dict,
    call_id: str,
) -> dict:
    """Build an assistant message with a single tool_call."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments, separators=(",", ":")),
                },
            }
        ],
    }


def _make_multi_tool_call_msg(
    tool_calls: List[dict],
) -> dict:
    """Build an assistant message with multiple tool_calls."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": tool_calls,
    }


def _make_tool_response(call_id: str, content: dict) -> dict:
    """Build a tool response message."""
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(content, separators=(",", ":")),
    }


def _make_single_tool_call_entry(
    tool_name: str,
    arguments: dict,
    call_id: str,
) -> dict:
    """Build one entry for a tool_calls list."""
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": tool_name,
            "arguments": json.dumps(arguments, separators=(",", ":")),
        },
    }


# ---------------------------------------------------------------------------
# Category generators
# ---------------------------------------------------------------------------


def _generate_address_hallucination(
    scenarios: List[ConversationScenario],
    count: int,
    rng: random.Random,
) -> List[dict]:
    """Generate address_hallucination DPO pairs.

    Chosen: assistant saves the actual address from the user message.
    Rejected: assistant saves a hallucinated/fake address.
    """
    pairs: List[dict] = []

    for i in range(count):
        scenario = scenarios[i % len(scenarios)]
        biz = scenario.business
        addr = biz.get("mailing_address", {})
        real_street = addr.get("line_one", "123 Main St")
        real_city = addr.get("city", "Anytown")
        real_state = addr.get("state", "TX")
        real_zip = addr.get("zip_code", "75001")

        # Pick a fake address that differs from the real one
        fake_addr = _FAKE_ADDRESSES[i % len(_FAKE_ADDRESSES)]
        # Ensure it's actually different
        if fake_addr["street"] == real_street:
            fake_addr = _FAKE_ADDRESSES[(i + 1) % len(_FAKE_ADDRESSES)]

        # Build shared system prompt
        system_content = build_training_system_prompt(
            phase="applicant_info",
            form_state={"business_name": {
                "value": biz.get("business_name", ""),
                "confidence": 0.95,
                "source": "user_stated",
                "status": "confirmed",
            }},
            lobs=list(scenario.lobs),
            assigned_forms=list(scenario.assigned_forms),
        )

        # Shared user message: provide address
        user_seed = rng.randint(0, 2**31)
        user_msg = render_user_template(
            "provide_address",
            seed=user_seed,
            street=real_street,
            city=real_city,
            state=real_state,
            zip=real_zip,
        )

        # --- CHOSEN: save actual address ---
        chosen_calls = []
        chosen_tool_responses = []
        for field_name, value in [
            ("mailing_street", real_street),
            ("mailing_city", real_city),
            ("mailing_state", real_state),
            ("mailing_zip", real_zip),
        ]:
            cid = _make_call_id_from_rng(rng)
            chosen_calls.append(_make_single_tool_call_entry(
                "save_field",
                {"field_name": field_name, "value": value, "source": "user_stated", "status": "pending"},
                cid,
            ))
            chosen_tool_responses.append(_make_tool_response(cid, {
                "status": "saved", "field_name": field_name, "value": value, "confidence": 0.95,
            }))

        chosen_tool_msg = _make_multi_tool_call_msg(chosen_calls)
        chosen_ack = {
            "role": "assistant",
            "content": (
                f"I've recorded your address as {real_street}, {real_city}, "
                f"{real_state} {real_zip}. Let me move on to the next question. "
                f"What is your entity type and federal tax ID?"
            ),
        }

        # --- REJECTED: save hallucinated address ---
        rejected_calls = []
        rejected_tool_responses = []
        for field_name, value in [
            ("mailing_street", fake_addr["street"]),
            ("mailing_city", fake_addr["city"]),
            ("mailing_state", fake_addr["state"]),
            ("mailing_zip", fake_addr["zip"]),
        ]:
            cid = _make_call_id_from_rng(rng)
            rejected_calls.append(_make_single_tool_call_entry(
                "save_field",
                {"field_name": field_name, "value": value, "source": "user_stated", "status": "pending"},
                cid,
            ))
            rejected_tool_responses.append(_make_tool_response(cid, {
                "status": "saved", "field_name": field_name, "value": value, "confidence": 0.95,
            }))

        rejected_tool_msg = _make_multi_tool_call_msg(rejected_calls)
        rejected_ack = {
            "role": "assistant",
            "content": (
                f"I've recorded your address as {fake_addr['street']}, {fake_addr['city']}, "
                f"{fake_addr['state']} {fake_addr['zip']}. What is your entity type and federal tax ID?"
            ),
        }

        # Assemble pair
        system_msg = {"role": "system", "content": system_content}
        user_msg_dict = {"role": "user", "content": user_msg}

        chosen = [system_msg, user_msg_dict, chosen_tool_msg] + chosen_tool_responses + [chosen_ack]
        rejected = [system_msg, user_msg_dict, rejected_tool_msg] + rejected_tool_responses + [rejected_ack]

        pairs.append({
            "chosen": chosen,
            "rejected": rejected,
            "category": "address_hallucination",
        })

    return pairs


def _generate_quote_fabrication(
    scenarios: List[ConversationScenario],
    count: int,
    rng: random.Random,
) -> List[dict]:
    """Generate quote_fabrication DPO pairs.

    Chosen: assistant presents ONLY tool-provided quote data.
    Rejected: assistant invents additional carriers or changes premiums.
    """
    pairs: List[dict] = []

    for i in range(count):
        scenario = scenarios[i % len(scenarios)]

        # Build realistic quote data from scenario
        real_carriers = []
        base_premium = 15000
        if scenario.prior_insurance:
            try:
                base_premium = int(scenario.prior_insurance[0].get("premium", "15000"))
            except (ValueError, TypeError):
                pass

        # Generate 3 "real" quotes
        carrier_pool = list(CARRIER_NAMES)
        rng.shuffle(carrier_pool)
        for j in range(3):
            carrier = carrier_pool[j % len(carrier_pool)]
            premium = base_premium + rng.randint(-3000, 5000)
            real_carriers.append({
                "carrier_name": carrier,
                "total_annual_premium": premium,
                "quote_id": f"quote_{j + 1}",
            })

        # Build quote comparison for system prompt
        quote_comparison = {
            "quotes": [
                {
                    "carrier": q["carrier_name"],
                    "total_annual": q["total_annual_premium"],
                    "monthly_estimate": round(q["total_annual_premium"] / 12, 2),
                    "quote_id": q["quote_id"],
                    "coverages": [],
                }
                for q in real_carriers
            ],
            "cheapest": {
                "carrier": min(real_carriers, key=lambda x: x["total_annual_premium"])["carrier_name"],
                "premium": min(q["total_annual_premium"] for q in real_carriers),
            },
        }

        # Build system prompt with quote data
        system_content = build_training_system_prompt(
            phase="quoting",
            form_state={},
            lobs=list(scenario.lobs),
            assigned_forms=list(scenario.assigned_forms),
            quotes=real_carriers,
            quote_comparison=quote_comparison,
        )

        # User message: ask about quotes
        user_seed = rng.randint(0, 2**31)
        user_msg = render_user_template("ask_for_quotes", seed=user_seed)

        # --- CHOSEN: present only real quote data ---
        quote_lines = []
        for q in real_carriers:
            monthly = round(q["total_annual_premium"] / 12, 2)
            quote_lines.append(
                f"- {q['carrier_name']}: ${q['total_annual_premium']:,}/yr "
                f"(~${monthly:,.2f}/mo)"
            )
        cheapest = min(real_carriers, key=lambda x: x["total_annual_premium"])
        chosen_content = (
            f"Here are your quote results:\n"
            + "\n".join(quote_lines)
            + f"\n\nThe most affordable option is {cheapest['carrier_name']} "
            f"at ${cheapest['total_annual_premium']:,}/yr. "
            f"All premiums are estimates and final rates require carrier underwriting. "
            f"Which quote would you like to go with?"
        )

        # --- REJECTED: fabricate additional carrier/premium ---
        fab_quote = _FABRICATED_QUOTES[i % len(_FABRICATED_QUOTES)]
        rejected_lines = list(quote_lines)  # Start with real ones
        rejected_lines.append(
            f"- {fab_quote['carrier']}: ${fab_quote['premium']:,}/yr "
            f"(~${round(fab_quote['premium'] / 12, 2):,.2f}/mo)"
        )
        # Also change one real premium
        altered_carrier = real_carriers[0]["carrier_name"]
        altered_premium = real_carriers[0]["total_annual_premium"] - rng.randint(2000, 5000)
        rejected_content = (
            f"Here are your quote results:\n"
            + "\n".join(rejected_lines)
            + f"\n\nI also found that {altered_carrier} can offer you a special rate of "
            f"${altered_premium:,}/yr if you bundle coverage. "
            f"Which quote would you like to go with?"
        )

        system_msg = {"role": "system", "content": system_content}
        user_msg_dict = {"role": "user", "content": user_msg}

        chosen = [
            system_msg,
            user_msg_dict,
            {"role": "assistant", "content": chosen_content},
        ]
        rejected = [
            system_msg,
            user_msg_dict,
            {"role": "assistant", "content": rejected_content},
        ]

        pairs.append({
            "chosen": chosen,
            "rejected": rejected,
            "category": "quote_fabrication",
        })

    return pairs


def _generate_tool_ordering(
    scenarios: List[ConversationScenario],
    count: int,
    rng: random.Random,
) -> List[dict]:
    """Generate tool_ordering DPO pairs.

    Chosen: classify_lobs -> assign_forms (correct order).
    Rejected: assign_forms called WITHOUT prior classify_lobs.
    """
    pairs: List[dict] = []

    for i in range(count):
        scenario = scenarios[i % len(scenarios)]

        # System prompt: policy_details phase
        system_content = build_training_system_prompt(
            phase="policy_details",
            form_state={
                "business_name": {
                    "value": scenario.business.get("business_name", ""),
                    "confidence": 0.95, "source": "user_stated", "status": "confirmed",
                },
            },
        )

        # User describes insurance needs
        lob_desc = ", ".join(scenario.lobs)
        user_seed = rng.randint(0, 2**31)
        user_msg = render_user_template(
            "provide_coverage_needs", seed=user_seed, coverage_type=lob_desc,
        )

        # --- CHOSEN: classify_lobs then assign_forms ---
        # Tool call 1: classify_lobs
        cid1 = _make_call_id_from_rng(rng)
        classify_tc = _make_single_tool_call_entry(
            "classify_lobs",
            {"description": scenario.business.get("operations_description", lob_desc)},
            cid1,
        )
        classify_resp = _make_tool_response(cid1, {
            "lobs": list(scenario.lobs),
            "reasoning": f"Based on operations: {scenario.business.get('operations_description', '')}",
        })

        # Tool call 2: assign_forms
        cid2 = _make_call_id_from_rng(rng)
        from finetune.agent.scenario_generator import LOB_FORMS
        lob_form_mapping = {lob: LOB_FORMS.get(lob, []) for lob in scenario.lobs}
        assign_tc = _make_single_tool_call_entry(
            "assign_forms",
            {"lobs": list(scenario.lobs)},
            cid2,
        )
        assign_resp = _make_tool_response(cid2, {
            "assigned_forms": list(scenario.assigned_forms),
            "lob_form_mapping": lob_form_mapping,
        })

        chosen_tool_msg = _make_multi_tool_call_msg([classify_tc, assign_tc])
        chosen_ack = {
            "role": "assistant",
            "content": (
                f"Based on your needs, I've identified the following lines of business: "
                f"{lob_desc}. The required forms are: ACORD "
                f"{', '.join(str(f) for f in scenario.assigned_forms)}. "
                f"Let me now ask about your desired effective date."
            ),
        }

        # --- REJECTED: assign_forms WITHOUT classify_lobs ---
        cid3 = _make_call_id_from_rng(rng)
        rejected_assign_tc = _make_single_tool_call_entry(
            "assign_forms",
            {"lobs": list(scenario.lobs)},
            cid3,
        )
        rejected_assign_resp = _make_tool_response(cid3, {
            "assigned_forms": list(scenario.assigned_forms),
            "lob_form_mapping": lob_form_mapping,
        })

        rejected_tool_msg = _make_multi_tool_call_msg([rejected_assign_tc])
        rejected_ack = {
            "role": "assistant",
            "content": (
                f"I've assigned the forms for your coverage. "
                f"The required forms are: ACORD "
                f"{', '.join(str(f) for f in scenario.assigned_forms)}. "
                f"What is your desired effective date?"
            ),
        }

        system_msg = {"role": "system", "content": system_content}
        user_msg_dict = {"role": "user", "content": user_msg}

        chosen = [
            system_msg, user_msg_dict,
            chosen_tool_msg, classify_resp, assign_resp,
            chosen_ack,
        ]
        rejected = [
            system_msg, user_msg_dict,
            rejected_tool_msg, rejected_assign_resp,
            rejected_ack,
        ]

        pairs.append({
            "chosen": chosen,
            "rejected": rejected,
            "category": "tool_ordering",
        })

    return pairs


def _generate_phase_inappropriate_tools(
    scenarios: List[ConversationScenario],
    count: int,
    rng: random.Random,
) -> List[dict]:
    """Generate phase_inappropriate_tools DPO pairs.

    Chosen: in greeting phase, assistant just greets (no tools).
    Rejected: in greeting phase, assistant calls save_field or classify_lobs.
    """
    pairs: List[dict] = []

    for i in range(count):
        scenario = scenarios[i % len(scenarios)]

        # System prompt: greeting phase
        system_content = build_training_system_prompt(
            phase="greeting",
            form_state={},
        )

        # User greeting
        greetings = [
            "Hi, I need help with commercial insurance",
            "Hello, I'm looking for insurance for my business",
            "Hey there, I need to get some insurance quotes",
            "Hi, can you help me with a commercial insurance application?",
            "Good morning, I need to set up insurance for my company",
        ]
        user_msg = greetings[i % len(greetings)]

        # --- CHOSEN: just greet, no tools ---
        asst_seed = rng.randint(0, 2**31)
        chosen_content = render_assistant_template("greet_customer", seed=asst_seed)

        # --- REJECTED: inappropriately calls save_field in greeting phase ---
        cid = _make_call_id_from_rng(rng)
        # The assistant guesses a business name or calls classify_lobs prematurely
        inappropriate_tools = [
            ("save_field", {
                "field_name": "business_name",
                "value": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)} Insurance",
                "source": "llm_inferred",
                "status": "pending",
            }),
            ("classify_lobs", {
                "description": "commercial insurance",
            }),
            ("save_field", {
                "field_name": "nature_of_business",
                "value": "unknown",
                "source": "llm_inferred",
                "status": "pending",
            }),
        ]
        tool_choice = inappropriate_tools[i % len(inappropriate_tools)]
        tool_name, tool_args = tool_choice

        rejected_tc = _make_single_tool_call_entry(tool_name, tool_args, cid)
        rejected_tool_msg = _make_multi_tool_call_msg([rejected_tc])

        if tool_name == "save_field":
            tool_resp_content = {
                "status": "saved",
                "field_name": tool_args["field_name"],
                "value": tool_args["value"],
                "confidence": 0.60,
            }
        else:
            tool_resp_content = {
                "lobs": ["general_liability"],
                "reasoning": "Inferred from greeting",
            }
        rejected_tool_resp = _make_tool_response(cid, tool_resp_content)

        rejected_ack = {
            "role": "assistant",
            "content": (
                f"Welcome! I've already started processing your information. "
                f"Let me continue gathering details. What is your business name?"
            ),
        }

        system_msg = {"role": "system", "content": system_content}
        user_msg_dict = {"role": "user", "content": user_msg}

        chosen = [
            system_msg,
            user_msg_dict,
            {"role": "assistant", "content": chosen_content},
        ]
        rejected = [
            system_msg,
            user_msg_dict,
            rejected_tool_msg,
            rejected_tool_resp,
            rejected_ack,
        ]

        pairs.append({
            "chosen": chosen,
            "rejected": rejected,
            "category": "phase_inappropriate_tools",
        })

    return pairs


def _generate_multi_field_completeness(
    scenarios: List[ConversationScenario],
    count: int,
    rng: random.Random,
) -> List[dict]:
    """Generate multi_field_completeness DPO pairs.

    User provides 5+ fields in one message.
    Chosen: saves ALL fields.
    Rejected: saves only 1-2 fields, missing the rest.
    """
    pairs: List[dict] = []

    for i in range(count):
        scenario = scenarios[i % len(scenarios)]
        biz = scenario.business
        addr = biz.get("mailing_address", {})

        # Build a set of 5+ fields the user provides
        all_fields = {
            "business_name": biz.get("business_name", "Acme Corp"),
            "mailing_street": addr.get("line_one", "100 Main St"),
            "mailing_city": addr.get("city", "Dallas"),
            "mailing_state": addr.get("state", "TX"),
            "mailing_zip": addr.get("zip_code", "75201"),
            "entity_type": biz.get("entity_type", "llc"),
            "tax_id": biz.get("tax_id", "12-3456789"),
        }

        # System prompt
        system_content = build_training_system_prompt(
            phase="applicant_info",
            form_state={},
            lobs=list(scenario.lobs),
            assigned_forms=list(scenario.assigned_forms),
        )

        # User provides everything at once
        field_parts = [f"{k}: {v}" for k, v in all_fields.items()]
        user_msg = "Here's all the business info: " + ", ".join(field_parts)

        # --- CHOSEN: save ALL fields ---
        chosen_calls = []
        chosen_tool_responses = []
        for field_name, value in all_fields.items():
            cid = _make_call_id_from_rng(rng)
            chosen_calls.append(_make_single_tool_call_entry(
                "save_field",
                {"field_name": field_name, "value": value, "source": "user_stated", "status": "pending"},
                cid,
            ))
            chosen_tool_responses.append(_make_tool_response(cid, {
                "status": "saved", "field_name": field_name, "value": value, "confidence": 0.95,
            }))

        chosen_tool_msg = _make_multi_tool_call_msg(chosen_calls)
        chosen_ack = {
            "role": "assistant",
            "content": (
                f"I've saved all {len(all_fields)} fields you provided: "
                f"{', '.join(all_fields.keys())}. "
                f"Let me move on to the next section."
            ),
        }

        # --- REJECTED: save only 1-2 fields ---
        # Pick just the first 1-2 fields
        partial_count = rng.randint(1, 2)
        partial_fields = dict(list(all_fields.items())[:partial_count])

        rejected_calls = []
        rejected_tool_responses = []
        for field_name, value in partial_fields.items():
            cid = _make_call_id_from_rng(rng)
            rejected_calls.append(_make_single_tool_call_entry(
                "save_field",
                {"field_name": field_name, "value": value, "source": "user_stated", "status": "pending"},
                cid,
            ))
            rejected_tool_responses.append(_make_tool_response(cid, {
                "status": "saved", "field_name": field_name, "value": value, "confidence": 0.95,
            }))

        rejected_tool_msg = _make_multi_tool_call_msg(rejected_calls)
        missed_fields = [k for k in all_fields if k not in partial_fields]
        rejected_ack = {
            "role": "assistant",
            "content": (
                f"I've recorded the business name. "
                f"Now, can you tell me your mailing address?"
            ),
        }

        system_msg = {"role": "system", "content": system_content}
        user_msg_dict = {"role": "user", "content": user_msg}

        chosen = [system_msg, user_msg_dict, chosen_tool_msg] + chosen_tool_responses + [chosen_ack]
        rejected = [system_msg, user_msg_dict, rejected_tool_msg] + rejected_tool_responses + [rejected_ack]

        pairs.append({
            "chosen": chosen,
            "rejected": rejected,
            "category": "multi_field_completeness",
        })

    return pairs


def _generate_confirmation_handling(
    scenarios: List[ConversationScenario],
    count: int,
    rng: random.Random,
) -> List[dict]:
    """Generate confirmation_handling DPO pairs.

    User says "looks good" / "yes that's correct".
    Chosen: assistant acknowledges and moves on.
    Rejected: assistant re-asks about an already-confirmed field.
    """
    pairs: List[dict] = []

    for i in range(count):
        scenario = scenarios[i % len(scenarios)]
        biz = scenario.business
        addr = biz.get("mailing_address", {})

        # Build form_state with several confirmed fields
        form_state = {
            "business_name": {
                "value": biz.get("business_name", ""),
                "confidence": 0.95, "source": "user_stated", "status": "confirmed",
            },
            "mailing_street": {
                "value": addr.get("line_one", ""),
                "confidence": 0.95, "source": "user_stated", "status": "confirmed",
            },
            "mailing_city": {
                "value": addr.get("city", ""),
                "confidence": 0.95, "source": "user_stated", "status": "confirmed",
            },
            "mailing_state": {
                "value": addr.get("state", ""),
                "confidence": 0.95, "source": "user_stated", "status": "confirmed",
            },
            "mailing_zip": {
                "value": addr.get("zip_code", ""),
                "confidence": 0.95, "source": "user_stated", "status": "confirmed",
            },
            "entity_type": {
                "value": biz.get("entity_type", ""),
                "confidence": 0.95, "source": "user_stated", "status": "confirmed",
            },
        }

        # System prompt with confirmed fields
        system_content = build_training_system_prompt(
            phase="applicant_info",
            form_state=form_state,
            lobs=list(scenario.lobs),
            assigned_forms=list(scenario.assigned_forms),
        )

        # Build context: assistant previously read back the data, user confirms
        prev_assistant = {
            "role": "assistant",
            "content": (
                f"Let me confirm what I have so far: "
                f"Business name: {biz.get('business_name', '')}, "
                f"Address: {addr.get('line_one', '')}, {addr.get('city', '')}, "
                f"{addr.get('state', '')} {addr.get('zip_code', '')}. "
                f"Entity type: {biz.get('entity_type', '')}. "
                f"Is everything correct?"
            ),
        }

        # User confirms
        user_seed = rng.randint(0, 2**31)
        user_msg = render_user_template("confirm_data", seed=user_seed)

        # --- CHOSEN: acknowledge and move on ---
        chosen_content = (
            "Great, everything is confirmed. Let me now move on to your "
            "insurance needs. What type of coverage are you looking for?"
        )

        # --- REJECTED: re-question an already-confirmed field ---
        # Pick a confirmed field to re-question
        confirmed_fields = list(form_state.items())
        field_name, field_info = confirmed_fields[i % len(confirmed_fields)]
        field_value = field_info["value"]

        re_question_template = _RE_QUESTION_PHRASES[i % len(_RE_QUESTION_PHRASES)]
        rejected_content = re_question_template.format(
            field=field_name, value=field_value,
        )

        system_msg = {"role": "system", "content": system_content}
        prev_asst_msg = prev_assistant
        user_msg_dict = {"role": "user", "content": user_msg}

        chosen = [
            system_msg,
            prev_asst_msg,
            user_msg_dict,
            {"role": "assistant", "content": chosen_content},
        ]
        rejected = [
            system_msg,
            prev_asst_msg,
            user_msg_dict,
            {"role": "assistant", "content": rejected_content},
        ]

        pairs.append({
            "chosen": chosen,
            "rejected": rejected,
            "category": "confirmation_handling",
        })

    return pairs


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------


def generate_dpo_pairs(
    scenarios: Optional[List[ConversationScenario]] = None,
    pairs_per_category: int = 20,
    seed: int = 42,
) -> List[dict]:
    """Generate DPO preference pairs across 6 anti-hallucination categories.

    Args:
        scenarios: Base scenarios to derive pairs from. If None, generates them.
        pairs_per_category: Number of pairs per category (default: 20, total: 120+).
        seed: Random seed for reproducibility.

    Returns:
        List of dicts, each with keys:
            - "chosen": list of messages (OpenAI chat format) showing GOOD behavior
            - "rejected": list of messages showing BAD behavior
            - "category": one of the 6 category strings
    """
    rng = random.Random(seed)

    if scenarios is None:
        scenarios = generate_scenarios(seed=seed)

    # Shuffle scenarios to get variety across categories
    shuffled = list(scenarios)
    rng.shuffle(shuffled)

    # Generate pairs for each category
    all_pairs: List[dict] = []

    # Each category generator gets a different slice of shuffled scenarios
    # to maximize diversity. We cycle through if needed.
    generators = [
        ("address_hallucination", _generate_address_hallucination),
        ("quote_fabrication", _generate_quote_fabrication),
        ("tool_ordering", _generate_tool_ordering),
        ("phase_inappropriate_tools", _generate_phase_inappropriate_tools),
        ("multi_field_completeness", _generate_multi_field_completeness),
        ("confirmation_handling", _generate_confirmation_handling),
    ]

    offset = 0
    for _cat_name, gen_func in generators:
        # Give each category a different starting slice of scenarios
        cat_scenarios = shuffled[offset:] + shuffled[:offset]
        cat_rng = random.Random(rng.randint(0, 2**31))
        cat_pairs = gen_func(cat_scenarios, pairs_per_category, cat_rng)
        all_pairs.extend(cat_pairs)
        offset = (offset + pairs_per_category) % len(shuffled)

    return all_pairs
