"""
Interactive CLI for Insurance Form Automation System.
Provides a chat-based interface for filling ACORD forms.
"""
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # Load .env file

from src.graph import define_graph
from src.generated_schemas import FullFormsData
from src.tools import monitoring

def print_banner():
    print("\n" + "="*60)
    print("🏢 INEVO INSURANCE FORM ASSISTANT")
    print("="*60)
    print("Type your responses to fill out the insurance forms.")
    print("Commands: 'quit' to exit, 'status' to see current data")
    print("="*60 + "\n")

def print_state_summary(state):
    """Print a summary of current form data."""
    forms_data = state.get("forms_data")
    if forms_data:
        # Show form 125 data as example
        data = forms_data.form_125.model_dump(exclude_none=True)
        if data:
            print("\n📋 Current Form 125 Data:")
            for k, v in data.items():
                print(f"   • {k}: {v}")
        else:
            print("\n📋 No data collected yet.")
    print(f"📍 Phase: {state.get('current_phase', 'unknown')}")
    print(f"📊 Status: {state.get('submission_status', 'draft')}\n")

def main():
    graph = define_graph()
    
    # Initial State with Pydantic models
    state = {
        "session_id": "interactive_session_1",
        "user_id": "user_cli",
        "conversation_history": [],
        "current_timestamp": datetime.now(),
        "forms_data": FullFormsData(),
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
        "state_history": []
    }
    
    print_banner()
    
    config = {"recursion_limit": 100}
    
    while True:
        # Run graph until it stops (waiting for input or completion)
        try:
            for output in graph.stream(state, config=config):
                for key, value in output.items():
                    # Merge updates into state
                    state.update(value)
                    
                    # Print bot messages
                    if "conversation_history" in value and value["conversation_history"]:
                        for msg in value["conversation_history"]:
                            if msg.get("role") == "assistant":
                                print(f"\n🤖 Assistant: {msg['content']}")
                    
                    # Check for completion
                    if state.get("submission_status") == "quoted":
                        print("\n" + "="*60)
                        print("✅ QUOTE GENERATED SUCCESSFULLY!")
                        print(f"   Quote ID: {state.get('guidewire_submission_id')}")
                        print(f"   Amount: ${state.get('quote_amount')}")
                        print("="*60)
                        print_state_summary(state)
                        return
                        
        except Exception as e:
            if "recursion" in str(e).lower():
                pass  # Expected when waiting for input
            else:
                print(f"⚠️ Error: {e}")
        
        # Check if waiting for user input
        if state.get("waiting_for_input"):
            try:
                user_input = input("\n👤 You: ").strip()
            except EOFError:
                break
                
            # Handle special commands
            if user_input.lower() == "quit":
                print("\n👋 Goodbye!")
                break
            elif user_input.lower() == "status":
                print_state_summary(state)
                continue
            elif not user_input:
                continue
                
            # Update state with user input
            state["pending_input_value"] = user_input
            state["waiting_for_input"] = False
            
            # Add to conversation history
            state["conversation_history"] = state.get("conversation_history", []) + [
                {"role": "user", "content": user_input}
            ]
            
            monitoring.log_event("INFO", "USER_INPUT", f"User provided: {user_input[:50]}...")
        else:
            # If not waiting and not complete, something is wrong
            if state.get("next_agent") is None and state.get("submission_status") != "quoted":
                print("\n⚠️ Workflow ended unexpectedly.")
                print_state_summary(state)
                break

if __name__ == "__main__":
    main()
