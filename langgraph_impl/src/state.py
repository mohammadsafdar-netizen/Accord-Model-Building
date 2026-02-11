from typing import TypedDict, Annotated, List, Dict, Optional, Any
import operator
from datetime import datetime

# UNIVERSAL STATE (Shared across all agents)
class UniversalState(TypedDict):
    """Core state shared by all agents"""
    # Conversation Context
    session_id: str
    user_id: str
    conversation_history: Annotated[List[Dict[str, Any]], operator.add]
    current_timestamp: datetime
    
    # Form Data (The Source of Truth)
    # We aggregate all data into a single Pydantic sourced structure for strict typing
    # Access via state['forms_data'].form_125.insured_name etc.
    forms_data: Any # Typed as FullFormsData
    
    # Conditional Form Logic
    active_form_ids: List[str] # E.g., ['form_125'] - determines which forms are "visible" to the agent
    
    # Workflow Control
    current_phase: str  # "common_fields" | "form_specific" | "verification" | "submission"
    current_agent: str  # Which agent is active
    next_agent: Optional[str]
    waiting_for_input: bool # Signal UI to request user input
    
    # Validation & Completeness
    validation_errors: Annotated[List[Dict[str, Any]], operator.add]
    field_completion_status: Dict[str, Any]  # Which fields are filled
    required_fields_status: Dict[str, Any]  # Which required fields are missing
    
    # Temporary Input Processing (The Pipeline)
    pending_input_field: Optional[str] # The field user tried to fill
    pending_input_value: Any           # The raw value provided
    validated_value: Any               # The value after validation
    is_input_valid: bool               # Flag to signal Mapper
    
    # User Preferences
    completion_method: Optional[str]  # "chat" | "manual" | "email"
    
    # Submission Status
    guidewire_submission_id: Optional[str]
    quote_amount: Optional[float]
    submission_status: str  # "draft" | "pending" | "submitted" | "quoted" | "emailed"
    
    # Incoming Email Simulation
    incoming_email_attachment: Optional[str] # Path to the file received via email
    
    # Audit Trail
    state_history: Annotated[List[Dict[str, Any]], operator.add]  # For rollback/debugging


# PER-AGENT PRIVATE STATE (Not shared, agent-specific working memory)
class AgentPrivateState(TypedDict):
    """Each agent can have its own working memory"""
    agent_name: str
    working_data: Dict[str, Any]  # Temporary calculations, intermediate results
    tool_results: List[Dict[str, Any]]  # Results from tool calls
    retry_count: int
    error_context: Optional[Dict[str, Any]]
