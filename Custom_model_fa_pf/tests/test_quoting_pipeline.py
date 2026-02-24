"""Tests for the quoting pipeline: quote builder, carrier matcher, premium estimator, tools."""

import json
import pytest

from Custom_model_fa_pf.agent.quote_builder import build_quote_request, QuoteRequest
from Custom_model_fa_pf.agent.carrier_matcher import match_carriers, CarrierMatch
from Custom_model_fa_pf.agent.premium_estimator import (
    generate_quote,
    generate_quotes_for_matches,
    Quote,
)


# --- Shared test fixtures ---

@pytest.fixture
def sample_entities():
    return {
        "business": {
            "business_name": "Pinnacle Logistics LLC",
            "dba": "",
            "entity_type": "llc",
            "tax_id": "75-1234567",
            "mailing_address": {
                "line_one": "4500 Commerce Street Suite 200",
                "city": "Dallas",
                "state": "TX",
                "zip_code": "75226",
            },
            "nature_of_business": "Freight trucking",
            "years_in_business": "8",
            "employee_count": "45",
            "annual_revenue": "12500000",
            "annual_payroll": "2000000",
        },
        "policy": {
            "effective_date": "04/01/2026",
            "expiration_date": "04/01/2027",
        },
        "vehicles": [
            {"vin": "1FTFW1E80NFA00001", "year": "2023", "make": "Ford", "model": "F-150"},
            {"vin": "1FTFW1E80NFA00002", "year": "2022", "make": "Ford", "model": "F-250"},
            {"vin": "3AKJGLDR5KSLA0003", "year": "2021", "make": "Freightliner", "model": "Cascadia"},
        ],
        "drivers": [
            {"full_name": "John Doe", "dob": "01/15/1985", "license_number": "TX12345", "license_state": "TX"},
            {"full_name": "Jane Smith", "dob": "03/22/1990", "license_number": "TX67890", "license_state": "TX"},
        ],
        "prior_insurance": [
            {"carrier_name": "Old Guard Insurance", "premium": "25000"},
        ],
        "loss_history": [
            {"date": "06/15/2024", "amount": "5000", "description": "Minor fender bender"},
        ],
        "coverages": [],
        "locations": [],
    }


@pytest.fixture
def sample_lobs():
    return ["commercial_auto", "general_liability"]


@pytest.fixture
def sample_forms():
    return ["125", "127"]


# ============================================================
# Quote Builder Tests
# ============================================================

class TestQuoteBuilder:
    def test_build_basic(self, sample_entities, sample_lobs, sample_forms):
        qr = build_quote_request(sample_entities, sample_lobs, sample_forms)
        assert isinstance(qr, QuoteRequest)
        assert qr.business_name == "Pinnacle Logistics LLC"
        assert qr.fein == "75-1234567"
        assert len(qr.lobs) == 2
        assert "commercial_auto" in qr.lobs
        assert len(qr.vehicles) == 3
        assert len(qr.drivers) == 2

    def test_risk_profile_populated(self, sample_entities, sample_lobs, sample_forms):
        qr = build_quote_request(sample_entities, sample_lobs, sample_forms)
        rp = qr.risk_profile
        assert rp["fleet_size"] == 3
        assert rp["driver_count"] == 2
        assert rp["years_in_business"] == 8
        assert rp["employee_count"] == 45
        assert rp["state"] == "TX"
        assert rp["prior_carrier"] == "Old Guard Insurance"
        assert rp["total_loss_amount"] == 5000.0

    def test_to_dict(self, sample_entities, sample_lobs, sample_forms):
        qr = build_quote_request(sample_entities, sample_lobs, sample_forms)
        d = qr.to_dict()
        assert isinstance(d, dict)
        assert d["business_name"] == "Pinnacle Logistics LLC"
        assert "risk_profile" in d

    def test_empty_entities(self):
        qr = build_quote_request({}, [], [])
        assert qr.business_name == ""
        assert qr.risk_profile["fleet_size"] == 0

    def test_form_state_supplement(self, sample_entities, sample_lobs, sample_forms):
        """form_state should fill gaps in entities."""
        entities = dict(sample_entities)
        entities["business"]["mailing_address"]["state"] = ""  # Clear state
        fs = {"mailing_state": {"value": "CA"}}
        qr = build_quote_request(entities, sample_lobs, sample_forms, form_state=fs)
        assert qr.risk_profile["state"] == "CA"


# ============================================================
# Carrier Matcher Tests
# ============================================================

