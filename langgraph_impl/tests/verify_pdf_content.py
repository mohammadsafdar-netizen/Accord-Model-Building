import os
import sys
from pathlib import Path

# Portable: add langgraph_impl root to path (works from any install location)
_LANGGRAPH_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LANGGRAPH_ROOT))

from pypdf import PdfReader

def check_pdf_content(form_id, expected_data):
    path = _LANGGRAPH_ROOT / "filled_forms" / f"filled_form_{form_id}.pdf"
    
    if not path.exists():
        print(f"FAILED: File {path} does not exist.")
        return
        
    print(f"Inspecting {path}...")
    try:
        reader = PdfReader(path)
        fields = reader.get_form_text_fields()
        
        all_match = True
        for key, expected_val in expected_data.items():
            actual = fields.get(key)
            if actual == expected_val:
                 print(f"✅ Match: {key} = '{actual}'")
            else:
                 print(f"❌ Mismatch: {key} Expected '{expected_val}', Got '{actual}'")
                 all_match = False
                 
        if all_match:
            print("SUCCESS: PDF contains correct data.")
        else:
            print("FAILURE: Data mismatch.")
            
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    # Based on user chat history
    expected = {
        "NamedInsured_FullName_A": "safdar", 
        "NamedInsured_Contact_PrimaryEmailAddress_A": "safdar@gmail.com",
        "NamedInsured_Primary_PhoneNumber_A": "8877667888",
        #"Policy_EffectiveDate_A": "2025-12-12", # Format might differ in PDF depending on form
        "CommercialStructure_PhysicalAddress_CityName_A": "faridabad" 
    }
    check_pdf_content("125", expected)
