from typing import Any, List, Optional, Tuple, Dict
from src.generated_schemas import FullFormsData

class FormManager:
    """
    Manages the logic for traversing and filling the FullFormsData structure.
    """
    
    @staticmethod
    def get_common_fields_list() -> List[str]:
        return [
             "named_insured_full_name_a",
             "named_insured_contact_primary_email_address_a",
             "named_insured_primary_phone_number_a",
             "policy_effective_date_a", 
             "commercial_policy_operations_description_a",
             "named_insured_mailing_address_line_one_a",
             "named_insured_mailing_address_city_name_a",
             "named_insured_mailing_address_state_or_province_code_a"
        ]
    
    @staticmethod
    def get_form_priority() -> List[str]:
        """
        Return the order in which forms should be filled.
        Dynamically discovers fields starting with 'form_' in FullFormsData.
        """
        # Dynamic Discovery
        all_fields = FullFormsData.model_fields.keys()
        form_keys = [k for k in all_fields if k.startswith("form_")]
        
        # Sort numerically if possible (form_125 < form_127)
        def sort_key(k):
            try:
                # Extract number: form_125 -> 125
                return int(k.split("_")[1])
            except:
                return 99999 # Put non-numbered forms last
        
        return sorted(form_keys, key=sort_key)

    # --- SECTION DEFINITIONS ---
    # These define the logical flow of questions for the ACORD forms.
    
    SECTION_ORDER_125 = [
        # 1. Applicant Info (Strict Common)
        "named_insured_full_name_a",
        "named_insured_contact_primary_email_address_a",
        "named_insured_primary_phone_number_a",
        "named_insured_mailing_address_line_one_a",
        "named_insured_mailing_address_city_name_a",
        "named_insured_mailing_address_state_or_province_code_a",
        "policy_effective_date_a", 
        "commercial_policy_operations_description_a",

        # 2. Status of Business
        "named_insured_legal_entity_type_code_a",
        "named_insured_business_start_date_a",
        "audit_contact_primary_phone_number_a",
        "audit_contact_primary_email_address_a",

        # 3. General Policy Info (Specific)
        "policy_expiration_date_a", 
        "policy_section_attached_vehicle_schedule_indicator_a",
        "policy_section_attached_driver_schedule_indicator_a",
        "policy_section_attached_applicable_state_supplement_indicator_a",
        "prior_policy_prior_carrier_name_a",
        "prior_policy_prior_policy_number_a",

        # 4. Additional Interests
        "additional_interest_interest_rank_number_a",
        "additional_interest_interest_name_a",
        "additional_interest_interest_type_code_a",
        "additional_interest_interest_address_line_one_a",
        "additional_interest_interest_city_name_a",
        "additional_interest_interest_state_or_province_code_a"
    ]

    SECTION_ORDER_127 = [
        # 1. Driver Info
        "driver_info_driver_1_full_name_a",
        "driver_info_driver_1_birth_date_a",
        "driver_info_driver_1_license_number_a",
        "driver_info_driver_1_license_state_province_code_a",
        "driver_info_driver_1_hire_date_a",
        "driver_info_driver_1_gender_code_a",
        
        # 2. Vehicle Info
        "vehicle_info_vehicle_1_model_year_a",
        "vehicle_info_vehicle_1_manufacturer_name_a",
        "vehicle_info_vehicle_1_model_name_a",
        "vehicle_info_vehicle_1_vin_a",
        "vehicle_info_vehicle_1_cost_new_amount_a",
        "vehicle_info_vehicle_1_body_type_code_a",
        
        # 3. Coverages
        "coverage_liab_limit_a",
        "coverage_medical_payments_limit_a",
        "coverage_uninsured_motorist_limit_a"
    ]

    @staticmethod
    def get_next_missing_common_field(forms_data: FullFormsData) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Strictly checks only the 8 common fields."""
        common = FormManager.get_common_fields_list()
        form_attr = "form_125"
        form_model = getattr(forms_data, form_attr, None)
        if not form_model: return (None, None, None)
        
        schema = type(form_model).model_fields
        for name in common:
            # Robust check for missing data
            val = getattr(form_model, name, None)
            if val is None or str(val).strip() in ("", "None", "nan", "[]"):
                # Field IS missing
                description = schema[name].description if name in schema else name
                return (form_attr, name, description)
        return (None, None, None)

    @staticmethod
    def get_next_missing_field(forms_data: FullFormsData, active_form_ids: List[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Scans forms in priority order using Section Ordering and returns the first missing field.
        Returns: (form_id, field_name, field_description)
        """
        priority = FormManager.get_form_priority()
        
        # Filter by active forms if provided
        if active_form_ids:
            priority = [f for f in priority if f in active_form_ids]
        
        # 1. Iterate through Active Forms in Priority Order (125 -> 127 -> ...)
        for form_attr in priority:
            form_model = getattr(forms_data, form_attr, None)
            if not form_model: continue
            
            schema = type(form_model).model_fields
            
            # Determine Section List based on Form ID
            ordered_fields = []
            if "125" in form_attr:
                ordered_fields = FormManager.SECTION_ORDER_125
            elif "127" in form_attr:
                 ordered_fields = FormManager.SECTION_ORDER_127
            
            # 2. Check Explicitly Ordered Fields FIRST (Section-Wise)
            for name in ordered_fields:
                if name in schema:
                    value = getattr(form_model, name)
                    if value is None or value == "":
                         description = schema[name].description or name
                         return (form_attr, name, description)
            
            # 3. Fallback: Check Remaining Fields (that were not in the explicit list)
            # This ensures we don't miss anything even if the list is incomplete.
            for name, field_info in schema.items():
                if name in ordered_fields: continue # Already checked
                
                value = getattr(form_model, name)
                if value is None or value == "":
                    # Heuristic: Prioritize primary fields (_a) to avoid obscure repeats
                    if name.endswith("_a") or not any(name.endswith(f"_{x}") for x in "bcdefghijklmnopqrstuvwxyz"):
                        description = field_info.description or name
                        return (form_attr, name, description)
                        
        return (None, None, None)

    @staticmethod
    def update_field(forms_data: FullFormsData, form_id: str, field_name: str, value: Any) -> bool:
        """
        Updates a specific field AND propagates to all other forms with same field name.
        """
        # 1. Update Target
        form_model = getattr(forms_data, form_id, None)
        if not form_model or not hasattr(form_model, field_name):
            return False
            
        setattr(form_model, field_name, str(value)) 
        
        # 2. Data Propagation (Smart Filling)
        # Check all OTHER active forms for the same field name
        all_forms = FormManager.get_form_priority() # Get all potential forms
        for other_form_id in all_forms:
            if other_form_id == form_id: continue
            
            other_model = getattr(forms_data, other_form_id, None)
            if other_model and hasattr(other_model, field_name):
                # Only update if empty? Or overwrite to keep sync?
                # "Single Source of Truth" implies we should keep them in sync.
                setattr(other_model, field_name, str(value))
                # We could log this propagation if we had the logger here
                
        return True

    @staticmethod
    def get_active_form_id(forms_data: FullFormsData, active_form_ids: List[str] = None) -> Optional[str]:
        """Returns the ID of the form currently being worked on."""
        form, field, _ = FormManager.get_next_missing_field(forms_data, active_form_ids)
        return form