class TestCarrierMatcher:
    def test_match_auto_and_gl(self):
        rp = {
            "fleet_size": 10,
            "years_in_business": 5,
            "state": "TX",
            "total_loss_amount": 5000,
            "prior_premium": 25000,
        }
        matches = match_carriers(rp, ["commercial_auto", "general_liability"])
        assert len(matches) > 0
        eligible = [m for m in matches if m.eligible]
        assert len(eligible) >= 2  # Hartford + Travelers at minimum

    def test_progressive_fleet_limit(self):
        """Progressive rejects fleets over 50."""
        rp = {"fleet_size": 60, "years_in_business": 5, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0}
        matches = match_carriers(rp, ["commercial_auto"])
        progressive = next(m for m in matches if m.carrier_id == "progressive_commercial")
        assert not progressive.eligible

    def test_progressive_eligible_small_fleet(self):
        rp = {"fleet_size": 10, "years_in_business": 3, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0}
        matches = match_carriers(rp, ["commercial_auto"])
        progressive = next(m for m in matches if m.carrier_id == "progressive_commercial")
        assert progressive.eligible

    def test_employers_mutual_state_exclusion(self):
        """EMC excludes CA, NY, FL."""
        rp = {"fleet_size": 5, "years_in_business": 5, "state": "CA",
               "total_loss_amount": 0, "prior_premium": 0}
        matches = match_carriers(rp, ["workers_compensation"])
        emc = next(m for m in matches if m.carrier_id == "employers_mutual")
        assert not emc.eligible
        assert "CA" in emc.reasoning

    def test_years_in_business_filter(self):
        """Carriers requiring 3+ years should reject new businesses."""
        rp = {"fleet_size": 5, "years_in_business": 1, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0}
        matches = match_carriers(rp, ["commercial_auto"])
        travelers = next(m for m in matches if m.carrier_id == "travelers")
        assert not travelers.eligible

    def test_no_lob_overlap(self):
        """Carrier that doesn't write any requested LOB should be ineligible."""
        rp = {"fleet_size": 5, "years_in_business": 5, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0}
        matches = match_carriers(rp, ["cyber"])
        # None of the dummy carriers write cyber
        eligible = [m for m in matches if m.eligible]
        assert len(eligible) == 0

    def test_sorted_by_eligibility(self):
        rp = {"fleet_size": 10, "years_in_business": 5, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0}
        matches = match_carriers(rp, ["commercial_auto"])
        # Eligible should come before ineligible
        saw_ineligible = False
        for m in matches:
            if not m.eligible:
                saw_ineligible = True
            if saw_ineligible and m.eligible:
                pytest.fail("Eligible carrier found after ineligible one — sort broken")


# ============================================================
# Premium Estimator Tests
# ============================================================

