from typing import Optional, List, Literal
from pydantic import BaseModel, Field

# --- Common Schema (Bare Minimum) ---
class CommonInsuranceData(BaseModel):
    """
    Bare minimum fields required to start a submission across all forms.
    """
    insured_name: Optional[str] = Field(None, description="The full legal name of the insured entity.")
    effective_date: Optional[str] = Field(None, description="The desired policy effective date (YYYY-MM-DD).")
    email: Optional[str] = Field(None, description="Contact email for the insured.")
    business_nature: Optional[str] = Field(None, description="Brief description of the business operations.")
    business_address_city: Optional[str] = Field(None, description="City of the primary business address.")
    naic_code: Optional[str] = Field(None, description="The NAIC code for the business nature.")
    
    # Extended Common Fields
    mailing_address_street: Optional[str] = Field(None, description="Street address for mailing.")
    mailing_address_city: Optional[str] = Field(None, description="City for mailing.")
    mailing_address_state: Optional[str] = Field(None, description="State abbreviation for mailing (e.g. CA).")
    mailing_address_zip: Optional[str] = Field(None, description="Zip/Postal code for mailing.")
    phone_number: Optional[str] = Field(None, description="Primary contact phone number.")
    entity_type: Optional[Literal["Corporation", "LLC", "Individual", "Partnership", "Joint Venture", "Other"]] = Field(None, description="Legal entity structure.")

# --- Specific Form Schemas ---
# In a real app, these would have hundreds of fields. 
# We define a representational subset for the demo logic.

class Acord125Data(BaseModel):
    """Specific fields for ACORD 125 - Commercial Insurance Application"""
    policy_number: Optional[str] = Field(None, description="Existing policy number if applicable.")
    prior_carrier: Optional[str] = Field(None, description="Name of the previous insurance carrier.")
    loss_history_3_years: Optional[bool] = Field(None, description="Any losses in the last 3 years?")

class Acord127Data(BaseModel):
    """Specific fields for ACORD 127 - Business Auto"""
    vehicle_count: Optional[int] = Field(None, description="Number of vehicles to insure.")
    driver_count: Optional[int] = Field(None, description="Number of drivers.")
    radius_of_operations: Optional[str] = Field(None, description="Max radius of operations in miles.")

class Acord129Data(BaseModel):
    """Specific fields for ACORD 129 - Vehicle Schedule"""
    vehicle_vin_list: Optional[List[str]] = Field(default_factory=list, description="List of VINs.")

class Acord163Data(BaseModel):
    """Specific fields for ACORD 163 - Driver Schedule"""
    driver_license_list: Optional[List[str]] = Field(default_factory=list, description="List of Driver License Numbers.")

class AllFormsData(BaseModel):
    """Aggregate of all form data"""
    common: CommonInsuranceData = Field(default_factory=CommonInsuranceData)
    acord_125: Acord125Data = Field(default_factory=Acord125Data)
    acord_127: Acord127Data = Field(default_factory=Acord127Data)
    acord_129: Acord129Data = Field(default_factory=Acord129Data)
    acord_163: Acord163Data = Field(default_factory=Acord163Data)
