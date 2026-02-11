from typing import Dict, Any, Literal
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.generated_schemas import FullFormsData
from src.state import UniversalState, AgentPrivateState
from src.tools import (
    orchestrator,
    validator,
    mapper,
    conversation,
    form_population,
    completeness,
    email,
    doc_intel,
    guidewire,
    monitoring
)
from src.tools.form_manager import FormManager

# --- Agent 1: Orchestrator ---
def orchestrator_node(state: UniversalState) -> Dict[str, Any]:
    """
    Orchestrator Agent: Decides the next step.
    """
    monitoring.log_event("INFO", "NODE_ENTRY", "Entering Orchestrator Node")
    
    current_phase = state.get("current_phase", "common_fields")
    field_status = state.get("field_completion_status", {})
    val_errors = state.get("validation_errors", [])
    pending_field = state.get("pending_input_field")
    is_valid = state.get("is_input_valid", False)
    waiting = state.get("waiting_for_input", False)
    sub_status = state.get("submission_status")
    
    # If workflow already marked complete, stop further processing
    if state.get('workflow_complete'):
        return {"current_agent": "orchestrator", "next_agent": None}

    monitoring.log_event("INFO", "DEBUG_ORCH", f"Orchestrator State: waiting={waiting}, phase={current_phase}, agent={state.get('current_agent')}")
    
    # CRITICAL FIX: IF we are waiting for input, AND no fresh input just arrived, STOP immediately.
    # If pending_input_value IS present, it means the user just typed something,
    # so we should CONTINUE processing even if the state still says 'waiting'.
    if waiting and not state.get("pending_input_value"):
        # Do NOT overwrite current_agent, so we know where we paused when we resume.
        # We only return next_agent: None to stop the graph execution. 
        # The key 'current_agent' is OMITTED to preserve the existing value in state.
        return {"next_agent": None} # None maps to END in graph.py
    
    # If submission_status indicates a final state, stop further processing.
    # 'draft' is an intermediate state and should continue the workflow.
    final_statuses = {"quoted", "submitted", "emailed", "bound"}
    if sub_status in final_statuses:
        monitoring.log_event("INFO", "ORCHESTRATOR", f"Submission status '{sub_status}' detected. Ending workflow.")
        state["workflow_complete"] = True
        monitoring.log_event("INFO", "ORCHESTRATOR", f"Submission status '{sub_status}' detected. Ending workflow.")
        state["workflow_complete"] = True
        return {"next_agent": None}
    
    # 0. Check for Interrupts (Stop/Preferences)
    if pending_field == "GLOBAL_INTERRUPT" or (state.get("pending_input_value") and not waiting):
         # Check input content for commands
         val = str(state.get("pending_input_value")).lower().strip()
         
         # 1. Email Ingestion (Already added)
         if val.startswith("email:") or val.startswith("attachment:"):
             path = val.split(":", 1)[1].strip()
             monitoring.log_event("INFO", "ORCHESTRATOR", f"Detected Incoming Email: {path}")
             return {
                 "current_agent": "orchestrator", 
                 "next_agent": "document_intelligence",
                 "incoming_email_attachment": path,
                 "pending_input_value": None
             }

         # 2. Menu / Stop / Change Mode
         monitoring.log_event("INFO", "DEBUG_INT", f"Checking interrupt for value: '{val}'")
         interrupt_keywords = ["menu", "stop", "options", "change mode", "switch mode", "pause", "exit", "quit"]
         if any(k in val for k in interrupt_keywords): # Changed to substring match for robustness
             monitoring.log_event("INFO", "INTERRUPT", "User requested Menu/Interrupt.")
             return {
                 "current_agent": "orchestrator", 
                 "next_agent": "user_preference",
                 "pending_input_value": None, 
                 "pending_input_field": "GLOBAL_INTERRUPT", # Clear the specific field we were asking
                 "current_phase": "common_completed" # Reset phase to Decision
             }
             
    if pending_field == "GLOBAL_INTERRUPT":
         return {"current_agent": "orchestrator", "next_agent": "user_preference"}
    
    # 1. Check if we are in the Decision Phase
    # This block only runs if the User Preference node was the last runner but hasn't finished yet.
    if state.get("current_agent") == "user_preference":
        # A. Did the node make a decision? If so, follow it immediately.
        decision = state.get("next_agent")
        if decision: return {"current_agent": "orchestrator", "next_agent": decision}

        # B. If no decision, but we have a pending input
        if state.get("pending_input_value") and not waiting:
             val = str(state.get("pending_input_value")).lower().strip()
             if val and val not in ("none", "nan", "null", "undefined"):
                 return {"current_agent": "orchestrator", "next_agent": "user_preference"}
    
    # 2. Check for Completion Method
    method = state.get("completion_method")
    if method == "email" and state.get("current_agent") != "email_processing":
        return {"current_agent": "orchestrator", "next_agent": "email_processing"}
    if method == "manual":
         # Already generated forms (via population), so now we stop/submit
         return {"current_agent": "orchestrator", "next_agent": None} # Stop workflow
         
    # 3. Standard Routing
    next_agent, reason = orchestrator.route_to_agent(
        current_phase, 
        field_status, 
        val_errors,
        pending_field,
        is_valid,
        waiting,
        sub_status
    )
    
    monitoring.log_event("INFO", "ROUTING", f"Routing to {next_agent}: {reason}")
    
    return {"current_agent": "orchestrator", "next_agent": next_agent}