class TestPremiumEstimator:
    def test_generate_single_quote(self):
        rp = {
            "fleet_size": 10,
            "years_in_business": 5,
            "employee_count": 45,
            "annual_revenue": 12500000,
            "annual_payroll": 2000000,
            "state": "TX",
            "total_loss_amount": 5000,
            "prior_premium": 25000,
        }
        quote = generate_quote("progressive_commercial", "Progressive Commercial",
                               ["commercial_auto"], rp)
        assert isinstance(quote, Quote)
        assert quote.total_annual_premium > 0
        assert len(quote.coverage_premiums) == 1
        assert quote.coverage_premiums[0]["lob"] == "commercial_auto"
        assert len(quote.payment_options) == 4  # annual, semi, quarterly, monthly
        assert "ESTIMATE" in quote.disclaimer

    def test_multi_lob_quote(self):
        rp = {
            "fleet_size": 10,
            "years_in_business": 5,
            "employee_count": 45,
            "annual_revenue": 12500000,
            "annual_payroll": 2000000,
            "state": "TX",
            "total_loss_amount": 0,
            "prior_premium": 0,
        }
        quote = generate_quote("hartford", "The Hartford",
                               ["commercial_auto", "general_liability"], rp)
        assert len(quote.coverage_premiums) == 2
        auto_prem = next(cp for cp in quote.coverage_premiums if cp["lob"] == "commercial_auto")
        gl_prem = next(cp for cp in quote.coverage_premiums if cp["lob"] == "general_liability")
        assert auto_prem["annual_premium"] > 0
        assert gl_prem["annual_premium"] > 0
        total = auto_prem["annual_premium"] + gl_prem["annual_premium"]
        assert abs(quote.total_annual_premium - total) < 0.01

    def test_payment_options_pricing(self):
        rp = {"fleet_size": 5, "years_in_business": 5, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0, "employee_count": 10,
               "annual_revenue": 500000, "annual_payroll": 200000}
        quote = generate_quote("progressive_commercial", "Progressive",
                               ["commercial_auto"], rp)
        annual_opt = next(po for po in quote.payment_options if po["plan"] == "annual")
        monthly_opt = next(po for po in quote.payment_options if po["plan"] == "monthly")
        # Monthly total should be more than annual (installment fees)
        assert monthly_opt["total_cost"] > annual_opt["total_cost"]

    def test_territory_factor_applied(self):
        """CA should be more expensive than TX for same risk."""
        base_rp = {
            "fleet_size": 10,
            "years_in_business": 5,
            "total_loss_amount": 0,
            "prior_premium": 0,
            "employee_count": 10,
            "annual_revenue": 500000,
            "annual_payroll": 200000,
        }
        tx = generate_quote("hartford", "Hartford", ["commercial_auto"], {**base_rp, "state": "TX"})
        ca = generate_quote("hartford", "Hartford", ["commercial_auto"], {**base_rp, "state": "CA"})
        assert ca.total_annual_premium > tx.total_annual_premium

    def test_generate_quotes_for_matches(self):
        matches = [
            {"carrier_id": "progressive_commercial", "carrier_name": "Progressive",
             "eligible": True, "supported_lobs": ["commercial_auto"]},
            {"carrier_id": "hartford", "carrier_name": "Hartford",
             "eligible": True, "supported_lobs": ["commercial_auto", "general_liability"]},
            {"carrier_id": "bad_carrier", "carrier_name": "Bad",
             "eligible": False, "supported_lobs": ["commercial_auto"]},
        ]
        rp = {"fleet_size": 10, "years_in_business": 5, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0, "employee_count": 10,
               "annual_revenue": 500000, "annual_payroll": 200000}
        quotes = generate_quotes_for_matches(matches, ["commercial_auto"], rp)
        # Should only have quotes for eligible carriers
        assert len(quotes) == 2
        carrier_ids = {q.carrier_id for q in quotes}
        assert "bad_carrier" not in carrier_ids
        # Should be sorted cheapest first
        assert quotes[0].total_annual_premium <= quotes[1].total_annual_premium

    def test_to_dict(self):
        rp = {"fleet_size": 5, "years_in_business": 3, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0, "employee_count": 5,
               "annual_revenue": 500000, "annual_payroll": 100000}
        quote = generate_quote("hartford", "Hartford", ["commercial_auto"], rp)
        d = quote.to_dict()
        assert isinstance(d, dict)
        assert "total_annual_premium" in d
        assert "coverage_premiums" in d
        assert "payment_options" in d


# ============================================================
# Tool Tests
# ============================================================

