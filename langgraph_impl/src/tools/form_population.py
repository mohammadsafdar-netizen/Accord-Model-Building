import os
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from typing import Dict, List, Any
import src.tools.mapper as mapper

# Portable: paths relative to langgraph_impl root
_LANGGRAPH_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = _LANGGRAPH_ROOT / "filled_forms"

def fill_pdf_form_field(pdf_path: str, data_dict: Dict[str, Any], output_filename: str) -> str:
    """
    Writes data to PDF form fields using pypdf and saves to output_dir.
    Returns path to filled PDF.
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    # Copy all pages
    writer.append(reader)
    
    # Update fields on the writer (which affects all pages appended so far if they share the root form)
    # pypdf's update_page_form_field_values is convenient for this.
    # It takes the first page (usually where the form definition links are) or we can just iterate.
    # Actually, the most robust way in pypdf for AcroForms is straightforward:
    
    writer.update_page_form_field_values(
        writer.pages[0], 
        data_dict,
        auto_regenerate=True # Critical for visibility!
    )
    
    # Ensure output dir exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_path = OUTPUT_DIR / output_filename
    with open(output_path, "wb") as f:
        writer.write(f)

    return str(output_path)

def read_pdf_form_fields(pdf_path: str) -> Dict[str, Any]:
    """
    Reads all fillable fields from PDF using pypdf.
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_form_text_fields() # Returns dict of {key: value}
    return fields if fields else {}

def extract_pdf_field_tooltips(pdf_path: str) -> Dict[str, Dict[str, str]]:
    """
    Extracts field tooltips/descriptions from PDF form fields.
    Returns: {field_name: {"tooltip": "...", "mapping_name": "..."}}
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    
    if not fields:
        return {}
    
    result = {}
    for name, field in fields.items():
        tooltip = field.get('/TU', '')  # TU = Tool Tip / User-facing description
        mapping_name = field.get('/TM', '')  # TM = Mapping Name (alternate field name)
        
        if tooltip or mapping_name:
            result[name] = {
                "tooltip": str(tooltip) if tooltip else "",
                "mapping_name": str(mapping_name) if mapping_name else ""
            }
    
    return result

def get_form_template(form_type: str) -> str:
    """
    Retrieves blank ACORD form template path.
    """
    import re
    base_path = _LANGGRAPH_ROOT / "demo_data"

    # Dynamic Scan
    if not base_path.exists():
        return str(base_path / "not_found.pdf")

    for filename in os.listdir(base_path):
        # Match "ACORD 125", "ACORD_125", "Acord-125" etc
        if re.search(f"acord[\\s_\\-]*{form_type}", filename, re.IGNORECASE):
            return str(base_path / filename)

    # Fallback to original map if scan fails (legacy support)
    mapping = {
        "125": base_path / "1. ACORD_0125_CommercialInsurance_Acroform.pdf",
        "127": base_path / "2. Acord-127.pdf - BUSINESS AUTO SECTION.pdf",
        "129": base_path / "3. ACORD 129 Vehicle Schedule.pdf",
        "163": base_path / "6. ACORD_163_DriverSchedule.pdf"
    }
    return str(mapping.get(form_type, base_path / "unknown_form.pdf"))

def get_all_form_tooltips() -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Extracts tooltips from all ACORD forms.
    Returns: {form_id: {field_name: {"tooltip": "...", "mapping_name": "..."}}}
    """
    all_tooltips = {}
    for form_id in ["125", "127", "129", "163"]:
        path = get_form_template(form_id)
        if os.path.exists(path):
            try:
                all_tooltips[form_id] = extract_pdf_field_tooltips(path)
            except Exception as e:
                print(f"Error extracting tooltips from form {form_id}: {e}")
                all_tooltips[form_id] = {}
    return all_tooltips

