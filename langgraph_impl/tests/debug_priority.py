import sys
import os
from pathlib import Path

# Portable: add langgraph_impl root to path
_LANGGRAPH_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LANGGRAPH_ROOT))

from src.generated_schemas import FullFormsData
from src.tools.form_manager import FormManager

def debug_priority():
    print("DEBUG: Initializing Data...")
    data = FullFormsData()
    active_forms = ["form_125"]
    
    print("DEBUG: Checking Form 125 schema...")
    form_125 = data.form_125
    schema = form_125.model_fields
    
    print(f"DEBUG: 'named_insured_full_name_a' in schema? {'named_insured_full_name_a' in schema}")
    print(f"DEBUG: 'policy_section_attached_vehicle_schedule_indicator_a' in schema? {'policy_section_attached_vehicle_schedule_indicator_a' in schema}")
    
    print("DEBUG: Calling FormManager.get_next_missing_field...")
    form_id, field, desc = FormManager.get_next_missing_field(data, active_forms)
    
    print(f"DEBUG: Result -> Form: {form_id}, Field: {field}")
    
    if field == "named_insured_full_name_a":
        print("SUCCESS: Priority worked (Name).")
    elif field == "policy_section_attached_vehicle_schedule_indicator_a":
        print("SUCCESS: Priority worked (Vehicle Trigger).")
    else:
        print(f"FAILURE: Expected priority field, got {field}")

if __name__ == "__main__":
    debug_priority()