# --- Agent 2: Input Validator ---
def input_validator_node(state: UniversalState) -> Dict[str, Any]:
    """
    Validates pending user input.
    """
    monitoring.log_event("INFO", "NODE_ENTRY", "Entering Input Validator Node")
    
    field = state.get("pending_input_field")
    value = state.get("pending_input_value")
    
    if not field:
        return {"current_agent": "input_validator"}

    # Validation Logic
    is_valid = True
    error_msg = None
    clean_val = value

    # Since field names are now "form_125:field_name" or snake_case, apply generic validation
    # or specific regex if field name suggests (e.g., 'email', 'date').
    
    field_str = str(field).lower()

    if "email" in field_str:
        is_valid, clean_val, error_msg = validator.validate_email(value)
    if "date" in field_str or "dob" in field_str:
        is_valid, clean_val, error_msg = validator.validate_date(value)
        if not is_valid:
            error_msg = f"Invalid date. Please use YYYY-MM-DD."
    
    if is_valid:
        monitoring.log_event("INFO", "VALIDATION", f"Field {field} is valid.")
        return {
            "current_agent": "input_validator",
            "is_input_valid": True,
            "validated_value": clean_val,
            "validation_errors": []
        }
    else:
        monitoring.log_event("WARN", "VALIDATION", f"Field {field} invalid: {error_msg}")
        
        # AGENTIC PATTERN: REFLECTION
        # Call LLM to generate a smart, helpful correction message
        reflection_msg = conversation.generate_reflection_response(str(value), field_str.split(':')[-1], error_msg)
        
        return {
            "current_agent": "input_validator",
            "is_input_valid": False,
            "validation_errors": [{"field": field, "error": error_msg}],
            "conversation_history": [
                {"role": "assistant", "content": reflection_msg} 
            ],
            "waiting_for_input": True,
            "pending_input_value": None
        }


# --- Agent 3: Schema Mapper ---
def schema_mapper_node(state: UniversalState) -> Dict[str, Any]:
    """
    Maps validated data to form schemas using FormManager.
    """
    monitoring.log_event("INFO", "NODE_ENTRY", "Entering Schema Mapper Node")
    
    if not state.get("is_input_valid"):
        return {"current_agent": "schema_mapper"}
        
    val = state.get("validated_value")
    pending_field = state.get("pending_input_field") # Expected format "form_id:field_name"
    
    forms_data = state.get("forms_data")
    if not forms_data:
        forms_data = FullFormsData()
        
    mapped = False
    
    mapped = False
    new_active_forms = state.get("active_form_ids", ["form_125"])[:]
    
    if pending_field and ":" in pending_field:
        # It's a precise mapping from Conversation Manager
        form_id, field_name = pending_field.split(":", 1)
        
        # Clean up any potential confusion about 'form_' prefix
        # FormManager expects the attribute name of FullFormsData, which IS "form_125"
        
        success = FormManager.update_field(forms_data, form_id, field_name, val)
        if success:
            monitoring.log_event("INFO", "MAPPING", f"Mapped {form_id}.{field_name} = {val}")
            mapped = True
            
            # --- CONDITIONAL FORM ACTIVATION LOGIC ---
            # Trigger: Vehicle Schedule Indicator Checkbox -> Activate ACORD 127
            TRIGGER_FIELD = "policy_section_attached_vehicle_schedule_indicator_a"
            
            if field_name == TRIGGER_FIELD:
                # Normalize response (checkbox logic)
                is_yes = str(val).lower() in ["yes", "true", "1", "x"]
                if is_yes and "form_127" not in new_active_forms:
                    new_active_forms.append("form_127")
                    monitoring.log_event("INFO", "TRIGGER", "Activated Form 127 (Business Auto) based on user input.")
            # ----------------------------------------

        else:
             monitoring.log_event("ERROR", "MAPPING", f"Could not map {form_id}.{field_name}")
    else:
        # Fallback for generic inputs (rare in this new flow)
        monitoring.log_event("WARN", "MAPPING", f"Received unformatted field target: {pending_field}, ambiguous mapping.")
    
    return {
        "current_agent": "schema_mapper",
        "forms_data": forms_data,
        "active_form_ids": new_active_forms,
        "pending_input_field": None,
        "pending_input_value": None,
        "is_input_valid": False,
        "validation_errors": [] # Clear errors after mapping success
    }


