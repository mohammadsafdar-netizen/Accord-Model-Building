import pytest
from src.tools.orchestrator import (
    route_to_agent,
    validate_state_transition,
    create_checkpoint,
    check_workflow_completion,
    log_orchestration_metrics
)

def test_route_to_agent():
    # Test 1: Validation errors priority
    agent, reason = route_to_agent("common_fields", {}, [{"error": "fail"}])
    assert agent == "input_validator"
    
    # Test 2: Common fields not complete
    agent, reason = route_to_agent("common_fields", {"common_complete": False}, [])
    assert agent == "conversation_manager"
    
    # Test 3: Common fields complete
    agent, reason = route_to_agent("common_fields", {"common_complete": True}, [])
    assert agent == "form_population"

def test_validate_state_transition():
    # Valid
    valid, issues = validate_state_transition("common_fields", "form_specific", {})
    assert valid is True
    assert len(issues) == 0
    
    # Invalid transition
    valid, issues = validate_state_transition("common_fields", "submission", {}) # skipping steps
    assert valid is False
    
    # Blocking issues for submission
    valid, issues = validate_state_transition("verification", "submission", {"critical_missing": ["ssn"]})
    assert valid is False
    assert "Critical fields missing." in issues

def test_create_checkpoint():
    # Mock state
    state = {}
    cp_id, ts = create_checkpoint("sess_1", state)
    assert isinstance(cp_id, str)
    assert len(cp_id) > 0
    assert isinstance(ts, str)

def test_check_workflow_completion():
    # Complete
    can_proceed, missing, next_phase = check_workflow_completion({}, {"missing": []}, "common_fields")
    assert can_proceed is True
    assert next_phase == "form_specific"
    
    # Incomplete
    can_proceed, missing, next_phase = check_workflow_completion({}, {"missing": ["name"]}, "common_fields")
    assert can_proceed is False
    assert "name" in missing

def test_log_metrics():
    success = log_orchestration_metrics("task_complete", "orchestrator", 0.5, True)
    assert success is True
    # Verify it hit our mock store (check side effect if needed, though simple return check is fine for unit test)
