"""Entity-to-field mapping for ACORD Form 127 (Business Auto Section).

Maps drivers and vehicles to Form 127 PDF widget field names.
Drivers use suffixes A-M (up to 13), vehicles use suffixes A-D (up to 4).
Also maps additional interests (lienholders) and vehicle coverage indicators.
"""

from typing import Dict
from Custom_model_fa_pf.entity_schema import CustomerSubmission

DRIVER_SUFFIXES = list("ABCDEFGHIJKLM")  # 13 drivers max
VEHICLE_SUFFIXES = list("ABCD")           # 4 vehicles max

# Vehicle use type → indicator field base name
VEHICLE_USE_INDICATORS = {
    "commercial": "Vehicle_Use_CommercialIndicator",
    "service": "Vehicle_Use_ServiceIndicator",
    "retail": "Vehicle_Use_RetailIndicator",
    "pleasure": "Vehicle_Use_PleasureIndicator",
    "farm": "Vehicle_Use_FarmIndicator",
    "for_hire": "Vehicle_Use_ForHireIndicator",
}


def map_fields(submission: CustomerSubmission) -> Dict[str, str]:
    """Map extracted entities to Form 127 field names.

    Args:
        submission: Extracted customer submission data

    Returns:
        Dict of field_name -> value for Form 127
    """
    fields: Dict[str, str] = {}

    # --- Header fields ---
    biz = submission.business
    if biz and biz.business_name:
        fields["NamedInsured_FullName_A"] = biz.business_name

    pol = submission.policy
    if pol:
        if pol.effective_date:
            fields["Policy_EffectiveDate_A"] = pol.effective_date
        if pol.policy_number:
            fields["Policy_PolicyNumberIdentifier_A"] = pol.policy_number

    prod = submission.producer
    if prod:
        if prod.agency_name:
            fields["Producer_FullName_A"] = prod.agency_name
        if prod.producer_code:
            fields["Producer_CustomerIdentifier_A"] = prod.producer_code
        if prod.license_number:
            fields["Producer_StateLicenseIdentifier_A"] = prod.license_number

    # --- Drivers ---
    for i, driver in enumerate(submission.drivers[:len(DRIVER_SUFFIXES)]):
        sfx = f"_{DRIVER_SUFFIXES[i]}"

        first = driver.get_first_name()
        last = driver.get_last_name()
        if first:
            fields[f"Driver_GivenName{sfx}"] = first
        if last:
            fields[f"Driver_Surname{sfx}"] = last
        if driver.middle_initial:
            fields[f"Driver_OtherGivenNameInitial{sfx}"] = driver.middle_initial
        if driver.dob:
            fields[f"Driver_BirthDate{sfx}"] = driver.dob
        if driver.sex:
            fields[f"Driver_GenderCode{sfx}"] = driver.sex
        if driver.marital_status:
            fields[f"Driver_MaritalStatusCode{sfx}"] = driver.marital_status
        if driver.license_number:
            fields[f"Driver_LicenseNumberIdentifier{sfx}"] = driver.license_number
        if driver.license_state:
            fields[f"Driver_LicensedStateOrProvinceCode{sfx}"] = driver.license_state
        if driver.years_experience:
            fields[f"Driver_ExperienceYearCount{sfx}"] = str(driver.years_experience)
        if driver.licensed_year:
            fields[f"Driver_LicensedYear{sfx}"] = str(driver.licensed_year)
        if driver.hire_date:
            fields[f"Driver_HiredDate{sfx}"] = driver.hire_date

        # Driver mailing address
        d_addr = driver.mailing_address
        if d_addr:
            if d_addr.city:
                fields[f"Driver_MailingAddress_CityName{sfx}"] = d_addr.city
            if d_addr.state:
                fields[f"Driver_MailingAddress_StateOrProvinceCode{sfx}"] = d_addr.state
            if d_addr.zip_code:
                fields[f"Driver_MailingAddress_PostalCode{sfx}"] = d_addr.zip_code

    # --- Vehicles ---
    for i, vehicle in enumerate(submission.vehicles[:len(VEHICLE_SUFFIXES)]):
        sfx = f"_{VEHICLE_SUFFIXES[i]}"

        if vehicle.vin:
            fields[f"Vehicle_VINIdentifier{sfx}"] = vehicle.vin
        if vehicle.year:
            fields[f"Vehicle_ModelYear{sfx}"] = str(vehicle.year)
        if vehicle.make:
            fields[f"Vehicle_ManufacturersName{sfx}"] = vehicle.make
        if vehicle.model:
            fields[f"Vehicle_ModelName{sfx}"] = vehicle.model
        if vehicle.body_type:
            fields[f"Vehicle_BodyCode{sfx}"] = vehicle.body_type
        if vehicle.gvw:
            fields[f"Vehicle_GrossVehicleWeight{sfx}"] = str(vehicle.gvw)
        if vehicle.cost_new:
            fields[f"Vehicle_CostNewAmount{sfx}"] = str(vehicle.cost_new)
        if vehicle.radius_of_travel:
            fields[f"Vehicle_RadiusOfUse{sfx}"] = str(vehicle.radius_of_travel)
        if vehicle.farthest_zone:
            fields[f"Vehicle_FarthestZoneCode{sfx}"] = vehicle.farthest_zone

        # Vehicle garaging address
        g_addr = vehicle.garaging_address
        if g_addr:
            if g_addr.line_one:
                fields[f"Vehicle_PhysicalAddress_LineOne{sfx}"] = g_addr.line_one
            if g_addr.city:
                fields[f"Vehicle_PhysicalAddress_CityName{sfx}"] = g_addr.city
            if g_addr.state:
                fields[f"Vehicle_PhysicalAddress_StateOrProvinceCode{sfx}"] = g_addr.state
            if g_addr.zip_code:
                fields[f"Vehicle_PhysicalAddress_PostalCode{sfx}"] = g_addr.zip_code

        # Vehicle use type indicator
        if vehicle.use_type:
            use_lower = vehicle.use_type.lower()
            for use_key, field_base in VEHICLE_USE_INDICATORS.items():
                if use_key in use_lower:
                    fields[f"{field_base}{sfx}"] = "1"
                    break

        # Vehicle type indicators
        if vehicle.body_type:
            bt = vehicle.body_type.upper()
            if bt in ("PP", "SD", "CV"):
                # Private Passenger
                fields[f"Vehicle_VehicleType_PrivatePassengerIndicator{sfx}"] = "1"
            elif bt in ("PK", "VN", "TT", "TR", "BU", "TK"):
                # Commercial
                fields[f"Vehicle_VehicleType_CommercialIndicator{sfx}"] = "1"

    # --- Coverage Indicators per vehicle ---
    for cov in submission.coverages:
        if not cov.coverage_type:
            continue
        ct = cov.coverage_type.lower().replace(" ", "_")
        num_vehicles = min(len(submission.vehicles), len(VEHICLE_SUFFIXES))
        for j in range(max(1, num_vehicles)):
            sfx = f"_{VEHICLE_SUFFIXES[j]}"
            if "liability" in ct or "csl" in ct:
                fields[f"Vehicle_Coverage_LiabilityIndicator{sfx}"] = "1"
            if "collision" in ct:
                fields[f"Vehicle_Coverage_CollisionIndicator{sfx}"] = "1"
                if cov.deductible:
                    fields[f"Vehicle_Collision_DeductibleAmount{sfx}"] = str(cov.deductible)
            if "comprehensive" in ct:
                fields[f"Vehicle_Coverage_ComprehensiveIndicator{sfx}"] = "1"
                if cov.deductible:
                    fields[f"Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount{sfx}"] = str(cov.deductible)
            if "medical" in ct:
                fields[f"Vehicle_Coverage_MedicalPaymentsIndicator{sfx}"] = "1"
            if "uninsured" in ct and "under" not in ct:
                fields[f"Vehicle_Coverage_UninsuredMotoristsIndicator{sfx}"] = "1"
            if "underinsured" in ct:
                fields[f"Vehicle_Coverage_UnderinsuredMotoristsIndicator{sfx}"] = "1"
            if "towing" in ct:
                fields[f"Vehicle_Coverage_TowingAndLabourIndicator{sfx}"] = "1"
            if "rental" in ct:
                fields[f"Vehicle_Coverage_RentalReimbursementIndicator{sfx}"] = "1"

    # --- Additional Interests (Lienholders — up to 2) ---
    if hasattr(submission, "additional_interests"):
        ai_suffixes = ["_A", "_B"]
        for i, ai in enumerate(submission.additional_interests[:2]):
            sfx = ai_suffixes[i]
            if ai.name:
                fields[f"AdditionalInterest_FullName{sfx}"] = ai.name
            if ai.address:
                if ai.address.line_one:
                    fields[f"AdditionalInterest_MailingAddress_LineOne{sfx}"] = ai.address.line_one
                if ai.address.city:
                    fields[f"AdditionalInterest_MailingAddress_CityName{sfx}"] = ai.address.city
                if ai.address.state:
                    fields[f"AdditionalInterest_MailingAddress_StateOrProvinceCode{sfx}"] = ai.address.state
                if ai.address.zip_code:
                    fields[f"AdditionalInterest_MailingAddress_PostalCode{sfx}"] = ai.address.zip_code
            if ai.interest_type:
                it = ai.interest_type.lower()
                if "lienholder" in it:
                    fields[f"AdditionalInterest_Interest_LienholderIndicator{sfx}"] = "1"
                elif "loss_payee" in it or "loss payee" in it:
                    fields[f"AdditionalInterest_Interest_LossPayeeIndicator{sfx}"] = "1"
                elif "additional_insured" in it or "additional insured" in it:
                    fields[f"AdditionalInterest_Interest_AdditionalInsuredIndicator{sfx}"] = "1"
            if ai.account_number:
                fields[f"AdditionalInterest_AccountNumberIdentifier{sfx}"] = ai.account_number

    return fields
