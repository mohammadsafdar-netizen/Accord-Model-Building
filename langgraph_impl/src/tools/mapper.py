from typing import Any, Dict, List, Tuple, Optional

# Mock Schema mappings
COMMON_TO_FORM_MAPPING = {
    "insured_name": {
        "125": "NamedInsured_FullName_A",
        "127": "NamedInsured_FullName_A",
        "129": "NamedInsured_FullName_A",
        "163": "NamedInsured_FullName_A"
    },
    "effective_date": {
        "125": "Policy_EffectiveDate_A",
        "127": "Policy_EffectiveDate_A",
        "129": "Policy_EffectiveDate_A",
        "163": "Policy_EffectiveDate_A"
    },
    "business_nature": {
        "125": "CommercialPolicy_OperationsDescription_A",
        "127": "CommercialPolicy_OperationsDescription_A", 
    },
    "business_address_city": {
        "125": "CommercialStructure_PhysicalAddress_CityName_A",
        "127": "CommercialStructure_PhysicalAddress_CityName_A"
    },
    "naic_code": {
        "125": "NamedInsured_NAICSCode_A",
        "127": "NamedInsured_NAICSCode_A"
    },
    # --- New Fields for Basic Completeness ---
    "mailing_address_street": {
        "125": "NamedInsured_MailingAddress_LineOne_A",
        "127": "NamedInsured_MailingAddress_LineOne_A"
    },
    "mailing_address_city": { # Separate from physical city if needed, but for now map same logic
        "125": "NamedInsured_MailingAddress_CityName_A",
        "127": "NamedInsured_MailingAddress_CityName_A"
    },
    "mailing_address_state": {
        "125": "NamedInsured_MailingAddress_StateOrProvinceCode_A",
        "127": "NamedInsured_MailingAddress_StateOrProvinceCode_A"
    },
    "mailing_address_zip": {
        "125": "NamedInsured_MailingAddress_PostalCode_A",
        "127": "NamedInsured_MailingAddress_PostalCode_A"
    },
    "phone_number": {
        "125": "NamedInsured_Primary_PhoneNumber_A",
        "127": "NamedInsured_Primary_PhoneNumber_A"
    },
    # Checkboxes handled via logic in get_pdf_data_for_form
    "entity_type": {} 
}

def get_pdf_data_for_form(common_data: Dict[str, Any], form_id: str) -> Dict[str, Any]:
    """
    Translates common logical data (e.g. 'insured_name') into 
    specific PDF keys for the given form_id. Handles complex types like Checkboxes.
    """
    pdf_data = {}
    
    # Iterate over common data fields
    for field_key, value in common_data.items():
        # Clean key
        clean_key = field_key.replace("common.", "")
        
        # Special Handler: Entity Type
        if clean_key == "entity_type" and value:
            # Map value (e.g. "Corporation") to specific checkbox key
            entity_map = {
                "corporation": "NamedInsured_LegalEntity_CorporationIndicator_A",
                "llc": "NamedInsured_LegalEntity_LimitedLiabilityCorporationIndicator_A",
                "individual": "NamedInsured_LegalEntity_IndividualIndicator_A",
                "partnership": "NamedInsured_LegalEntity_PartnershipIndicator_A",
                "joint_venture": "NamedInsured_LegalEntity_JointVentureIndicator_A"
            }
            # normalization
            val_norm = str(value).lower().strip()
            # fuzzy match or direct
            target_key = None
            for key_check, pdf_key in entity_map.items():
                if key_check in val_norm:
                    target_key = pdf_key
                    break
            
            if target_key: # Ensure it works for this form_id (mostly 125/127 share these)
                # We assume these keys are consistent across 125/127 as seen in logs
                pdf_data[target_key] = "/On" # Checkbox value is usually /On or /Yes
        
        # Standard Mapping
        elif clean_key in COMMON_TO_FORM_MAPPING:
            form_key = COMMON_TO_FORM_MAPPING[clean_key].get(form_id)
            if form_key:
                pdf_data[form_key] = value
        
        # Fallback check
        elif field_key in COMMON_TO_FORM_MAPPING:
             form_key = COMMON_TO_FORM_MAPPING[field_key].get(form_id)
             if form_key:
                 pdf_data[form_key] = value
                 
    return pdf_data

def map_to_common_schema(field_name: str, validated_value: Any) -> Tuple[Optional[str], Any]:
    """
    Maps input to common/bare minimum schema.
    Simple mock pass-through or dictionary lookup.
    """
    # Logic: field_name might be a raw user input key, we try to standardize it.
    # For this mock tool, we assume field_name IS the common schema key if passed directly, 
    # or we handle aliases.
    aliases = {
        "name": "common.insured_name",
        "start_date": "common.effective_date",
        "description": "common.business_nature",
        "city": "common.business_address_city",
        "naic": "common.naic_code",
        # Map user-friendly keys from LLM prompts
        "insured_name": "common.insured_name",
        "effective_date": "common.effective_date",
        "business_nature": "common.business_nature",
        "business_address_city": "common.business_address_city",
        "naic_code": "common.naic_code"
    }
    
    schema_path = aliases.get(field_name, field_name)
    return schema_path, validated_value

def map_common_field_to_all_forms(common_field_path: str, value: Any) -> Dict[str, str]:
    """
    Maps common field to all ACORD forms simultaneously.
    """
    mappings = COMMON_TO_FORM_MAPPING.get(common_field_path)
    if not mappings:
        return {}
    
    result = {}
    for form, path in mappings.items():
        # Using form_id directly as key prefix not needed if we fill specific templates known by ID
        # But our fill function takes a dict key.
        # Let's return just the path->value map, but split by form?
        # The form_population tool iterates forms.
        # Actually, let's return a dict keyed by form_id containing the dict for that form?
        # Existing code: result[f"{form}_data.{path}"] = value
        # This seems to imply a flattened structure or specific consumer.
        # Let's check consumer: form_populator.py likely expects just the PDF key for THAT form.
        # But this function returns a single dict for ALL forms?
        # Let's return {path: value} and assume we only support 125 for now or 
        # we need to know which form we are filling.
        # The current implementation of form_population logic seems simple.
        # Let's checking `form_population.py` logic again if needed.
        # It calls `fill_pdf_form_field(..., data_dict)`.
        # So `data_dict` should have the PDF KEY directly.
        
        # If we have multiple forms, we might have collisions if keys overlap but mean different things?
        # For now, let's just return key=value.
        result[path] = value
        
    return result

def convert_to_schema_type(value: Any, target_type: str) -> Tuple[Any, bool]:
    """
    Converts validated input to schema-required type.
    """
    try:
        if target_type == "string":
            return str(value) if value is not None else None, True
        if target_type == "int":
            return int(value), True
        return value, True # Fallback
    except Exception:
        return value, False

# --- LLM Extraction ---
# Imports moved inside function to avoid heavy dependency at module level

def extract_fields_from_text(text: str, current_schema_keys: List[str]) -> Dict[str, Any]:
    """
    Uses LLM to extract schema fields from natural language text.
    """
    import os
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.exceptions import OutputParserException
    import json

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {}
        
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=api_key)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a data extraction assistant. Extract information from the user's message that matches the provided schema keys. Return JSON only. Keys must be exactly as provided. If a value is not found, do not include the key. Schema Keys: {keys}"),
        ("human", "{text}")
    ])
    
    chain = prompt | llm | JsonOutputParser()
    
    try:
        return chain.invoke({"text": text, "keys": current_schema_keys})
    except (OutputParserException, json.JSONDecodeError):
        # Fallback: return empty
        return {}