# --- Agent 4: Conversation Manager ---
def conversation_manager_node(state: UniversalState) -> Dict[str, Any]:
    """
    Manages user interaction using Dynamic FormManager.
    """
    monitoring.log_event("INFO", "NODE_ENTRY", "Entering Conversation Manager Node")
    
    forms_data = state.get("forms_data")
    if not forms_data: forms_data = FullFormsData()
    
    # Check for validation errors and return early if needed (Input Validator handled msg)
    val_errs = state.get("validation_errors")
    if val_errs:
         monitoring.log_event("WARN", "CONVERSATION", f"Found validation errors: {val_errs}. Waiting for input.")
         return {"current_agent": "conversation_manager", "waiting_for_input": True}
    else:
         monitoring.log_event("INFO", "CONVERSATION", "No validation errors, proceeding to find next field.")

    # Select next field based on phase
    current_phase = state.get("current_phase", "common_fields")
    if current_phase == "common_fields":
        form_id, field_name, description = FormManager.get_next_missing_common_field(forms_data)
    else:
        active_forms = state.get("active_form_ids", ["form_125"])
        form_id, field_name, description = FormManager.get_next_missing_field(forms_data, active_forms)
    
    if form_id and field_name:
        # We found a missing field!
        
        # AGENTIC PATTERN: PLANNING
        # Check if we switched forms/sections from last time
        # We can store 'last_form_id' in state or just field_completion_status
        last_form = state.get("field_completion_status", {}).get("last_active_form")
        
        planning_msg = ""
        if last_form and last_form != form_id:
             # Transition detected!
             prev_phase = last_form.replace("form_", "ACORD ")
             next_phase = form_id.replace("form_", "ACORD ")
             planning_msg = conversation.generate_planning_message(prev_phase, next_phase)
             monitoring.log_event("INFO", "PLANNING", f"Transition: {prev_phase} -> {next_phase}")

        # Update status
        new_status = state.get("field_completion_status", {}).copy()
        new_status["last_active_form"] = form_id
        
        # Construct context
        target_context = f"{form_id}:{field_name}"
        phase_name = form_id.replace("form_", "ACORD ")
        
        # DEBUG: Log what we found
        monitoring.log_event("INFO", "CONVERSATION", f"Asking for field: {field_name}")
        
        question, _, _ = conversation.generate_next_question([field_name], phase_name)
        
        # Combine Planning + Question
        final_message = f"{planning_msg}\n\n{question}" if planning_msg else question
        
        # DEBUG: Log the message length
        monitoring.log_event("INFO", "CONVERSATION", f"Generated message len: {len(final_message)}")
        
        res = {
            "current_agent": "conversation_manager",
            "conversation_history": [
                {"role": "assistant", "content": final_message.strip()}
            ],
            "pending_input_field": target_context,
            "waiting_for_input": True,
            "is_input_valid": False,
            "field_completion_status": new_status,
            "next_agent": None # Break any decision loops
        }
        monitoring.log_event("INFO", "DEBUG_RET", f"Returning waiting_for_input={res['waiting_for_input']}")
        return res
    else:
        # No more fields found by FormManager
        # Check if we were in "common_fields" phase
        current_phase = state.get("current_phase", "common_fields")
        
        if current_phase == "common_fields":
            # Just finished Common Fields!
            # Double check we really did (Form Manager prioritized them, so if it returns None, they are done)
            monitoring.log_event("INFO", "CONVERSATION", "Common Fields Phase Complete.")
            
            return {
                "current_agent": "conversation_manager",
                "field_completion_status": {"common_complete": True},
                "current_phase": "common_completed" # Triggers Orchestrator to route to User Preference
            }
            
        # Specific Forms also done
        monitoring.log_event("INFO", "CONVERSATION", "All forms complete.")
        return {
            "current_agent": "conversation_manager",
            "field_completion_status": {"common_complete": True, "forms_filled": True},
            "current_phase": "submission" # Transition!
        }


