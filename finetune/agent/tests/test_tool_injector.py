"""Tests for the deterministic tool call injector."""

import json

import pytest

from finetune.agent.skeleton_builder import TurnSkeleton
from finetune.agent.tool_injector import KEY_ALIASES, inject_tool_calls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_save_field_turn():
    return TurnSkeleton(
        phase="applicant_info",
        user_fields={"business_name": "Acme Corp", "business_address_street": "123 Main St"},
        tools_to_call=["save_field", "save_field", "validate_fields"],
        action="save_fields",
        assistant_should_ask="What is your address?",
    )


def _make_simple_scenario():
    from finetune.agent.scenario_generator import generate_scenarios
    return generate_scenarios()[0]


# ---------------------------------------------------------------------------
# Basic return-type tests
# ---------------------------------------------------------------------------


class TestInjectReturnTypes:
    def test_inject_returns_tuple(self):
        turn = _make_save_field_turn()
        scenario = _make_simple_scenario()
        result, new_fs = inject_tool_calls(turn, {}, scenario)
        assert isinstance(result, list)
        assert isinstance(new_fs, dict)

    def test_tool_call_id_format(self):
        turn = _make_save_field_turn()
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        for i in interactions:
            assert i["tool_call"]["id"].startswith("call_")
            assert len(i["tool_call"]["id"]) == 13  # "call_" + 8 hex chars

    def test_arguments_are_json_strings(self):
        turn = _make_save_field_turn()
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        for i in interactions:
            assert isinstance(i["tool_call"]["function"]["arguments"], str)
            json.loads(i["tool_call"]["function"]["arguments"])  # Should not raise

    def test_tool_response_has_matching_id(self):
        turn = _make_save_field_turn()
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        for i in interactions:
            assert i["tool_response"]["tool_call_id"] == i["tool_call"]["id"]

    def test_tool_response_has_role(self):
        turn = _make_save_field_turn()
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        for i in interactions:
            assert i["tool_response"]["role"] == "tool"

    def test_tool_call_has_type_function(self):
        turn = _make_save_field_turn()
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        for i in interactions:
            assert i["tool_call"]["type"] == "function"


# ---------------------------------------------------------------------------
# save_field tests
# ---------------------------------------------------------------------------


