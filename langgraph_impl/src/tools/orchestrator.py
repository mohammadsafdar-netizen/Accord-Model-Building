import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List
from src.state import UniversalState

# Mock for Prometheus metrics
METRICS_STORE = []

def route_to_agent(
    current_phase: str, 
    field_completion_status: Dict[str, Any], 
    validation_errors: List[Dict],
    pending_input_field: Optional[str] = None,
    is_input_valid: bool = False,
    waiting_for_input: bool = False,
    submission_status: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Determines next agent based on current state.
    """
    if waiting_for_input:
        return None, "Waiting for user input."

    # 1. Pipeline: Input -> Validation -> Mapping
    if pending_input_field:
        if is_input_valid:
            return "schema_mapper", "Input validated, routing to mapper."
        
        # Always route to validator if we have pending input that isn't valid yet
        return "input_validator", "New input detected, routing to validator."

    # 2. Standard Workflow
    if current_phase == "common_fields":
        if field_completion_status.get("common_complete", False):
            # TRANSITION: Common Fields Done -> Decision Phase (User Preference Node)
            return "user_preference", "Common fields complete, asking user preference."
        return "conversation_manager", "Common fields incomplete, continuing conversation."

    if current_phase == "common_completed":
         # Fallback catch-all
         return "user_preference", "Common fields complete."
         
    if current_phase == "decision_making":
        # Check if user made a choice
        method = field_completion_status.get("completion_method")
        if method == "chat":
            return "form_population", "User chose chat, moving to form specific."
        elif method == "email":
            return "email_processing", "User chose email, routing to email agent."
        elif method == "manual":
            return "form_population", "User chose manual, routing to form pop (simulated manual flow)."
        else:
            return "conversation_manager", "Choice needed: Chat, Manual, or Email?"

    if current_phase == "form_specific":
        # Check if we have gathered specific info (Simulated check)
        if field_completion_status.get("forms_filled", False):
             return "completeness_verification", "Forms filled, moving to verification."
        
        # Otherwise, keep filling (Start specific questions loop)
        return "conversation_manager", "Continuing specific form questions."

    if current_phase == "verification":
        # Route to Completeness Agent to run checks
        return "completeness_verification", "In verification phase."
    
    if current_phase == "submission":
        if submission_status in ["quoted", "submitted", "emailed"]: 
           # Stop the workflow if already submitted
           return None, "Submission complete."
           
        return "guidewire_integration", "Ready for submission."

    return None, "No active phase or unknown state."

def validate_state_transition(current_phase: str, next_phase: str, required_fields_status: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Ensures state transition is valid.
    """
    valid_transitions = {
        "common_fields": ["decision_making", "form_specific", "verification"],
        "decision_making": ["form_specific", "email_processing"],
        "form_specific": ["verification", "common_fields"],
        "verification": ["submission", "form_specific"],
        "submission": ["verification", "common_fields"] # Can bounce back if failed
    }
    
    if next_phase not in valid_transitions.get(current_phase, []):
        return False, [f"Invalid transition from {current_phase} to {next_phase}"]
        
    blocking_issues = []
    if next_phase == "submission":
         # Check if we have critical errors
         if required_fields_status.get("critical_missing", []):
             blocking_issues.append("Critical fields missing.")
             
    return len(blocking_issues) == 0, blocking_issues

def create_checkpoint(session_id: str, state: UniversalState) -> Tuple[str, str]:
    """
    Saves state snapshot (Mock implementation).
    """
    checkpoint_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    # In a real app, this would write to Postgres
    return checkpoint_id, timestamp

def recover_from_checkpoint(session_id: str, checkpoint_id: str) -> Optional[UniversalState]:
    """
    Restores state from checkpoint (Mock implementation).
    """
    # In real app, read from Postgres
    return None 

def check_workflow_completion(common_schema_data: Dict, required_fields_status: Dict, current_phase: str) -> Tuple[bool, List[str], Optional[str]]:
    """
    Checks if workflow can proceed to next phase.
    """
    missing = required_fields_status.get("missing", [])
    if current_phase == "common_fields":
        if not missing:
            return True, [], "form_specific"
        return False, missing, None
        
    return True, [], None

def log_orchestration_metrics(event_type: str, agent_name: str, duration: float, success: bool) -> bool:
    """
    Logs workflow metrics (Mock).
    """
    METRICS_STORE.append({
        "event_type": event_type,
        "agent_name": agent_name,
        "duration": duration,
        "success": success,
        "timestamp": datetime.now()
    })
    return True
