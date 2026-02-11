import pytest
from src.tools.conversation import (
    generate_next_question,
    classify_user_intent,
    track_conversation_context,
    calculate_form_progress
)

def test_generate_next_question():
    q, field, type_ = generate_next_question(["common.insured_name"], "common")
    assert "legal name" in q
    assert field == "common.insured_name"
    
    q, _, _ = generate_next_question([], "common")
    assert "All set" in q

def test_classify_intent():
    intent, conf = classify_user_intent("Please stop")
    assert intent == "cancel"
    
    intent, conf = classify_user_intent("My name is John")
    assert intent == "provide_info"

def test_context_tracking():
    h = track_conversation_context("hello", [])
    assert len(h) == 1
    assert h[0]["content"] == "hello"

def test_progress():
    pct, rem = calculate_form_progress(5, 10)
    assert pct == 50.0
    assert rem == 5