class TestQuotingTools:
    def test_build_quote_request_tool(self, sample_entities, sample_lobs, sample_forms):
        from Custom_model_fa_pf.agent.tools import build_quote_request_tool
        result = build_quote_request_tool.invoke({
            "entities_json": json.dumps(sample_entities),
            "lobs_json": json.dumps(sample_lobs),
            "assigned_forms_json": json.dumps(sample_forms),
        })
        parsed = json.loads(result)
        assert "error" not in parsed
        assert parsed["business_name"] == "Pinnacle Logistics LLC"
        assert "risk_profile" in parsed

    def test_match_carriers_tool(self, sample_entities, sample_lobs, sample_forms):
        from Custom_model_fa_pf.agent.tools import build_quote_request_tool, match_carriers_tool
        qr = json.loads(build_quote_request_tool.invoke({
            "entities_json": json.dumps(sample_entities),
            "lobs_json": json.dumps(sample_lobs),
            "assigned_forms_json": json.dumps(sample_forms),
        }))
        result = match_carriers_tool.invoke({"quote_request_json": json.dumps(qr)})
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert "carrier_id" in parsed[0]
        assert "eligible" in parsed[0]

    def test_generate_quotes_tool(self):
        from Custom_model_fa_pf.agent.tools import generate_quotes_tool
        matches = [
            {"carrier_id": "progressive_commercial", "carrier_name": "Progressive",
             "eligible": True, "supported_lobs": ["commercial_auto"]},
        ]
        rp = {"fleet_size": 5, "years_in_business": 3, "state": "TX",
               "total_loss_amount": 0, "prior_premium": 0, "employee_count": 5,
               "annual_revenue": 500000, "annual_payroll": 100000}
        result = generate_quotes_tool.invoke({
            "carrier_matches_json": json.dumps(matches),
            "lobs_json": json.dumps(["commercial_auto"]),
            "risk_profile_json": json.dumps(rp),
        })
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["carrier_id"] == "progressive_commercial"
        assert parsed[0]["total_annual_premium"] > 0

    def test_compare_quotes_tool(self):
        from Custom_model_fa_pf.agent.tools import compare_quotes_tool
        quotes = [
            {"quote_id": "Q1", "carrier_name": "Progressive",
             "total_annual_premium": 15000,
             "coverage_premiums": [{"lob": "commercial_auto", "lob_display": "Commercial Auto", "annual_premium": 15000}],
             "payment_options": [{"plan": "annual", "installment_amount": 15000, "installment_count": 1, "total_cost": 15000}]},
            {"quote_id": "Q2", "carrier_name": "Hartford",
             "total_annual_premium": 18000,
             "coverage_premiums": [
                 {"lob": "commercial_auto", "lob_display": "Commercial Auto", "annual_premium": 12000},
                 {"lob": "general_liability", "lob_display": "General Liability", "annual_premium": 6000},
             ],
             "payment_options": [{"plan": "annual", "installment_amount": 18000, "installment_count": 1, "total_cost": 18000}]},
        ]
        result = compare_quotes_tool.invoke({"quotes_json": json.dumps(quotes)})
        parsed = json.loads(result)
        assert parsed["quote_count"] == 2
        assert parsed["cheapest"]["carrier"] == "Progressive"
        assert parsed["most_coverage"]["carrier"] == "Hartford"

    def test_select_quote_tool(self):
        from Custom_model_fa_pf.agent.tools import select_quote_tool
        result = select_quote_tool.invoke({"quote_id": "Q-TEST-001", "payment_plan": "monthly"})
        parsed = json.loads(result)
        assert parsed["status"] == "selected"
        assert parsed["quote_id"] == "Q-TEST-001"
        assert parsed["payment_plan"] == "monthly"

    def test_submit_bind_request_tool(self):
        from Custom_model_fa_pf.agent.tools import submit_bind_request_tool
        result = submit_bind_request_tool.invoke({
            "quote_id": "Q-TEST-001",
            "carrier_name": "Progressive",
            "total_premium": 15000.0,
            "payment_plan": "annual",
            "customer_acknowledgment": "Yes, I confirm. Please proceed with binding.",
        })
        parsed = json.loads(result)
        assert parsed["status"] == "submitted"
        assert "bind_request_id" in parsed
        assert parsed["bind_status"] == "pending_carrier_review"
        assert len(parsed["next_steps"]) > 0

    def test_submit_bind_requires_acknowledgment(self):
        from Custom_model_fa_pf.agent.tools import submit_bind_request_tool
        result = submit_bind_request_tool.invoke({
            "quote_id": "Q-TEST-001",
            "carrier_name": "Progressive",
            "total_premium": 15000.0,
            "payment_plan": "annual",
            "customer_acknowledgment": "",
        })
        parsed = json.loads(result)
        assert parsed["status"] == "error"

    def test_all_tools_registered(self):
        from Custom_model_fa_pf.agent.tools import get_all_tools
        tools = get_all_tools()
        names = [t.name for t in tools]
        assert "build_quote_request" in names
        assert "match_carriers" in names
        assert "generate_quotes" in names
        assert "compare_quotes" in names
        assert "select_quote" in names
        assert "submit_bind_request" in names
        assert len(tools) == 16  # 10 original + 6 new


# ============================================================
# State Hydration Tests (Bug Fix #1)
# ============================================================

