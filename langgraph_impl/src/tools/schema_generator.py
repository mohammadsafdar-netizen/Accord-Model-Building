import os
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from pypdf import PdfReader

# Portable: paths relative to langgraph_impl root (this file is in src/tools/)
_LANGGRAPH_ROOT = Path(__file__).resolve().parent.parent.parent
DEMO_DATA_DIR = _LANGGRAPH_ROOT / "demo_data"
OUTPUT_FILE = _LANGGRAPH_ROOT / "src" / "generated_schemas.py"

FORMS = {
    "125": "1. ACORD_0125_CommercialInsurance_Acroform.pdf",
    "127": "2. Acord-127.pdf - BUSINESS AUTO SECTION.pdf",
    "129": "3. ACORD 129 Vehicle Schedule.pdf"
    # 163 excluded for now as it has 0 standard fields
}

def sanitize_field_name(field_name: str) -> str:
    """
    Converts PDF field name to snake_case python identifier.
    Ex: 'NamedInsured_FullName_A' -> 'named_insured_full_name_a'
    """
    # Replace non-alphanumeric with underscore
    clean = re.sub(r'[^a-zA-Z0-9]', '_', field_name)
    # Convert camelCase to snake_case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', clean)
    snake = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    # Ensure no double underscores
    snake = re.sub(r'_+', '_', snake)
    # Ensure valid python identifier start
    if snake[0].isdigit():
        snake = f"field_{snake}"
    return snake

def extract_fields(pdf_path: str) -> Dict[str, Dict[str, str]]:
    """
    Returns {pdf_field_name: {'tooltip': '...', 'python_name': '...'}}
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if not fields:
        return {}
    
    result = {}
    for name, field in fields.items():
        tooltip = str(field.get('/TU', '')) or "No description available."
        clean_tooltip = tooltip.replace('\n', ' ').replace('"', "'")
        
        result[name] = {
            "tooltip": clean_tooltip,
            "python_name": sanitize_field_name(name)
        }
    return result

def generate_python_code(forms_data: Dict[str, Dict[str, Any]]) -> str:
    code = [
        "from typing import Optional, Dict",
        "from pydantic import BaseModel, Field",
        "",
        "# --- AUTO-GENERATED FILE. DO NOT EDIT MANUALLY ---",
        "",
    ]
    
    all_forms_map = {}
    
    for form_id, fields in forms_data.items():
        class_name = f"Acord{form_id}Data"
        code.append(f"class {class_name}(BaseModel):")
        code.append(f"    \"\"\"Auto-generated schema for ACORD {form_id}\"\"\"")
        
        # Field Definitions
        field_mapping = {} # python_name -> pdf_name
        
        sorted_fields = sorted(fields.items(), key=lambda x: x[1]['python_name'])
        
        for pdf_name, info in sorted_fields:
            if not pdf_name: continue
            
            py_name = info['python_name']
            tooltip = info['tooltip']
            
            # Truncate tooltip if too long
            if len(tooltip) > 200:
                tooltip = tooltip[:197] + "..."
                
            code.append(f"    {py_name}: Optional[str] = Field(None, description=\"{tooltip}\")")
            field_mapping[py_name] = pdf_name
            
        # Add internal mapping
        all_forms_map[form_id] = field_mapping
        code.append("")
        
        # Add getter for mapping
        code.append(f"    @classmethod")
        code.append(f"    def get_field_mapping(cls) -> Dict[str, str]:")
        code.append(f"        return {{")
        for k, v in field_mapping.items():
            code.append(f"            \"{k}\": \"{v}\",")
        code.append(f"        }}")
        code.append("")
        code.append("")

    # Aggregate Model
    code.append("class FullFormsData(BaseModel):")
    code.append("    \"\"\"Aggregate schema for all forms\"\"\"")
    for form_id in forms_data.keys():
        code.append(f"    form_{form_id}: {f'Acord{form_id}Data'} = Field(default_factory={f'Acord{form_id}Data'})")
    
    return "\n".join(code)

def main():
    print("Starting Schema Generation...")
    
    collected_data = {}
    
    for form_id, filename in FORMS.items():
        path = DEMO_DATA_DIR / filename
        if not path.exists():
            print(f"Skipping {form_id}: File not found at {path}")
            continue
            
        print(f"Processing Form {form_id}...")
        fields = extract_fields(path)
        print(f"  Found {len(fields)} fields.")
        collected_data[form_id] = fields
        
    code_content = generate_python_code(collected_data)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(code_content)
        
    print(f"Successfully generated schema at {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
