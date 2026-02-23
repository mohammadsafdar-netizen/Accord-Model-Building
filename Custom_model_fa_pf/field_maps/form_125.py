"""Entity-to-field mapping for ACORD Form 125 (Commercial Insurance Application).

Maps CustomerSubmission entities to Form 125 PDF widget field names.
Covers: Named Insured, Producer, Policy, Locations (up to 4), Loss History (up to 3),
Additional Interests (up to 2), Prior Coverage, and Business Information.
"""

from typing import Dict, Optional
from Custom_model_fa_pf.entity_schema import CustomerSubmission

# Legal entity type → checkbox field name
ENTITY_TYPE_CHECKBOXES = {
    "corporation": "NamedInsured_LegalEntity_CorporationIndicator_A",
    "partnership": "NamedInsured_LegalEntity_PartnershipIndicator_A",
    "llc": "NamedInsured_LegalEntity_LimitedLiabilityCorporationIndicator_A",
    "individual": "NamedInsured_LegalEntity_IndividualIndicator_A",
    "subchapter_s": "NamedInsured_LegalEntity_SubchapterSCorporationIndicator_A",
    "joint_venture": "NamedInsured_LegalEntity_JointVentureIndicator_A",
    "not_for_profit": "NamedInsured_LegalEntity_NotForProfitIndicator_A",
}

# Policy status → checkbox field name
POLICY_STATUS_CHECKBOXES = {
    "new": "Policy_Status_QuoteIndicator_A",
    "renewal": "Policy_Status_RenewIndicator_A",
}

# Business type → indicator field
BUSINESS_TYPE_CHECKBOXES = {
    "manufacturing": "BusinessInformation_BusinessType_ManufacturingIndicator_A",
    "office": "BusinessInformation_BusinessType_OfficeIndicator_A",
    "retail": "BusinessInformation_BusinessType_RetailIndicator_A",
    "restaurant": "BusinessInformation_BusinessType_RestaurantIndicator_A",
    "wholesale": "BusinessInformation_BusinessType_WholesaleIndicator_A",
    "service": "BusinessInformation_BusinessType_ServiceIndicator_A",
    "contractor": "BusinessInformation_BusinessType_ContractorIndicator_A",
    "institutional": "BusinessInformation_BusinessType_InstitutionalIndicator_A",
    "apartments": "BusinessInformation_BusinessType_ApartmentsIndicator_A",
    "condominiums": "BusinessInformation_BusinessType_CondominiumsIndicator_A",
}

LOCATION_SUFFIXES = ["_A", "_B", "_C", "_D"]


