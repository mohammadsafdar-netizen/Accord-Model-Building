"""Tests for the scenario generator — agent fine-tuning dataset."""

import pytest

from finetune.agent.scenario_generator import (
    ConversationScenario,
    LOB_FORMS,
    generate_scenarios,
)


# Cache scenarios across test module (expensive to regenerate 500+).
@pytest.fixture(scope="module")
def scenarios():
    return generate_scenarios()


# ------------------------------------------------------------------
# Count / shape
# ------------------------------------------------------------------

def test_generate_scenarios_count(scenarios):
    assert len(scenarios) >= 500


def test_scenario_is_dataclass_instance(scenarios):
    assert isinstance(scenarios[0], ConversationScenario)


# ------------------------------------------------------------------
# Required fields
# ------------------------------------------------------------------

def test_scenario_has_required_fields(scenarios):
    s = scenarios[0]
    assert s.business.get("business_name")
    assert s.lobs
    assert s.assigned_forms
    assert s.delivery_style in ("conversational", "bulk_email", "mixed")
    assert s.user_persona in ("knowledgeable", "novice", "detailed")


def test_scenario_business_has_address(scenarios):
    s = scenarios[0]
    addr = s.business.get("mailing_address", {})
    assert addr.get("city")
    assert addr.get("state")
    assert addr.get("zip_code")


def test_scenario_ids_unique(scenarios):
    ids = [s.scenario_id for s in scenarios]
    assert len(ids) == len(set(ids))


# ------------------------------------------------------------------
# LOB coverage
# ------------------------------------------------------------------

def test_all_lobs_covered(scenarios):
    all_lobs = set()
    for s in scenarios:
        all_lobs.update(s.lobs)
    assert len(all_lobs) == 7, f"Missing LOBs: {set(LOB_FORMS) - all_lobs}"


def test_multi_lob_scenarios_exist(scenarios):
    multi = [s for s in scenarios if len(s.lobs) > 1]
    assert len(multi) >= 50


# ------------------------------------------------------------------
# Delivery styles & personas
# ------------------------------------------------------------------

def test_all_delivery_styles_present(scenarios):
    styles = {s.delivery_style for s in scenarios}
    assert styles == {"conversational", "bulk_email", "mixed"}


def test_all_personas_present(scenarios):
    personas = {s.user_persona for s in scenarios}
    assert personas == {"knowledgeable", "novice", "detailed"}


# ------------------------------------------------------------------
# Form / LOB consistency
# ------------------------------------------------------------------

def test_forms_match_lobs(scenarios):
    for s in scenarios:
        expected_forms = set()
        for lob in s.lobs:
            expected_forms.update(LOB_FORMS.get(lob, []))
        assert set(s.assigned_forms).issubset(expected_forms), (
            f"Scenario {s.scenario_id}: unexpected forms {s.assigned_forms} "
            f"for LOBs {s.lobs}"
        )


def test_forms_are_deduplicated(scenarios):
    for s in scenarios:
        assert len(s.assigned_forms) == len(set(s.assigned_forms)), (
            f"Scenario {s.scenario_id} has duplicate forms: {s.assigned_forms}"
        )


# ------------------------------------------------------------------
# Vehicles / Drivers (for auto LOB)
# ------------------------------------------------------------------

def test_auto_scenarios_have_vehicles(scenarios):
    auto = [s for s in scenarios if "commercial_auto" in s.lobs]
    assert auto, "No commercial_auto scenarios found"
    for s in auto:
        assert len(s.vehicles) >= 1, (
            f"Scenario {s.scenario_id} has commercial_auto but no vehicles"
        )


def test_auto_scenarios_have_drivers(scenarios):
    auto = [s for s in scenarios if "commercial_auto" in s.lobs]
    for s in auto:
        assert len(s.drivers) >= 1, (
            f"Scenario {s.scenario_id} has commercial_auto but no drivers"
        )


# ------------------------------------------------------------------
# Property / BOP scenarios have locations
# ------------------------------------------------------------------

def test_property_scenarios_have_locations(scenarios):
    prop = [
        s for s in scenarios
        if "commercial_property" in s.lobs or "bop" in s.lobs
    ]
    assert prop, "No property/BOP scenarios found"
    for s in prop:
        assert len(s.locations) >= 1, (
            f"Scenario {s.scenario_id} has property/BOP but no locations"
        )


# ------------------------------------------------------------------
# Reproducibility
# ------------------------------------------------------------------

def test_reproducibility():
    """Two calls to generate_scenarios() with default seed produce identical output."""
    a = generate_scenarios()
    b = generate_scenarios()
    assert len(a) == len(b)
    for sa, sb in zip(a, b):
        assert sa.scenario_id == sb.scenario_id
        assert sa.business == sb.business
        assert sa.lobs == sb.lobs