# Mapping from common schema field names to PDF field names
COMMON_TO_PDF_FIELD_MAP = {
    "insured_name": "NamedInsured_FullName_A",
    "effective_date": "Policy_EffectiveDate_A",
    "email": "NamedInsured_Contact_PrimaryEmailAddress_A",
    "business_nature": "CommercialPolicy_OperationsDescription_A",
    "business_address_city": "CommercialStructure_PhysicalAddress_CityName_A",
    "naic_code": "NamedInsured_NAICSCode_A",
    "mailing_address_street": "NamedInsured_MailingAddress_LineOne_A",
    "mailing_address_city": "NamedInsured_MailingAddress_CityName_A",
    "mailing_address_state": "NamedInsured_MailingAddress_StateOrProvinceCode_A",
    "mailing_address_zip": "NamedInsured_MailingAddress_PostalCode_A",
    "phone_number": "NamedInsured_Primary_PhoneNumber_A",
}

# Cache for tooltips
_TOOLTIP_CACHE = None

def get_tooltip_for_field(common_field_name: str) -> str:
    """
    Gets the PDF tooltip for a common schema field.
    Uses ACORD 125 as the primary source since it has the most comprehensive tooltips.
    """
    global _TOOLTIP_CACHE
    
    if _TOOLTIP_CACHE is None:
        # Load tooltips from ACORD 125 (most comprehensive)
        path = get_form_template("125")
        if os.path.exists(path):
            _TOOLTIP_CACHE = extract_pdf_field_tooltips(path)
        else:
            _TOOLTIP_CACHE = {}
    
    # Get the PDF field name for this common field
    pdf_field_name = COMMON_TO_PDF_FIELD_MAP.get(common_field_name)
    if not pdf_field_name:
        return ""
    
    # Look up the tooltip
    field_info = _TOOLTIP_CACHE.get(pdf_field_name, {})
    return field_info.get("tooltip", "")

def auto_fill_common_fields_all_forms(common_data: Dict, form_ids: List[str]) -> Dict[str, str]:
    """
    Fills common fields across all specified forms simultaneously.
    Returns map of form_id -> filled_pdf_path
    """
    results = {}
    for form_id in form_ids:
        path = get_form_template(form_id)
        if os.path.exists(path):
            try:
                # TRANSLATE KEYS HERE!
                pdf_data = mapper.get_pdf_data_for_form(common_data, form_id)
                
                out_name = f"filled_form_{form_id}.pdf"
                filled_path = fill_pdf_form_field(path, pdf_data, out_name)
                results[form_id] = filled_path
            except Exception as e:
                print(f"Error filling form {form_id}: {e}")
                results[form_id] = "Error"
    return results

def fill_forms_from_full_data(full_data: Any) -> Dict[str, str]:
    """
    Fills forms using the generated FullFormsData structure.
    Dynamically introspects fields to find corresponding schemas.
    """
    # No more manual imports of specific forms (125, 127, etc)
    results = {}
    
    # Introspect FullFormsData instance
    for field_name, model_field in full_data.model_fields.items():
        if not field_name.startswith("form_"):
            continue
            
        # Get the actual data object (e.g., Acord125Data instance)
        form_instance = getattr(full_data, field_name)
        if not form_instance:
            continue
            
        # Extract ID "125" from "form_125"
        form_id = field_name.split("_")[1]
        
        # Get the class of the instance (Acord125Data)
        cls = type(form_instance)
        
        # Check if it has the mapping method
        if not hasattr(cls, 'get_field_mapping'):
            continue
            
        # Get data map: {python_name: value}
        data_map = form_instance.model_dump(exclude_none=True)
        if not data_map: continue
        
        # Get Key Map: {python_name: pdf_name}
        key_map = cls.get_field_mapping()
        
        # create PDF payload
        pdf_payload = {}
        for py_key, val in data_map.items():
            pdf_key = key_map.get(py_key)
            if pdf_key:
                pdf_payload[pdf_key] = val
        
        # Fill
        path = get_form_template(form_id)
        if os.path.exists(path) and "unknown_form" not in path:
             out_name = f"filled_form_{form_id}.pdf"
             try:
                 res = fill_pdf_form_field(path, pdf_payload, out_name)
                 results[form_id] = res
             except Exception as e:
                 print(f"Failed to fill {form_id}: {e}")
                 results[form_id] = "Error: " + str(e)
        else:
            results[form_id] = f"Skipped (Template not found for {form_id})"

    return results
