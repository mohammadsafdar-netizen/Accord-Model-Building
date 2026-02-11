import streamlit as st
import time
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from src.graph import define_graph
from src.generated_schemas import FullFormsData

st.set_page_config(page_title="Inevo Agentic Workflow", layout="wide")

# if "graph" not in st.session_state:
st.session_state.graph = define_graph()
    
if "workflow_state" not in st.session_state or st.session_state.workflow_state is None:
    # Initial State with Pydantic models
    st.session_state.workflow_state = {
        "session_id": "session_1",
        "user_id": "user_1",
        "conversation_history": [],
        "current_timestamp": datetime.now(),
        "forms_data": FullFormsData(),  # Pydantic typed state
        "active_form_ids": ["form_125"], # Start with ONLY the root form
        "current_phase": "common_fields",
        "current_agent": "orchestrator",
        "next_agent": None,
        "waiting_for_input": False,
        "validation_errors": [],
        "field_completion_status": {"common_complete": False},
        "required_fields_status": {},
        "pending_input_field": None,
        "pending_input_value": None,
        "validated_value": None,
        "is_input_valid": False,
        "completion_method": None,
        "submission_status": "draft",
        "incoming_email_attachment": None, # Email Queue
        "state_history": []
    }

# ... (Imports remain same) ...

# Display Title and Status
st.title("🏢 Inevo Agentic Form Assistant")

with st.sidebar:
    st.subheader("📊 Control Panel")
    if st.button("Reset Session"):
        st.session_state.workflow_state = None
        st.rerun()
        
    st.divider()
    st.subheader("Simulate Email Reply")
    uploaded_file = st.file_uploader("Attach Filled PDF", type=["pdf"])
    if uploaded_file:
        # Save to temp
        temp_path = f"filled_forms/start_email_reply_{int(time.time())}.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if st.button("Send Email Reply"):
            # Inject Magic Command
            st.session_state.workflow_state["pending_input_value"] = f"email: {temp_path}"
            st.session_state.workflow_state["waiting_for_input"] = False
            st.session_state.workflow_state["conversation_history"].append(
                {"role": "user", "content": f"📨 [Simulated Email] Attached: {uploaded_file.name}"}
            )
            st.rerun()

    st.divider()
    st.subheader("🔧 Debug Info")
    # ... (Debug info) ...

# Display Chat History
for msg in st.session_state.workflow_state.get("conversation_history", []):
    role = msg["role"]
    content = msg["content"]
    if role == "user":
        with st.chat_message("user"):
            st.write(content)
    else:
        with st.chat_message("assistant"):
            st.write(content)

# Handling Workflow Execution
# Stop if waiting for input, or if fully finished (quoted/bound/submitted)
is_waiting = st.session_state.workflow_state.get("waiting_for_input")
status = st.session_state.workflow_state.get("submission_status")
is_finished = status in ["quoted", "bound", "emailed", "submitted"] or st.session_state.workflow_state.get("workflow_complete")

if not is_waiting and not is_finished:
    with st.spinner("Agent is thinking..."):
        config = {"recursion_limit": 50}
        try:
            # Run the graph until it stops (due to waiting or completion)
            events = st.session_state.graph.stream(st.session_state.workflow_state, config=config)
            
            event_count = 0
            for event in events:
                event_count += 1
                for node_name, value in event.items():
                    # Update state
                    if isinstance(value, dict):
                        for k, v in value.items():
                            if k == "conversation_history" and v:
                                # Append instead of overwrite
                                existing = st.session_state.workflow_state.get("conversation_history", [])
                                st.session_state.workflow_state["conversation_history"] = existing + v
                            elif k == "validation_errors" and v:
                                existing = st.session_state.workflow_state.get("validation_errors", [])
                                st.session_state.workflow_state["validation_errors"] = existing + v
                            else:
                                st.session_state.workflow_state[k] = v
                    else:
                        st.session_state.workflow_state[node_name] = value
            
            # If no events occurred, we might be stuck or done. Stop the spinner.
            if event_count == 0:
                 pass 
            else:
                 # State changed, rerun to update UI
                 st.rerun()
            
        except Exception as e:
            st.error(f"Workflow Error: {e}")

# Handling User Input
if st.session_state.workflow_state.get("waiting_for_input"):
    user_input = st.chat_input("Your answer...")
    if user_input:
        # Update state with user input
        st.session_state.workflow_state["pending_input_value"] = user_input
        st.session_state.workflow_state["waiting_for_input"] = False
        
        # Append to history immediately for visual feedback
        st.session_state.workflow_state["conversation_history"].append(
            {"role": "user", "content": user_input}
        )
        
        st.rerun()

# Success State
if status == "quoted":
    st.success(f"Quote Generated! ID: {st.session_state.workflow_state.get('guidewire_submission_id')}")
    st.metric("Quote Amount", value=f"${st.session_state.workflow_state.get('quote_amount')}")
elif status == "bound":
     st.success("🎉 Policy Bound Successfully! Check your email for confirmation.")
elif status == "emailed":
     st.info("Forms have been emailed to you. Please reply with the completed PDF using the sidebar.")
