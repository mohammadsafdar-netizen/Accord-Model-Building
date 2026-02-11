import sys
import os
from pathlib import Path

# Portable: add langgraph_impl root to path
_LANGGRAPH_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LANGGRAPH_ROOT))

from src.generated_schemas import FullFormsData
from src.tools.form_manager import FormManager

def test_conditional_activation():
    print("Testing Conditional Activation...")
    
    # 1. Setup Data
    data = FullFormsData()
    active_forms = ["form_125"] # Only 125 active initially
    
    # 2. Check 127 is hidden
    priority = FormManager.get_form_priority()
    filtered = [f for f in priority if f in active_forms]
    print(f"Initially Visible Forms: {filtered}")
    assert "form_127" not in filtered
    
    # 3. Simulate Trigger in Nodes.py Logic
    # We are simulating the logic we wrote in schema_mapper_node
    TRIGGER_FIELD = "policy_section_attached_vehicle_schedule_indicator_a"
    val = "Yes"
    
    print(f"User inputs '{val}' for {TRIGGER_FIELD}...")
    
    # Update Data
    FormManager.update_field(data, "form_125", TRIGGER_FIELD, val)
    
    # Update Active Forms (Simulate Node Logic)
    if val.lower() in ["yes", "true"]:
        if "form_127" not in active_forms:
            active_forms.append("form_127")
            
    # 4. Check 127 is now visible
    filtered_new = [f for f in priority if f in active_forms]
    print(f"Now Visible Forms: {filtered_new}")
    
    assert "form_127" in filtered_new
    print("✅ Success: Form 127 activated!")

if __name__ == "__main__":
    test_conditional_activation()