class TestStateHydration:
    def test_classify_lobs_hydrates_state(self):
        """classify_lobs results should populate state.lobs."""
        from langchain_core.messages import AIMessage, ToolMessage
        from Custom_model_fa_pf.agent.nodes import process_tool_results_node

        lobs_result = json.dumps([
            {"lob_id": "commercial_auto", "confidence": 0.95, "reasoning": "fleet"},
            {"lob_id": "general_liability", "confidence": 0.80, "reasoning": "business ops"},
        ])
        state = {
            "messages": [
                AIMessage(content="", tool_calls=[{"id": "1", "name": "classify_lobs", "args": {}}]),
                ToolMessage(content=lobs_result, tool_call_id="1"),
            ],
            "form_state": {},
            "entities": {},
            "lobs": [],
            "assigned_forms": [],
            "uploaded_documents": [],
        }
        result = process_tool_results_node(state)
        assert "lobs" in result
        assert "commercial_auto" in result["lobs"]
        assert "general_liability" in result["lobs"]

    def test_assign_forms_hydrates_state(self):
        """assign_forms results should populate state.assigned_forms."""
        from langchain_core.messages import AIMessage, ToolMessage
        from Custom_model_fa_pf.agent.nodes import process_tool_results_node

        forms_result = json.dumps([
            {"form_number": "125", "purpose": "Commercial Insurance Application", "lobs": ["commercial_auto"]},
            {"form_number": "127", "purpose": "Commercial Auto Section", "lobs": ["commercial_auto"]},
        ])
        state = {
            "messages": [
                AIMessage(content="", tool_calls=[{"id": "1", "name": "assign_forms", "args": {}}]),
                ToolMessage(content=forms_result, tool_call_id="1"),
            ],
            "form_state": {},
            "entities": {},
            "lobs": [],
            "assigned_forms": [],
            "uploaded_documents": [],
        }
        result = process_tool_results_node(state)
        assert "assigned_forms" in result
        assert "125" in result["assigned_forms"]
        assert "127" in result["assigned_forms"]

    def test_no_duplicate_lobs(self):
        """Re-classifying should not duplicate LOBs."""
        from langchain_core.messages import AIMessage, ToolMessage
        from Custom_model_fa_pf.agent.nodes import process_tool_results_node

        lobs_result = json.dumps([{"lob_id": "commercial_auto", "confidence": 0.95}])
        state = {
            "messages": [
                AIMessage(content="", tool_calls=[{"id": "1", "name": "classify_lobs", "args": {}}]),
                ToolMessage(content=lobs_result, tool_call_id="1"),
            ],
            "form_state": {},
            "entities": {},
            "lobs": ["commercial_auto"],  # Already present
            "assigned_forms": [],
            "uploaded_documents": [],
        }
        result = process_tool_results_node(state)
        assert result["lobs"].count("commercial_auto") == 1


# ============================================================
# Fill Forms Guard Tests (Bug Fix #2)
# ============================================================

class TestFillFormsGuard:
    def test_fill_rejects_missing_business_name(self):
        from Custom_model_fa_pf.agent.tools import fill_forms_tool
        result = fill_forms_tool.invoke({
            "entities_json": json.dumps({"business": {}}),
            "assigned_forms_json": json.dumps([{"form_number": "125"}]),
        })
        parsed = json.loads(result)
        assert parsed["status"] == "error"
        assert "business name" in parsed["error"].lower()

    def test_fill_rejects_no_forms(self):
        from Custom_model_fa_pf.agent.tools import fill_forms_tool
        result = fill_forms_tool.invoke({
            "entities_json": json.dumps({"business": {"business_name": "Test"}}),
            "assigned_forms_json": json.dumps([]),
        })
        parsed = json.loads(result)
        assert parsed["status"] == "error"
        assert "no forms" in parsed["error"].lower()


# ============================================================
# Routing Tests
# ============================================================

class TestQuotingRouting:
    def test_quoting_phase_routes_to_respond(self):
        from Custom_model_fa_pf.agent.nodes import route_after_gaps
        from Custom_model_fa_pf.agent.state import IntakePhase
        state = {
            "phase": IntakePhase.QUOTING.value,
            "form_state": {}, "entities": {}, "lobs": [], "assigned_forms": [],
            "validation_issues": [],
        }
        assert route_after_gaps(state) == "respond"

    def test_quote_selection_phase_routes_to_respond(self):
        from Custom_model_fa_pf.agent.nodes import route_after_gaps
        from Custom_model_fa_pf.agent.state import IntakePhase
        state = {
            "phase": IntakePhase.QUOTE_SELECTION.value,
            "form_state": {}, "entities": {}, "lobs": [], "assigned_forms": [],
            "validation_issues": [],
        }
        assert route_after_gaps(state) == "respond"

    def test_bind_request_phase_routes_to_respond(self):
        from Custom_model_fa_pf.agent.nodes import route_after_gaps
        from Custom_model_fa_pf.agent.state import IntakePhase
        state = {
            "phase": IntakePhase.BIND_REQUEST.value,
            "form_state": {}, "entities": {}, "lobs": [], "assigned_forms": [],
            "validation_issues": [],
        }
        assert route_after_gaps(state) == "respond"
