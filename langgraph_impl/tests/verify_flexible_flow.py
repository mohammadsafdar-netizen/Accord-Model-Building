import sys
import os
from pathlib import Path

# Portable: add langgraph_impl root to path
_LANGGRAPH_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LANGGRAPH_ROOT))

from src.generated_schemas import FullFormsData
from src.state import UniversalState
from src.tools.form_manager import FormManager
from src.tools.orchestrator import route_to_agent
from src.nodes import conversation_manager_node

# Mock Env
os.environ["GROQ_API_KEY"] = "mock_key"

def test_flexible_workflow():
    print("TEST: Flexible Workflow Simulation")
    
    # 1. Setup State: Emulate end of common fields
    data = FullFormsData()
    # Fill all common fields manually
    common_fields = FormManager.get_common_fields_list()
    for field in common_fields:
        FormManager.update_field(data, "form_125", field, "Mock Value")
        
    state = UniversalState(
        forms_data=data,
        active_form_ids=["form_125"],
        current_phase="common_fields",
        field_completion_status={},
        conversation_history=[]
    )
    
    # 2. Run Conversation Manager -> Should detect completion
    print("Running Conversation Manager (Expect transition to common_completed)...")
    res = conversation_manager_node(state)
    
    new_phase = res.get("current_phase")
    print(f"Result Phase: {new_phase}")
    
    if new_phase != "common_completed":
        print("FAILURE: Did not transition to common_completed")
        return
        
    # 3. Test Orchestrator Routing
    print("Testing Orchestrator Routing for 'common_completed'...")
    next_agent, reason = route_to_agent("common_completed", {}, []) # simplified args
    print(f"Next Agent: {next_agent} ({reason})")
    
    if next_agent != "user_preference":
         print("FAILURE: Orchestrator did not route to user_preference")
         return
         
    print("✅ SUCCESS: Workflow logic verified.")

if __name__ == "__main__":
    test_flexible_workflow()
