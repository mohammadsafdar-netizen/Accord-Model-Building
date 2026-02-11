from typing import Dict, List, Any, Tuple
from pypdf import PdfReader
import os

# Mapping for Reverse Lookup (PDF Field -> Schema Field)
# Use the invert of what's in form_population.py
PDF_TO_COMMON_MAP = {
    "NamedInsured_FullName_A": "named_insured_full_name_a",
    "Policy_EffectiveDate_A": "policy_effective_date_a",
    "NamedInsured_Contact_PrimaryEmailAddress_A": "named_insured_contact_primary_email_address_a",
    "CommercialPolicy_OperationsDescription_A": "commercial_policy_operations_description_a",
    "CommercialStructure_PhysicalAddress_CityName_A": "named_insured_mailing_address_city_name_a", # Approximate mapping based on usage
    "NamedInsured_NAICSCode_A": "named_insured_naics_code_a",
    "NamedInsured_MailingAddress_LineOne_A": "named_insured_mailing_address_line_one_a",
    "NamedInsured_MailingAddress_CityName_A": "named_insured_mailing_address_city_name_a",
    "NamedInsured_MailingAddress_StateOrProvinceCode_A": "named_insured_mailing_address_state_or_province_code_a",
    "NamedInsured_MailingAddress_PostalCode_A": "named_insured_mailing_address_postal_code_a",
    "NamedInsured_Primary_PhoneNumber_A": "named_insured_primary_phone_number_a",
    "PolicySection_AttachedVehicleScheduleIndicator_A": "policy_section_attached_vehicle_schedule_indicator_a"
}

def perform_ocr(image_path: str) -> Tuple[str, float]:
    """
    Mock OCR.
    """
    return f"Extracted text from {image_path}", 0.95

def extract_data_from_fillable_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extracts data from a fillable PDF and maps it to internal schema fields.
    """
    if not os.path.exists(pdf_path):
        return {}
        
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_form_text_fields() # {PDF_Key: Value}
        
        normalized_data = {}
        
        if not fields:
            return {}

        # 1. Map known common fields
        for pdf_key, value in fields.items():
            if not value: continue
            
            # Try exact match in map
            if pdf_key in PDF_TO_COMMON_MAP:
                schema_key = PDF_TO_COMMON_MAP[pdf_key]
                normalized_data[schema_key] = value
                
            # Heuristic for specific forms (Acord 127 etc)
            # If we had a massive reverse map, we'd use it.
            # For now, we rely on the Common Fields for the "Analysis"
            
        return normalized_data
        
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return {}

def extract_form_fields(document_image: str, form_type: str) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """
    Mock extracting fields from image (Legacy/Vision).
    """
    # ... legacy mock ...
    return {}, {}

def detect_form_type(document_path: str) -> Tuple[str, str, float]:
    """
    Identifies form type.
    """
    if "125" in document_path: return "125", "2023", 0.99
    if "127" in document_path: return "127", "2023", 0.99
    return "unknown", "0", 0.0

def validate_extracted_data(extracted: Dict, form_type: str) -> Tuple[bool, List, Dict]:
    # Mock pass
    return True, [], extracted