class TestSaveField:
    def test_save_field_uses_key_aliases(self):
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_address_street": "123 Main St"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, fs = inject_tool_calls(turn, {}, scenario)
        assert len(interactions) >= 1
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert args["field_name"] == "mailing_street"  # Alias resolved

    def test_form_state_updated_after_save(self):
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_name": "Acme Corp"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        _, fs = inject_tool_calls(turn, {}, scenario)
        assert "business_name" in fs
        assert fs["business_name"]["value"] == "Acme Corp"
        assert fs["business_name"]["confidence"] == 0.95

    def test_form_state_has_source_and_status(self):
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_name": "Acme Corp"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        _, fs = inject_tool_calls(turn, {}, scenario)
        assert fs["business_name"]["source"] == "user_stated"
        assert fs["business_name"]["status"] == "confirmed"

    def test_save_field_skips_duplicate(self):
        """If field already exists with same value, skip the save_field call."""
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_name": "Acme Corp"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        existing_state = {
            "business_name": {"value": "Acme Corp", "confidence": 0.95, "source": "user_stated", "status": "confirmed"}
        }
        interactions, fs = inject_tool_calls(turn, existing_state, scenario)
        # No save_field calls should be generated for the duplicate
        save_calls = [i for i in interactions if i["tool_call"]["function"]["name"] == "save_field"]
        assert len(save_calls) == 0

    def test_save_field_response_format(self):
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_name": "Acme Corp"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        save_calls = [i for i in interactions if i["tool_call"]["function"]["name"] == "save_field"]
        assert len(save_calls) == 1
        resp = json.loads(save_calls[0]["tool_response"]["content"])
        assert resp["status"] == "saved"
        assert resp["field_name"] == "business_name"
        assert resp["value"] == "Acme Corp"
        assert resp["confidence"] == 0.95

    def test_save_field_arguments_has_source_and_status(self):
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_name": "Acme Corp"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert args["source"] == "user_stated"
        assert args["status"] == "pending"

    def test_multiple_save_fields(self):
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_name": "Acme Corp", "entity_type": "llc"},
            tools_to_call=["save_field", "save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, fs = inject_tool_calls(turn, {}, scenario)
        save_calls = [i for i in interactions if i["tool_call"]["function"]["name"] == "save_field"]
        assert len(save_calls) == 2
        assert "business_name" in fs
        assert "entity_type" in fs


# ---------------------------------------------------------------------------
# Monetary normalization
# ---------------------------------------------------------------------------


class TestMonetaryNormalization:
    def test_monetary_value_normalized(self):
        turn = TurnSkeleton(
            phase="business_info",
            user_fields={"annual_revenue": "$5,000,000"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, fs = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert args["value"] == "5000000"  # Normalized

    def test_monetary_million_text(self):
        turn = TurnSkeleton(
            phase="business_info",
            user_fields={"annual_revenue": "$4.2 million"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert args["value"] == "4200000"

    def test_non_monetary_field_not_stripped(self):
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_name": "$pecial Corp"},
            tools_to_call=["save_field"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        # business_name is not a monetary field, so $ should be preserved
        assert args["value"] == "$pecial Corp"


# ---------------------------------------------------------------------------
# validate_fields tests
# ---------------------------------------------------------------------------


class TestValidateFields:
    def test_validate_fields_after_saves(self):
        turn = TurnSkeleton(
            phase="applicant_info",
            user_fields={"business_name": "Acme Corp", "entity_type": "llc"},
            tools_to_call=["save_field", "save_field", "validate_fields"],
            action="save_fields",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        validate_calls = [i for i in interactions if i["tool_call"]["function"]["name"] == "validate_fields"]
        assert len(validate_calls) == 1
        args = json.loads(validate_calls[0]["tool_call"]["function"]["arguments"])
        assert "fields" in args
        assert set(args["fields"]) == {"business_name", "entity_type"}
        resp = json.loads(validate_calls[0]["tool_response"]["content"])
        assert resp["status"] == "valid"
        assert resp["issues"] == []


# ---------------------------------------------------------------------------
# classify_lobs tests
# ---------------------------------------------------------------------------


class TestClassifyLobs:
    def test_classify_lobs_uses_scenario_lobs(self):
        turn = TurnSkeleton(
            phase="policy_details",
            user_fields={},
            tools_to_call=["classify_lobs"],
            action="classify_lobs",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        resp = json.loads(interactions[0]["tool_response"]["content"])
        assert "lobs" in resp
        assert set(resp["lobs"]) == set(scenario.lobs)

    def test_classify_lobs_arguments_has_description(self):
        turn = TurnSkeleton(
            phase="policy_details",
            user_fields={},
            tools_to_call=["classify_lobs"],
            action="classify_lobs",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert "description" in args


# ---------------------------------------------------------------------------
# assign_forms tests
# ---------------------------------------------------------------------------


class TestAssignForms:
    def test_assign_forms_uses_scenario_forms(self):
        turn = TurnSkeleton(
            phase="policy_details",
            user_fields={},
            tools_to_call=["assign_forms"],
            action="assign_forms",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        resp = json.loads(interactions[0]["tool_response"]["content"])
        assert "assigned_forms" in resp
        assert set(resp["assigned_forms"]) == set(scenario.assigned_forms)

    def test_assign_forms_arguments_has_lobs(self):
        turn = TurnSkeleton(
            phase="policy_details",
            user_fields={},
            tools_to_call=["assign_forms"],
            action="assign_forms",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert "lobs" in args


# ---------------------------------------------------------------------------
# analyze_gaps tests
# ---------------------------------------------------------------------------


class TestAnalyzeGaps:
    def test_no_state_param_in_arguments(self):
        """InjectedState params must not appear in training data."""
        turn = TurnSkeleton(
            phase="form_specific",
            user_fields={},
            tools_to_call=["analyze_gaps"],
            action="analyze_gaps",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        for i in interactions:
            args_str = i["tool_call"]["function"]["arguments"]
            assert "state" not in json.loads(args_str)

    def test_analyze_gaps_response_has_completeness(self):
        turn = TurnSkeleton(
            phase="form_specific",
            user_fields={},
            tools_to_call=["analyze_gaps"],
            action="analyze_gaps",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        # Pre-populate some form state
        form_state = {
            "business_name": {"value": "Acme Corp", "confidence": 0.95, "source": "user_stated", "status": "confirmed"},
            "mailing_street": {"value": "123 Main", "confidence": 0.95, "source": "user_stated", "status": "confirmed"},
        }
        interactions, _ = inject_tool_calls(turn, form_state, scenario)
        resp = json.loads(interactions[0]["tool_response"]["content"])
        assert "completeness_pct" in resp
        assert isinstance(resp["completeness_pct"], (int, float))
        assert "missing_critical" in resp
        assert "missing_important" in resp


# ---------------------------------------------------------------------------
# fill_forms tests
# ---------------------------------------------------------------------------


class TestFillForms:
    def test_fill_forms_response(self):
        turn = TurnSkeleton(
            phase="review",
            user_fields={},
            tools_to_call=["fill_forms"],
            action="fill_forms",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        resp = json.loads(interactions[0]["tool_response"]["content"])
        assert resp["status"] == "success"
        assert "forms_filled" in resp
        assert "output_directory" in resp

    def test_fill_forms_no_state_in_args(self):
        turn = TurnSkeleton(
            phase="review",
            user_fields={},
            tools_to_call=["fill_forms"],
            action="fill_forms",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert "state" not in args


# ---------------------------------------------------------------------------
# select_quote tests
# ---------------------------------------------------------------------------


class TestSelectQuote:
    def test_select_quote_response(self):
        turn = TurnSkeleton(
            phase="quote_selection",
            user_fields={"selected_quote": "quote_1"},
            tools_to_call=["select_quote"],
            action="select_quote",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert "quote_id" in args
        assert "payment_plan" in args
        resp = json.loads(interactions[0]["tool_response"]["content"])
        assert resp["status"] == "selected"
        assert "carrier" in resp
        assert "total_premium" in resp


# ---------------------------------------------------------------------------
# submit_bind_request tests
# ---------------------------------------------------------------------------


class TestSubmitBindRequest:
    def test_submit_bind_request_response(self):
        turn = TurnSkeleton(
            phase="bind_request",
            user_fields={"bind_confirmation": "yes"},
            tools_to_call=["submit_bind_request"],
            action="submit_bind_request",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        resp = json.loads(interactions[0]["tool_response"]["content"])
        assert resp["status"] == "submitted"
        assert "bind_request_id" in resp
        assert resp["bind_request_id"].startswith("BR-")
        assert "timestamp" in resp

    def test_submit_bind_request_no_state_in_args(self):
        turn = TurnSkeleton(
            phase="bind_request",
            user_fields={},
            tools_to_call=["submit_bind_request"],
            action="submit_bind_request",
            assistant_should_ask="",
        )
        scenario = _make_simple_scenario()
        interactions, _ = inject_tool_calls(turn, {}, scenario)
        args = json.loads(interactions[0]["tool_call"]["function"]["arguments"])
        assert "state" not in args


# ---------------------------------------------------------------------------
# No-tool turns
# ---------------------------------------------------------------------------


class TestNoToolTurns:
    def test_greeting_turn_no_tools(self):
        turn = TurnSkeleton(
            phase="greeting",
            user_fields={},
            tools_to_call=[],
            action="greet",
            assistant_should_ask="Ask how the assistant can help",
        )
        scenario = _make_simple_scenario()
        interactions, fs = inject_tool_calls(turn, {}, scenario)
        assert interactions == []
        assert fs == {}


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_same_output(self):
        turn = _make_save_field_turn()
        scenario = _make_simple_scenario()
        r1, fs1 = inject_tool_calls(turn, {}, scenario, seed=123)
        r2, fs2 = inject_tool_calls(turn, {}, scenario, seed=123)
        # tool_call IDs differ (uuid), but argument contents should match
        for a, b in zip(r1, r2):
            assert a["tool_call"]["function"]["name"] == b["tool_call"]["function"]["name"]
            assert a["tool_call"]["function"]["arguments"] == b["tool_call"]["function"]["arguments"]