# --- Agent 5: Form Population ---
def form_population_node(state: UniversalState) -> Dict[str, Any]:
    monitoring.log_event("INFO", "NODE_ENTRY", "Entering Form Population Node")
    
    forms_data = state.get("forms_data")
    if forms_data:
        # DEBUG: Check if data is actually here
        sample_name = getattr(forms_data.form_125, "named_insured_full_name_a", "N/A")
        monitoring.log_event("INFO", "DEBUG_POP", f"Data received for Form 125 Name: {sample_name}")
    else:
        monitoring.log_event("ERROR", "DEBUG_POP", "No forms_data in state!")

    # Use the new Full Data population logic
    results = form_population.fill_forms_from_full_data(forms_data)
    
    monitoring.log_event("INFO", "FORM_FILL", f"Filled forms: {results}")
    
    return {
        "current_agent": "form_population",
        "current_phase": "verification", # Or submission
        "submission_status": "submitted" # Demo end state
    }

# --- Agent 6: Completeness ---
def completeness_verification_node(state: UniversalState) -> Dict[str, Any]:
    monitoring.log_event("INFO", "NODE_ENTRY", "Entering Completeness Verification Node")
    
    forms_data = state.get("forms_data")
    if not forms_data: forms_data = FullFormsData()
    
    # Check what is missing
    # We check all active forms
    active_forms = state.get("active_form_ids", ["form_125"])
    form_id, field_name, description = FormManager.get_next_missing_field(forms_data, active_forms)
    
    # If we have already notified the user about missing info and are waiting for their correction,
    # do not re-enter the email processing loop.
    if state.get('submission_status') == 'waiting_correction':
        monitoring.log_event("INFO", "COMPLETENESS", "Waiting for user correction, not re-triggering email.")
        return {"current_agent": "completeness_verification", "next_agent": None, "submission_status": "waiting_correction"}
    # Existing logic
    if not field_name:
        monitoring.log_event("INFO", "COMPLETENESS", "All forms are complete!")
        return {
            "current_agent": "completeness_verification",
            "next_agent": "email_processing",
            "submission_status": "analyzed_complete"  # Signal for Email Agent
        }
    else:
        monitoring.log_event("INFO", "COMPLETENESS", f"Still missing field: {field_name}")
        return {
            "current_agent": "completeness_verification",
            "next_agent": "email_processing",
            "submission_status": "analyzed_incomplete",  # Signal for Email Agent
            "missing_field_info": f"{field_name} ({description})"
        }

# --- Agent 7: Email ---
def email_processing_node(state: UniversalState) -> Dict[str, Any]:
    status = state.get("submission_status")
    monitoring.log_event("INFO", "NODE_ENTRY", f"Entering Email Processing Node (Status: {status})")
    
    if status == "analyzed_complete":
        msg = """
        [Simulated Email Sent]
        Subject: Application Complete!
        Body: Thank you for sending the forms. We have analyzed them and confirmed everything is complete.
        We will proceed to bind your policy.
        """
        print(msg)
        return {"current_agent": "email_processing", "next_agent": None, "submission_status": "bound"}

    elif status == "analyzed_incomplete":
        missing = state.get("missing_field_info", "fields")
        msg = f"""
        [Simulated Email Sent]
        Subject: Action Required - Missing Information
        Body: We analyzed your email. It looks like we are still missing: {missing}.
        Please reply with the completed info or chat with us.
        """
        print(msg)
        return {"current_agent": "email_processing", "next_agent": "conversation_manager", "submission_status": "waiting_correction"}

    # Default: Generate Mock Status Report (Initial Send)
    monitoring.log_event("INFO", "EMAIL", "Generating status report email...")
    
    # Calculate stats
    total_fields = 1500 # Approx
    filled = 15 # Mock
    percent = (filled / total_fields) * 100
    
    msg = f"""
    [Simulated Email Sent]
    To: {state.get('user_id')}@example.com
    Subject: Your Inevo Application Status
    
    Body:
    You have completed {percent:.1f}% of the application.
    Attached are the forms filled so far.
    
    [Attachments: filled_form_125.pdf, ...]
    """
    print(msg) # Verify in console
    
    return {
        "current_agent": "email_processing", 
        "next_agent": None,
        "submission_status": "emailed"
    }

