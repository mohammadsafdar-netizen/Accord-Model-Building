"""Tests for conversation message templates — agent fine-tuning dataset."""

import pytest

from finetune.agent.conversation_templates import (
    USER_TEMPLATES,
    ASSISTANT_TEMPLATES,
    render_user_template,
    render_assistant_template,
    render_bulk_message,
)


# ------------------------------------------------------------------
# Template count / coverage
# ------------------------------------------------------------------


def test_user_template_count():
    total = sum(len(v) for v in USER_TEMPLATES.values())
    assert total >= 30


def test_assistant_template_count():
    total = sum(len(v) for v in ASSISTANT_TEMPLATES.values())
    assert total >= 20


def test_user_template_categories():
    required = {
        "provide_business_name", "provide_address", "provide_vehicle",
        "provide_driver", "confirm_data", "ask_for_quotes", "confirm_binding",
    }
    assert required.issubset(set(USER_TEMPLATES.keys()))


def test_assistant_template_categories():
    required = {
        "greet_customer", "acknowledge_and_ask_next", "confirm_field",
        "present_gap_summary", "present_review", "present_quotes",
        "ask_for_quote_selection", "confirm_bind", "ask_business_name",
        "ask_address", "ask_coverage_needs", "ask_vehicle_info",
        "ask_driver_info", "transition_to_next_phase",
    }
    assert required.issubset(set(ASSISTANT_TEMPLATES.keys()))


def test_each_user_category_has_multiple_variants():
    for topic, templates in USER_TEMPLATES.items():
        assert len(templates) >= 3, f"Topic '{topic}' has only {len(templates)} variants"


def test_each_assistant_category_has_multiple_variants():
    for topic, templates in ASSISTANT_TEMPLATES.items():
        assert len(templates) >= 3, f"Topic '{topic}' has only {len(templates)} variants"


# ------------------------------------------------------------------
# render_user_template
# ------------------------------------------------------------------


def test_render_user_template_fills_slots():
    msg = render_user_template(
        "provide_vehicle",
        year="2024", make="Ford", model="Transit", vin="1FTBW...",
    )
    assert "2024" in msg
    assert "Ford" in msg


def test_render_user_template_deterministic_with_seed():
    msg1 = render_user_template(
        "provide_business_name", seed=42, business_name="Acme",
    )
    msg2 = render_user_template(
        "provide_business_name", seed=42, business_name="Acme",
    )
    assert msg1 == msg2


def test_render_user_template_different_seeds_can_differ():
    """Different seeds should (probably) select different templates."""
    results = set()
    for seed in range(50):
        msg = render_user_template(
            "provide_business_name", seed=seed, business_name="Acme",
        )
        results.add(msg)
    # With 5+ variants and 50 seeds, we should see at least 2 variants
    assert len(results) >= 2


def test_render_user_template_raises_on_unknown_topic():
    with pytest.raises(KeyError):
        render_user_template("nonexistent_topic_xyz")


# ------------------------------------------------------------------
# render_assistant_template
# ------------------------------------------------------------------


def test_render_assistant_template_fills_slots():
    msg = render_assistant_template(
        "acknowledge_and_ask_next",
        field="business name", value="Acme Corp",
        next_question="What is your address?",
    )
    assert "Acme Corp" in msg


def test_render_assistant_template_deterministic_with_seed():
    msg1 = render_assistant_template(
        "greet_customer", seed=42,
    )
    msg2 = render_assistant_template(
        "greet_customer", seed=42,
    )
    assert msg1 == msg2


# ------------------------------------------------------------------
# render_bulk_message
# ------------------------------------------------------------------


def test_render_bulk_message():
    fields = {
        "business_name": "Acme Corp",
        "street": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip": "78701",
    }
    msg = render_bulk_message(fields, seed=42)
    assert "Acme Corp" in msg
    assert "Austin" in msg


def test_render_bulk_message_deterministic_with_seed():
    fields = {
        "business_name": "Acme Corp",
        "street": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip": "78701",
        "entity_type": "LLC",
        "tax_id": "12-3456789",
    }
    msg1 = render_bulk_message(fields, seed=99)
    msg2 = render_bulk_message(fields, seed=99)
    assert msg1 == msg2


def test_render_bulk_message_contains_multiple_field_values():
    fields = {
        "business_name": "Zenith Logistics",
        "entity_type": "corporation",
        "street": "500 Park Ave",
        "city": "New York",
        "state": "NY",
        "zip": "10001",
        "tax_id": "99-7654321",
        "phone": "555-123-4567",
        "email": "info@zenith.com",
    }
    msg = render_bulk_message(fields, seed=42)
    # At least a few fields should appear
    found = sum(1 for v in fields.values() if v in msg)
    assert found >= 3, f"Only {found} fields found in bulk message: {msg}"


# ------------------------------------------------------------------
# Casual / typo variants for confirm_data
# ------------------------------------------------------------------


def test_confirm_data_includes_casual_variants():
    templates = USER_TEMPLATES["confirm_data"]
    # Should have typo/casual variants
    casual_count = sum(
        1 for t in templates
        if any(word in t.lower() for word in ["yep", "yse", "lok", "thats"])
    )
    assert casual_count >= 2


# ------------------------------------------------------------------
# Template string sanity
# ------------------------------------------------------------------


def test_user_templates_are_nonempty_strings():
    for topic, templates in USER_TEMPLATES.items():
        for i, t in enumerate(templates):
            assert isinstance(t, str), f"{topic}[{i}] is not a string"
            assert len(t.strip()) > 0, f"{topic}[{i}] is empty"


def test_assistant_templates_are_nonempty_strings():
    for topic, templates in ASSISTANT_TEMPLATES.items():
        for i, t in enumerate(templates):
            assert isinstance(t, str), f"{topic}[{i}] is not a string"
            assert len(t.strip()) > 0, f"{topic}[{i}] is empty"