def map_fields(submission: CustomerSubmission, lob_checkboxes: list[str] | None = None) -> Dict[str, str]:
    """Map extracted entities to Form 125 field names.

    Args:
        submission: Extracted customer submission data
        lob_checkboxes: List of LOB checkbox field names to set to "1"

    Returns:
        Dict of field_name -> value for Form 125
    """
    fields: Dict[str, str] = {}

    # --- Named Insured ---
    biz = submission.business
    if biz:
        if biz.business_name:
            fields["NamedInsured_FullName_A"] = biz.business_name
        if biz.dba:
            fields["NamedInsured_FullName_B"] = biz.dba

        addr = biz.mailing_address
        if addr:
            if addr.line_one:
                fields["NamedInsured_MailingAddress_LineOne_A"] = addr.line_one
            if addr.line_two:
                fields["NamedInsured_MailingAddress_LineTwo_A"] = addr.line_two
            if addr.city:
                fields["NamedInsured_MailingAddress_CityName_A"] = addr.city
            if addr.state:
                fields["NamedInsured_MailingAddress_StateOrProvinceCode_A"] = addr.state
            if addr.zip_code:
                fields["NamedInsured_MailingAddress_PostalCode_A"] = addr.zip_code

        if biz.tax_id:
            fields["NamedInsured_TaxIdentifier_A"] = biz.tax_id

        if biz.naics:
            fields["NamedInsured_NAICSCode_A"] = biz.naics
        if biz.sic:
            fields["NamedInsured_SICCode_A"] = biz.sic

        if biz.entity_type and biz.entity_type in ENTITY_TYPE_CHECKBOXES:
            fields[ENTITY_TYPE_CHECKBOXES[biz.entity_type]] = "1"

        if biz.business_start_date:
            fields["NamedInsured_BusinessStartDate_A"] = biz.business_start_date

        # Contacts — first contact as primary, second as secondary
        if biz.contacts:
            c0 = biz.contacts[0]
            if c0.full_name:
                fields["NamedInsured_Contact_FullName_A"] = c0.full_name
            if c0.phone:
                fields["NamedInsured_Primary_PhoneNumber_A"] = c0.phone
                fields["NamedInsured_Contact_PrimaryPhoneNumber_A"] = c0.phone
            if c0.email:
                fields["NamedInsured_Contact_PrimaryEmailAddress_A"] = c0.email
            if c0.role:
                fields["NamedInsured_Contact_ContactDescription_A"] = c0.role

            if len(biz.contacts) > 1:
                c1 = biz.contacts[1]
                if c1.full_name:
                    fields["NamedInsured_Contact_FullName_B"] = c1.full_name
                if c1.phone:
                    fields["NamedInsured_Contact_PrimaryPhoneNumber_B"] = c1.phone
                if c1.email:
                    fields["NamedInsured_Contact_PrimaryEmailAddress_B"] = c1.email
                if c1.role:
                    fields["NamedInsured_Contact_ContactDescription_B"] = c1.role

        if biz.website:
            fields["NamedInsured_Primary_WebsiteAddress_A"] = biz.website

        # --- Business Information ---
        if biz.employee_count:
            fields["BusinessInformation_FullTimeEmployeeCount_A"] = str(biz.employee_count)
        if biz.operations_description:
            # Map business type to checkbox if it matches
            ops_lower = biz.operations_description.lower()
            for btype, checkbox in BUSINESS_TYPE_CHECKBOXES.items():
                if btype in ops_lower:
                    fields[checkbox] = "1"
                    break
            else:
                # If no match, set "Other" with description
                fields["BusinessInformation_BusinessType_OtherIndicator_A"] = "1"
                fields["BusinessInformation_BusinessType_OtherDescription_A"] = biz.operations_description

    # --- Commercial Structure / Locations (up to 4) ---
    for i, loc in enumerate(submission.locations[:len(LOCATION_SUFFIXES)]):
        sfx = LOCATION_SUFFIXES[i]
        if loc.address:
            la = loc.address
            if la.line_one:
                fields[f"CommercialStructure_PhysicalAddress_LineOne{sfx}"] = la.line_one
            if la.city:
                fields[f"CommercialStructure_PhysicalAddress_CityName{sfx}"] = la.city
            if la.state:
                fields[f"CommercialStructure_PhysicalAddress_StateOrProvinceCode{sfx}"] = la.state
            if la.zip_code:
                fields[f"CommercialStructure_PhysicalAddress_PostalCode{sfx}"] = la.zip_code
        if loc.building_area:
            fields[f"BuildingOccupancy_OccupiedArea{sfx}"] = str(loc.building_area)
        if loc.construction_type:
            fields[f"Construction_TypeCode{sfx}"] = loc.construction_type
        if loc.year_built:
            fields[f"CommercialStructure_YearBuilt{sfx}"] = str(loc.year_built)
        if loc.occupancy:
            fields[f"BuildingOccupancy_OccupancyDescription{sfx}"] = loc.occupancy

    # --- Producer ---
    prod = submission.producer
    if prod:
        if prod.agency_name:
            fields["Producer_FullName_A"] = prod.agency_name
        if prod.contact_name:
            fields["Producer_ContactPerson_FullName_A"] = prod.contact_name
        if prod.phone:
            fields["Producer_ContactPerson_PhoneNumber_A"] = prod.phone
        if prod.email:
            fields["Producer_ContactPerson_EmailAddress_A"] = prod.email
        if prod.fax:
            fields["Producer_FaxNumber_A"] = prod.fax
        if prod.producer_code:
            fields["Producer_CustomerIdentifier_A"] = prod.producer_code
        if prod.license_number:
            fields["Producer_StateLicenseIdentifier_A"] = prod.license_number

        p_addr = prod.mailing_address
        if p_addr:
            if p_addr.line_one:
                fields["Producer_MailingAddress_LineOne_A"] = p_addr.line_one
            if p_addr.line_two:
                fields["Producer_MailingAddress_LineTwo_A"] = p_addr.line_two
            if p_addr.city:
                fields["Producer_MailingAddress_CityName_A"] = p_addr.city
            if p_addr.state:
                fields["Producer_MailingAddress_StateOrProvinceCode_A"] = p_addr.state
            if p_addr.zip_code:
                fields["Producer_MailingAddress_PostalCode_A"] = p_addr.zip_code

    # --- Policy ---
    pol = submission.policy
    if pol:
        if pol.effective_date:
            fields["Policy_EffectiveDate_A"] = pol.effective_date
        if pol.expiration_date:
            fields["Policy_ExpirationDate_A"] = pol.expiration_date
        if pol.policy_number:
            fields["Policy_PolicyNumberIdentifier_A"] = pol.policy_number

        # Status checkboxes
        if pol.status and pol.status in POLICY_STATUS_CHECKBOXES:
            fields[POLICY_STATUS_CHECKBOXES[pol.status]] = "1"

        # Payment / billing
        if pol.billing_plan:
            bp = pol.billing_plan.lower()
            if bp == "direct":
                fields["Policy_Payment_DirectBillIndicator_A"] = "1"
            elif bp == "agency":
                fields["Policy_Payment_ProducerBillIndicator_A"] = "1"
        if pol.payment_plan:
            fields["Policy_Payment_PaymentScheduleCode_A"] = pol.payment_plan
        if pol.deposit_amount:
            fields["Policy_Payment_DepositAmount_A"] = str(pol.deposit_amount)
        if pol.estimated_premium:
            fields["Policy_Payment_EstimatedTotalAmount_A"] = str(pol.estimated_premium)

    # --- LOB Checkboxes ---
    if lob_checkboxes:
        for cb_field in lob_checkboxes:
            fields[cb_field] = "1"

    # --- Loss History (up to 3) ---
    loss_suffixes = ["_A", "_B", "_C"]
    for i, loss in enumerate(submission.loss_history[:3]):
        sfx = loss_suffixes[i]
        if loss.date:
            fields[f"LossHistory_OccurrenceDate{sfx}"] = loss.date
        if loss.lob:
            fields[f"LossHistory_LineOfBusiness{sfx}"] = loss.lob
        if loss.description:
            fields[f"LossHistory_OccurrenceDescription{sfx}"] = loss.description
        if loss.amount:
            fields[f"LossHistory_PaidAmount{sfx}"] = str(loss.amount)
        if loss.claim_status:
            status_lower = loss.claim_status.lower()
            if status_lower in ("open", "pending"):
                fields[f"LossHistory_ClaimStatus_OpenCode{sfx}"] = "O"
            elif status_lower in ("subrogation", "subrogated"):
                fields[f"LossHistory_ClaimStatus_SubrogationCode{sfx}"] = "S"

    # No prior losses indicator
    if not submission.loss_history:
        fields["LossHistory_NoPriorLossesIndicator_A"] = "1"

    # --- Additional Interests (up to 2) ---
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
                type_map = {
                    "additional_insured": f"AdditionalInterest_Interest_AdditionalInsuredIndicator{sfx}",
                    "mortgagee": f"AdditionalInterest_Interest_MortgageeIndicator{sfx}",
                    "lienholder": f"AdditionalInterest_Interest_LienholderIndicator{sfx}",
                    "loss_payee": f"AdditionalInterest_Interest_LossPayeeIndicator{sfx}",
                    "lenders_loss_payable": f"AdditionalInterest_Interest_LendersLossPayableIndicator{sfx}",
                }
                if it in type_map:
                    fields[type_map[it]] = "1"
            if ai.account_number:
                fields[f"AdditionalInterest_AccountNumberIdentifier{sfx}"] = ai.account_number
            if ai.certificate_required:
                fields[f"AdditionalInterest_CertificateRequiredIndicator{sfx}"] = "1"

    # --- Prior Coverage ---
    if hasattr(submission, "prior_insurance"):
        for pi in submission.prior_insurance[:1]:
            if pi.carrier_name:
                fields["PriorCoverage_Automobile_InsurerFullName_A"] = pi.carrier_name
            if pi.policy_number:
                fields["PriorCoverage_Automobile_PolicyNumberIdentifier_A"] = pi.policy_number
            if pi.effective_date:
                fields["PriorCoverage_Automobile_EffectiveDate_A"] = pi.effective_date
            if pi.expiration_date:
                fields["PriorCoverage_Automobile_ExpirationDate_A"] = pi.expiration_date
            if pi.premium:
                fields["PriorCoverage_Automobile_TotalPremiumAmount_A"] = str(pi.premium)

    return fields