# --- NEW NODE: User Preference (The Crossroads) ---
def user_preference_node(state: UniversalState) -> Dict[str, Any]:
    """
    Asks the user how they want to proceed: Chat, Manual, Email.
    """
    monitoring.log_event("INFO", "NODE_ENTRY", "Entering User Preference Node")
    
    # Check if we have pending input (User answered)
    if state.get("pending_input_value") is not None:
        # Process answer
        ans = str(state.get("pending_input_value")).lower()
        
        # Clear the input so we don't process it again next time
        # (Though we usually transition away)
        
        if "chat" in ans or "continue" in ans or "1" in ans:
             monitoring.log_event("INFO", "CHOICE", "User chose: CHAT")
             # Update phase so we don't come back here!
             return {
                 "current_agent": "user_preference", 
                 "completion_method": "chat", 
                 "next_agent": "conversation_manager",
                 "current_phase": "form_specific",
                 "waiting_for_input": False,
                 "pending_input_value": None
             }
             
        elif "manual" in ans or "download" in ans or "2" in ans:
             monitoring.log_event("INFO", "CHOICE", "User chose: MANUAL")
             # Trigger form generation first so they get the PDF
             return {
                 "current_agent": "user_preference",
                 "completion_method": "manual",
                 "next_agent": "form_population",
                 "waiting_for_input": False,
                 "pending_input_value": None
             }
             
        elif "email" in ans or "send" in ans or "3" in ans:
             monitoring.log_event("INFO", "CHOICE", "User chose: EMAIL")
             return {
                 "current_agent": "user_preference",
                 "completion_method": "email",
                 "next_agent": "form_population",
                 "waiting_for_input": False,
                 "pending_input_value": None
             } # Populate then Email
             
        else:
            # Re-ask if unclear
            monitoring.log_event("WARN", "CHOICE", f"Unclear choice: '{ans}'")
            return {
                "current_agent": "user_preference",
                "conversation_history": [
                    {"role": "assistant", "content": "I didn't catch that. Please type 'Chat', 'Manual', or 'Email'."}
                ],
                "waiting_for_input": True,
                "pending_input_value": None, # Clear the bad input
                "next_agent": None
            }

    # First time entry
    msg = """We've finished the basic information. How would you like to proceed?
    1. **Chat**: Continue filling details here.
    2. **Manual**: Download the partially filled PDF to finish yourself.
    3. **Email**: Have me email you the forms with a status report.
    
    (Type 'Chat', 'Manual', or 'Email')"""
    
    return {
        "current_agent": "user_preference",
        "conversation_history": [
            {"role": "assistant", "content": msg}
        ],
        "waiting_for_input": True,
        "next_agent": None, # Force clear old decisions
        "pending_input_value": None # Ensure we start clean
    }

# This block is assumed to be part of an orchestrator function that processes global interrupts.
# It is placed here based on the provided instruction's context, but would typically reside
# in a higher-level routing function that calls these nodes.


# --- Agent 8: Doc Intel ---
def document_intelligence_node(state: UniversalState) -> Dict[str, Any]:
    monitoring.log_event("INFO", "NODE_ENTRY", "Entering Document Intelligence Node")
    
    attachment = state.get("incoming_email_attachment")
    
    if attachment:
        monitoring.log_event("INFO", "DOC_INTEL", f"Processing attachment: {attachment}")
        
        # 1. Extract
        extracted_data = doc_intel.extract_data_from_fillable_pdf(attachment)
        monitoring.log_event("INFO", "DOC_INTEL", f"Extracted {len(extracted_data)} fields.")
        
        # 2. Update Forms Data
        forms_data = state.get("forms_data")
        if not forms_data: forms_data = FullFormsData()
        
        updates = 0
        for field, value in extracted_data.items():
            # We assume extraction returns normalized keys (named_insured_...)
            # We need to find which form this belongs to.
            # FormManager.update_field searches dynamically!
            # But update_field needs a form_id. 
            # We can try updating 'form_125' default, or iterate common forms.
            
            # Since our extraction map targets common fields, likely form_125
            if FormManager.update_field(forms_data, "form_125", field, value):
                updates += 1
                
        monitoring.log_event("INFO", "DOC_INTEL", f"Updated {updates} fields in Form 125.")
        
        # 3. Route to Verification
        return {
            "current_agent": "document_intelligence",
            "forms_data": forms_data, # Persist updates
            "next_agent": "completeness_verification",
            "incoming_email_attachment": None # Clear queue
        }
        
    return {"current_agent": "document_intelligence"}

# --- Agent 9: Guidewire ---
def guidewire_integration_node(state: UniversalState) -> Dict[str, Any]:
    return {"current_agent": "guidewire_integration", "submission_status": "quoted"}

# --- Agent 10: Monitoring ---
def monitoring_node(state: UniversalState) -> Dict[str, Any]:
    return {"current_agent": "monitoring"}
