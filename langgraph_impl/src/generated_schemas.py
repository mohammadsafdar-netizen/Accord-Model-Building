from typing import Optional, Dict
from pydantic import BaseModel, Field

# --- AUTO-GENERATED FILE. DO NOT EDIT MANUALLY ---

class Acord125Data(BaseModel):
    """Auto-generated schema for ACORD 125"""
    additional_interest_account_number_identifier_a: Optional[str] = Field(None, description="Enter identifier: The loan number, account number or other controlling number that the additional interest may have assigned the insured. ")
    additional_interest_certificate_required_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates if the additional interest requires a Certificate of Insurance. ")
    additional_interest_full_name_a: Optional[str] = Field(None, description="Enter text: The additional interest's full name. ")
    additional_interest_full_name_b: Optional[str] = Field(None, description="Enter text: The additional interest's full name.  As used here, this is the name of the trust.")
    additional_interest_interest_additional_insured_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is an additional insured. ")
    additional_interest_interest_breach_of_warranty_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a breach of warranty. ")
    additional_interest_interest_co_owner_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a co-owner. ")
    additional_interest_interest_employee_as_lessor_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is an employee as lessor. ")
    additional_interest_interest_end_date_a: Optional[str] = Field(None, description="Enter date: The date the interest holder's interest terminates. ")
    additional_interest_interest_leaseback_owner_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a leaseback owner. ")
    additional_interest_interest_lenders_loss_payable_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a lender's loss payable. ")
    additional_interest_interest_lienholder_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a lien holder. ")
    additional_interest_interest_loss_payee_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a loss payee. ")
    additional_interest_interest_mortgagee_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a mortgagee. ")
    additional_interest_interest_other_description_a: Optional[str] = Field(None, description="Enter text: The description of the other type of additional interest. ")
    additional_interest_interest_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest is other than those listed. ")
    additional_interest_interest_owner_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is an owner. ")
    additional_interest_interest_rank_a: Optional[str] = Field(None, description="Enter number: The ranking of 'this' additional interest when multiple additional interests are associated with the same item. ")
    additional_interest_interest_reason_description_a: Optional[str] = Field(None, description="Enter text: The description for the interest in the item. ")
    additional_interest_interest_registrant_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a registrant. ")
    additional_interest_interest_trustee_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest type is a trustee. ")
    additional_interest_item_aircraft_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The producer assigned number of the aircraft which has an additional interest. ")
    additional_interest_item_airport_identifier_a: Optional[str] = Field(None, description="Enter identifier: The Federal Aviation Administration's designator for the airport (e.g. ORD - O'Hare International Airport). ")
    additional_interest_item_boat_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The producer assigned number of the boat which has an additional interest. ")
    additional_interest_item_building_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The producer assigned number of the building which has an additional interest. ")
    additional_interest_item_description_a: Optional[str] = Field(None, description="Enter text: The description of the item of interest if needed to further clarify.  For a vehicle, list the make, model and VIN number.  For a scheduled item, list the description, such as three car...")
    additional_interest_item_location_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The producer assigned number of the location which has an additional interest. ")
    additional_interest_item_scheduled_item_class_code_a: Optional[str] = Field(None, description="Enter code: The description of the property class of the scheduled item (i.e. Jewelry, Furs, Contractors Equipment, etc.). ")
    additional_interest_item_scheduled_item_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The producer assigned number of the scheduled item which has an additional interest. ")
    additional_interest_item_vehicle_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The producer assigned number of the vehicle which has an additional interest. ")
    additional_interest_loan_amount_a: Optional[str] = Field(None, description="Enter amount: The amount of the loan. ")
    additional_interest_mailing_address_city_name_a: Optional[str] = Field(None, description="Enter text: The additional interest's mailing address city name. ")
    additional_interest_mailing_address_country_code_a: Optional[str] = Field(None, description="Enter code: The additional interest's country code. ")
    additional_interest_mailing_address_line_one_a: Optional[str] = Field(None, description="Enter text: The additional interest's mailing address line one. ")
    additional_interest_mailing_address_line_two_a: Optional[str] = Field(None, description="Enter text: The additional interest's mailing address line two. ")
    additional_interest_mailing_address_postal_code_a: Optional[str] = Field(None, description="Enter code: The additional interest's mailing address postal code. ")
    additional_interest_mailing_address_state_or_province_code_a: Optional[str] = Field(None, description="Enter code: The additional interest's mailing address state or province code. ")
    additional_interest_policy_required_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the additional interest requires a copy of the policy. ")
    additional_interest_primary_email_address_a: Optional[str] = Field(None, description="Enter text: The primary e-mail address for the additional interest. ")
    additional_interest_primary_fax_number_a: Optional[str] = Field(None, description="Enter number: The primary fax number of the additional interest. ")
    additional_interest_primary_phone_number_a: Optional[str] = Field(None, description="Enter number: The primary phone number of the additional interest. ")
    additional_interest_send_bill_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the bill should be sent to the additional interest. ")
    boiler_and_machinery_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Boiler & Machinery line of business. ")
    building_occupancy_occupied_area_a: Optional[str] = Field(None, description="Enter number: The area, in square feet, of the space in the building that is occupied by the named insured. ")
    building_occupancy_occupied_area_b: Optional[str] = Field(None, description="Enter number: The area, in square feet, of the space in the building that is occupied by the named insured. ")
    building_occupancy_occupied_area_c: Optional[str] = Field(None, description="Enter number: The area, in square feet, of the space in the building that is occupied by the named insured. ")
    building_occupancy_occupied_area_d: Optional[str] = Field(None, description="Enter number: The area, in square feet, of the space in the building that is occupied by the named insured. ")
    building_occupancy_open_to_public_area_a: Optional[str] = Field(None, description="Enter number: The area, in square feet, of the building that is open to the public. ")
    building_occupancy_open_to_public_area_b: Optional[str] = Field(None, description="Enter number: The area, in square feet, of the building that is open to the public. ")
    building_occupancy_open_to_public_area_c: Optional[str] = Field(None, description="Enter number: The area, in square feet, of the building that is open to the public. ")
    building_occupancy_open_to_public_area_d: Optional[str] = Field(None, description="Enter number: The area, in square feet, of the building that is open to the public. ")
    building_occupancy_operations_description_a: Optional[str] = Field(None, description="Enter text: The description of what business each applicant performs and the way it is conducted by premises.  Operations which may not be apparent in a general description of operations may be seg...")
    building_occupancy_operations_description_b: Optional[str] = Field(None, description="Enter text: The description of what business each applicant performs and the way it is conducted by premises.  Operations which may not be apparent in a general description of operations may be seg...")
    building_occupancy_operations_description_c: Optional[str] = Field(None, description="Enter text: The description of what business each applicant performs and the way it is conducted by premises.  Operations which may not be apparent in a general description of operations may be seg...")
    building_occupancy_operations_description_d: Optional[str] = Field(None, description="Enter text: The description of what business each applicant performs and the way it is conducted by premises.  Operations which may not be apparent in a general description of operations may be seg...")
    business_information_business_type_apartments_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is apartments. ")
    business_information_business_type_condominiums_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is condominiums. ")
    business_information_business_type_contractor_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is a contractor. ")
    business_information_business_type_institutional_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is institutional. ")
    business_information_business_type_manufacturing_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is manufacturing. ")
    business_information_business_type_office_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is an office. ")
    business_information_business_type_other_description_a: Optional[str] = Field(None, description="Enter text: The description of the other nature / type of business. ")
    business_information_business_type_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is other than those listed. ")
    business_information_business_type_restaurant_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is a restaurant. ")
    business_information_business_type_retail_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is retail. ")
    business_information_business_type_service_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is service. ")
    business_information_business_type_wholesale_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the nature of business is wholesale. ")
    business_information_full_time_employee_count_a: Optional[str] = Field(None, description="Enter number: The number of full time employees. ")
    business_information_full_time_employee_count_b: Optional[str] = Field(None, description="Enter number: The number of full time employees. ")
    business_information_full_time_employee_count_c: Optional[str] = Field(None, description="Enter number: The number of full time employees. ")
    business_information_full_time_employee_count_d: Optional[str] = Field(None, description="Enter number: The number of full time employees. ")
    business_information_parent_organization_name_a: Optional[str] = Field(None, description="Enter text: The name of the parent organization. ")
    business_information_part_time_employee_count_a: Optional[str] = Field(None, description="Enter number: The number of part time employees. ")
    business_information_part_time_employee_count_b: Optional[str] = Field(None, description="Enter number: The number of part time employees. ")
    business_information_part_time_employee_count_c: Optional[str] = Field(None, description="Enter number: The number of part time employees. ")
    business_information_part_time_employee_count_d: Optional[str] = Field(None, description="Enter number: The number of part time employees. ")
    business_owners_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The total estimated premium amount for the business owners (BOP) line of business. ")
    cancel_non_renew_agent_no_longer_writes_for_insurer_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is being cancelled because the agent is no longer writing business for the insurer. ")
    cancel_non_renew_non_payment_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is being cancelled due to non-payment of premium. ")
    cancel_non_renew_non_renewal_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is being cancelled due to non-renewal. ")
    cancel_non_renew_other_description_a: Optional[str] = Field(None, description="Enter text: The description of why the policy is being cancelled or terminated. ")
    cancel_non_renew_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is being cancelled due to reasons other than those listed. ")
    cancel_non_renew_underwriting_condition_corrected_description_a: Optional[str] = Field(None, description="Enter text: The description of how the underwriting condition that caused the policy to not be written has been corrected. ")
    cancel_non_renew_underwriting_condition_corrected_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the underwriting condition that caused the policy to not be written has been corrected. ")
    cancel_non_renew_underwriting_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is being cancelled due to underwriting reasons. ")
    commercial_inland_marine_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for commercial inland marine line of business. ")
    commercial_policy_any_exposure_to_flammable_explosives_chemicals_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation as to whether there is any exposure to flammable, explosive or chemicals. ")
    commercial_policy_applicant_hire_others_operate_drones_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation as to whether the applicant hires others to operate drones. ")
    commercial_policy_applicant_other_business_ventures_coverage_not_requested_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation of any other business ventures for which coverage is not requested. ")
    commercial_policy_applicant_own_lease_operate_drones_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation as to whether the applicant owns, leases or operates any drones. ")
    commercial_policy_attachment_additional_interest_schedule_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates ACORD 45, Additional Interest Schedule is attached to the application. ")
    commercial_policy_attachment_additional_premises_schedule_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates an Additional Premises Information Schedule is attached to the application. ")
    commercial_policy_attachment_apartment_building_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates an Apartment Building Supplement is attached. ")
    commercial_policy_attachment_condominium_association_by_laws_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the condominium association bylaws are attached to the application. ")
    commercial_policy_attachment_contractors_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Contractors Supplement is attached to the application. ")
    commercial_policy_attachment_coverages_schedule_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a coverages schedule is attached. ")
    commercial_policy_attachment_hotel_motel_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Hotel / Motel Supplement is attached to the application. ")
    commercial_policy_attachment_international_liability_exposure_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates an International Liability Exposure Supplement is attached to the application. ")
    commercial_policy_attachment_international_property_exposure_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates an International Property Exposure Supplement is attached to the application. ")
    commercial_policy_attachment_loss_summary_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that a loss summary report is attached to the application. ")
    commercial_policy_attachment_other_description_a: Optional[str] = Field(None, description="Enter text: The description of the type of other attachment. ")
    commercial_policy_attachment_other_description_b: Optional[str] = Field(None, description="Enter text: The description of the type of other attachment. ")
    commercial_policy_attachment_other_description_c: Optional[str] = Field(None, description="Enter text: The description of the type of other attachment. ")
    commercial_policy_attachment_other_description_d: Optional[str] = Field(None, description="Enter text: The description of the type of other attachment. ")
    commercial_policy_attachment_other_description_e: Optional[str] = Field(None, description="Enter text: The description of the type of other attachment. ")
    commercial_policy_attachment_other_description_f: Optional[str] = Field(None, description="Enter text: The description of the type of other attachment. ")
    commercial_policy_attachment_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates there is an attachment other than those listed on the application. ")
    commercial_policy_attachment_other_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates there is an attachment other than those listed on the application. ")
    commercial_policy_attachment_other_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates there is an attachment other than those listed on the application. ")
    commercial_policy_attachment_other_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates there is an attachment other than those listed on the application. ")
    commercial_policy_attachment_other_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates there is an attachment other than those listed on the application. ")
    commercial_policy_attachment_other_indicator_f: Optional[str] = Field(None, description="Check the box (if applicable): Indicates there is an attachment other than those listed on the application. ")
    commercial_policy_attachment_premium_payment_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Premium Payment Supplement is attached to the application. ")
    commercial_policy_attachment_professional_liability_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Professional Liability Supplement is attached to the application. ")
    commercial_policy_attachment_restaurant_tavern_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Restaurant / Tavern Supplement is attached to the application. ")
    commercial_policy_attachment_state_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that a state supplement is attached to the application. ")
    commercial_policy_attachment_statement_of_values_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Statement / Schedule of Values is attached to the application. ")
    commercial_policy_attachment_vacant_building_supplement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Vacant Building Supplement is attached to the application. ")
    commercial_policy_foreclosure_repossession_bankruptcy_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation as to whether the applicant has had a foreclosure, repossession, bankruptcy or filed for bankruptcy during last mandated number of years. ")
    commercial_policy_foreclosure_repossession_bankruptcy_explanation_b: Optional[str] = Field(None, description="Enter text: An explanation as to whether the applicant has had a foreclosure, repossession, bankruptcy or filed for bankruptcy during last mandated number of years. ")
    commercial_policy_foreclosure_repossession_bankruptcy_occurrence_date_a: Optional[str] = Field(None, description="Enter date: The occurrence date associated with the applicant's foreclosure, repossession, bankruptcy or bankruptcy filing during the last mandated number of years. ")
    commercial_policy_foreclosure_repossession_bankruptcy_occurrence_date_b: Optional[str] = Field(None, description="Enter date: The occurrence date associated with the applicant's foreclosure, repossession, bankruptcy or bankruptcy filing during the last mandated number of years. ")
    commercial_policy_foreclosure_repossession_bankruptcy_resolution_date_a: Optional[str] = Field(None, description="Enter date: The resolution date associated with any foreclosure, repossession or bankruptcy filings within the last mandated number of years. ")
    commercial_policy_foreclosure_repossession_bankruptcy_resolution_date_b: Optional[str] = Field(None, description="Enter date: The resolution date associated with any foreclosure, repossession or bankruptcy filings within the last mandated number of years. ")
    commercial_policy_foreclosure_repossession_bankruptcy_resolution_description_a: Optional[str] = Field(None, description="Enter text: The resolution associated with any foreclosure, repossession or bankruptcy filings within the last mandated number of years. ")
    commercial_policy_foreclosure_repossession_bankruptcy_resolution_description_b: Optional[str] = Field(None, description="Enter text: The resolution associated with any foreclosure, repossession or bankruptcy filings within the last mandated number of years. ")
    commercial_policy_formal_safety_program_monthly_meetings_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates monthly meetings are part of the formal safety program. ")
    commercial_policy_formal_safety_program_osha_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the formal safety program meets OSHA guidelines. ")
    commercial_policy_formal_safety_program_other_description_b: Optional[str] = Field(None, description="Enter text: The description of the formal safety program. ")
    commercial_policy_formal_safety_program_other_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates there is a formal safety program other than those listed. ")
    commercial_policy_formal_safety_program_safety_manual_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a safety manual is part of the formal safety program. ")
    commercial_policy_formal_safety_program_safety_position_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a safety position is part of the formal safety program. ")
    commercial_policy_judgement_or_lien_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation as to whether the applicant has a judgement or lien during the last mandated number of years. ")
    commercial_policy_judgement_or_lien_explanation_b: Optional[str] = Field(None, description="Enter text: An explanation as to whether the applicant has a judgement or lien during the last mandated number of years. ")
    commercial_policy_judgement_or_lien_occurrence_date_a: Optional[str] = Field(None, description="Enter date: The occurrence date associated with the applicant's judgement or lien during the last mandated number of years. ")
    commercial_policy_judgement_or_lien_occurrence_date_b: Optional[str] = Field(None, description="Enter date: The occurrence date associated with the applicant's judgement or lien during the last mandated number of years. ")
    commercial_policy_judgement_or_lien_resolution_date_a: Optional[str] = Field(None, description="Enter date: The resolution date associated with any judgement or lien during the last mandated number of years. ")
    commercial_policy_judgement_or_lien_resolution_date_b: Optional[str] = Field(None, description="Enter date: The resolution date associated with any judgement or lien during the last mandated number of years. ")
    commercial_policy_judgement_or_lien_resolution_description_a: Optional[str] = Field(None, description="Enter text: The resolution associated with any judgement or lien during the last mandated number of years. ")
    commercial_policy_judgement_or_lien_resolution_description_b: Optional[str] = Field(None, description="Enter text: The resolution associated with any judgement or lien during the last mandated number of years. ")
    commercial_policy_operations_description_a: Optional[str] = Field(None, description="Enter text: The description of the operations of this risk or insured.  As used here, this is the description of primary operations.")
    commercial_policy_operations_description_b: Optional[str] = Field(None, description="Enter text: The description of the operations of this risk or insured.  As used here, this is the description of operations for other named insureds.")
    commercial_policy_past_five_years_any_applicant_indicted_or_convicted_fraud_bribery_arson_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation as to whether any applicant has been indicted or convicted of any degree of fraud, bribery or any arson related crime in connection with this or any other property within...")
    commercial_policy_past_losses_claims_relating_sexual_abuse_discrimination_negligent_hiring_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation of any past losses or claims relating to sexual abuse or molestation allegations, discrimination or negligent hiring. ")
    commercial_policy_question_aac_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Any policy or coverage declined, cancelled or non-renewed during the mandated number of years?'. As...")
    commercial_policy_question_aad_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Any past losses or claims relating to sexual abuse or molestation allegations, discrimination or ne...")
    commercial_policy_question_aaf_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Any uncorrected fire code violations?'. ")
    commercial_policy_question_aah_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Any other insurance with this company?'. ")
    commercial_policy_question_aai_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Is the applicant a subsidiary of another entity?'. ")
    commercial_policy_question_aaj_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Does the applicant have any subsidiaries?'. ")
    commercial_policy_question_abb_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Has business been placed in a trust?'. ")
    commercial_policy_question_abc_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Any exposure to flammables, explosives, chemicals?'. ")
    commercial_policy_question_kaa_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Is a formal safety program in operation?'. ")
    commercial_policy_question_kab_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'During the mandated number of years, has any applicant been indicted for or convicted of any degree...")
    commercial_policy_question_kac_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Any foreign operations, foreign products distributed in USA, or US products sold/distributed in for...")
    commercial_policy_question_kak_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response.  Indicates the response to the question, 'Has applicant had a foreclosure, repossession, bankruptcy, or filed for bankruptcy during the past...")
    commercial_policy_question_kal_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response.  Indicates the response to the question, 'Has applicant had a judgment or lien during the past specified number of years?'.  The answer is “...")
    commercial_policy_question_kam_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Does applicant have other business ventures for which coverage is not requested?'. ")
    commercial_policy_question_kan_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Does applicant own / lease / operate any drones? ")
    commercial_policy_question_kao_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates the response to the question, 'Does applicant hire others to operate drones?' ")
    commercial_policy_remark_text_a: Optional[str] = Field(None, description="Enter text: The commercial policy general remarks. ")
    commercial_policy_uncorrected_fire_code_violation_explanation_a: Optional[str] = Field(None, description="Enter text: An explanation as to whether there are any uncorrected fire code violations. ")
    commercial_policy_uncorrected_fire_code_violation_explanation_b: Optional[str] = Field(None, description="Enter text: An explanation as to whether there are any uncorrected fire code violations. ")
    commercial_policy_uncorrected_fire_code_violation_occurrence_date_a: Optional[str] = Field(None, description="Enter date: The occurrence date of any uncorrected fire code violations. ")
    commercial_policy_uncorrected_fire_code_violation_occurrence_date_b: Optional[str] = Field(None, description="Enter date: The occurrence date of any uncorrected fire code violations. ")
    commercial_policy_uncorrected_fire_code_violation_resolution_date_a: Optional[str] = Field(None, description="Enter date: The resolution date associated with the fire code violation. ")
    commercial_policy_uncorrected_fire_code_violation_resolution_date_b: Optional[str] = Field(None, description="Enter date: The resolution date associated with the fire code violation. ")
    commercial_policy_uncorrected_fire_code_violation_resolution_description_a: Optional[str] = Field(None, description="Enter text: The resolution associated with any fire code violations. ")
    commercial_policy_uncorrected_fire_code_violation_resolution_description_b: Optional[str] = Field(None, description="Enter text: The resolution associated with any fire code violations. ")
    commercial_property_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Commercial Property line of business. ")
    commercial_structure_annual_revenue_amount_a: Optional[str] = Field(None, description="Enter amount: The annual revenue amount for this location. ")
    commercial_structure_annual_revenue_amount_b: Optional[str] = Field(None, description="Enter amount: The annual revenue amount for this location. ")
    commercial_structure_annual_revenue_amount_c: Optional[str] = Field(None, description="Enter amount: The annual revenue amount for this location. ")
    commercial_structure_annual_revenue_amount_d: Optional[str] = Field(None, description="Enter amount: The annual revenue amount for this location. ")
    commercial_structure_building_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The building number for the premises.  Used when more than one building exists at an individual location. ")
    commercial_structure_building_producer_identifier_b: Optional[str] = Field(None, description="Enter number: The building number for the premises.  Used when more than one building exists at an individual location. ")
    commercial_structure_building_producer_identifier_c: Optional[str] = Field(None, description="Enter number: The building number for the premises.  Used when more than one building exists at an individual location. ")
    commercial_structure_building_producer_identifier_d: Optional[str] = Field(None, description="Enter number: The building number for the premises.  Used when more than one building exists at an individual location. ")
    commercial_structure_installation_repair_work_off_premises_percent_a: Optional[str] = Field(None, description="Enter percentage: The percentage of total sales of a retail store or service operation attributed to installation, service or repair work completed off premises. ")
    commercial_structure_installation_repair_work_percent_a: Optional[str] = Field(None, description="Enter percentage: The percentage of total sales of a retail store or service operation attributed to installation, service or repair work. ")
    commercial_structure_insured_interest_other_description_a: Optional[str] = Field(None, description="Enter text: The description of the insured's interest in the building when it is other than those listed. ")
    commercial_structure_insured_interest_other_description_b: Optional[str] = Field(None, description="Enter text: The description of the insured's interest in the building when it is other than those listed. ")
    commercial_structure_insured_interest_other_description_c: Optional[str] = Field(None, description="Enter text: The description of the insured's interest in the building when it is other than those listed. ")
    commercial_structure_insured_interest_other_description_d: Optional[str] = Field(None, description="Enter text: The description of the insured's interest in the building when it is other than those listed. ")
    commercial_structure_insured_interest_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is other than those listed. ")
    commercial_structure_insured_interest_other_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is other than those listed. ")
    commercial_structure_insured_interest_other_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is other than those listed. ")
    commercial_structure_insured_interest_other_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is other than those listed. ")
    commercial_structure_insured_interest_owner_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is as its owner. ")
    commercial_structure_insured_interest_owner_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is as its owner. ")
    commercial_structure_insured_interest_owner_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is as its owner. ")
    commercial_structure_insured_interest_owner_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is as its owner. ")
    commercial_structure_insured_interest_tenant_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is as its tenant. ")
    commercial_structure_insured_interest_tenant_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is as its tenant. ")
    commercial_structure_insured_interest_tenant_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is as its tenant. ")
    commercial_structure_insured_interest_tenant_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the named insured's interest in the building is as its tenant. ")
    commercial_structure_location_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The location number for the premises. ")
    commercial_structure_location_producer_identifier_b: Optional[str] = Field(None, description="Enter number: The location number for the premises. ")
    commercial_structure_location_producer_identifier_c: Optional[str] = Field(None, description="Enter number: The location number for the premises. ")
    commercial_structure_location_producer_identifier_d: Optional[str] = Field(None, description="Enter number: The location number for the premises. ")
    commercial_structure_physical_address_city_name_a: Optional[str] = Field(None, description="Enter text: The city of the commercial structure. ")
    commercial_structure_physical_address_city_name_b: Optional[str] = Field(None, description="Enter text: The city of the commercial structure. ")
    commercial_structure_physical_address_city_name_c: Optional[str] = Field(None, description="Enter text: The city of the commercial structure. ")
    commercial_structure_physical_address_city_name_d: Optional[str] = Field(None, description="Enter text: The city of the commercial structure. ")
    commercial_structure_physical_address_county_name_a: Optional[str] = Field(None, description="Enter text: The county of the commercial structure. ")
    commercial_structure_physical_address_county_name_b: Optional[str] = Field(None, description="Enter text: The county of the commercial structure. ")
    commercial_structure_physical_address_county_name_c: Optional[str] = Field(None, description="Enter text: The county of the commercial structure. ")
    commercial_structure_physical_address_county_name_d: Optional[str] = Field(None, description="Enter text: The county of the commercial structure. ")
    commercial_structure_physical_address_line_one_a: Optional[str] = Field(None, description="Enter text: The first address line of the commercial structure. ")
    commercial_structure_physical_address_line_one_b: Optional[str] = Field(None, description="Enter text: The first address line of the commercial structure. ")
    commercial_structure_physical_address_line_one_c: Optional[str] = Field(None, description="Enter text: The first address line of the commercial structure. ")
    commercial_structure_physical_address_line_one_d: Optional[str] = Field(None, description="Enter text: The first address line of the commercial structure. ")
    commercial_structure_physical_address_line_two_a: Optional[str] = Field(None, description="Enter text: The second address line of the commercial structure. ")
    commercial_structure_physical_address_line_two_b: Optional[str] = Field(None, description="Enter text: The second address line of the commercial structure. ")
    commercial_structure_physical_address_line_two_c: Optional[str] = Field(None, description="Enter text: The second address line of the commercial structure. ")
    commercial_structure_physical_address_line_two_d: Optional[str] = Field(None, description="Enter text: The second address line of the commercial structure. ")
    commercial_structure_physical_address_postal_code_a: Optional[str] = Field(None, description="Enter code: The postal code of the commercial structure. ")
    commercial_structure_physical_address_postal_code_b: Optional[str] = Field(None, description="Enter code: The postal code of the commercial structure. ")
    commercial_structure_physical_address_postal_code_c: Optional[str] = Field(None, description="Enter code: The postal code of the commercial structure. ")
    commercial_structure_physical_address_postal_code_d: Optional[str] = Field(None, description="Enter code: The postal code of the commercial structure. ")
    commercial_structure_physical_address_state_or_province_code_a: Optional[str] = Field(None, description="Enter code: The state or province code of the commercial structure. ")
    commercial_structure_physical_address_state_or_province_code_b: Optional[str] = Field(None, description="Enter code: The state or province code of the commercial structure. ")
    commercial_structure_physical_address_state_or_province_code_c: Optional[str] = Field(None, description="Enter code: The state or province code of the commercial structure. ")
    commercial_structure_physical_address_state_or_province_code_d: Optional[str] = Field(None, description="Enter code: The state or province code of the commercial structure. ")
    commercial_structure_question_abb_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response.  Indicates the response to the question, 'Any area leased to others?'. ")
    commercial_structure_question_abb_code_b: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response.  Indicates the response to the question, 'Any area leased to others?'. ")
    commercial_structure_question_abb_code_c: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response.  Indicates the response to the question, 'Any area leased to others?'. ")
    commercial_structure_question_abb_code_d: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response.  Indicates the response to the question, 'Any area leased to others?'. ")
    commercial_structure_risk_location_inside_city_limits_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is within the city limits. ")
    commercial_structure_risk_location_inside_city_limits_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is within the city limits. ")
    commercial_structure_risk_location_inside_city_limits_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is within the city limits. ")
    commercial_structure_risk_location_inside_city_limits_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is within the city limits. ")
    commercial_structure_risk_location_other_description_a: Optional[str] = Field(None, description="Enter text: The description of the risk location if not inside nor outside the city limits. ")
    commercial_structure_risk_location_other_description_b: Optional[str] = Field(None, description="Enter text: The description of the risk location if not inside nor outside the city limits. ")
    commercial_structure_risk_location_other_description_c: Optional[str] = Field(None, description="Enter text: The description of the risk location if not inside nor outside the city limits. ")
    commercial_structure_risk_location_other_description_d: Optional[str] = Field(None, description="Enter text: The description of the risk location if not inside nor outside the city limits. ")
    commercial_structure_risk_location_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is not inside nor outside city limits.  For example, unincorporated. ")
    commercial_structure_risk_location_other_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is not inside nor outside city limits.  For example, unincorporated. ")
    commercial_structure_risk_location_other_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is not inside nor outside city limits.  For example, unincorporated. ")
    commercial_structure_risk_location_other_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is not inside nor outside city limits.  For example, unincorporated. ")
    commercial_structure_risk_location_outside_city_limits_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is outside the city limits. ")
    commercial_structure_risk_location_outside_city_limits_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is outside the city limits. ")
    commercial_structure_risk_location_outside_city_limits_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is outside the city limits. ")
    commercial_structure_risk_location_outside_city_limits_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the building is outside the city limits. ")
    commercial_umbrella_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Commercial Umbrella line of business. ")
    commercial_vehicle_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Commercial Vehicle (Business Auto) line of business. ")
    construction_building_area_a: Optional[str] = Field(None, description="Enter number: The number of square feet of the building at this location for which insurance is being requested. ")
    construction_building_area_b: Optional[str] = Field(None, description="Enter number: The number of square feet of the building at this location for which insurance is being requested. ")
    construction_building_area_c: Optional[str] = Field(None, description="Enter number: The number of square feet of the building at this location for which insurance is being requested. ")
    construction_building_area_d: Optional[str] = Field(None, description="Enter number: The number of square feet of the building at this location for which insurance is being requested. ")
    crime_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Crime line of business. ")
    cyber_and_privacy_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Cyber and Privacy line of business ")
    fiduciary_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Fiduciary Liability line of business. ")
    form_completion_date_a: Optional[str] = Field(None, description="Enter date: The date on which the form is completed.  (MM/DD/YYYY) ")
    form_edition_identifier_a: Optional[str] = Field(None, description="The edition identifier of the form including the form number and edition (the date is typically formatted YYYY/MM).")
    garage_and_dealers_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Garage and Dealers line of business. ")
    general_liability_line_of_business_total_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The total premium amount for the commercial general liability line of business. ")
    insurer_full_name_a: Optional[str] = Field(None, description="Enter text: The insurer's full legal company name(s) as found in the file copy of the policy.  Use the actual name of the company within the group to which the policy has been issued.  This is not ...")
    insurer_naic_code_a: Optional[str] = Field(None, description="Enter code: The identification code assigned to the insurer by the National Association of Insurance Commissioners (NAIC). ")
    insurer_producer_identifier_a: Optional[str] = Field(None, description="Enter code: The identification code assigned to the producer (e.g., agency or brokerage firm) by the insurer. ")
    insurer_product_code_a: Optional[str] = Field(None, description="Enter code: The product code assigned by the insurer for the policy. ")
    insurer_product_description_a: Optional[str] = Field(None, description="Enter text: The description of an independently filed policy or program that may be optionally available from the insurance company.  It may also be used to name the subsidiary company in which the...")
    insurer_sub_producer_identifier_a: Optional[str] = Field(None, description="Enter code: The identification code assigned by the insurer to the sub-producer (e.g., individual) within a producer's office (e.g., agency or brokerage). ")
    insurer_underwriter_full_name_a: Optional[str] = Field(None, description="Enter text: The company underwriter (or other company staff person) that this form should be directed to. ")
    insurer_underwriter_office_identifier_a: Optional[str] = Field(None, description="Enter identifier: The company underwriting office that this application should be directed to. ")
    liquor_liability_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Liquor Liability line of business. ")
    loss_history_claim_date_a: Optional[str] = Field(None, description="Enter date: The date the claim was filed.  (MM/DD/YYYY) ")
    loss_history_claim_date_b: Optional[str] = Field(None, description="Enter date: The date the claim was filed.  (MM/DD/YYYY) ")
    loss_history_claim_date_c: Optional[str] = Field(None, description="Enter date: The date the claim was filed.  (MM/DD/YYYY) ")
    loss_history_claim_status_open_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates if the claim is still open. ")
    loss_history_claim_status_open_code_b: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates if the claim is still open. ")
    loss_history_claim_status_open_code_c: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates if the claim is still open. ")
    loss_history_claim_status_subrogation_code_a: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates if the claim is in subrogation. ")
    loss_history_claim_status_subrogation_code_b: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates if the claim is in subrogation. ")
    loss_history_claim_status_subrogation_code_c: Optional[str] = Field(None, description="Enter Y for a “Yes” response. Input N for “No” response. Indicates if the claim is in subrogation. ")
    loss_history_information_year_count_a: Optional[str] = Field(None, description="Enter number: The number of years of loss information required by the insurer.   ")
    loss_history_line_of_business_a: Optional[str] = Field(None, description="Enter text: The line of business involved in the loss (e.g. Automobile Liability, Property, General Liability). ")
    loss_history_line_of_business_b: Optional[str] = Field(None, description="Enter text: The line of business involved in the loss (e.g. Automobile Liability, Property, General Liability). ")
    loss_history_line_of_business_c: Optional[str] = Field(None, description="Enter text: The line of business involved in the loss (e.g. Automobile Liability, Property, General Liability). ")
    loss_history_no_prior_losses_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates there are no prior losses or occurrences that may give rise to claims for the mandated number of years. ")
    loss_history_occurrence_date_a: Optional[str] = Field(None, description="Enter date: The date when the accident or incident occurred that resulted in the filing of a claim.  (MM/DD/YYYY) ")
    loss_history_occurrence_date_b: Optional[str] = Field(None, description="Enter date: The date when the accident or incident occurred that resulted in the filing of a claim.  (MM/DD/YYYY) ")
    loss_history_occurrence_date_c: Optional[str] = Field(None, description="Enter date: The date when the accident or incident occurred that resulted in the filing of a claim.  (MM/DD/YYYY) ")
    loss_history_occurrence_description_a: Optional[str] = Field(None, description="Enter text: A brief description of the loss. ")
    loss_history_occurrence_description_b: Optional[str] = Field(None, description="Enter text: A brief description of the loss. ")
    loss_history_occurrence_description_c: Optional[str] = Field(None, description="Enter text: A brief description of the loss. ")
    loss_history_paid_amount_a: Optional[str] = Field(None, description="Enter amount: The amount that has been paid on this claim to date. ")
    loss_history_paid_amount_b: Optional[str] = Field(None, description="Enter amount: The amount that has been paid on this claim to date. ")
    loss_history_paid_amount_c: Optional[str] = Field(None, description="Enter amount: The amount that has been paid on this claim to date. ")
    loss_history_reserved_amount_a: Optional[str] = Field(None, description="Enter amount: The reserve amount the previous carrier is holding open for this claim. ")
    loss_history_reserved_amount_b: Optional[str] = Field(None, description="Enter amount: The reserve amount the previous carrier is holding open for this claim. ")
    loss_history_reserved_amount_c: Optional[str] = Field(None, description="Enter amount: The reserve amount the previous carrier is holding open for this claim. ")
    loss_history_total_amount_a: Optional[str] = Field(None, description="Enter amount: The amount that has been paid on all losses to date. ")
    motor_carrier_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for motor carrier line of business. ")
    named_insured_business_start_date_a: Optional[str] = Field(None, description="Enter date: The date the applicant began in business.  This is important because it helps the underwriter determine the expertise and business success of the applicant. ")
    named_insured_contact_contact_description_a: Optional[str] = Field(None, description="Enter text: The type of contact being described (e.g. accounting, claims, etc.). ")
    named_insured_contact_contact_description_b: Optional[str] = Field(None, description="Enter text: The type of contact being described (e.g. accounting, claims, etc.). ")
    named_insured_contact_full_name_a: Optional[str] = Field(None, description="Enter text: The full name of the contact. ")
    named_insured_contact_full_name_b: Optional[str] = Field(None, description="Enter text: The full name of the contact. ")
    named_insured_contact_primary_business_phone_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's primary phone is a business phone. ")
    named_insured_contact_primary_business_phone_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's primary phone is a business phone. ")
    named_insured_contact_primary_cell_phone_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's primary phone is a cell phone. ")
    named_insured_contact_primary_cell_phone_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's primary phone is a cell phone. ")
    named_insured_contact_primary_email_address_a: Optional[str] = Field(None, description="Enter text: The contact's primary e-mail address. ")
    named_insured_contact_primary_email_address_b: Optional[str] = Field(None, description="Enter text: The contact's primary e-mail address. ")
    named_insured_contact_primary_home_phone_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's primary phone is a home phone. ")
    named_insured_contact_primary_home_phone_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's primary phone is a home phone. ")
    named_insured_contact_primary_phone_number_a: Optional[str] = Field(None, description="Enter number: The primary phone number of the contact. ")
    named_insured_contact_primary_phone_number_b: Optional[str] = Field(None, description="Enter number: The primary phone number of the contact. ")
    named_insured_contact_secondary_business_phone_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's secondary phone number is a business phone. ")
    named_insured_contact_secondary_business_phone_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's secondary phone number is a business phone. ")
    named_insured_contact_secondary_cell_phone_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's secondary phone number is a cell phone. ")
    named_insured_contact_secondary_cell_phone_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's secondary phone number is a cell phone. ")
    named_insured_contact_secondary_email_address_a: Optional[str] = Field(None, description="Enter text: The contact's secondary e-mail address. ")
    named_insured_contact_secondary_email_address_b: Optional[str] = Field(None, description="Enter text: The contact's secondary e-mail address. ")
    named_insured_contact_secondary_home_phone_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's secondary phone number is a home phone. ")
    named_insured_contact_secondary_home_phone_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the contact's secondary phone number is a home phone. ")
    named_insured_contact_secondary_phone_number_a: Optional[str] = Field(None, description="Enter number: The secondary phone number of the contact. ")
    named_insured_contact_secondary_phone_number_b: Optional[str] = Field(None, description="Enter number: The secondary phone number of the contact. ")
    named_insured_full_name_a: Optional[str] = Field(None, description="Enter text: The named insured(s) as it / they will appear on the policy declarations page. ")
    named_insured_full_name_b: Optional[str] = Field(None, description="Enter text: The named insured(s) as it / they will appear on the policy declarations page. ")
    named_insured_full_name_c: Optional[str] = Field(None, description="Enter text: The named insured(s) as it / they will appear on the policy declarations page. ")
    named_insured_general_liability_code_a: Optional[str] = Field(None, description="Enter code: The code identifying the general liability nature of business for the insured. The source of this code list is the Insurance Services Office Commercial Lines Manual (CLM) or individual ...")
    named_insured_general_liability_code_b: Optional[str] = Field(None, description="Enter code: The code identifying the general liability nature of business for the insured. The source of this code list is the Insurance Services Office Commercial Lines Manual (CLM) or individual ...")
    named_insured_general_liability_code_c: Optional[str] = Field(None, description="Enter code: The code identifying the general liability nature of business for the insured. The source of this code list is the Insurance Services Office Commercial Lines Manual (CLM) or individual ...")
    named_insured_initials_a: Optional[str] = Field(None, description="Initial here: The named insured's initials. ")
    named_insured_legal_entity_corporation_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Corporation'. ")
    named_insured_legal_entity_corporation_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Corporation'. ")
    named_insured_legal_entity_corporation_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Corporation'. ")
    named_insured_legal_entity_individual_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Individual'. ")
    named_insured_legal_entity_individual_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Individual'. ")
    named_insured_legal_entity_individual_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Individual'. ")
    named_insured_legal_entity_joint_venture_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Joint Venture'. ")
    named_insured_legal_entity_joint_venture_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Joint Venture'. ")
    named_insured_legal_entity_joint_venture_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Joint Venture'. ")
    named_insured_legal_entity_limited_liability_corporation_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Limited Liability Corporation'. ")
    named_insured_legal_entity_limited_liability_corporation_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Limited Liability Corporation'. ")
    named_insured_legal_entity_limited_liability_corporation_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Limited Liability Corporation'. ")
    named_insured_legal_entity_member_manager_count_a: Optional[str] = Field(None, description="Enter number: The number of members and managers for the limited liability corporation. ")
    named_insured_legal_entity_member_manager_count_b: Optional[str] = Field(None, description="Enter number: The number of members and managers for the limited liability corporation. ")
    named_insured_legal_entity_member_manager_count_c: Optional[str] = Field(None, description="Enter number: The number of members and managers for the limited liability corporation. ")
    named_insured_legal_entity_not_for_profit_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Not For Profit Organization'. ")
    named_insured_legal_entity_not_for_profit_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Not For Profit Organization'. ")
    named_insured_legal_entity_not_for_profit_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Not For Profit Organization'. ")
    named_insured_legal_entity_other_description_a: Optional[str] = Field(None, description="Enter text: The description of the other legal entity. ")
    named_insured_legal_entity_other_description_b: Optional[str] = Field(None, description="Enter text: The description of the other legal entity. ")
    named_insured_legal_entity_other_description_c: Optional[str] = Field(None, description="Enter text: The description of the other legal entity. ")
    named_insured_legal_entity_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is other than those listed on the form. ")
    named_insured_legal_entity_other_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is other than those listed on the form. ")
    named_insured_legal_entity_other_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is other than those listed on the form. ")
    named_insured_legal_entity_partnership_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Partnership'. ")
    named_insured_legal_entity_partnership_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Partnership'. ")
    named_insured_legal_entity_partnership_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Partnership'. ")
    named_insured_legal_entity_subchapter_s_corporation_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Subchapter S Corporation'. ")
    named_insured_legal_entity_subchapter_s_corporation_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Subchapter S Corporation'. ")
    named_insured_legal_entity_subchapter_s_corporation_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Subchapter S Corporation'. ")
    named_insured_legal_entity_trust_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Trust'. ")
    named_insured_legal_entity_trust_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Trust'. ")
    named_insured_legal_entity_trust_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the legal entity code for the named insured is 'Trust'. ")
    named_insured_mailing_address_city_name_a: Optional[str] = Field(None, description="Enter text: The named insured's mailing address city name. ")
    named_insured_mailing_address_city_name_b: Optional[str] = Field(None, description="Enter text: The named insured's mailing address city name. ")
    named_insured_mailing_address_city_name_c: Optional[str] = Field(None, description="Enter text: The named insured's mailing address city name. ")
    named_insured_mailing_address_line_one_a: Optional[str] = Field(None, description="Enter text: The named insured's mailing address line one. ")
    named_insured_mailing_address_line_one_b: Optional[str] = Field(None, description="Enter text: The named insured's mailing address line one. ")
    named_insured_mailing_address_line_one_c: Optional[str] = Field(None, description="Enter text: The named insured's mailing address line one. ")
    named_insured_mailing_address_line_two_a: Optional[str] = Field(None, description="Enter text: The named insured's mailing address line two. ")
    named_insured_mailing_address_line_two_b: Optional[str] = Field(None, description="Enter text: The named insured's mailing address line two. ")
    named_insured_mailing_address_line_two_c: Optional[str] = Field(None, description="Enter text: The named insured's mailing address line two. ")
    named_insured_mailing_address_postal_code_a: Optional[str] = Field(None, description="Enter code: The named insured's mailing address postal code. ")
    named_insured_mailing_address_postal_code_b: Optional[str] = Field(None, description="Enter code: The named insured's mailing address postal code. ")
    named_insured_mailing_address_postal_code_c: Optional[str] = Field(None, description="Enter code: The named insured's mailing address postal code. ")
    named_insured_mailing_address_state_or_province_code_a: Optional[str] = Field(None, description="Enter code: The named insured's mailing address state or province code. ")
    named_insured_mailing_address_state_or_province_code_b: Optional[str] = Field(None, description="Enter code: The named insured's mailing address state or province code. ")
    named_insured_mailing_address_state_or_province_code_c: Optional[str] = Field(None, description="Enter code: The named insured's mailing address state or province code. ")
    named_insured_naics_code_a: Optional[str] = Field(None, description="Enter code: The North American Industry Classification System (NAICS) 6-digit industry code assigned to the business activity (if known). ")
    named_insured_naics_code_b: Optional[str] = Field(None, description="Enter code: The North American Industry Classification System (NAICS) 6-digit industry code assigned to the business activity (if known). ")
    named_insured_naics_code_c: Optional[str] = Field(None, description="Enter code: The North American Industry Classification System (NAICS) 6-digit industry code assigned to the business activity (if known). ")
    named_insured_primary_phone_number_a: Optional[str] = Field(None, description="Enter number: The named insured's primary phone number. ")
    named_insured_primary_phone_number_b: Optional[str] = Field(None, description="Enter number: The named insured's primary phone number. ")
    named_insured_primary_phone_number_c: Optional[str] = Field(None, description="Enter number: The named insured's primary phone number. ")
    named_insured_primary_website_address_a: Optional[str] = Field(None, description="Enter text: The primary website address for the named insured. ")
    named_insured_primary_website_address_b: Optional[str] = Field(None, description="Enter text: The primary website address for the named insured. ")
    named_insured_primary_website_address_c: Optional[str] = Field(None, description="Enter text: The primary website address for the named insured. ")
    named_insured_sic_code_a: Optional[str] = Field(None, description="Enter code: The Standard Industry Classification code assigned to the business activity (if known).  This is the code which represents the nature of the employer's business which is contained in th...")
    named_insured_sic_code_b: Optional[str] = Field(None, description="Enter code: The Standard Industry Classification code assigned to the business activity (if known).  This is the code which represents the nature of the employer's business which is contained in th...")
    named_insured_sic_code_c: Optional[str] = Field(None, description="Enter code: The Standard Industry Classification code assigned to the business activity (if known).  This is the code which represents the nature of the employer's business which is contained in th...")
    named_insured_signature_a: Optional[str] = Field(None, description="Sign here: Accommodates the signature of the applicant or named insured. ")
    named_insured_signature_date_a: Optional[str] = Field(None, description="Enter date: The date the form was signed by the applicant or named insured.  (MM/DD/YYYY) ")
    named_insured_tax_identifier_a: Optional[str] = Field(None, description="Enter identifier: The tax identifier of the named insured. ")
    named_insured_tax_identifier_b: Optional[str] = Field(None, description="Enter identifier: The tax identifier of the named insured. ")
    named_insured_tax_identifier_c: Optional[str] = Field(None, description="Enter identifier: The tax identifier of the named insured. ")
    other_policy_line_of_business_code_a: Optional[str] = Field(None, description="Enter code: The line of business of the other policy. ")
    other_policy_line_of_business_code_b: Optional[str] = Field(None, description="Enter code: The line of business of the other policy. ")
    other_policy_line_of_business_code_c: Optional[str] = Field(None, description="Enter code: The line of business of the other policy. ")
    other_policy_line_of_business_code_d: Optional[str] = Field(None, description="Enter code: The line of business of the other policy. ")
    other_policy_policy_number_identifier_a: Optional[str] = Field(None, description="Enter identifier: The other policy number exactly as it appears on the policy, including prefix and suffix symbols. ")
    other_policy_policy_number_identifier_b: Optional[str] = Field(None, description="Enter identifier: The other policy number exactly as it appears on the policy, including prefix and suffix symbols. ")
    other_policy_policy_number_identifier_c: Optional[str] = Field(None, description="Enter identifier: The other policy number exactly as it appears on the policy, including prefix and suffix symbols. ")
    other_policy_policy_number_identifier_d: Optional[str] = Field(None, description="Enter identifier: The other policy number exactly as it appears on the policy, including prefix and suffix symbols. ")
    policy_audit_frequency_code_a: Optional[str] = Field(None, description="Enter code: The audit term for policies that are subject to periodic audit.  If the audit period is known, enter the code; A - annual, S - semi-annual, Q - Quarterly, M - Monthly, O - Other. ")
    policy_effective_date_a: Optional[str] = Field(None, description="Enter date: The effective date of the policy.  The date that the terms and conditions of the policy commence.  (MM/DD/YYYY)  As used here, this is the proposed effective date.")
    policy_expiration_date_a: Optional[str] = Field(None, description="Enter date: The date on which the terms and conditions of the policy will expire.  (MM/DD/YYYY)  As used here, this is the proposed expiration date.")
    policy_information_practices_notice_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that a copy of the Notice of Information Practices (ACORD 38 or state specific ACORD 38) has been given to the applicant.  State specific 38s are available ...")
    policy_line_of_business_boiler_and_machinery_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Boiler & Machinery line of business is being selected for coverage. ")
    policy_line_of_business_business_auto_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Business Auto line of business is being selected for coverage. ")
    policy_line_of_business_business_owners_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Business Owners line of business is being selected for coverage. ")
    policy_line_of_business_commercial_general_liability_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Commercial General Liability line of business is being selected for coverage. ")
    policy_line_of_business_commercial_inland_marine_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Commercial Inland Marine line of business is being selected for coverage. ")
    policy_line_of_business_commercial_property_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Commercial Property line of business is being selected for coverage. ")
    policy_line_of_business_crime_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Crime line of business is being selected for coverage. ")
    policy_line_of_business_cyber_and_privacy_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Cyber and Privacy line of business is being selected for coverage. ")
    policy_line_of_business_fiduciary_liability_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Fiduciary Liability line of business is being selected for coverage. ")
    policy_line_of_business_garage_and_dealers_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Garage and Dealers line of business is being selected for coverage. ")
    policy_line_of_business_liquor_liability_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Liquor Liability line of business is being selected for coverage. ")
    policy_line_of_business_motor_carrier_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Motor Carrier line of business is being selected for coverage. ")
    policy_line_of_business_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that lines of business other than those listed are being selected for coverage. ")
    policy_line_of_business_other_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that lines of business other than those listed are being selected for coverage. ")
    policy_line_of_business_other_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that lines of business other than those listed are being selected for coverage. ")
    policy_line_of_business_other_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that lines of business other than those listed are being selected for coverage. ")
    policy_line_of_business_other_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that lines of business other than those listed are being selected for coverage. ")
    policy_line_of_business_other_indicator_f: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that lines of business other than those listed are being selected for coverage. ")
    policy_line_of_business_other_line_of_business_description_a: Optional[str] = Field(None, description="Enter text: The description of the other line of business. ")
    policy_line_of_business_other_line_of_business_description_b: Optional[str] = Field(None, description="Enter text: The description of the other line of business. ")
    policy_line_of_business_other_line_of_business_description_c: Optional[str] = Field(None, description="Enter text: The description of the other line of business. ")
    policy_line_of_business_other_line_of_business_description_d: Optional[str] = Field(None, description="Enter text: The description of the other line of business. ")
    policy_line_of_business_other_line_of_business_description_e: Optional[str] = Field(None, description="Enter text: The description of the other line of business. ")
    policy_line_of_business_other_line_of_business_description_f: Optional[str] = Field(None, description="Enter text: The description of the other line of business. ")
    policy_line_of_business_truckers_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Truckers line of business is being selected for coverage. ")
    policy_line_of_business_umbrella_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Umbrella line of business is being selected for coverage. ")
    policy_line_of_business_yacht_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates that Yacht line of business is being selected for coverage. ")
    policy_payment_deposit_amount_a: Optional[str] = Field(None, description="Enter amount: The amount of the premium received as a deposit. ")
    policy_payment_direct_bill_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is to be direct billed. ")
    policy_payment_estimated_total_amount_a: Optional[str] = Field(None, description="Enter amount: The estimated total cost amount of the policy. ")
    policy_payment_method_method_description_a: Optional[str] = Field(None, description="Enter text: The method the invoice will be paid. ")
    policy_payment_minimum_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The minimum premium amount for the policy. ")
    policy_payment_payment_schedule_code_a: Optional[str] = Field(None, description="Enter code: The payment plan for the policy (i.e., AN - Annual, MO - Monthly, QT - Quarterly, etc.). ")
    policy_payment_producer_bill_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is to be producer / agency billed. ")
    policy_policy_number_identifier_a: Optional[str] = Field(None, description="Enter identifier: The identifier assigned by the insurer to the policy, or submission, being referenced exactly as it appears on the policy, including prefix and suffix symbols.  If required for se...")
    policy_section_attached_accounts_receivable_valuable_papers_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates an Accounts Receivable /  Valuable Papers section is attached to the application. ")
    policy_section_attached_dealer_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Dealers Section is attached to the application. ")
    policy_section_attached_driver_information_schedule_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Driver Information Schedule is attached to the application. ")
    policy_section_attached_electronic_data_processing_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates an Electronic Data Processing Section is attached to this application. ")
    policy_section_attached_glass_and_sign_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Glass and Sign Section is attached to the application. ")
    policy_section_attached_installation_builders_risk_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates an Installation / Builder's Risk Section is attached to the application. ")
    policy_section_attached_open_cargo_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates an Open Cargo Section is attached to the application. ")
    policy_section_attached_other_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount the for the other line of business. ")
    policy_section_attached_other_premium_amount_b: Optional[str] = Field(None, description="Enter amount: The premium amount the for the other line of business. ")
    policy_section_attached_other_premium_amount_c: Optional[str] = Field(None, description="Enter amount: The premium amount the for the other line of business. ")
    policy_section_attached_other_premium_amount_d: Optional[str] = Field(None, description="Enter amount: The premium amount the for the other line of business. ")
    policy_section_attached_other_premium_amount_e: Optional[str] = Field(None, description="Enter amount: The premium amount the for the other line of business. ")
    policy_section_attached_other_premium_amount_f: Optional[str] = Field(None, description="Enter amount: The premium amount the for the other line of business. ")
    policy_section_attached_vehicle_schedule_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates a Vehicle Schedule is attached to the application. ")
    policy_status_bound_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the coverage has been bound. ")
    policy_status_cancel_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is being submitted for cancellation. ")
    policy_status_change_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the policy is being submitted for a policy change. ")
    policy_status_effective_date_a: Optional[str] = Field(None, description="Enter date: The date the policy status becomes effective.  This date is used for policy statuses of bound, change, and cancel.  (MM/DD/YYYY) ")
    policy_status_effective_time_a: Optional[str] = Field(None, description="Enter time: The time the policy status becomes effective.  The time is used for policy statuses of bound, change, and cancel. ")
    policy_status_effective_time_am_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the effective time of the policy status is before 12:00 pm. ")
    policy_status_effective_time_pm_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the effective time of the policy status is 12:00 pm or later. ")
    policy_status_issue_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the response expected from the company is an issued policy. ")
    policy_status_quote_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the response expected from the company is a quote. ")
    policy_status_renew_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the response expected from the company is a renewed policy. ")
    prior_coverage_automobile_effective_date_a: Optional[str] = Field(None, description="Enter date: The effective date of the prior automobile policy. ")
    prior_coverage_automobile_effective_date_b: Optional[str] = Field(None, description="Enter date: The effective date of the prior automobile policy. ")
    prior_coverage_automobile_effective_date_c: Optional[str] = Field(None, description="Enter date: The effective date of the prior automobile policy. ")
    prior_coverage_automobile_expiration_date_a: Optional[str] = Field(None, description="Enter date: The expiration date of the previous automobile coverage. ")
    prior_coverage_automobile_expiration_date_b: Optional[str] = Field(None, description="Enter date: The expiration date of the previous automobile coverage. ")
    prior_coverage_automobile_expiration_date_c: Optional[str] = Field(None, description="Enter date: The expiration date of the previous automobile coverage. ")
    prior_coverage_automobile_insurer_full_name_a: Optional[str] = Field(None, description="Enter text: The name of the previous automobile insurer. ")
    prior_coverage_automobile_insurer_full_name_b: Optional[str] = Field(None, description="Enter text: The name of the previous automobile insurer. ")
    prior_coverage_automobile_insurer_full_name_c: Optional[str] = Field(None, description="Enter text: The name of the previous automobile insurer. ")
    prior_coverage_automobile_policy_number_identifier_a: Optional[str] = Field(None, description="Enter number: The automobile policy number of the previous coverage. ")
    prior_coverage_automobile_policy_number_identifier_b: Optional[str] = Field(None, description="Enter number: The automobile policy number of the previous coverage. ")
    prior_coverage_automobile_policy_number_identifier_c: Optional[str] = Field(None, description="Enter number: The automobile policy number of the previous coverage. ")
    prior_coverage_automobile_total_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the automobile line of business. ")
    prior_coverage_automobile_total_premium_amount_b: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the automobile line of business. ")
    prior_coverage_automobile_total_premium_amount_c: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the automobile line of business. ")
    prior_coverage_general_liability_effective_date_a: Optional[str] = Field(None, description="Enter date: The effective date of the prior general liability policy. ")
    prior_coverage_general_liability_effective_date_b: Optional[str] = Field(None, description="Enter date: The effective date of the prior general liability policy. ")
    prior_coverage_general_liability_effective_date_c: Optional[str] = Field(None, description="Enter date: The effective date of the prior general liability policy. ")
    prior_coverage_general_liability_expiration_date_a: Optional[str] = Field(None, description="Enter date: The expiration date of the previous general liability coverage. ")
    prior_coverage_general_liability_expiration_date_b: Optional[str] = Field(None, description="Enter date: The expiration date of the previous general liability coverage. ")
    prior_coverage_general_liability_expiration_date_c: Optional[str] = Field(None, description="Enter date: The expiration date of the previous general liability coverage. ")
    prior_coverage_general_liability_insurer_full_name_a: Optional[str] = Field(None, description="Enter text: The name of the previous general liability insurer. ")
    prior_coverage_general_liability_insurer_full_name_b: Optional[str] = Field(None, description="Enter text: The name of the previous general liability insurer. ")
    prior_coverage_general_liability_insurer_full_name_c: Optional[str] = Field(None, description="Enter text: The name of the previous general liability insurer. ")
    prior_coverage_general_liability_policy_number_identifier_a: Optional[str] = Field(None, description="Enter number: The general liability policy number of the previous coverage. ")
    prior_coverage_general_liability_policy_number_identifier_b: Optional[str] = Field(None, description="Enter number: The general liability policy number of the previous coverage. ")
    prior_coverage_general_liability_policy_number_identifier_c: Optional[str] = Field(None, description="Enter number: The general liability policy number of the previous coverage. ")
    prior_coverage_general_liability_total_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the general liability line of business. ")
    prior_coverage_general_liability_total_premium_amount_b: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the general liability line of business. ")
    prior_coverage_general_liability_total_premium_amount_c: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the general liability line of business. ")
    prior_coverage_other_line_effective_date_a: Optional[str] = Field(None, description="Enter date: The effective date of the prior policy for the other line of business. ")
    prior_coverage_other_line_effective_date_b: Optional[str] = Field(None, description="Enter date: The effective date of the prior policy for the other line of business. ")
    prior_coverage_other_line_effective_date_c: Optional[str] = Field(None, description="Enter date: The effective date of the prior policy for the other line of business. ")
    prior_coverage_other_line_expiration_date_a: Optional[str] = Field(None, description="Enter date: The expiration date of the previous  coverage for the other line of business. ")
    prior_coverage_other_line_expiration_date_b: Optional[str] = Field(None, description="Enter date: The expiration date of the previous  coverage for the other line of business. ")
    prior_coverage_other_line_expiration_date_c: Optional[str] = Field(None, description="Enter date: The expiration date of the previous  coverage for the other line of business. ")
    prior_coverage_other_line_insurer_full_name_a: Optional[str] = Field(None, description="Enter text: The name of the previous insurer for the other line of business. ")
    prior_coverage_other_line_insurer_full_name_b: Optional[str] = Field(None, description="Enter text: The name of the previous insurer for the other line of business. ")
    prior_coverage_other_line_insurer_full_name_c: Optional[str] = Field(None, description="Enter text: The name of the previous insurer for the other line of business. ")
    prior_coverage_other_line_line_of_business_code_a: Optional[str] = Field(None, description="Enter code: The line of business code used to identify the other prior coverage. ")
    prior_coverage_other_line_policy_number_identifier_a: Optional[str] = Field(None, description="Enter number: The  policy number of the previous coverage for the other line of business. ")
    prior_coverage_other_line_policy_number_identifier_b: Optional[str] = Field(None, description="Enter number: The  policy number of the previous coverage for the other line of business. ")
    prior_coverage_other_line_policy_number_identifier_c: Optional[str] = Field(None, description="Enter number: The  policy number of the previous coverage for the other line of business. ")
    prior_coverage_other_line_total_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for other lines of business. ")
    prior_coverage_other_line_total_premium_amount_b: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for other lines of business. ")
    prior_coverage_other_line_total_premium_amount_c: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for other lines of business. ")
    prior_coverage_policy_year_a: Optional[str] = Field(None, description="Enter year: The year for which you are providing information. ")
    prior_coverage_policy_year_b: Optional[str] = Field(None, description="Enter year: The year for which you are providing information. ")
    prior_coverage_policy_year_c: Optional[str] = Field(None, description="Enter year: The year for which you are providing information. ")
    prior_coverage_property_effective_date_a: Optional[str] = Field(None, description="Enter date: The effective date of the prior property policy. ")
    prior_coverage_property_effective_date_b: Optional[str] = Field(None, description="Enter date: The effective date of the prior property policy. ")
    prior_coverage_property_effective_date_c: Optional[str] = Field(None, description="Enter date: The effective date of the prior property policy. ")
    prior_coverage_property_expiration_date_a: Optional[str] = Field(None, description="Enter date: The expiration date of the previous property coverage. ")
    prior_coverage_property_expiration_date_b: Optional[str] = Field(None, description="Enter date: The expiration date of the previous property coverage. ")
    prior_coverage_property_expiration_date_c: Optional[str] = Field(None, description="Enter date: The expiration date of the previous property coverage. ")
    prior_coverage_property_insurer_full_name_a: Optional[str] = Field(None, description="Enter text: The name of the previous property insurer. ")
    prior_coverage_property_insurer_full_name_b: Optional[str] = Field(None, description="Enter text: The name of the previous property insurer. ")
    prior_coverage_property_insurer_full_name_c: Optional[str] = Field(None, description="Enter text: The name of the previous property insurer. ")
    prior_coverage_property_policy_number_identifier_a: Optional[str] = Field(None, description="Enter number: The policy number of the previous property coverage. ")
    prior_coverage_property_policy_number_identifier_b: Optional[str] = Field(None, description="Enter number: The policy number of the previous property coverage. ")
    prior_coverage_property_policy_number_identifier_c: Optional[str] = Field(None, description="Enter number: The policy number of the previous property coverage. ")
    prior_coverage_property_total_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the property line of business. ")
    prior_coverage_property_total_premium_amount_b: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the property line of business. ")
    prior_coverage_property_total_premium_amount_c: Optional[str] = Field(None, description="Enter amount: The annual modified premium charged (not including taxes or service charges) for the property line of business. ")
    producer_authorized_representative_full_name_a: Optional[str] = Field(None, description="Enter text: The name of the authorized representative of the producer, agency and/or broker that signed the form. ")
    producer_authorized_representative_signature_a: Optional[str] = Field(None, description="Sign here: Accommodates the signature of the authorized representative (e.g., producer, agent, broker, etc.) of the company(ies) listed on the document.  This is required in most states. ")
    producer_contact_person_email_address_a: Optional[str] = Field(None, description="Enter text: The producer's contact person's e-mail address. ")
    producer_contact_person_full_name_a: Optional[str] = Field(None, description="Enter text: The name of the individual at the producer's establishment that is the primary contact. ")
    producer_contact_person_phone_number_a: Optional[str] = Field(None, description="Enter number: The producer's contact person's phone number.  If applicable, include the area code and extension. ")
    producer_customer_identifier_a: Optional[str] = Field(None, description="Enter identifier: The customer's identification number assigned by the producer (e.g., agency or brokerage). ")
    producer_fax_number_a: Optional[str] = Field(None, description="Enter number: The fax number of the producer / agency. ")
    producer_full_name_a: Optional[str] = Field(None, description="Enter text: The full name of the producer / agency. ")
    producer_mailing_address_city_name_a: Optional[str] = Field(None, description="Enter text: The mailing address city name of the producer / agency. ")
    producer_mailing_address_line_one_a: Optional[str] = Field(None, description="Enter text: The mailing address line one of the producer / agency. ")
    producer_mailing_address_line_two_a: Optional[str] = Field(None, description="Enter text: The mailing address line two of the producer / agency. ")
    producer_mailing_address_postal_code_a: Optional[str] = Field(None, description="Enter code: The mailing address postal code of the producer / agency. ")
    producer_mailing_address_state_or_province_code_a: Optional[str] = Field(None, description="Enter code: The mailing address state or province code of the producer / agency. ")
    producer_national_identifier_a: Optional[str] = Field(None, description="Enter identifier: The National Producer Number (NPN) as defined in the National Insurance Producer Registry (NIPR).  Note: The NPN is not the same as the producer state license number. ")
    producer_state_license_identifier_a: Optional[str] = Field(None, description="Enter identifier: The State License Number of the producer. ")
    subsidiary_organization_name_a: Optional[str] = Field(None, description="Enter text: The name of the subsidiary of the company.  This may also include owned foundations or charitable trusts. ")
    subsidiary_parent_ownership_percent_a: Optional[str] = Field(None, description="Enter percentage: The percent of ownership by the parent company. ")
    subsidiary_parent_ownership_percent_b: Optional[str] = Field(None, description="Enter percentage: The percent of ownership by the parent company. ")
    subsidiary_parent_subsidiary_relationship_description_a: Optional[str] = Field(None, description="Enter text: The description of the relationship between the parent company and the subsidiary. ")
    subsidiary_parent_subsidiary_relationship_description_b: Optional[str] = Field(None, description="Enter text: The description of the relationship between the parent company and the subsidiary. ")
    truckers_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Truckers line of business. ")
    yacht_line_of_business_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The premium amount for the Yacht line of business. ")

    @classmethod
    def get_field_mapping(cls) -> Dict[str, str]:
        return {
            "additional_interest_account_number_identifier_a": "AdditionalInterest_AccountNumberIdentifier_A",
            "additional_interest_certificate_required_indicator_a": "AdditionalInterest_CertificateRequiredIndicator_A",
            "additional_interest_full_name_a": "AdditionalInterest_FullName_A",
            "additional_interest_full_name_b": "AdditionalInterest_FullName_B",
            "additional_interest_interest_additional_insured_indicator_a": "AdditionalInterest_Interest_AdditionalInsuredIndicator_A",
            "additional_interest_interest_breach_of_warranty_indicator_a": "AdditionalInterest_Interest_BreachOfWarrantyIndicator_A",
            "additional_interest_interest_co_owner_indicator_a": "AdditionalInterest_Interest_CoOwnerIndicator_A",
            "additional_interest_interest_employee_as_lessor_indicator_a": "AdditionalInterest_Interest_EmployeeAsLessorIndicator_A",
            "additional_interest_interest_end_date_a": "AdditionalInterest_InterestEndDate_A",
            "additional_interest_interest_leaseback_owner_indicator_a": "AdditionalInterest_Interest_LeasebackOwnerIndicator_A",
            "additional_interest_interest_lenders_loss_payable_indicator_a": "AdditionalInterest_Interest_LendersLossPayableIndicator_A",
            "additional_interest_interest_lienholder_indicator_a": "AdditionalInterest_Interest_LienholderIndicator_A",
            "additional_interest_interest_loss_payee_indicator_a": "AdditionalInterest_Interest_LossPayeeIndicator_A",
            "additional_interest_interest_mortgagee_indicator_a": "AdditionalInterest_Interest_MortgageeIndicator_A",
            "additional_interest_interest_other_description_a": "AdditionalInterest_Interest_OtherDescription_A",
            "additional_interest_interest_other_indicator_a": "AdditionalInterest_Interest_OtherIndicator_A",
            "additional_interest_interest_owner_indicator_a": "AdditionalInterest_Interest_OwnerIndicator_A",
            "additional_interest_interest_rank_a": "AdditionalInterest_InterestRank_A",
            "additional_interest_interest_reason_description_a": "AdditionalInterest_InterestReasonDescription_A",
            "additional_interest_interest_registrant_indicator_a": "AdditionalInterest_Interest_RegistrantIndicator_A",
            "additional_interest_interest_trustee_indicator_a": "AdditionalInterest_Interest_TrusteeIndicator_A",
            "additional_interest_item_aircraft_producer_identifier_a": "AdditionalInterest_Item_AircraftProducerIdentifier_A",
            "additional_interest_item_airport_identifier_a": "AdditionalInterest_Item_AirportIdentifier_A",
            "additional_interest_item_boat_producer_identifier_a": "AdditionalInterest_Item_BoatProducerIdentifier_A",
            "additional_interest_item_building_producer_identifier_a": "AdditionalInterest_Item_BuildingProducerIdentifier_A",
            "additional_interest_item_description_a": "AdditionalInterest_ItemDescription_A",
            "additional_interest_item_location_producer_identifier_a": "AdditionalInterest_Item_LocationProducerIdentifier_A",
            "additional_interest_item_scheduled_item_class_code_a": "AdditionalInterest_Item_ScheduledItemClassCode_A",
            "additional_interest_item_scheduled_item_producer_identifier_a": "AdditionalInterest_Item_ScheduledItemProducerIdentifier_A",
            "additional_interest_item_vehicle_producer_identifier_a": "AdditionalInterest_Item_VehicleProducerIdentifier_A",
            "additional_interest_loan_amount_a": "AdditionalInterest_LoanAmount_A",
            "additional_interest_mailing_address_city_name_a": "AdditionalInterest_MailingAddress_CityName_A",
            "additional_interest_mailing_address_country_code_a": "AdditionalInterest_MailingAddress_CountryCode_A",
            "additional_interest_mailing_address_line_one_a": "AdditionalInterest_MailingAddress_LineOne_A",
            "additional_interest_mailing_address_line_two_a": "AdditionalInterest_MailingAddress_LineTwo_A",
            "additional_interest_mailing_address_postal_code_a": "AdditionalInterest_MailingAddress_PostalCode_A",
            "additional_interest_mailing_address_state_or_province_code_a": "AdditionalInterest_MailingAddress_StateOrProvinceCode_A",
            "additional_interest_policy_required_indicator_a": "AdditionalInterest_PolicyRequiredIndicator_A",
            "additional_interest_primary_email_address_a": "AdditionalInterest_Primary_EmailAddress_A",
            "additional_interest_primary_fax_number_a": "AdditionalInterest_Primary_FaxNumber_A",
            "additional_interest_primary_phone_number_a": "AdditionalInterest_Primary_PhoneNumber_A",
            "additional_interest_send_bill_indicator_a": "AdditionalInterest_SendBillIndicator_A",
            "boiler_and_machinery_line_of_business_premium_amount_a": "BoilerAndMachineryLineOfBusiness_PremiumAmount_A",
            "building_occupancy_occupied_area_a": "BuildingOccupancy_OccupiedArea_A",
            "building_occupancy_occupied_area_b": "BuildingOccupancy_OccupiedArea_B",
            "building_occupancy_occupied_area_c": "BuildingOccupancy_OccupiedArea_C",
            "building_occupancy_occupied_area_d": "BuildingOccupancy_OccupiedArea_D",
            "building_occupancy_open_to_public_area_a": "BuildingOccupancy_OpenToPublicArea_A",
            "building_occupancy_open_to_public_area_b": "BuildingOccupancy_OpenToPublicArea_B",
            "building_occupancy_open_to_public_area_c": "BuildingOccupancy_OpenToPublicArea_C",
            "building_occupancy_open_to_public_area_d": "BuildingOccupancy_OpenToPublicArea_D",
            "building_occupancy_operations_description_a": "BuildingOccupancy_OperationsDescription_A",
            "building_occupancy_operations_description_b": "BuildingOccupancy_OperationsDescription_B",
            "building_occupancy_operations_description_c": "BuildingOccupancy_OperationsDescription_C",
            "building_occupancy_operations_description_d": "BuildingOccupancy_OperationsDescription_D",
            "business_information_business_type_apartments_indicator_a": "BusinessInformation_BusinessType_ApartmentsIndicator_A",
            "business_information_business_type_condominiums_indicator_a": "BusinessInformation_BusinessType_CondominiumsIndicator_A",
            "business_information_business_type_contractor_indicator_a": "BusinessInformation_BusinessType_ContractorIndicator_A",
            "business_information_business_type_institutional_indicator_a": "BusinessInformation_BusinessType_InstitutionalIndicator_A",
            "business_information_business_type_manufacturing_indicator_a": "BusinessInformation_BusinessType_ManufacturingIndicator_A",
            "business_information_business_type_office_indicator_a": "BusinessInformation_BusinessType_OfficeIndicator_A",
            "business_information_business_type_other_description_a": "BusinessInformation_BusinessType_OtherDescription_A",
            "business_information_business_type_other_indicator_a": "BusinessInformation_BusinessType_OtherIndicator_A",
            "business_information_business_type_restaurant_indicator_a": "BusinessInformation_BusinessType_RestaurantIndicator_A",
            "business_information_business_type_retail_indicator_a": "BusinessInformation_BusinessType_RetailIndicator_A",
            "business_information_business_type_service_indicator_a": "BusinessInformation_BusinessType_ServiceIndicator_A",
            "business_information_business_type_wholesale_indicator_a": "BusinessInformation_BusinessType_WholesaleIndicator_A",
            "business_information_full_time_employee_count_a": "BusinessInformation_FullTimeEmployeeCount_A",
            "business_information_full_time_employee_count_b": "BusinessInformation_FullTimeEmployeeCount_B",
            "business_information_full_time_employee_count_c": "BusinessInformation_FullTimeEmployeeCount_C",
            "business_information_full_time_employee_count_d": "BusinessInformation_FullTimeEmployeeCount_D",
            "business_information_parent_organization_name_a": "BusinessInformation_ParentOrganizationName_A",
            "business_information_part_time_employee_count_a": "BusinessInformation_PartTimeEmployeeCount_A",
            "business_information_part_time_employee_count_b": "BusinessInformation_PartTimeEmployeeCount_B",
            "business_information_part_time_employee_count_c": "BusinessInformation_PartTimeEmployeeCount_C",
            "business_information_part_time_employee_count_d": "BusinessInformation_PartTimeEmployeeCount_D",
            "business_owners_line_of_business_premium_amount_a": "BusinessOwnersLineOfBusiness_PremiumAmount_A",
            "cancel_non_renew_agent_no_longer_writes_for_insurer_indicator_a": "CancelNonRenew_AgentNoLongerWritesForInsurerIndicator_A",
            "cancel_non_renew_non_payment_indicator_a": "CancelNonRenew_NonPaymentIndicator_A",
            "cancel_non_renew_non_renewal_indicator_a": "CancelNonRenew_NonRenewalIndicator_A",
            "cancel_non_renew_other_description_a": "CancelNonRenew_OtherDescription_A",
            "cancel_non_renew_other_indicator_a": "CancelNonRenew_OtherIndicator_A",
            "cancel_non_renew_underwriting_condition_corrected_description_a": "CancelNonRenew_UnderwritingConditionCorrectedDescription_A",
            "cancel_non_renew_underwriting_condition_corrected_indicator_a": "CancelNonRenew_UnderwritingConditionCorrectedIndicator_A",
            "cancel_non_renew_underwriting_indicator_a": "CancelNonRenew_UnderwritingIndicator_A",
            "commercial_inland_marine_line_of_business_premium_amount_a": "CommercialInlandMarineLineOfBusiness_PremiumAmount_A",
            "commercial_policy_any_exposure_to_flammable_explosives_chemicals_explanation_a": "CommercialPolicy_AnyExposureToFlammableExplosivesChemicalsExplanation_A",
            "commercial_policy_applicant_hire_others_operate_drones_explanation_a": "CommercialPolicy_ApplicantHireOthersOperateDronesExplanation_A",
            "commercial_policy_applicant_other_business_ventures_coverage_not_requested_explanation_a": "CommercialPolicy_ApplicantOtherBusinessVenturesCoverageNotRequestedExplanation_A",
            "commercial_policy_applicant_own_lease_operate_drones_explanation_a": "CommercialPolicy_ApplicantOwnLeaseOperateDronesExplanation_A",
            "commercial_policy_attachment_additional_interest_schedule_indicator_a": "CommercialPolicy_Attachment_AdditionalInterestScheduleIndicator_A",
            "commercial_policy_attachment_additional_premises_schedule_indicator_a": "CommercialPolicy_Attachment_AdditionalPremisesScheduleIndicator_A",
            "commercial_policy_attachment_apartment_building_supplement_indicator_a": "CommercialPolicy_Attachment_ApartmentBuildingSupplementIndicator_A",
            "commercial_policy_attachment_condominium_association_by_laws_indicator_a": "CommercialPolicy_Attachment_CondominiumAssociationByLawsIndicator_A",
            "commercial_policy_attachment_contractors_supplement_indicator_a": "CommercialPolicy_Attachment_ContractorsSupplementIndicator_A",
            "commercial_policy_attachment_coverages_schedule_indicator_a": "CommercialPolicy_Attachment_CoveragesScheduleIndicator_A",
            "commercial_policy_attachment_hotel_motel_supplement_indicator_a": "CommercialPolicy_Attachment_HotelMotelSupplementIndicator_A",
            "commercial_policy_attachment_international_liability_exposure_supplement_indicator_a": "CommercialPolicy_Attachment_InternationalLiabilityExposureSupplementIndicator_A",
            "commercial_policy_attachment_international_property_exposure_supplement_indicator_a": "CommercialPolicy_Attachment_InternationalPropertyExposureSupplementIndicator_A",
            "commercial_policy_attachment_loss_summary_indicator_a": "CommercialPolicy_Attachment_LossSummaryIndicator_A",
            "commercial_policy_attachment_other_description_a": "CommercialPolicy_Attachment_OtherDescription_A",
            "commercial_policy_attachment_other_description_b": "CommercialPolicy_Attachment_OtherDescription_B",
            "commercial_policy_attachment_other_description_c": "CommercialPolicy_Attachment_OtherDescription_C",
            "commercial_policy_attachment_other_description_d": "CommercialPolicy_Attachment_OtherDescription_D",
            "commercial_policy_attachment_other_description_e": "CommercialPolicy_Attachment_OtherDescription_E",
            "commercial_policy_attachment_other_description_f": "CommercialPolicy_Attachment_OtherDescription_F",
            "commercial_policy_attachment_other_indicator_a": "CommercialPolicy_Attachment_OtherIndicator_A",
            "commercial_policy_attachment_other_indicator_b": "CommercialPolicy_Attachment_OtherIndicator_B",
            "commercial_policy_attachment_other_indicator_c": "CommercialPolicy_Attachment_OtherIndicator_C",
            "commercial_policy_attachment_other_indicator_d": "CommercialPolicy_Attachment_OtherIndicator_D",
            "commercial_policy_attachment_other_indicator_e": "CommercialPolicy_Attachment_OtherIndicator_E",
            "commercial_policy_attachment_other_indicator_f": "CommercialPolicy_Attachment_OtherIndicator_F",
            "commercial_policy_attachment_premium_payment_supplement_indicator_a": "CommercialPolicy_Attachment_PremiumPaymentSupplementIndicator_A",
            "commercial_policy_attachment_professional_liability_supplement_indicator_a": "CommercialPolicy_Attachment_ProfessionalLiabilitySupplementIndicator_A",
            "commercial_policy_attachment_restaurant_tavern_supplement_indicator_a": "CommercialPolicy_Attachment_RestaurantTavernSupplementIndicator_A",
            "commercial_policy_attachment_state_supplement_indicator_a": "CommercialPolicy_Attachment_StateSupplementIndicator_A",
            "commercial_policy_attachment_statement_of_values_indicator_a": "CommercialPolicy_Attachment_StatementOfValuesIndicator_A",
            "commercial_policy_attachment_vacant_building_supplement_indicator_a": "CommercialPolicy_Attachment_VacantBuildingSupplementIndicator_A",
            "commercial_policy_foreclosure_repossession_bankruptcy_explanation_a": "CommercialPolicy_ForeclosureRepossessionBankruptcyExplanation_A",
            "commercial_policy_foreclosure_repossession_bankruptcy_explanation_b": "CommercialPolicy_ForeclosureRepossessionBankruptcyExplanation_B",
            "commercial_policy_foreclosure_repossession_bankruptcy_occurrence_date_a": "CommercialPolicy_ForeclosureRepossessionBankruptcy_OccurrenceDate_A",
            "commercial_policy_foreclosure_repossession_bankruptcy_occurrence_date_b": "CommercialPolicy_ForeclosureRepossessionBankruptcy_OccurrenceDate_B",
            "commercial_policy_foreclosure_repossession_bankruptcy_resolution_date_a": "CommercialPolicy_ForeclosureRepossessionBankruptcy_ResolutionDate_A",
            "commercial_policy_foreclosure_repossession_bankruptcy_resolution_date_b": "CommercialPolicy_ForeclosureRepossessionBankruptcy_ResolutionDate_B",
            "commercial_policy_foreclosure_repossession_bankruptcy_resolution_description_a": "CommercialPolicy_ForeclosureRepossessionBankruptcy_ResolutionDescription_A",
            "commercial_policy_foreclosure_repossession_bankruptcy_resolution_description_b": "CommercialPolicy_ForeclosureRepossessionBankruptcy_ResolutionDescription_B",
            "commercial_policy_formal_safety_program_monthly_meetings_indicator_b": "CommercialPolicy_FormalSafetyProgram_MonthlyMeetingsIndicator_B",
            "commercial_policy_formal_safety_program_osha_indicator_b": "CommercialPolicy_FormalSafetyProgram_OSHAIndicator_B",
            "commercial_policy_formal_safety_program_other_description_b": "CommercialPolicy_FormalSafetyProgram_OtherDescription_B",
            "commercial_policy_formal_safety_program_other_indicator_b": "CommercialPolicy_FormalSafetyProgram_OtherIndicator_B",
            "commercial_policy_formal_safety_program_safety_manual_indicator_a": "CommercialPolicy_FormalSafetyProgram_SafetyManualIndicator_A",
            "commercial_policy_formal_safety_program_safety_position_indicator_b": "CommercialPolicy_FormalSafetyProgram_SafetyPositionIndicator_B",
            "commercial_policy_judgement_or_lien_explanation_a": "CommercialPolicy_JudgementOrLienExplanation_A",
            "commercial_policy_judgement_or_lien_explanation_b": "CommercialPolicy_JudgementOrLienExplanation_B",
            "commercial_policy_judgement_or_lien_occurrence_date_a": "CommercialPolicy_JudgementOrLien_OccurrenceDate_A",
            "commercial_policy_judgement_or_lien_occurrence_date_b": "CommercialPolicy_JudgementOrLien_OccurrenceDate_B",
            "commercial_policy_judgement_or_lien_resolution_date_a": "CommercialPolicy_JudgementOrLien_ResolutionDate_A",
            "commercial_policy_judgement_or_lien_resolution_date_b": "CommercialPolicy_JudgementOrLien_ResolutionDate_B",
            "commercial_policy_judgement_or_lien_resolution_description_a": "CommercialPolicy_JudgementOrLien_ResolutionDescription_A",
            "commercial_policy_judgement_or_lien_resolution_description_b": "CommercialPolicy_JudgementOrLien_ResolutionDescription_B",
            "commercial_policy_operations_description_a": "CommercialPolicy_OperationsDescription_A",
            "commercial_policy_operations_description_b": "CommercialPolicy_OperationsDescription_B",
            "commercial_policy_past_five_years_any_applicant_indicted_or_convicted_fraud_bribery_arson_explanation_a": "CommercialPolicy_PastFiveYearsAnyApplicantIndictedOrConvictedFraudBriberyArsonExplanation_A",
            "commercial_policy_past_losses_claims_relating_sexual_abuse_discrimination_negligent_hiring_explanation_a": "CommercialPolicy_PastLossesClaimsRelatingSexualAbuseDiscriminationNegligentHiringExplanation_A",
            "commercial_policy_question_aac_code_a": "CommercialPolicy_Question_AACCode_A",
            "commercial_policy_question_aad_code_a": "CommercialPolicy_Question_AADCode_A",
            "commercial_policy_question_aaf_code_a": "CommercialPolicy_Question_AAFCode_A",
            "commercial_policy_question_aah_code_a": "CommercialPolicy_Question_AAHCode_A",
            "commercial_policy_question_aai_code_a": "CommercialPolicy_Question_AAICode_A",
            "commercial_policy_question_aaj_code_a": "CommercialPolicy_Question_AAJCode_A",
            "commercial_policy_question_abb_code_a": "CommercialPolicy_Question_ABBCode_A",
            "commercial_policy_question_abc_code_a": "CommercialPolicy_Question_ABCCode_A",
            "commercial_policy_question_kaa_code_a": "CommercialPolicy_Question_KAACode_A",
            "commercial_policy_question_kab_code_a": "CommercialPolicy_Question_KABCode_A",
            "commercial_policy_question_kac_code_a": "CommercialPolicy_Question_KACCode_A",
            "commercial_policy_question_kak_code_a": "CommercialPolicy_Question_KAKCode_A",
            "commercial_policy_question_kal_code_a": "CommercialPolicy_Question_KALCode_A",
            "commercial_policy_question_kam_code_a": "CommercialPolicy_Question_KAMCode_A",
            "commercial_policy_question_kan_code_a": "CommercialPolicy_Question_KANCode_A",
            "commercial_policy_question_kao_code_a": "CommercialPolicy_Question_KAOCode_A",
            "commercial_policy_remark_text_a": "CommercialPolicy_RemarkText_A",
            "commercial_policy_uncorrected_fire_code_violation_explanation_a": "CommercialPolicy_UncorrectedFireCodeViolationExplanation_A",
            "commercial_policy_uncorrected_fire_code_violation_explanation_b": "CommercialPolicy_UncorrectedFireCodeViolationExplanation_B",
            "commercial_policy_uncorrected_fire_code_violation_occurrence_date_a": "CommercialPolicy_UncorrectedFireCodeViolation_OccurrenceDate_A",
            "commercial_policy_uncorrected_fire_code_violation_occurrence_date_b": "CommercialPolicy_UncorrectedFireCodeViolation_OccurrenceDate_B",
            "commercial_policy_uncorrected_fire_code_violation_resolution_date_a": "CommercialPolicy_UncorrectedFireCodeViolation_ResolutionDate_A",
            "commercial_policy_uncorrected_fire_code_violation_resolution_date_b": "CommercialPolicy_UncorrectedFireCodeViolation_ResolutionDate_B",
            "commercial_policy_uncorrected_fire_code_violation_resolution_description_a": "CommercialPolicy_UncorrectedFireCodeViolation_ResolutionDescription_A",
            "commercial_policy_uncorrected_fire_code_violation_resolution_description_b": "CommercialPolicy_UncorrectedFireCodeViolation_ResolutionDescription_B",
            "commercial_property_line_of_business_premium_amount_a": "CommercialPropertyLineOfBusiness_PremiumAmount_A",
            "commercial_structure_annual_revenue_amount_a": "CommercialStructure_AnnualRevenueAmount_A",
            "commercial_structure_annual_revenue_amount_b": "CommercialStructure_AnnualRevenueAmount_B",
            "commercial_structure_annual_revenue_amount_c": "CommercialStructure_AnnualRevenueAmount_C",
            "commercial_structure_annual_revenue_amount_d": "CommercialStructure_AnnualRevenueAmount_D",
            "commercial_structure_building_producer_identifier_a": "CommercialStructure_Building_ProducerIdentifier_A",
            "commercial_structure_building_producer_identifier_b": "CommercialStructure_Building_ProducerIdentifier_B",
            "commercial_structure_building_producer_identifier_c": "CommercialStructure_Building_ProducerIdentifier_C",
            "commercial_structure_building_producer_identifier_d": "CommercialStructure_Building_ProducerIdentifier_D",
            "commercial_structure_installation_repair_work_off_premises_percent_a": "CommercialStructure_InstallationRepairWorkOffPremisesPercent_A",
            "commercial_structure_installation_repair_work_percent_a": "CommercialStructure_InstallationRepairWorkPercent_A",
            "commercial_structure_insured_interest_other_description_a": "CommercialStructure_InsuredInterest_OtherDescription_A",
            "commercial_structure_insured_interest_other_description_b": "CommercialStructure_InsuredInterest_OtherDescription_B",
            "commercial_structure_insured_interest_other_description_c": "CommercialStructure_InsuredInterest_OtherDescription_C",
            "commercial_structure_insured_interest_other_description_d": "CommercialStructure_InsuredInterest_OtherDescription_D",
            "commercial_structure_insured_interest_other_indicator_a": "CommercialStructure_InsuredInterest_OtherIndicator_A",
            "commercial_structure_insured_interest_other_indicator_b": "CommercialStructure_InsuredInterest_OtherIndicator_B",
            "commercial_structure_insured_interest_other_indicator_c": "CommercialStructure_InsuredInterest_OtherIndicator_C",
            "commercial_structure_insured_interest_other_indicator_d": "CommercialStructure_InsuredInterest_OtherIndicator_D",
            "commercial_structure_insured_interest_owner_indicator_a": "CommercialStructure_InsuredInterest_OwnerIndicator_A",
            "commercial_structure_insured_interest_owner_indicator_b": "CommercialStructure_InsuredInterest_OwnerIndicator_B",
            "commercial_structure_insured_interest_owner_indicator_c": "CommercialStructure_InsuredInterest_OwnerIndicator_C",
            "commercial_structure_insured_interest_owner_indicator_d": "CommercialStructure_InsuredInterest_OwnerIndicator_D",
            "commercial_structure_insured_interest_tenant_indicator_a": "CommercialStructure_InsuredInterest_TenantIndicator_A",
            "commercial_structure_insured_interest_tenant_indicator_b": "CommercialStructure_InsuredInterest_TenantIndicator_B",
            "commercial_structure_insured_interest_tenant_indicator_c": "CommercialStructure_InsuredInterest_TenantIndicator_C",
            "commercial_structure_insured_interest_tenant_indicator_d": "CommercialStructure_InsuredInterest_TenantIndicator_D",
            "commercial_structure_location_producer_identifier_a": "CommercialStructure_Location_ProducerIdentifier_A",
            "commercial_structure_location_producer_identifier_b": "CommercialStructure_Location_ProducerIdentifier_B",
            "commercial_structure_location_producer_identifier_c": "CommercialStructure_Location_ProducerIdentifier_C",
            "commercial_structure_location_producer_identifier_d": "CommercialStructure_Location_ProducerIdentifier_D",
            "commercial_structure_physical_address_city_name_a": "CommercialStructure_PhysicalAddress_CityName_A",
            "commercial_structure_physical_address_city_name_b": "CommercialStructure_PhysicalAddress_CityName_B",
            "commercial_structure_physical_address_city_name_c": "CommercialStructure_PhysicalAddress_CityName_C",
            "commercial_structure_physical_address_city_name_d": "CommercialStructure_PhysicalAddress_CityName_D",
            "commercial_structure_physical_address_county_name_a": "CommercialStructure_PhysicalAddress_CountyName_A",
            "commercial_structure_physical_address_county_name_b": "CommercialStructure_PhysicalAddress_CountyName_B",
            "commercial_structure_physical_address_county_name_c": "CommercialStructure_PhysicalAddress_CountyName_C",
            "commercial_structure_physical_address_county_name_d": "CommercialStructure_PhysicalAddress_CountyName_D",
            "commercial_structure_physical_address_line_one_a": "CommercialStructure_PhysicalAddress_LineOne_A",
            "commercial_structure_physical_address_line_one_b": "CommercialStructure_PhysicalAddress_LineOne_B",
            "commercial_structure_physical_address_line_one_c": "CommercialStructure_PhysicalAddress_LineOne_C",
            "commercial_structure_physical_address_line_one_d": "CommercialStructure_PhysicalAddress_LineOne_D",
            "commercial_structure_physical_address_line_two_a": "CommercialStructure_PhysicalAddress_LineTwo_A",
            "commercial_structure_physical_address_line_two_b": "CommercialStructure_PhysicalAddress_LineTwo_B",
            "commercial_structure_physical_address_line_two_c": "CommercialStructure_PhysicalAddress_LineTwo_C",
            "commercial_structure_physical_address_line_two_d": "CommercialStructure_PhysicalAddress_LineTwo_D",
            "commercial_structure_physical_address_postal_code_a": "CommercialStructure_PhysicalAddress_PostalCode_A",
            "commercial_structure_physical_address_postal_code_b": "CommercialStructure_PhysicalAddress_PostalCode_B",
            "commercial_structure_physical_address_postal_code_c": "CommercialStructure_PhysicalAddress_PostalCode_C",
            "commercial_structure_physical_address_postal_code_d": "CommercialStructure_PhysicalAddress_PostalCode_D",
            "commercial_structure_physical_address_state_or_province_code_a": "CommercialStructure_PhysicalAddress_StateOrProvinceCode_A",
            "commercial_structure_physical_address_state_or_province_code_b": "CommercialStructure_PhysicalAddress_StateOrProvinceCode_B",
            "commercial_structure_physical_address_state_or_province_code_c": "CommercialStructure_PhysicalAddress_StateOrProvinceCode_C",
            "commercial_structure_physical_address_state_or_province_code_d": "CommercialStructure_PhysicalAddress_StateOrProvinceCode_D",
            "commercial_structure_question_abb_code_a": "CommercialStructure_Question_ABBCode_A",
            "commercial_structure_question_abb_code_b": "CommercialStructure_Question_ABBCode_B",
            "commercial_structure_question_abb_code_c": "CommercialStructure_Question_ABBCode_C",
            "commercial_structure_question_abb_code_d": "CommercialStructure_Question_ABBCode_D",
            "commercial_structure_risk_location_inside_city_limits_indicator_a": "CommercialStructure_RiskLocation_InsideCityLimitsIndicator_A",
            "commercial_structure_risk_location_inside_city_limits_indicator_b": "CommercialStructure_RiskLocation_InsideCityLimitsIndicator_B",
            "commercial_structure_risk_location_inside_city_limits_indicator_c": "CommercialStructure_RiskLocation_InsideCityLimitsIndicator_C",
            "commercial_structure_risk_location_inside_city_limits_indicator_d": "CommercialStructure_RiskLocation_InsideCityLimitsIndicator_D",
            "commercial_structure_risk_location_other_description_a": "CommercialStructure_RiskLocation_OtherDescription_A",
            "commercial_structure_risk_location_other_description_b": "CommercialStructure_RiskLocation_OtherDescription_B",
            "commercial_structure_risk_location_other_description_c": "CommercialStructure_RiskLocation_OtherDescription_C",
            "commercial_structure_risk_location_other_description_d": "CommercialStructure_RiskLocation_OtherDescription_D",
            "commercial_structure_risk_location_other_indicator_a": "CommercialStructure_RiskLocation_OtherIndicator_A",
            "commercial_structure_risk_location_other_indicator_b": "CommercialStructure_RiskLocation_OtherIndicator_B",
            "commercial_structure_risk_location_other_indicator_c": "CommercialStructure_RiskLocation_OtherIndicator_C",
            "commercial_structure_risk_location_other_indicator_d": "CommercialStructure_RiskLocation_OtherIndicator_D",
            "commercial_structure_risk_location_outside_city_limits_indicator_a": "CommercialStructure_RiskLocation_OutsideCityLimitsIndicator_A",
            "commercial_structure_risk_location_outside_city_limits_indicator_b": "CommercialStructure_RiskLocation_OutsideCityLimitsIndicator_B",
            "commercial_structure_risk_location_outside_city_limits_indicator_c": "CommercialStructure_RiskLocation_OutsideCityLimitsIndicator_C",
            "commercial_structure_risk_location_outside_city_limits_indicator_d": "CommercialStructure_RiskLocation_OutsideCityLimitsIndicator_D",
            "commercial_umbrella_line_of_business_premium_amount_a": "CommercialUmbrellaLineOfBusiness_PremiumAmount_A",
            "commercial_vehicle_line_of_business_premium_amount_a": "CommercialVehicleLineOfBusiness_PremiumAmount_A",
            "construction_building_area_a": "Construction_BuildingArea_A",
            "construction_building_area_b": "Construction_BuildingArea_B",
            "construction_building_area_c": "Construction_BuildingArea_C",
            "construction_building_area_d": "Construction_BuildingArea_D",
            "crime_line_of_business_premium_amount_a": "CrimeLineOfBusiness_PremiumAmount_A",
            "cyber_and_privacy_line_of_business_premium_amount_a": "CyberAndPrivacyLineOfBusiness_PremiumAmount_A",
            "fiduciary_line_of_business_premium_amount_a": "FiduciaryLineOfBusiness_PremiumAmount_A",
            "form_completion_date_a": "Form_CompletionDate_A",
            "form_edition_identifier_a": "Form_EditionIdentifier_A",
            "garage_and_dealers_line_of_business_premium_amount_a": "GarageAndDealersLineOfBusiness_PremiumAmount_A",
            "general_liability_line_of_business_total_premium_amount_a": "GeneralLiabilityLineOfBusiness_TotalPremiumAmount_A",
            "insurer_full_name_a": "Insurer_FullName_A",
            "insurer_naic_code_a": "Insurer_NAICCode_A",
            "insurer_producer_identifier_a": "Insurer_ProducerIdentifier_A",
            "insurer_product_code_a": "Insurer_ProductCode_A",
            "insurer_product_description_a": "Insurer_ProductDescription_A",
            "insurer_sub_producer_identifier_a": "Insurer_SubProducerIdentifier_A",
            "insurer_underwriter_full_name_a": "Insurer_Underwriter_FullName_A",
            "insurer_underwriter_office_identifier_a": "Insurer_Underwriter_OfficeIdentifier_A",
            "liquor_liability_line_of_business_premium_amount_a": "LiquorLiabilityLineOfBusiness_PremiumAmount_A",
            "loss_history_claim_date_a": "LossHistory_ClaimDate_A",
            "loss_history_claim_date_b": "LossHistory_ClaimDate_B",
            "loss_history_claim_date_c": "LossHistory_ClaimDate_C",
            "loss_history_claim_status_open_code_a": "LossHistory_ClaimStatus_OpenCode_A",
            "loss_history_claim_status_open_code_b": "LossHistory_ClaimStatus_OpenCode_B",
            "loss_history_claim_status_open_code_c": "LossHistory_ClaimStatus_OpenCode_C",
            "loss_history_claim_status_subrogation_code_a": "LossHistory_ClaimStatus_SubrogationCode_A",
            "loss_history_claim_status_subrogation_code_b": "LossHistory_ClaimStatus_SubrogationCode_B",
            "loss_history_claim_status_subrogation_code_c": "LossHistory_ClaimStatus_SubrogationCode_C",
            "loss_history_information_year_count_a": "LossHistory_InformationYearCount_A",
            "loss_history_line_of_business_a": "LossHistory_LineOfBusiness_A",
            "loss_history_line_of_business_b": "LossHistory_LineOfBusiness_B",
            "loss_history_line_of_business_c": "LossHistory_LineOfBusiness_C",
            "loss_history_no_prior_losses_indicator_a": "LossHistory_NoPriorLossesIndicator_A",
            "loss_history_occurrence_date_a": "LossHistory_OccurrenceDate_A",
            "loss_history_occurrence_date_b": "LossHistory_OccurrenceDate_B",
            "loss_history_occurrence_date_c": "LossHistory_OccurrenceDate_C",
            "loss_history_occurrence_description_a": "LossHistory_OccurrenceDescription_A",
            "loss_history_occurrence_description_b": "LossHistory_OccurrenceDescription_B",
            "loss_history_occurrence_description_c": "LossHistory_OccurrenceDescription_C",
            "loss_history_paid_amount_a": "LossHistory_PaidAmount_A",
            "loss_history_paid_amount_b": "LossHistory_PaidAmount_B",
            "loss_history_paid_amount_c": "LossHistory_PaidAmount_C",
            "loss_history_reserved_amount_a": "LossHistory_ReservedAmount_A",
            "loss_history_reserved_amount_b": "LossHistory_ReservedAmount_B",
            "loss_history_reserved_amount_c": "LossHistory_ReservedAmount_C",
            "loss_history_total_amount_a": "LossHistory_TotalAmount_A",
            "motor_carrier_line_of_business_premium_amount_a": "MotorCarrierLineOfBusiness_PremiumAmount_A",
            "named_insured_business_start_date_a": "NamedInsured_BusinessStartDate_A",
            "named_insured_contact_contact_description_a": "NamedInsured_Contact_ContactDescription_A",
            "named_insured_contact_contact_description_b": "NamedInsured_Contact_ContactDescription_B",
            "named_insured_contact_full_name_a": "NamedInsured_Contact_FullName_A",
            "named_insured_contact_full_name_b": "NamedInsured_Contact_FullName_B",
            "named_insured_contact_primary_business_phone_indicator_a": "NamedInsured_Contact_PrimaryBusinessPhoneIndicator_A",
            "named_insured_contact_primary_business_phone_indicator_b": "NamedInsured_Contact_PrimaryBusinessPhoneIndicator_B",
            "named_insured_contact_primary_cell_phone_indicator_a": "NamedInsured_Contact_PrimaryCellPhoneIndicator_A",
            "named_insured_contact_primary_cell_phone_indicator_b": "NamedInsured_Contact_PrimaryCellPhoneIndicator_B",
            "named_insured_contact_primary_email_address_a": "NamedInsured_Contact_PrimaryEmailAddress_A",
            "named_insured_contact_primary_email_address_b": "NamedInsured_Contact_PrimaryEmailAddress_B",
            "named_insured_contact_primary_home_phone_indicator_a": "NamedInsured_Contact_PrimaryHomePhoneIndicator_A",
            "named_insured_contact_primary_home_phone_indicator_b": "NamedInsured_Contact_PrimaryHomePhoneIndicator_B",
            "named_insured_contact_primary_phone_number_a": "NamedInsured_Contact_PrimaryPhoneNumber_A",
            "named_insured_contact_primary_phone_number_b": "NamedInsured_Contact_PrimaryPhoneNumber_B",
            "named_insured_contact_secondary_business_phone_indicator_a": "NamedInsured_Contact_SecondaryBusinessPhoneIndicator_A",
            "named_insured_contact_secondary_business_phone_indicator_b": "NamedInsured_Contact_SecondaryBusinessPhoneIndicator_B",
            "named_insured_contact_secondary_cell_phone_indicator_a": "NamedInsured_Contact_SecondaryCellPhoneIndicator_A",
            "named_insured_contact_secondary_cell_phone_indicator_b": "NamedInsured_Contact_SecondaryCellPhoneIndicator_B",
            "named_insured_contact_secondary_email_address_a": "NamedInsured_Contact_SecondaryEmailAddress_A",
            "named_insured_contact_secondary_email_address_b": "NamedInsured_Contact_SecondaryEmailAddress_B",
            "named_insured_contact_secondary_home_phone_indicator_a": "NamedInsured_Contact_SecondaryHomePhoneIndicator_A",
            "named_insured_contact_secondary_home_phone_indicator_b": "NamedInsured_Contact_SecondaryHomePhoneIndicator_B",
            "named_insured_contact_secondary_phone_number_a": "NamedInsured_Contact_SecondaryPhoneNumber_A",
            "named_insured_contact_secondary_phone_number_b": "NamedInsured_Contact_SecondaryPhoneNumber_B",
            "named_insured_full_name_a": "NamedInsured_FullName_A",
            "named_insured_full_name_b": "NamedInsured_FullName_B",
            "named_insured_full_name_c": "NamedInsured_FullName_C",
            "named_insured_general_liability_code_a": "NamedInsured_GeneralLiabilityCode_A",
            "named_insured_general_liability_code_b": "NamedInsured_GeneralLiabilityCode_B",
            "named_insured_general_liability_code_c": "NamedInsured_GeneralLiabilityCode_C",
            "named_insured_initials_a": "NamedInsured_Initials_A",
            "named_insured_legal_entity_corporation_indicator_a": "NamedInsured_LegalEntity_CorporationIndicator_A",
            "named_insured_legal_entity_corporation_indicator_b": "NamedInsured_LegalEntity_CorporationIndicator_B",
            "named_insured_legal_entity_corporation_indicator_c": "NamedInsured_LegalEntity_CorporationIndicator_C",
            "named_insured_legal_entity_individual_indicator_a": "NamedInsured_LegalEntity_IndividualIndicator_A",
            "named_insured_legal_entity_individual_indicator_b": "NamedInsured_LegalEntity_IndividualIndicator_B",
            "named_insured_legal_entity_individual_indicator_c": "NamedInsured_LegalEntity_IndividualIndicator_C",
            "named_insured_legal_entity_joint_venture_indicator_a": "NamedInsured_LegalEntity_JointVentureIndicator_A",
            "named_insured_legal_entity_joint_venture_indicator_b": "NamedInsured_LegalEntity_JointVentureIndicator_B",
            "named_insured_legal_entity_joint_venture_indicator_c": "NamedInsured_LegalEntity_JointVentureIndicator_C",
            "named_insured_legal_entity_limited_liability_corporation_indicator_a": "NamedInsured_LegalEntity_LimitedLiabilityCorporationIndicator_A",
            "named_insured_legal_entity_limited_liability_corporation_indicator_b": "NamedInsured_LegalEntity_LimitedLiabilityCorporationIndicator_B",
            "named_insured_legal_entity_limited_liability_corporation_indicator_c": "NamedInsured_LegalEntity_LimitedLiabilityCorporationIndicator_C",
            "named_insured_legal_entity_member_manager_count_a": "NamedInsured_LegalEntity_MemberManagerCount_A",
            "named_insured_legal_entity_member_manager_count_b": "NamedInsured_LegalEntity_MemberManagerCount_B",
            "named_insured_legal_entity_member_manager_count_c": "NamedInsured_LegalEntity_MemberManagerCount_C",
            "named_insured_legal_entity_not_for_profit_indicator_a": "NamedInsured_LegalEntity_NotForProfitIndicator_A",
            "named_insured_legal_entity_not_for_profit_indicator_b": "NamedInsured_LegalEntity_NotForProfitIndicator_B",
            "named_insured_legal_entity_not_for_profit_indicator_c": "NamedInsured_LegalEntity_NotForProfitIndicator_C",
            "named_insured_legal_entity_other_description_a": "NamedInsured_LegalEntity_OtherDescription_A",
            "named_insured_legal_entity_other_description_b": "NamedInsured_LegalEntity_OtherDescription_B",
            "named_insured_legal_entity_other_description_c": "NamedInsured_LegalEntity_OtherDescription_C",
            "named_insured_legal_entity_other_indicator_a": "NamedInsured_LegalEntity_OtherIndicator_A",
            "named_insured_legal_entity_other_indicator_b": "NamedInsured_LegalEntity_OtherIndicator_B",
            "named_insured_legal_entity_other_indicator_c": "NamedInsured_LegalEntity_OtherIndicator_C",
            "named_insured_legal_entity_partnership_indicator_a": "NamedInsured_LegalEntity_PartnershipIndicator_A",
            "named_insured_legal_entity_partnership_indicator_b": "NamedInsured_LegalEntity_PartnershipIndicator_B",
            "named_insured_legal_entity_partnership_indicator_c": "NamedInsured_LegalEntity_PartnershipIndicator_C",
            "named_insured_legal_entity_subchapter_s_corporation_indicator_a": "NamedInsured_LegalEntity_SubchapterSCorporationIndicator_A",
            "named_insured_legal_entity_subchapter_s_corporation_indicator_b": "NamedInsured_LegalEntity_SubchapterSCorporationIndicator_B",
            "named_insured_legal_entity_subchapter_s_corporation_indicator_c": "NamedInsured_LegalEntity_SubchapterSCorporationIndicator_C",
            "named_insured_legal_entity_trust_indicator_a": "NamedInsured_LegalEntity_TrustIndicator_A",
            "named_insured_legal_entity_trust_indicator_b": "NamedInsured_LegalEntity_TrustIndicator_B",
            "named_insured_legal_entity_trust_indicator_c": "NamedInsured_LegalEntity_TrustIndicator_C",
            "named_insured_mailing_address_city_name_a": "NamedInsured_MailingAddress_CityName_A",
            "named_insured_mailing_address_city_name_b": "NamedInsured_MailingAddress_CityName_B",
            "named_insured_mailing_address_city_name_c": "NamedInsured_MailingAddress_CityName_C",
            "named_insured_mailing_address_line_one_a": "NamedInsured_MailingAddress_LineOne_A",
            "named_insured_mailing_address_line_one_b": "NamedInsured_MailingAddress_LineOne_B",
            "named_insured_mailing_address_line_one_c": "NamedInsured_MailingAddress_LineOne_C",
            "named_insured_mailing_address_line_two_a": "NamedInsured_MailingAddress_LineTwo_A",
            "named_insured_mailing_address_line_two_b": "NamedInsured_MailingAddress_LineTwo_B",
            "named_insured_mailing_address_line_two_c": "NamedInsured_MailingAddress_LineTwo_C",
            "named_insured_mailing_address_postal_code_a": "NamedInsured_MailingAddress_PostalCode_A",
            "named_insured_mailing_address_postal_code_b": "NamedInsured_MailingAddress_PostalCode_B",
            "named_insured_mailing_address_postal_code_c": "NamedInsured_MailingAddress_PostalCode_C",
            "named_insured_mailing_address_state_or_province_code_a": "NamedInsured_MailingAddress_StateOrProvinceCode_A",
            "named_insured_mailing_address_state_or_province_code_b": "NamedInsured_MailingAddress_StateOrProvinceCode_B",
            "named_insured_mailing_address_state_or_province_code_c": "NamedInsured_MailingAddress_StateOrProvinceCode_C",
            "named_insured_naics_code_a": "NamedInsured_NAICSCode_A",
            "named_insured_naics_code_b": "NamedInsured_NAICSCode_B",
            "named_insured_naics_code_c": "NamedInsured_NAICSCode_C",
            "named_insured_primary_phone_number_a": "NamedInsured_Primary_PhoneNumber_A",
            "named_insured_primary_phone_number_b": "NamedInsured_Primary_PhoneNumber_B",
            "named_insured_primary_phone_number_c": "NamedInsured_Primary_PhoneNumber_C",
            "named_insured_primary_website_address_a": "NamedInsured_Primary_WebsiteAddress_A",
            "named_insured_primary_website_address_b": "NamedInsured_Primary_WebsiteAddress_B",
            "named_insured_primary_website_address_c": "NamedInsured_Primary_WebsiteAddress_C",
            "named_insured_sic_code_a": "NamedInsured_SICCode_A",
            "named_insured_sic_code_b": "NamedInsured_SICCode_B",
            "named_insured_sic_code_c": "NamedInsured_SICCode_C",
            "named_insured_signature_a": "NamedInsured_Signature_A",
            "named_insured_signature_date_a": "NamedInsured_SignatureDate_A",
            "named_insured_tax_identifier_a": "NamedInsured_TaxIdentifier_A",
            "named_insured_tax_identifier_b": "NamedInsured_TaxIdentifier_B",
            "named_insured_tax_identifier_c": "NamedInsured_TaxIdentifier_C",
            "other_policy_line_of_business_code_a": "OtherPolicy_LineOfBusinessCode_A",
            "other_policy_line_of_business_code_b": "OtherPolicy_LineOfBusinessCode_B",
            "other_policy_line_of_business_code_c": "OtherPolicy_LineOfBusinessCode_C",
            "other_policy_line_of_business_code_d": "OtherPolicy_LineOfBusinessCode_D",
            "other_policy_policy_number_identifier_a": "OtherPolicy_PolicyNumberIdentifier_A",
            "other_policy_policy_number_identifier_b": "OtherPolicy_PolicyNumberIdentifier_B",
            "other_policy_policy_number_identifier_c": "OtherPolicy_PolicyNumberIdentifier_C",
            "other_policy_policy_number_identifier_d": "OtherPolicy_PolicyNumberIdentifier_D",
            "policy_audit_frequency_code_a": "Policy_Audit_FrequencyCode_A",
            "policy_effective_date_a": "Policy_EffectiveDate_A",
            "policy_expiration_date_a": "Policy_ExpirationDate_A",
            "policy_information_practices_notice_indicator_a": "Policy_InformationPracticesNoticeIndicator_A",
            "policy_line_of_business_boiler_and_machinery_indicator_a": "Policy_LineOfBusiness_BoilerAndMachineryIndicator_A",
            "policy_line_of_business_business_auto_indicator_a": "Policy_LineOfBusiness_BusinessAutoIndicator_A",
            "policy_line_of_business_business_owners_indicator_a": "Policy_LineOfBusiness_BusinessOwnersIndicator_A",
            "policy_line_of_business_commercial_general_liability_a": "Policy_LineOfBusiness_CommercialGeneralLiability_A",
            "policy_line_of_business_commercial_inland_marine_indicator_a": "Policy_LineOfBusiness_CommercialInlandMarineIndicator_A",
            "policy_line_of_business_commercial_property_a": "Policy_LineOfBusiness_CommercialProperty_A",
            "policy_line_of_business_crime_indicator_a": "Policy_LineOfBusiness_CrimeIndicator_A",
            "policy_line_of_business_cyber_and_privacy_a": "Policy_LineOfBusiness_CyberAndPrivacy_A",
            "policy_line_of_business_fiduciary_liability_indicator_a": "Policy_LineOfBusiness_FiduciaryLiabilityIndicator_A",
            "policy_line_of_business_garage_and_dealers_indicator_a": "Policy_LineOfBusiness_GarageAndDealersIndicator_A",
            "policy_line_of_business_liquor_liability_indicator_a": "Policy_LineOfBusiness_LiquorLiabilityIndicator_A",
            "policy_line_of_business_motor_carrier_indicator_a": "Policy_LineOfBusiness_MotorCarrierIndicator_A",
            "policy_line_of_business_other_indicator_a": "Policy_LineOfBusiness_OtherIndicator_A",
            "policy_line_of_business_other_indicator_b": "Policy_LineOfBusiness_OtherIndicator_B",
            "policy_line_of_business_other_indicator_c": "Policy_LineOfBusiness_OtherIndicator_C",
            "policy_line_of_business_other_indicator_d": "Policy_LineOfBusiness_OtherIndicator_D",
            "policy_line_of_business_other_indicator_e": "Policy_LineOfBusiness_OtherIndicator_E",
            "policy_line_of_business_other_indicator_f": "Policy_LineOfBusiness_OtherIndicator_F",
            "policy_line_of_business_other_line_of_business_description_a": "Policy_LineOfBusiness_OtherLineOfBusinessDescription_A",
            "policy_line_of_business_other_line_of_business_description_b": "Policy_LineOfBusiness_OtherLineOfBusinessDescription_B",
            "policy_line_of_business_other_line_of_business_description_c": "Policy_LineOfBusiness_OtherLineOfBusinessDescription_C",
            "policy_line_of_business_other_line_of_business_description_d": "Policy_LineOfBusiness_OtherLineOfBusinessDescription_D",
            "policy_line_of_business_other_line_of_business_description_e": "Policy_LineOfBusiness_OtherLineOfBusinessDescription_E",
            "policy_line_of_business_other_line_of_business_description_f": "Policy_LineOfBusiness_OtherLineOfBusinessDescription_F",
            "policy_line_of_business_truckers_indicator_a": "Policy_LineOfBusiness_TruckersIndicator_A",
            "policy_line_of_business_umbrella_indicator_a": "Policy_LineOfBusiness_UmbrellaIndicator_A",
            "policy_line_of_business_yacht_indicator_a": "Policy_LineOfBusiness_YachtIndicator_A",
            "policy_payment_deposit_amount_a": "Policy_Payment_DepositAmount_A",
            "policy_payment_direct_bill_indicator_a": "Policy_Payment_DirectBillIndicator_A",
            "policy_payment_estimated_total_amount_a": "Policy_Payment_EstimatedTotalAmount_A",
            "policy_payment_method_method_description_a": "Policy_PaymentMethod_MethodDescription_A",
            "policy_payment_minimum_premium_amount_a": "Policy_Payment_MinimumPremiumAmount_A",
            "policy_payment_payment_schedule_code_a": "Policy_Payment_PaymentScheduleCode_A",
            "policy_payment_producer_bill_indicator_a": "Policy_Payment_ProducerBillIndicator_A",
            "policy_policy_number_identifier_a": "Policy_PolicyNumberIdentifier_A",
            "policy_section_attached_accounts_receivable_valuable_papers_indicator_a": "Policy_SectionAttached_AccountsReceivableValuablePapersIndicator_A",
            "policy_section_attached_dealer_indicator_a": "Policy_SectionAttached_DealerIndicator_A",
            "policy_section_attached_driver_information_schedule_indicator_a": "Policy_SectionAttached_DriverInformationScheduleIndicator_A",
            "policy_section_attached_electronic_data_processing_indicator_a": "Policy_SectionAttached_ElectronicDataProcessingIndicator_A",
            "policy_section_attached_glass_and_sign_indicator_a": "Policy_SectionAttached_GlassAndSignIndicator_A",
            "policy_section_attached_installation_builders_risk_indicator_a": "Policy_SectionAttached_InstallationBuildersRiskIndicator_A",
            "policy_section_attached_open_cargo_indicator_a": "Policy_SectionAttached_OpenCargoIndicator_A",
            "policy_section_attached_other_premium_amount_a": "Policy_SectionAttached_OtherPremiumAmount_A",
            "policy_section_attached_other_premium_amount_b": "Policy_SectionAttached_OtherPremiumAmount_B",
            "policy_section_attached_other_premium_amount_c": "Policy_SectionAttached_OtherPremiumAmount_C",
            "policy_section_attached_other_premium_amount_d": "Policy_SectionAttached_OtherPremiumAmount_D",
            "policy_section_attached_other_premium_amount_e": "Policy_SectionAttached_OtherPremiumAmount_E",
            "policy_section_attached_other_premium_amount_f": "Policy_SectionAttached_OtherPremiumAmount_F",
            "policy_section_attached_vehicle_schedule_indicator_a": "Policy_SectionAttached_VehicleScheduleIndicator_A",
            "policy_status_bound_indicator_a": "Policy_Status_BoundIndicator_A",
            "policy_status_cancel_indicator_a": "Policy_Status_CancelIndicator_A",
            "policy_status_change_indicator_a": "Policy_Status_ChangeIndicator_A",
            "policy_status_effective_date_a": "Policy_Status_EffectiveDate_A",
            "policy_status_effective_time_a": "Policy_Status_EffectiveTime_A",
            "policy_status_effective_time_am_indicator_a": "Policy_Status_EffectiveTimeAMIndicator_A",
            "policy_status_effective_time_pm_indicator_a": "Policy_Status_EffectiveTimePMIndicator_A",
            "policy_status_issue_indicator_a": "Policy_Status_IssueIndicator_A",
            "policy_status_quote_indicator_a": "Policy_Status_QuoteIndicator_A",
            "policy_status_renew_indicator_a": "Policy_Status_RenewIndicator_A",
            "prior_coverage_automobile_effective_date_a": "PriorCoverage_Automobile_EffectiveDate_A",
            "prior_coverage_automobile_effective_date_b": "PriorCoverage_Automobile_EffectiveDate_B",
            "prior_coverage_automobile_effective_date_c": "PriorCoverage_Automobile_EffectiveDate_C",
            "prior_coverage_automobile_expiration_date_a": "PriorCoverage_Automobile_ExpirationDate_A",
            "prior_coverage_automobile_expiration_date_b": "PriorCoverage_Automobile_ExpirationDate_B",
            "prior_coverage_automobile_expiration_date_c": "PriorCoverage_Automobile_ExpirationDate_C",
            "prior_coverage_automobile_insurer_full_name_a": "PriorCoverage_Automobile_InsurerFullName_A",
            "prior_coverage_automobile_insurer_full_name_b": "PriorCoverage_Automobile_InsurerFullName_B",
            "prior_coverage_automobile_insurer_full_name_c": "PriorCoverage_Automobile_InsurerFullName_C",
            "prior_coverage_automobile_policy_number_identifier_a": "PriorCoverage_Automobile_PolicyNumberIdentifier_A",
            "prior_coverage_automobile_policy_number_identifier_b": "PriorCoverage_Automobile_PolicyNumberIdentifier_B",
            "prior_coverage_automobile_policy_number_identifier_c": "PriorCoverage_Automobile_PolicyNumberIdentifier_C",
            "prior_coverage_automobile_total_premium_amount_a": "PriorCoverage_Automobile_TotalPremiumAmount_A",
            "prior_coverage_automobile_total_premium_amount_b": "PriorCoverage_Automobile_TotalPremiumAmount_B",
            "prior_coverage_automobile_total_premium_amount_c": "PriorCoverage_Automobile_TotalPremiumAmount_C",
            "prior_coverage_general_liability_effective_date_a": "PriorCoverage_GeneralLiability_EffectiveDate_A",
            "prior_coverage_general_liability_effective_date_b": "PriorCoverage_GeneralLiability_EffectiveDate_B",
            "prior_coverage_general_liability_effective_date_c": "PriorCoverage_GeneralLiability_EffectiveDate_C",
            "prior_coverage_general_liability_expiration_date_a": "PriorCoverage_GeneralLiability_ExpirationDate_A",
            "prior_coverage_general_liability_expiration_date_b": "PriorCoverage_GeneralLiability_ExpirationDate_B",
            "prior_coverage_general_liability_expiration_date_c": "PriorCoverage_GeneralLiability_ExpirationDate_C",
            "prior_coverage_general_liability_insurer_full_name_a": "PriorCoverage_GeneralLiability_InsurerFullName_A",
            "prior_coverage_general_liability_insurer_full_name_b": "PriorCoverage_GeneralLiability_InsurerFullName_B",
            "prior_coverage_general_liability_insurer_full_name_c": "PriorCoverage_GeneralLiability_InsurerFullName_C",
            "prior_coverage_general_liability_policy_number_identifier_a": "PriorCoverage_GeneralLiability_PolicyNumberIdentifier_A",
            "prior_coverage_general_liability_policy_number_identifier_b": "PriorCoverage_GeneralLiability_PolicyNumberIdentifier_B",
            "prior_coverage_general_liability_policy_number_identifier_c": "PriorCoverage_GeneralLiability_PolicyNumberIdentifier_C",
            "prior_coverage_general_liability_total_premium_amount_a": "PriorCoverage_GeneralLiability_TotalPremiumAmount_A",
            "prior_coverage_general_liability_total_premium_amount_b": "PriorCoverage_GeneralLiability_TotalPremiumAmount_B",
            "prior_coverage_general_liability_total_premium_amount_c": "PriorCoverage_GeneralLiability_TotalPremiumAmount_C",
            "prior_coverage_other_line_effective_date_a": "PriorCoverage_OtherLine_EffectiveDate_A",
            "prior_coverage_other_line_effective_date_b": "PriorCoverage_OtherLine_EffectiveDate_B",
            "prior_coverage_other_line_effective_date_c": "PriorCoverage_OtherLine_EffectiveDate_C",
            "prior_coverage_other_line_expiration_date_a": "PriorCoverage_OtherLine_ExpirationDate_A",
            "prior_coverage_other_line_expiration_date_b": "PriorCoverage_OtherLine_ExpirationDate_B",
            "prior_coverage_other_line_expiration_date_c": "PriorCoverage_OtherLine_ExpirationDate_C",
            "prior_coverage_other_line_insurer_full_name_a": "PriorCoverage_OtherLine_InsurerFullName_A",
            "prior_coverage_other_line_insurer_full_name_b": "PriorCoverage_OtherLine_InsurerFullName_B",
            "prior_coverage_other_line_insurer_full_name_c": "PriorCoverage_OtherLine_InsurerFullName_C",
            "prior_coverage_other_line_line_of_business_code_a": "PriorCoverage_OtherLine_LineOfBusinessCode_A",
            "prior_coverage_other_line_policy_number_identifier_a": "PriorCoverage_OtherLine_PolicyNumberIdentifier_A",
            "prior_coverage_other_line_policy_number_identifier_b": "PriorCoverage_OtherLine_PolicyNumberIdentifier_B",
            "prior_coverage_other_line_policy_number_identifier_c": "PriorCoverage_OtherLine_PolicyNumberIdentifier_C",
            "prior_coverage_other_line_total_premium_amount_a": "PriorCoverage_OtherLine_TotalPremiumAmount_A",
            "prior_coverage_other_line_total_premium_amount_b": "PriorCoverage_OtherLine_TotalPremiumAmount_B",
            "prior_coverage_other_line_total_premium_amount_c": "PriorCoverage_OtherLine_TotalPremiumAmount_C",
            "prior_coverage_policy_year_a": "PriorCoverage_PolicyYear_A",
            "prior_coverage_policy_year_b": "PriorCoverage_PolicyYear_B",
            "prior_coverage_policy_year_c": "PriorCoverage_PolicyYear_C",
            "prior_coverage_property_effective_date_a": "PriorCoverage_Property_EffectiveDate_A",
            "prior_coverage_property_effective_date_b": "PriorCoverage_Property_EffectiveDate_B",
            "prior_coverage_property_effective_date_c": "PriorCoverage_Property_EffectiveDate_C",
            "prior_coverage_property_expiration_date_a": "PriorCoverage_Property_ExpirationDate_A",
            "prior_coverage_property_expiration_date_b": "PriorCoverage_Property_ExpirationDate_B",
            "prior_coverage_property_expiration_date_c": "PriorCoverage_Property_ExpirationDate_C",
            "prior_coverage_property_insurer_full_name_a": "PriorCoverage_Property_InsurerFullName_A",
            "prior_coverage_property_insurer_full_name_b": "PriorCoverage_Property_InsurerFullName_B",
            "prior_coverage_property_insurer_full_name_c": "PriorCoverage_Property_InsurerFullName_C",
            "prior_coverage_property_policy_number_identifier_a": "PriorCoverage_Property_PolicyNumberIdentifier_A",
            "prior_coverage_property_policy_number_identifier_b": "PriorCoverage_Property_PolicyNumberIdentifier_B",
            "prior_coverage_property_policy_number_identifier_c": "PriorCoverage_Property_PolicyNumberIdentifier_C",
            "prior_coverage_property_total_premium_amount_a": "PriorCoverage_Property_TotalPremiumAmount_A",
            "prior_coverage_property_total_premium_amount_b": "PriorCoverage_Property_TotalPremiumAmount_B",
            "prior_coverage_property_total_premium_amount_c": "PriorCoverage_Property_TotalPremiumAmount_C",
            "producer_authorized_representative_full_name_a": "Producer_AuthorizedRepresentative_FullName_A",
            "producer_authorized_representative_signature_a": "Producer_AuthorizedRepresentative_Signature_A",
            "producer_contact_person_email_address_a": "Producer_ContactPerson_EmailAddress_A",
            "producer_contact_person_full_name_a": "Producer_ContactPerson_FullName_A",
            "producer_contact_person_phone_number_a": "Producer_ContactPerson_PhoneNumber_A",
            "producer_customer_identifier_a": "Producer_CustomerIdentifier_A",
            "producer_fax_number_a": "Producer_FaxNumber_A",
            "producer_full_name_a": "Producer_FullName_A",
            "producer_mailing_address_city_name_a": "Producer_MailingAddress_CityName_A",
            "producer_mailing_address_line_one_a": "Producer_MailingAddress_LineOne_A",
            "producer_mailing_address_line_two_a": "Producer_MailingAddress_LineTwo_A",
            "producer_mailing_address_postal_code_a": "Producer_MailingAddress_PostalCode_A",
            "producer_mailing_address_state_or_province_code_a": "Producer_MailingAddress_StateOrProvinceCode_A",
            "producer_national_identifier_a": "Producer_NationalIdentifier_A",
            "producer_state_license_identifier_a": "Producer_StateLicenseIdentifier_A",
            "subsidiary_organization_name_a": "Subsidiary_OrganizationName_A",
            "subsidiary_parent_ownership_percent_a": "Subsidiary_ParentOwnershipPercent_A",
            "subsidiary_parent_ownership_percent_b": "Subsidiary_ParentOwnershipPercent_B",
            "subsidiary_parent_subsidiary_relationship_description_a": "Subsidiary_ParentSubsidiaryRelationshipDescription_A",
            "subsidiary_parent_subsidiary_relationship_description_b": "Subsidiary_ParentSubsidiaryRelationshipDescription_B",
            "truckers_line_of_business_premium_amount_a": "TruckersLineOfBusiness_PremiumAmount_A",
            "yacht_line_of_business_premium_amount_a": "YachtLineOfBusiness_PremiumAmount_A",
        }


class Acord127Data(BaseModel):
    """Auto-generated schema for ACORD 127"""
    accident_conviction_driver_producer_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    accident_conviction_incident_date_a_0_: Optional[str] = Field(None, description="No description available.")
    accident_conviction_incident_description_a_0_: Optional[str] = Field(None, description="No description available.")
    accident_conviction_place_of_incident_a_0_: Optional[str] = Field(None, description="No description available.")
    accident_conviction_violation_year_count_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_account_number_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_account_number_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_certificate_required_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_certificate_required_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_full_name_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_full_name_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_full_name_c_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_full_name_d_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_additional_insured_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_additional_insured_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_employee_as_lessor_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_employee_as_lessor_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_lienholder_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_lienholder_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_loss_payee_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_loss_payee_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_other_description_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_other_description_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_other_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_other_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_owner_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_owner_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_rank_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_rank_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_registrant_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_interest_registrant_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_item_location_producer_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_item_location_producer_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_item_vehicle_producer_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_item_vehicle_producer_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_city_name_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_city_name_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_line_one_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_line_one_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_line_two_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_line_two_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_postal_code_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_postal_code_b_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_state_or_province_code_a_0_: Optional[str] = Field(None, description="No description available.")
    additional_interest_mailing_address_state_or_province_code_b_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_agent_inspected_vehicles_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_any_drivers_not_covered_workers_compensation_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_any_vehicles_owned_not_scheduled_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_applicant_obtain_mvr_verifications_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_applicant_specific_driver_recruiting_method_explanation_k_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_attachment_additional_interest_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_attachment_commercial_auto_driver_information_schedule_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_attachment_vehicle_schedule_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_hold_harmless_agreements_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_iccpuc_or_other_filings_required_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_maximum_exposure_all_vehicles_amount_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_operation_involve_transporting_hazardous_materials_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_over_fifty_percent_employees_use_autos_in_business_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aab_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aac_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aad_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aae_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aaf_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aag_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aah_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aai_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aaj_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_aba_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_abb_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_abc_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_kad_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_kae_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_kaf_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_question_kag_code_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_remark_text_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_remark_text_b_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_vehicle_maintenance_program_in_operation_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_vehicles_leased_to_others_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    commercial_vehicle_line_of_business_vehicles_used_by_family_members_explanation_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_birth_date_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_broadened_no_fault_indicator_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_coverage_driver_other_car_indicator_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_experience_year_count_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_gender_code_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_given_name_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_hired_date_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_license_number_identifier_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_state_or_province_code_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_licensed_year_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_city_name_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_line_one_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_postal_code_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_mailing_address_state_or_province_code_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_marital_status_code_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_other_given_name_initial_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_producer_identifier_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_surname_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_tax_identifier_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_producer_identifier_l_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_a_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_b_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_c_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_d_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_e_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_f_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_g_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_h_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_i_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_j_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_k_0_: Optional[str] = Field(None, description="No description available.")
    driver_vehicle_use_percent_l_0_: Optional[str] = Field(None, description="No description available.")
    form_completion_date_a_0_: Optional[str] = Field(None, description="No description available.")
    insurer_full_name_a_0_: Optional[str] = Field(None, description="No description available.")
    insurer_naic_code_a_0_: Optional[str] = Field(None, description="No description available.")
    named_insured_full_name_a_0_: Optional[str] = Field(None, description="No description available.")
    named_insured_signature_a_0_: Optional[str] = Field(None, description="No description available.")
    named_insured_signature_date_a_0_: Optional[str] = Field(None, description="No description available.")
    policy_effective_date_a_0_: Optional[str] = Field(None, description="No description available.")
    policy_policy_number_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    producer_authorized_representative_full_name_a_0_: Optional[str] = Field(None, description="No description available.")
    producer_authorized_representative_signature_a_0_: Optional[str] = Field(None, description="No description available.")
    producer_customer_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    producer_full_name_a_0_: Optional[str] = Field(None, description="No description available.")
    producer_national_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    producer_state_license_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_body_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_body_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_body_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_body_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_collision_deductible_amount_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_collision_deductible_amount_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_collision_deductible_amount_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_collision_deductible_amount_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_collision_symbol_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_collision_symbol_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_collision_symbol_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_collision_symbol_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_comprehensive_symbol_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_comprehensive_symbol_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_comprehensive_symbol_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_comprehensive_symbol_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_cost_new_amount_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_cost_new_amount_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_cost_new_amount_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_cost_new_amount_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_additional_no_fault_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_additional_no_fault_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_additional_no_fault_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_additional_no_fault_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_agreed_or_stated_amount_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_agreed_or_stated_amount_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_agreed_or_stated_amount_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_agreed_or_stated_amount_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_collision_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_collision_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_collision_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_collision_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_deductible_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_deductible_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_deductible_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_deductible_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_theft_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_theft_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_theft_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_theft_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_theft_windstorm_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_theft_windstorm_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_theft_windstorm_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_fire_theft_windstorm_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_full_glass_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_full_glass_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_full_glass_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_full_glass_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_liability_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_liability_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_liability_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_liability_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_limited_specified_perils_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_limited_specified_perils_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_limited_specified_perils_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_limited_specified_perils_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_medical_payments_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_medical_payments_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_medical_payments_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_medical_payments_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_no_fault_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_no_fault_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_no_fault_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_no_fault_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_other_description_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_other_description_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_other_description_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_other_description_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_other_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_other_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_other_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_other_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_rental_reimbursement_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_rental_reimbursement_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_rental_reimbursement_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_rental_reimbursement_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_specified_cause_of_loss_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_specified_cause_of_loss_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_specified_cause_of_loss_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_specified_cause_of_loss_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_towing_and_labour_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_towing_and_labour_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_towing_and_labour_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_towing_and_labour_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_underinsured_motorists_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_underinsured_motorists_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_underinsured_motorists_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_underinsured_motorists_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_uninsured_motorists_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_uninsured_motorists_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_uninsured_motorists_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_uninsured_motorists_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_actual_cash_value_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_actual_cash_value_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_actual_cash_value_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_actual_cash_value_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_agreed_amount_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_agreed_amount_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_agreed_amount_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_agreed_amount_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_stated_amount_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_stated_amount_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_stated_amount_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_coverage_valuation_stated_amount_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_farthest_zone_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_farthest_zone_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_farthest_zone_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_farthest_zone_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_gross_vehicle_weight_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_gross_vehicle_weight_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_gross_vehicle_weight_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_gross_vehicle_weight_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_manufacturers_name_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_manufacturers_name_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_manufacturers_name_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_manufacturers_name_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_model_name_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_model_name_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_model_name_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_model_name_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_model_year_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_model_year_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_model_year_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_model_year_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_net_rating_factor_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_net_rating_factor_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_net_rating_factor_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_net_rating_factor_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_city_name_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_city_name_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_city_name_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_city_name_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_county_name_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_county_name_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_county_name_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_county_name_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_line_one_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_line_one_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_line_one_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_line_one_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_postal_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_postal_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_postal_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_postal_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_state_or_province_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_state_or_province_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_state_or_province_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_physical_address_state_or_province_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_primary_liability_rating_factor_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_primary_liability_rating_factor_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_primary_liability_rating_factor_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_primary_liability_rating_factor_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_producer_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_producer_identifier_aa_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_producer_identifier_ab_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_producer_identifier_ac_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_producer_identifier_ad_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_producer_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_producer_identifier_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_producer_identifier_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_question_modified_equipment_cost_amount_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_question_modified_equipment_cost_amount_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_question_modified_equipment_description_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_question_modified_equipment_description_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_radius_of_use_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_radius_of_use_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_radius_of_use_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_radius_of_use_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_rate_class_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_rate_class_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_rate_class_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_rate_class_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_rating_territory_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_rating_territory_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_rating_territory_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_rating_territory_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_registration_state_or_province_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_registration_state_or_province_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_registration_state_or_province_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_registration_state_or_province_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_seating_capacity_count_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_seating_capacity_count_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_seating_capacity_count_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_seating_capacity_count_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_special_industry_class_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_special_industry_class_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_special_industry_class_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_special_industry_class_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_symbol_code_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_symbol_code_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_symbol_code_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_symbol_code_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_total_premium_amount_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_total_premium_amount_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_total_premium_amount_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_total_premium_amount_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_commercial_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_commercial_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_commercial_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_commercial_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_farm_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_farm_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_farm_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_farm_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_fifteen_miles_or_over_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_fifteen_miles_or_over_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_fifteen_miles_or_over_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_fifteen_miles_or_over_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_for_hire_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_for_hire_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_for_hire_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_for_hire_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_other_description_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_other_description_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_other_description_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_other_description_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_other_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_other_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_other_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_other_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_pleasure_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_pleasure_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_pleasure_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_pleasure_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_retail_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_retail_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_retail_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_retail_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_service_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_service_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_service_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_service_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_under_fifteen_miles_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_under_fifteen_miles_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_under_fifteen_miles_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_use_under_fifteen_miles_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_commercial_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_commercial_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_commercial_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_commercial_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_private_passenger_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_private_passenger_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_private_passenger_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_private_passenger_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_special_indicator_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_special_indicator_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_special_indicator_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vehicle_type_special_indicator_d_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vin_identifier_a_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vin_identifier_b_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vin_identifier_c_0_: Optional[str] = Field(None, description="No description available.")
    vehicle_vin_identifier_d_0_: Optional[str] = Field(None, description="No description available.")

    @classmethod
    def get_field_mapping(cls) -> Dict[str, str]:
        return {
            "accident_conviction_driver_producer_identifier_a_0_": "AccidentConviction_DriverProducerIdentifier_A[0]",
            "accident_conviction_incident_date_a_0_": "AccidentConviction_IncidentDate_A[0]",
            "accident_conviction_incident_description_a_0_": "AccidentConviction_IncidentDescription_A[0]",
            "accident_conviction_place_of_incident_a_0_": "AccidentConviction_PlaceOfIncident_A[0]",
            "accident_conviction_violation_year_count_a_0_": "AccidentConviction_ViolationYearCount_A[0]",
            "additional_interest_account_number_identifier_a_0_": "AdditionalInterest_AccountNumberIdentifier_A[0]",
            "additional_interest_account_number_identifier_b_0_": "AdditionalInterest_AccountNumberIdentifier_B[0]",
            "additional_interest_certificate_required_indicator_a_0_": "AdditionalInterest_CertificateRequiredIndicator_A[0]",
            "additional_interest_certificate_required_indicator_b_0_": "AdditionalInterest_CertificateRequiredIndicator_B[0]",
            "additional_interest_full_name_a_0_": "AdditionalInterest_FullName_A[0]",
            "additional_interest_full_name_b_0_": "AdditionalInterest_FullName_B[0]",
            "additional_interest_full_name_c_0_": "AdditionalInterest_FullName_C[0]",
            "additional_interest_full_name_d_0_": "AdditionalInterest_FullName_D[0]",
            "additional_interest_interest_additional_insured_indicator_a_0_": "AdditionalInterest_Interest_AdditionalInsuredIndicator_A[0]",
            "additional_interest_interest_additional_insured_indicator_b_0_": "AdditionalInterest_Interest_AdditionalInsuredIndicator_B[0]",
            "additional_interest_interest_employee_as_lessor_indicator_a_0_": "AdditionalInterest_Interest_EmployeeAsLessorIndicator_A[0]",
            "additional_interest_interest_employee_as_lessor_indicator_b_0_": "AdditionalInterest_Interest_EmployeeAsLessorIndicator_B[0]",
            "additional_interest_interest_lienholder_indicator_a_0_": "AdditionalInterest_Interest_LienholderIndicator_A[0]",
            "additional_interest_interest_lienholder_indicator_b_0_": "AdditionalInterest_Interest_LienholderIndicator_B[0]",
            "additional_interest_interest_loss_payee_indicator_a_0_": "AdditionalInterest_Interest_LossPayeeIndicator_A[0]",
            "additional_interest_interest_loss_payee_indicator_b_0_": "AdditionalInterest_Interest_LossPayeeIndicator_B[0]",
            "additional_interest_interest_other_description_a_0_": "AdditionalInterest_Interest_OtherDescription_A[0]",
            "additional_interest_interest_other_description_b_0_": "AdditionalInterest_Interest_OtherDescription_B[0]",
            "additional_interest_interest_other_indicator_a_0_": "AdditionalInterest_Interest_OtherIndicator_A[0]",
            "additional_interest_interest_other_indicator_b_0_": "AdditionalInterest_Interest_OtherIndicator_B[0]",
            "additional_interest_interest_owner_indicator_a_0_": "AdditionalInterest_Interest_OwnerIndicator_A[0]",
            "additional_interest_interest_owner_indicator_b_0_": "AdditionalInterest_Interest_OwnerIndicator_B[0]",
            "additional_interest_interest_rank_a_0_": "AdditionalInterest_InterestRank_A[0]",
            "additional_interest_interest_rank_b_0_": "AdditionalInterest_InterestRank_B[0]",
            "additional_interest_interest_registrant_indicator_a_0_": "AdditionalInterest_Interest_RegistrantIndicator_A[0]",
            "additional_interest_interest_registrant_indicator_b_0_": "AdditionalInterest_Interest_RegistrantIndicator_B[0]",
            "additional_interest_item_location_producer_identifier_a_0_": "AdditionalInterest_Item_LocationProducerIdentifier_A[0]",
            "additional_interest_item_location_producer_identifier_b_0_": "AdditionalInterest_Item_LocationProducerIdentifier_B[0]",
            "additional_interest_item_vehicle_producer_identifier_a_0_": "AdditionalInterest_Item_VehicleProducerIdentifier_A[0]",
            "additional_interest_item_vehicle_producer_identifier_b_0_": "AdditionalInterest_Item_VehicleProducerIdentifier_B[0]",
            "additional_interest_mailing_address_city_name_a_0_": "AdditionalInterest_MailingAddress_CityName_A[0]",
            "additional_interest_mailing_address_city_name_b_0_": "AdditionalInterest_MailingAddress_CityName_B[0]",
            "additional_interest_mailing_address_line_one_a_0_": "AdditionalInterest_MailingAddress_LineOne_A[0]",
            "additional_interest_mailing_address_line_one_b_0_": "AdditionalInterest_MailingAddress_LineOne_B[0]",
            "additional_interest_mailing_address_line_two_a_0_": "AdditionalInterest_MailingAddress_LineTwo_A[0]",
            "additional_interest_mailing_address_line_two_b_0_": "AdditionalInterest_MailingAddress_LineTwo_B[0]",
            "additional_interest_mailing_address_postal_code_a_0_": "AdditionalInterest_MailingAddress_PostalCode_A[0]",
            "additional_interest_mailing_address_postal_code_b_0_": "AdditionalInterest_MailingAddress_PostalCode_B[0]",
            "additional_interest_mailing_address_state_or_province_code_a_0_": "AdditionalInterest_MailingAddress_StateOrProvinceCode_A[0]",
            "additional_interest_mailing_address_state_or_province_code_b_0_": "AdditionalInterest_MailingAddress_StateOrProvinceCode_B[0]",
            "commercial_vehicle_line_of_business_agent_inspected_vehicles_explanation_a_0_": "CommercialVehicleLineOfBusiness_AgentInspectedVehiclesExplanation_A[0]",
            "commercial_vehicle_line_of_business_any_drivers_not_covered_workers_compensation_explanation_a_0_": "CommercialVehicleLineOfBusiness_AnyDriversNotCoveredWorkersCompensationExplanation_A[0]",
            "commercial_vehicle_line_of_business_any_vehicles_owned_not_scheduled_explanation_a_0_": "CommercialVehicleLineOfBusiness_AnyVehiclesOwnedNotScheduledExplanation_A[0]",
            "commercial_vehicle_line_of_business_applicant_obtain_mvr_verifications_explanation_a_0_": "CommercialVehicleLineOfBusiness_ApplicantObtainMVRVerificationsExplanation_A[0]",
            "commercial_vehicle_line_of_business_applicant_specific_driver_recruiting_method_explanation_k_0_": "CommercialVehicleLineOfBusiness_ApplicantSpecificDriverRecruitingMethodExplanation_K[0]",
            "commercial_vehicle_line_of_business_attachment_additional_interest_indicator_a_0_": "CommercialVehicleLineOfBusiness_Attachment_AdditionalInterestIndicator_A[0]",
            "commercial_vehicle_line_of_business_attachment_commercial_auto_driver_information_schedule_indicator_a_0_": "CommercialVehicleLineOfBusiness_Attachment_CommercialAutoDriverInformationScheduleIndicator_A[0]",
            "commercial_vehicle_line_of_business_attachment_vehicle_schedule_indicator_a_0_": "CommercialVehicleLineOfBusiness_Attachment_VehicleScheduleIndicator_A[0]",
            "commercial_vehicle_line_of_business_hold_harmless_agreements_explanation_a_0_": "CommercialVehicleLineOfBusiness_HoldHarmlessAgreementsExplanation_A[0]",
            "commercial_vehicle_line_of_business_iccpuc_or_other_filings_required_explanation_a_0_": "CommercialVehicleLineOfBusiness_ICCPUCOrOtherFilingsRequiredExplanation_A[0]",
            "commercial_vehicle_line_of_business_maximum_exposure_all_vehicles_amount_a_0_": "CommercialVehicleLineOfBusiness_MaximumExposureAllVehiclesAmount_A[0]",
            "commercial_vehicle_line_of_business_operation_involve_transporting_hazardous_materials_explanation_a_0_": "CommercialVehicleLineOfBusiness_OperationInvolveTransportingHazardousMaterialsExplanation_A[0]",
            "commercial_vehicle_line_of_business_over_fifty_percent_employees_use_autos_in_business_explanation_a_0_": "CommercialVehicleLineOfBusiness_OverFiftyPercentEmployeesUseAutosInBusinessExplanation_A[0]",
            "commercial_vehicle_line_of_business_question_aab_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AABCode_A[0]",
            "commercial_vehicle_line_of_business_question_aac_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AACCode_A[0]",
            "commercial_vehicle_line_of_business_question_aad_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AADCode_A[0]",
            "commercial_vehicle_line_of_business_question_aae_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AAECode_A[0]",
            "commercial_vehicle_line_of_business_question_aaf_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AAFCode_A[0]",
            "commercial_vehicle_line_of_business_question_aag_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AAGCode_A[0]",
            "commercial_vehicle_line_of_business_question_aah_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AAHCode_A[0]",
            "commercial_vehicle_line_of_business_question_aai_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AAICode_A[0]",
            "commercial_vehicle_line_of_business_question_aaj_code_a_0_": "CommercialVehicleLineOfBusiness_Question_AAJCode_A[0]",
            "commercial_vehicle_line_of_business_question_aba_code_a_0_": "CommercialVehicleLineOfBusiness_Question_ABACode_A[0]",
            "commercial_vehicle_line_of_business_question_abb_code_a_0_": "CommercialVehicleLineOfBusiness_Question_ABBCode_A[0]",
            "commercial_vehicle_line_of_business_question_abc_code_a_0_": "CommercialVehicleLineOfBusiness_Question_ABCCode_A[0]",
            "commercial_vehicle_line_of_business_question_kad_code_a_0_": "CommercialVehicleLineOfBusiness_Question_KADCode_A[0]",
            "commercial_vehicle_line_of_business_question_kae_code_a_0_": "CommercialVehicleLineOfBusiness_Question_KAECode_A[0]",
            "commercial_vehicle_line_of_business_question_kaf_code_a_0_": "CommercialVehicleLineOfBusiness_Question_KAFCode_A[0]",
            "commercial_vehicle_line_of_business_question_kag_code_a_0_": "CommercialVehicleLineOfBusiness_Question_KAGCode_A[0]",
            "commercial_vehicle_line_of_business_remark_text_a_0_": "CommercialVehicleLineOfBusiness_RemarkText_A[0]",
            "commercial_vehicle_line_of_business_remark_text_b_0_": "CommercialVehicleLineOfBusiness_RemarkText_B[0]",
            "commercial_vehicle_line_of_business_vehicle_maintenance_program_in_operation_explanation_a_0_": "CommercialVehicleLineOfBusiness_VehicleMaintenanceProgramInOperationExplanation_A[0]",
            "commercial_vehicle_line_of_business_vehicles_leased_to_others_explanation_a_0_": "CommercialVehicleLineOfBusiness_VehiclesLeasedToOthersExplanation_A[0]",
            "commercial_vehicle_line_of_business_vehicles_used_by_family_members_explanation_a_0_": "CommercialVehicleLineOfBusiness_VehiclesUsedByFamilyMembersExplanation_A[0]",
            "driver_birth_date_a_0_": "Driver_BirthDate_A[0]",
            "driver_birth_date_b_0_": "Driver_BirthDate_B[0]",
            "driver_birth_date_c_0_": "Driver_BirthDate_C[0]",
            "driver_birth_date_d_0_": "Driver_BirthDate_D[0]",
            "driver_birth_date_e_0_": "Driver_BirthDate_E[0]",
            "driver_birth_date_f_0_": "Driver_BirthDate_F[0]",
            "driver_birth_date_g_0_": "Driver_BirthDate_G[0]",
            "driver_birth_date_h_0_": "Driver_BirthDate_H[0]",
            "driver_birth_date_i_0_": "Driver_BirthDate_I[0]",
            "driver_birth_date_j_0_": "Driver_BirthDate_J[0]",
            "driver_birth_date_k_0_": "Driver_BirthDate_K[0]",
            "driver_birth_date_l_0_": "Driver_BirthDate_L[0]",
            "driver_coverage_broadened_no_fault_indicator_a_0_": "Driver_Coverage_BroadenedNoFaultIndicator_A[0]",
            "driver_coverage_broadened_no_fault_indicator_b_0_": "Driver_Coverage_BroadenedNoFaultIndicator_B[0]",
            "driver_coverage_broadened_no_fault_indicator_c_0_": "Driver_Coverage_BroadenedNoFaultIndicator_C[0]",
            "driver_coverage_broadened_no_fault_indicator_d_0_": "Driver_Coverage_BroadenedNoFaultIndicator_D[0]",
            "driver_coverage_broadened_no_fault_indicator_e_0_": "Driver_Coverage_BroadenedNoFaultIndicator_E[0]",
            "driver_coverage_broadened_no_fault_indicator_f_0_": "Driver_Coverage_BroadenedNoFaultIndicator_F[0]",
            "driver_coverage_broadened_no_fault_indicator_g_0_": "Driver_Coverage_BroadenedNoFaultIndicator_G[0]",
            "driver_coverage_broadened_no_fault_indicator_h_0_": "Driver_Coverage_BroadenedNoFaultIndicator_H[0]",
            "driver_coverage_broadened_no_fault_indicator_i_0_": "Driver_Coverage_BroadenedNoFaultIndicator_I[0]",
            "driver_coverage_broadened_no_fault_indicator_j_0_": "Driver_Coverage_BroadenedNoFaultIndicator_J[0]",
            "driver_coverage_broadened_no_fault_indicator_k_0_": "Driver_Coverage_BroadenedNoFaultIndicator_K[0]",
            "driver_coverage_broadened_no_fault_indicator_l_0_": "Driver_Coverage_BroadenedNoFaultIndicator_L[0]",
            "driver_coverage_driver_other_car_indicator_a_0_": "Driver_Coverage_DriverOtherCarIndicator_A[0]",
            "driver_coverage_driver_other_car_indicator_b_0_": "Driver_Coverage_DriverOtherCarIndicator_B[0]",
            "driver_coverage_driver_other_car_indicator_c_0_": "Driver_Coverage_DriverOtherCarIndicator_C[0]",
            "driver_coverage_driver_other_car_indicator_d_0_": "Driver_Coverage_DriverOtherCarIndicator_D[0]",
            "driver_coverage_driver_other_car_indicator_e_0_": "Driver_Coverage_DriverOtherCarIndicator_E[0]",
            "driver_coverage_driver_other_car_indicator_f_0_": "Driver_Coverage_DriverOtherCarIndicator_F[0]",
            "driver_coverage_driver_other_car_indicator_g_0_": "Driver_Coverage_DriverOtherCarIndicator_G[0]",
            "driver_coverage_driver_other_car_indicator_h_0_": "Driver_Coverage_DriverOtherCarIndicator_H[0]",
            "driver_coverage_driver_other_car_indicator_i_0_": "Driver_Coverage_DriverOtherCarIndicator_I[0]",
            "driver_coverage_driver_other_car_indicator_j_0_": "Driver_Coverage_DriverOtherCarIndicator_J[0]",
            "driver_coverage_driver_other_car_indicator_k_0_": "Driver_Coverage_DriverOtherCarIndicator_K[0]",
            "driver_coverage_driver_other_car_indicator_l_0_": "Driver_Coverage_DriverOtherCarIndicator_L[0]",
            "driver_experience_year_count_a_0_": "Driver_ExperienceYearCount_A[0]",
            "driver_experience_year_count_b_0_": "Driver_ExperienceYearCount_B[0]",
            "driver_experience_year_count_c_0_": "Driver_ExperienceYearCount_C[0]",
            "driver_experience_year_count_d_0_": "Driver_ExperienceYearCount_D[0]",
            "driver_experience_year_count_e_0_": "Driver_ExperienceYearCount_E[0]",
            "driver_experience_year_count_f_0_": "Driver_ExperienceYearCount_F[0]",
            "driver_experience_year_count_g_0_": "Driver_ExperienceYearCount_G[0]",
            "driver_experience_year_count_h_0_": "Driver_ExperienceYearCount_H[0]",
            "driver_experience_year_count_i_0_": "Driver_ExperienceYearCount_I[0]",
            "driver_experience_year_count_j_0_": "Driver_ExperienceYearCount_J[0]",
            "driver_experience_year_count_k_0_": "Driver_ExperienceYearCount_K[0]",
            "driver_experience_year_count_l_0_": "Driver_ExperienceYearCount_L[0]",
            "driver_gender_code_a_0_": "Driver_GenderCode_A[0]",
            "driver_gender_code_b_0_": "Driver_GenderCode_B[0]",
            "driver_gender_code_c_0_": "Driver_GenderCode_C[0]",
            "driver_gender_code_d_0_": "Driver_GenderCode_D[0]",
            "driver_gender_code_e_0_": "Driver_GenderCode_E[0]",
            "driver_gender_code_f_0_": "Driver_GenderCode_F[0]",
            "driver_gender_code_g_0_": "Driver_GenderCode_G[0]",
            "driver_gender_code_h_0_": "Driver_GenderCode_H[0]",
            "driver_gender_code_i_0_": "Driver_GenderCode_I[0]",
            "driver_gender_code_j_0_": "Driver_GenderCode_J[0]",
            "driver_gender_code_k_0_": "Driver_GenderCode_K[0]",
            "driver_gender_code_l_0_": "Driver_GenderCode_L[0]",
            "driver_given_name_a_0_": "Driver_GivenName_A[0]",
            "driver_given_name_b_0_": "Driver_GivenName_B[0]",
            "driver_given_name_c_0_": "Driver_GivenName_C[0]",
            "driver_given_name_d_0_": "Driver_GivenName_D[0]",
            "driver_given_name_e_0_": "Driver_GivenName_E[0]",
            "driver_given_name_f_0_": "Driver_GivenName_F[0]",
            "driver_given_name_g_0_": "Driver_GivenName_G[0]",
            "driver_given_name_h_0_": "Driver_GivenName_H[0]",
            "driver_given_name_i_0_": "Driver_GivenName_I[0]",
            "driver_given_name_j_0_": "Driver_GivenName_J[0]",
            "driver_given_name_k_0_": "Driver_GivenName_K[0]",
            "driver_given_name_l_0_": "Driver_GivenName_L[0]",
            "driver_hired_date_a_0_": "Driver_HiredDate_A[0]",
            "driver_hired_date_b_0_": "Driver_HiredDate_B[0]",
            "driver_hired_date_c_0_": "Driver_HiredDate_C[0]",
            "driver_hired_date_d_0_": "Driver_HiredDate_D[0]",
            "driver_hired_date_e_0_": "Driver_HiredDate_E[0]",
            "driver_hired_date_f_0_": "Driver_HiredDate_F[0]",
            "driver_hired_date_g_0_": "Driver_HiredDate_G[0]",
            "driver_hired_date_h_0_": "Driver_HiredDate_H[0]",
            "driver_hired_date_i_0_": "Driver_HiredDate_I[0]",
            "driver_hired_date_j_0_": "Driver_HiredDate_J[0]",
            "driver_hired_date_k_0_": "Driver_HiredDate_K[0]",
            "driver_hired_date_l_0_": "Driver_HiredDate_L[0]",
            "driver_license_number_identifier_a_0_": "Driver_LicenseNumberIdentifier_A[0]",
            "driver_license_number_identifier_b_0_": "Driver_LicenseNumberIdentifier_B[0]",
            "driver_license_number_identifier_c_0_": "Driver_LicenseNumberIdentifier_C[0]",
            "driver_license_number_identifier_d_0_": "Driver_LicenseNumberIdentifier_D[0]",
            "driver_license_number_identifier_e_0_": "Driver_LicenseNumberIdentifier_E[0]",
            "driver_license_number_identifier_f_0_": "Driver_LicenseNumberIdentifier_F[0]",
            "driver_license_number_identifier_g_0_": "Driver_LicenseNumberIdentifier_G[0]",
            "driver_license_number_identifier_h_0_": "Driver_LicenseNumberIdentifier_H[0]",
            "driver_license_number_identifier_i_0_": "Driver_LicenseNumberIdentifier_I[0]",
            "driver_license_number_identifier_j_0_": "Driver_LicenseNumberIdentifier_J[0]",
            "driver_license_number_identifier_k_0_": "Driver_LicenseNumberIdentifier_K[0]",
            "driver_license_number_identifier_l_0_": "Driver_LicenseNumberIdentifier_L[0]",
            "driver_licensed_state_or_province_code_a_0_": "Driver_LicensedStateOrProvinceCode_A[0]",
            "driver_licensed_state_or_province_code_b_0_": "Driver_LicensedStateOrProvinceCode_B[0]",
            "driver_licensed_state_or_province_code_c_0_": "Driver_LicensedStateOrProvinceCode_C[0]",
            "driver_licensed_state_or_province_code_d_0_": "Driver_LicensedStateOrProvinceCode_D[0]",
            "driver_licensed_state_or_province_code_e_0_": "Driver_LicensedStateOrProvinceCode_E[0]",
            "driver_licensed_state_or_province_code_f_0_": "Driver_LicensedStateOrProvinceCode_F[0]",
            "driver_licensed_state_or_province_code_g_0_": "Driver_LicensedStateOrProvinceCode_G[0]",
            "driver_licensed_state_or_province_code_h_0_": "Driver_LicensedStateOrProvinceCode_H[0]",
            "driver_licensed_state_or_province_code_i_0_": "Driver_LicensedStateOrProvinceCode_I[0]",
            "driver_licensed_state_or_province_code_j_0_": "Driver_LicensedStateOrProvinceCode_J[0]",
            "driver_licensed_state_or_province_code_k_0_": "Driver_LicensedStateOrProvinceCode_K[0]",
            "driver_licensed_state_or_province_code_l_0_": "Driver_LicensedStateOrProvinceCode_L[0]",
            "driver_licensed_year_a_0_": "Driver_LicensedYear_A[0]",
            "driver_licensed_year_b_0_": "Driver_LicensedYear_B[0]",
            "driver_licensed_year_c_0_": "Driver_LicensedYear_C[0]",
            "driver_licensed_year_d_0_": "Driver_LicensedYear_D[0]",
            "driver_licensed_year_e_0_": "Driver_LicensedYear_E[0]",
            "driver_licensed_year_f_0_": "Driver_LicensedYear_F[0]",
            "driver_licensed_year_g_0_": "Driver_LicensedYear_G[0]",
            "driver_licensed_year_h_0_": "Driver_LicensedYear_H[0]",
            "driver_licensed_year_i_0_": "Driver_LicensedYear_I[0]",
            "driver_licensed_year_j_0_": "Driver_LicensedYear_J[0]",
            "driver_licensed_year_k_0_": "Driver_LicensedYear_K[0]",
            "driver_licensed_year_l_0_": "Driver_LicensedYear_L[0]",
            "driver_mailing_address_city_name_a_0_": "Driver_MailingAddress_CityName_A[0]",
            "driver_mailing_address_city_name_b_0_": "Driver_MailingAddress_CityName_B[0]",
            "driver_mailing_address_city_name_c_0_": "Driver_MailingAddress_CityName_C[0]",
            "driver_mailing_address_city_name_d_0_": "Driver_MailingAddress_CityName_D[0]",
            "driver_mailing_address_city_name_e_0_": "Driver_MailingAddress_CityName_E[0]",
            "driver_mailing_address_city_name_f_0_": "Driver_MailingAddress_CityName_F[0]",
            "driver_mailing_address_city_name_g_0_": "Driver_MailingAddress_CityName_G[0]",
            "driver_mailing_address_city_name_h_0_": "Driver_MailingAddress_CityName_H[0]",
            "driver_mailing_address_city_name_i_0_": "Driver_MailingAddress_CityName_I[0]",
            "driver_mailing_address_city_name_j_0_": "Driver_MailingAddress_CityName_J[0]",
            "driver_mailing_address_city_name_k_0_": "Driver_MailingAddress_CityName_K[0]",
            "driver_mailing_address_city_name_l_0_": "Driver_MailingAddress_CityName_L[0]",
            "driver_mailing_address_line_one_a_0_": "Driver_MailingAddress_LineOne_A[0]",
            "driver_mailing_address_line_one_b_0_": "Driver_MailingAddress_LineOne_B[0]",
            "driver_mailing_address_line_one_c_0_": "Driver_MailingAddress_LineOne_C[0]",
            "driver_mailing_address_line_one_d_0_": "Driver_MailingAddress_LineOne_D[0]",
            "driver_mailing_address_line_one_e_0_": "Driver_MailingAddress_LineOne_E[0]",
            "driver_mailing_address_line_one_f_0_": "Driver_MailingAddress_LineOne_F[0]",
            "driver_mailing_address_line_one_g_0_": "Driver_MailingAddress_LineOne_G[0]",
            "driver_mailing_address_line_one_h_0_": "Driver_MailingAddress_LineOne_H[0]",
            "driver_mailing_address_line_one_i_0_": "Driver_MailingAddress_LineOne_I[0]",
            "driver_mailing_address_line_one_j_0_": "Driver_MailingAddress_LineOne_J[0]",
            "driver_mailing_address_line_one_k_0_": "Driver_MailingAddress_LineOne_K[0]",
            "driver_mailing_address_line_one_l_0_": "Driver_MailingAddress_LineOne_L[0]",
            "driver_mailing_address_postal_code_a_0_": "Driver_MailingAddress_PostalCode_A[0]",
            "driver_mailing_address_postal_code_b_0_": "Driver_MailingAddress_PostalCode_B[0]",
            "driver_mailing_address_postal_code_c_0_": "Driver_MailingAddress_PostalCode_C[0]",
            "driver_mailing_address_postal_code_d_0_": "Driver_MailingAddress_PostalCode_D[0]",
            "driver_mailing_address_postal_code_e_0_": "Driver_MailingAddress_PostalCode_E[0]",
            "driver_mailing_address_postal_code_f_0_": "Driver_MailingAddress_PostalCode_F[0]",
            "driver_mailing_address_postal_code_g_0_": "Driver_MailingAddress_PostalCode_G[0]",
            "driver_mailing_address_postal_code_h_0_": "Driver_MailingAddress_PostalCode_H[0]",
            "driver_mailing_address_postal_code_i_0_": "Driver_MailingAddress_PostalCode_I[0]",
            "driver_mailing_address_postal_code_j_0_": "Driver_MailingAddress_PostalCode_J[0]",
            "driver_mailing_address_postal_code_k_0_": "Driver_MailingAddress_PostalCode_K[0]",
            "driver_mailing_address_postal_code_l_0_": "Driver_MailingAddress_PostalCode_L[0]",
            "driver_mailing_address_state_or_province_code_a_0_": "Driver_MailingAddress_StateOrProvinceCode_A[0]",
            "driver_mailing_address_state_or_province_code_b_0_": "Driver_MailingAddress_StateOrProvinceCode_B[0]",
            "driver_mailing_address_state_or_province_code_c_0_": "Driver_MailingAddress_StateOrProvinceCode_C[0]",
            "driver_mailing_address_state_or_province_code_d_0_": "Driver_MailingAddress_StateOrProvinceCode_D[0]",
            "driver_mailing_address_state_or_province_code_e_0_": "Driver_MailingAddress_StateOrProvinceCode_E[0]",
            "driver_mailing_address_state_or_province_code_f_0_": "Driver_MailingAddress_StateOrProvinceCode_F[0]",
            "driver_mailing_address_state_or_province_code_g_0_": "Driver_MailingAddress_StateOrProvinceCode_G[0]",
            "driver_mailing_address_state_or_province_code_h_0_": "Driver_MailingAddress_StateOrProvinceCode_H[0]",
            "driver_mailing_address_state_or_province_code_i_0_": "Driver_MailingAddress_StateOrProvinceCode_I[0]",
            "driver_mailing_address_state_or_province_code_j_0_": "Driver_MailingAddress_StateOrProvinceCode_J[0]",
            "driver_mailing_address_state_or_province_code_k_0_": "Driver_MailingAddress_StateOrProvinceCode_K[0]",
            "driver_mailing_address_state_or_province_code_l_0_": "Driver_MailingAddress_StateOrProvinceCode_L[0]",
            "driver_marital_status_code_a_0_": "Driver_MaritalStatusCode_A[0]",
            "driver_marital_status_code_b_0_": "Driver_MaritalStatusCode_B[0]",
            "driver_marital_status_code_c_0_": "Driver_MaritalStatusCode_C[0]",
            "driver_marital_status_code_d_0_": "Driver_MaritalStatusCode_D[0]",
            "driver_marital_status_code_e_0_": "Driver_MaritalStatusCode_E[0]",
            "driver_marital_status_code_f_0_": "Driver_MaritalStatusCode_F[0]",
            "driver_marital_status_code_g_0_": "Driver_MaritalStatusCode_G[0]",
            "driver_marital_status_code_h_0_": "Driver_MaritalStatusCode_H[0]",
            "driver_marital_status_code_i_0_": "Driver_MaritalStatusCode_I[0]",
            "driver_marital_status_code_j_0_": "Driver_MaritalStatusCode_J[0]",
            "driver_marital_status_code_k_0_": "Driver_MaritalStatusCode_K[0]",
            "driver_marital_status_code_l_0_": "Driver_MaritalStatusCode_L[0]",
            "driver_other_given_name_initial_a_0_": "Driver_OtherGivenNameInitial_A[0]",
            "driver_other_given_name_initial_b_0_": "Driver_OtherGivenNameInitial_B[0]",
            "driver_other_given_name_initial_c_0_": "Driver_OtherGivenNameInitial_C[0]",
            "driver_other_given_name_initial_d_0_": "Driver_OtherGivenNameInitial_D[0]",
            "driver_other_given_name_initial_e_0_": "Driver_OtherGivenNameInitial_E[0]",
            "driver_other_given_name_initial_f_0_": "Driver_OtherGivenNameInitial_F[0]",
            "driver_other_given_name_initial_g_0_": "Driver_OtherGivenNameInitial_G[0]",
            "driver_other_given_name_initial_h_0_": "Driver_OtherGivenNameInitial_H[0]",
            "driver_other_given_name_initial_i_0_": "Driver_OtherGivenNameInitial_I[0]",
            "driver_other_given_name_initial_j_0_": "Driver_OtherGivenNameInitial_J[0]",
            "driver_other_given_name_initial_k_0_": "Driver_OtherGivenNameInitial_K[0]",
            "driver_other_given_name_initial_l_0_": "Driver_OtherGivenNameInitial_L[0]",
            "driver_producer_identifier_a_0_": "Driver_ProducerIdentifier_A[0]",
            "driver_producer_identifier_b_0_": "Driver_ProducerIdentifier_B[0]",
            "driver_producer_identifier_c_0_": "Driver_ProducerIdentifier_C[0]",
            "driver_producer_identifier_d_0_": "Driver_ProducerIdentifier_D[0]",
            "driver_producer_identifier_e_0_": "Driver_ProducerIdentifier_E[0]",
            "driver_producer_identifier_f_0_": "Driver_ProducerIdentifier_F[0]",
            "driver_producer_identifier_g_0_": "Driver_ProducerIdentifier_G[0]",
            "driver_producer_identifier_h_0_": "Driver_ProducerIdentifier_H[0]",
            "driver_producer_identifier_i_0_": "Driver_ProducerIdentifier_I[0]",
            "driver_producer_identifier_j_0_": "Driver_ProducerIdentifier_J[0]",
            "driver_producer_identifier_k_0_": "Driver_ProducerIdentifier_K[0]",
            "driver_producer_identifier_l_0_": "Driver_ProducerIdentifier_L[0]",
            "driver_surname_a_0_": "Driver_Surname_A[0]",
            "driver_surname_b_0_": "Driver_Surname_B[0]",
            "driver_surname_c_0_": "Driver_Surname_C[0]",
            "driver_surname_d_0_": "Driver_Surname_D[0]",
            "driver_surname_e_0_": "Driver_Surname_E[0]",
            "driver_surname_f_0_": "Driver_Surname_F[0]",
            "driver_surname_g_0_": "Driver_Surname_G[0]",
            "driver_surname_h_0_": "Driver_Surname_H[0]",
            "driver_surname_i_0_": "Driver_Surname_I[0]",
            "driver_surname_j_0_": "Driver_Surname_J[0]",
            "driver_surname_k_0_": "Driver_Surname_K[0]",
            "driver_surname_l_0_": "Driver_Surname_L[0]",
            "driver_tax_identifier_a_0_": "Driver_TaxIdentifier_A[0]",
            "driver_tax_identifier_b_0_": "Driver_TaxIdentifier_B[0]",
            "driver_tax_identifier_c_0_": "Driver_TaxIdentifier_C[0]",
            "driver_tax_identifier_d_0_": "Driver_TaxIdentifier_D[0]",
            "driver_tax_identifier_e_0_": "Driver_TaxIdentifier_E[0]",
            "driver_tax_identifier_f_0_": "Driver_TaxIdentifier_F[0]",
            "driver_tax_identifier_g_0_": "Driver_TaxIdentifier_G[0]",
            "driver_tax_identifier_h_0_": "Driver_TaxIdentifier_H[0]",
            "driver_tax_identifier_i_0_": "Driver_TaxIdentifier_I[0]",
            "driver_tax_identifier_j_0_": "Driver_TaxIdentifier_J[0]",
            "driver_tax_identifier_k_0_": "Driver_TaxIdentifier_K[0]",
            "driver_tax_identifier_l_0_": "Driver_TaxIdentifier_L[0]",
            "driver_vehicle_producer_identifier_a_0_": "Driver_Vehicle_ProducerIdentifier_A[0]",
            "driver_vehicle_producer_identifier_b_0_": "Driver_Vehicle_ProducerIdentifier_B[0]",
            "driver_vehicle_producer_identifier_c_0_": "Driver_Vehicle_ProducerIdentifier_C[0]",
            "driver_vehicle_producer_identifier_d_0_": "Driver_Vehicle_ProducerIdentifier_D[0]",
            "driver_vehicle_producer_identifier_e_0_": "Driver_Vehicle_ProducerIdentifier_E[0]",
            "driver_vehicle_producer_identifier_f_0_": "Driver_Vehicle_ProducerIdentifier_F[0]",
            "driver_vehicle_producer_identifier_g_0_": "Driver_Vehicle_ProducerIdentifier_G[0]",
            "driver_vehicle_producer_identifier_h_0_": "Driver_Vehicle_ProducerIdentifier_H[0]",
            "driver_vehicle_producer_identifier_i_0_": "Driver_Vehicle_ProducerIdentifier_I[0]",
            "driver_vehicle_producer_identifier_j_0_": "Driver_Vehicle_ProducerIdentifier_J[0]",
            "driver_vehicle_producer_identifier_k_0_": "Driver_Vehicle_ProducerIdentifier_K[0]",
            "driver_vehicle_producer_identifier_l_0_": "Driver_Vehicle_ProducerIdentifier_L[0]",
            "driver_vehicle_use_percent_a_0_": "Driver_Vehicle_UsePercent_A[0]",
            "driver_vehicle_use_percent_b_0_": "Driver_Vehicle_UsePercent_B[0]",
            "driver_vehicle_use_percent_c_0_": "Driver_Vehicle_UsePercent_C[0]",
            "driver_vehicle_use_percent_d_0_": "Driver_Vehicle_UsePercent_D[0]",
            "driver_vehicle_use_percent_e_0_": "Driver_Vehicle_UsePercent_E[0]",
            "driver_vehicle_use_percent_f_0_": "Driver_Vehicle_UsePercent_F[0]",
            "driver_vehicle_use_percent_g_0_": "Driver_Vehicle_UsePercent_G[0]",
            "driver_vehicle_use_percent_h_0_": "Driver_Vehicle_UsePercent_H[0]",
            "driver_vehicle_use_percent_i_0_": "Driver_Vehicle_UsePercent_I[0]",
            "driver_vehicle_use_percent_j_0_": "Driver_Vehicle_UsePercent_J[0]",
            "driver_vehicle_use_percent_k_0_": "Driver_Vehicle_UsePercent_K[0]",
            "driver_vehicle_use_percent_l_0_": "Driver_Vehicle_UsePercent_L[0]",
            "form_completion_date_a_0_": "Form_CompletionDate_A[0]",
            "insurer_full_name_a_0_": "Insurer_FullName_A[0]",
            "insurer_naic_code_a_0_": "Insurer_NAICCode_A[0]",
            "named_insured_full_name_a_0_": "NamedInsured_FullName_A[0]",
            "named_insured_signature_a_0_": "NamedInsured_Signature_A[0]",
            "named_insured_signature_date_a_0_": "NamedInsured_SignatureDate_A[0]",
            "policy_effective_date_a_0_": "Policy_EffectiveDate_A[0]",
            "policy_policy_number_identifier_a_0_": "Policy_PolicyNumberIdentifier_A[0]",
            "producer_authorized_representative_full_name_a_0_": "Producer_AuthorizedRepresentative_FullName_A[0]",
            "producer_authorized_representative_signature_a_0_": "Producer_AuthorizedRepresentative_Signature_A[0]",
            "producer_customer_identifier_a_0_": "Producer_CustomerIdentifier_A[0]",
            "producer_full_name_a_0_": "Producer_FullName_A[0]",
            "producer_national_identifier_a_0_": "Producer_NationalIdentifier_A[0]",
            "producer_state_license_identifier_a_0_": "Producer_StateLicenseIdentifier_A[0]",
            "vehicle_body_code_a_0_": "Vehicle_BodyCode_A[0]",
            "vehicle_body_code_b_0_": "Vehicle_BodyCode_B[0]",
            "vehicle_body_code_c_0_": "Vehicle_BodyCode_C[0]",
            "vehicle_body_code_d_0_": "Vehicle_BodyCode_D[0]",
            "vehicle_collision_deductible_amount_a_0_": "Vehicle_Collision_DeductibleAmount_A[0]",
            "vehicle_collision_deductible_amount_b_0_": "Vehicle_Collision_DeductibleAmount_B[0]",
            "vehicle_collision_deductible_amount_c_0_": "Vehicle_Collision_DeductibleAmount_C[0]",
            "vehicle_collision_deductible_amount_d_0_": "Vehicle_Collision_DeductibleAmount_D[0]",
            "vehicle_collision_symbol_code_a_0_": "Vehicle_CollisionSymbolCode_A[0]",
            "vehicle_collision_symbol_code_b_0_": "Vehicle_CollisionSymbolCode_B[0]",
            "vehicle_collision_symbol_code_c_0_": "Vehicle_CollisionSymbolCode_C[0]",
            "vehicle_collision_symbol_code_d_0_": "Vehicle_CollisionSymbolCode_D[0]",
            "vehicle_comprehensive_symbol_code_a_0_": "Vehicle_ComprehensiveSymbolCode_A[0]",
            "vehicle_comprehensive_symbol_code_b_0_": "Vehicle_ComprehensiveSymbolCode_B[0]",
            "vehicle_comprehensive_symbol_code_c_0_": "Vehicle_ComprehensiveSymbolCode_C[0]",
            "vehicle_comprehensive_symbol_code_d_0_": "Vehicle_ComprehensiveSymbolCode_D[0]",
            "vehicle_cost_new_amount_a_0_": "Vehicle_CostNewAmount_A[0]",
            "vehicle_cost_new_amount_b_0_": "Vehicle_CostNewAmount_B[0]",
            "vehicle_cost_new_amount_c_0_": "Vehicle_CostNewAmount_C[0]",
            "vehicle_cost_new_amount_d_0_": "Vehicle_CostNewAmount_D[0]",
            "vehicle_coverage_additional_no_fault_indicator_a_0_": "Vehicle_Coverage_AdditionalNoFaultIndicator_A[0]",
            "vehicle_coverage_additional_no_fault_indicator_b_0_": "Vehicle_Coverage_AdditionalNoFaultIndicator_B[0]",
            "vehicle_coverage_additional_no_fault_indicator_c_0_": "Vehicle_Coverage_AdditionalNoFaultIndicator_C[0]",
            "vehicle_coverage_additional_no_fault_indicator_d_0_": "Vehicle_Coverage_AdditionalNoFaultIndicator_D[0]",
            "vehicle_coverage_agreed_or_stated_amount_a_0_": "Vehicle_Coverage_AgreedOrStatedAmount_A[0]",
            "vehicle_coverage_agreed_or_stated_amount_b_0_": "Vehicle_Coverage_AgreedOrStatedAmount_B[0]",
            "vehicle_coverage_agreed_or_stated_amount_c_0_": "Vehicle_Coverage_AgreedOrStatedAmount_C[0]",
            "vehicle_coverage_agreed_or_stated_amount_d_0_": "Vehicle_Coverage_AgreedOrStatedAmount_D[0]",
            "vehicle_coverage_collision_indicator_a_0_": "Vehicle_Coverage_CollisionIndicator_A[0]",
            "vehicle_coverage_collision_indicator_b_0_": "Vehicle_Coverage_CollisionIndicator_B[0]",
            "vehicle_coverage_collision_indicator_c_0_": "Vehicle_Coverage_CollisionIndicator_C[0]",
            "vehicle_coverage_collision_indicator_d_0_": "Vehicle_Coverage_CollisionIndicator_D[0]",
            "vehicle_coverage_comprehensive_deductible_indicator_a_0_": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_A[0]",
            "vehicle_coverage_comprehensive_deductible_indicator_b_0_": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_B[0]",
            "vehicle_coverage_comprehensive_deductible_indicator_c_0_": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_C[0]",
            "vehicle_coverage_comprehensive_deductible_indicator_d_0_": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_D[0]",
            "vehicle_coverage_comprehensive_indicator_a_0_": "Vehicle_Coverage_ComprehensiveIndicator_A[0]",
            "vehicle_coverage_comprehensive_indicator_b_0_": "Vehicle_Coverage_ComprehensiveIndicator_B[0]",
            "vehicle_coverage_comprehensive_indicator_c_0_": "Vehicle_Coverage_ComprehensiveIndicator_C[0]",
            "vehicle_coverage_comprehensive_indicator_d_0_": "Vehicle_Coverage_ComprehensiveIndicator_D[0]",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_a_0_": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_A[0]",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_b_0_": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_B[0]",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_c_0_": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_C[0]",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_d_0_": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_D[0]",
            "vehicle_coverage_fire_indicator_a_0_": "Vehicle_Coverage_FireIndicator_A[0]",
            "vehicle_coverage_fire_indicator_b_0_": "Vehicle_Coverage_FireIndicator_B[0]",
            "vehicle_coverage_fire_indicator_c_0_": "Vehicle_Coverage_FireIndicator_C[0]",
            "vehicle_coverage_fire_indicator_d_0_": "Vehicle_Coverage_FireIndicator_D[0]",
            "vehicle_coverage_fire_theft_indicator_a_0_": "Vehicle_Coverage_FireTheftIndicator_A[0]",
            "vehicle_coverage_fire_theft_indicator_b_0_": "Vehicle_Coverage_FireTheftIndicator_B[0]",
            "vehicle_coverage_fire_theft_indicator_c_0_": "Vehicle_Coverage_FireTheftIndicator_C[0]",
            "vehicle_coverage_fire_theft_indicator_d_0_": "Vehicle_Coverage_FireTheftIndicator_D[0]",
            "vehicle_coverage_fire_theft_windstorm_indicator_a_0_": "Vehicle_Coverage_FireTheftWindstormIndicator_A[0]",
            "vehicle_coverage_fire_theft_windstorm_indicator_b_0_": "Vehicle_Coverage_FireTheftWindstormIndicator_B[0]",
            "vehicle_coverage_fire_theft_windstorm_indicator_c_0_": "Vehicle_Coverage_FireTheftWindstormIndicator_C[0]",
            "vehicle_coverage_fire_theft_windstorm_indicator_d_0_": "Vehicle_Coverage_FireTheftWindstormIndicator_D[0]",
            "vehicle_coverage_full_glass_indicator_a_0_": "Vehicle_Coverage_FullGlassIndicator_A[0]",
            "vehicle_coverage_full_glass_indicator_b_0_": "Vehicle_Coverage_FullGlassIndicator_B[0]",
            "vehicle_coverage_full_glass_indicator_c_0_": "Vehicle_Coverage_FullGlassIndicator_C[0]",
            "vehicle_coverage_full_glass_indicator_d_0_": "Vehicle_Coverage_FullGlassIndicator_D[0]",
            "vehicle_coverage_liability_indicator_a_0_": "Vehicle_Coverage_LiabilityIndicator_A[0]",
            "vehicle_coverage_liability_indicator_b_0_": "Vehicle_Coverage_LiabilityIndicator_B[0]",
            "vehicle_coverage_liability_indicator_c_0_": "Vehicle_Coverage_LiabilityIndicator_C[0]",
            "vehicle_coverage_liability_indicator_d_0_": "Vehicle_Coverage_LiabilityIndicator_D[0]",
            "vehicle_coverage_limited_specified_perils_indicator_a_0_": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_A[0]",
            "vehicle_coverage_limited_specified_perils_indicator_b_0_": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_B[0]",
            "vehicle_coverage_limited_specified_perils_indicator_c_0_": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_C[0]",
            "vehicle_coverage_limited_specified_perils_indicator_d_0_": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_D[0]",
            "vehicle_coverage_medical_payments_indicator_a_0_": "Vehicle_Coverage_MedicalPaymentsIndicator_A[0]",
            "vehicle_coverage_medical_payments_indicator_b_0_": "Vehicle_Coverage_MedicalPaymentsIndicator_B[0]",
            "vehicle_coverage_medical_payments_indicator_c_0_": "Vehicle_Coverage_MedicalPaymentsIndicator_C[0]",
            "vehicle_coverage_medical_payments_indicator_d_0_": "Vehicle_Coverage_MedicalPaymentsIndicator_D[0]",
            "vehicle_coverage_no_fault_indicator_a_0_": "Vehicle_Coverage_NoFaultIndicator_A[0]",
            "vehicle_coverage_no_fault_indicator_b_0_": "Vehicle_Coverage_NoFaultIndicator_B[0]",
            "vehicle_coverage_no_fault_indicator_c_0_": "Vehicle_Coverage_NoFaultIndicator_C[0]",
            "vehicle_coverage_no_fault_indicator_d_0_": "Vehicle_Coverage_NoFaultIndicator_D[0]",
            "vehicle_coverage_other_description_a_0_": "Vehicle_Coverage_OtherDescription_A[0]",
            "vehicle_coverage_other_description_b_0_": "Vehicle_Coverage_OtherDescription_B[0]",
            "vehicle_coverage_other_description_c_0_": "Vehicle_Coverage_OtherDescription_C[0]",
            "vehicle_coverage_other_description_d_0_": "Vehicle_Coverage_OtherDescription_D[0]",
            "vehicle_coverage_other_indicator_a_0_": "Vehicle_Coverage_OtherIndicator_A[0]",
            "vehicle_coverage_other_indicator_b_0_": "Vehicle_Coverage_OtherIndicator_B[0]",
            "vehicle_coverage_other_indicator_c_0_": "Vehicle_Coverage_OtherIndicator_C[0]",
            "vehicle_coverage_other_indicator_d_0_": "Vehicle_Coverage_OtherIndicator_D[0]",
            "vehicle_coverage_rental_reimbursement_indicator_a_0_": "Vehicle_Coverage_RentalReimbursementIndicator_A[0]",
            "vehicle_coverage_rental_reimbursement_indicator_b_0_": "Vehicle_Coverage_RentalReimbursementIndicator_B[0]",
            "vehicle_coverage_rental_reimbursement_indicator_c_0_": "Vehicle_Coverage_RentalReimbursementIndicator_C[0]",
            "vehicle_coverage_rental_reimbursement_indicator_d_0_": "Vehicle_Coverage_RentalReimbursementIndicator_D[0]",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_a_0_": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_A[0]",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_b_0_": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_B[0]",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_c_0_": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_C[0]",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_d_0_": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_D[0]",
            "vehicle_coverage_specified_cause_of_loss_indicator_a_0_": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_A[0]",
            "vehicle_coverage_specified_cause_of_loss_indicator_b_0_": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_B[0]",
            "vehicle_coverage_specified_cause_of_loss_indicator_c_0_": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_C[0]",
            "vehicle_coverage_specified_cause_of_loss_indicator_d_0_": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_D[0]",
            "vehicle_coverage_towing_and_labour_indicator_a_0_": "Vehicle_Coverage_TowingAndLabourIndicator_A[0]",
            "vehicle_coverage_towing_and_labour_indicator_b_0_": "Vehicle_Coverage_TowingAndLabourIndicator_B[0]",
            "vehicle_coverage_towing_and_labour_indicator_c_0_": "Vehicle_Coverage_TowingAndLabourIndicator_C[0]",
            "vehicle_coverage_towing_and_labour_indicator_d_0_": "Vehicle_Coverage_TowingAndLabourIndicator_D[0]",
            "vehicle_coverage_underinsured_motorists_indicator_a_0_": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_A[0]",
            "vehicle_coverage_underinsured_motorists_indicator_b_0_": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_B[0]",
            "vehicle_coverage_underinsured_motorists_indicator_c_0_": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_C[0]",
            "vehicle_coverage_underinsured_motorists_indicator_d_0_": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_D[0]",
            "vehicle_coverage_uninsured_motorists_indicator_a_0_": "Vehicle_Coverage_UninsuredMotoristsIndicator_A[0]",
            "vehicle_coverage_uninsured_motorists_indicator_b_0_": "Vehicle_Coverage_UninsuredMotoristsIndicator_B[0]",
            "vehicle_coverage_uninsured_motorists_indicator_c_0_": "Vehicle_Coverage_UninsuredMotoristsIndicator_C[0]",
            "vehicle_coverage_uninsured_motorists_indicator_d_0_": "Vehicle_Coverage_UninsuredMotoristsIndicator_D[0]",
            "vehicle_coverage_valuation_actual_cash_value_indicator_a_0_": "Vehicle_Coverage_ValuationActualCashValueIndicator_A[0]",
            "vehicle_coverage_valuation_actual_cash_value_indicator_b_0_": "Vehicle_Coverage_ValuationActualCashValueIndicator_B[0]",
            "vehicle_coverage_valuation_actual_cash_value_indicator_c_0_": "Vehicle_Coverage_ValuationActualCashValueIndicator_C[0]",
            "vehicle_coverage_valuation_actual_cash_value_indicator_d_0_": "Vehicle_Coverage_ValuationActualCashValueIndicator_D[0]",
            "vehicle_coverage_valuation_agreed_amount_indicator_a_0_": "Vehicle_Coverage_ValuationAgreedAmountIndicator_A[0]",
            "vehicle_coverage_valuation_agreed_amount_indicator_b_0_": "Vehicle_Coverage_ValuationAgreedAmountIndicator_B[0]",
            "vehicle_coverage_valuation_agreed_amount_indicator_c_0_": "Vehicle_Coverage_ValuationAgreedAmountIndicator_C[0]",
            "vehicle_coverage_valuation_agreed_amount_indicator_d_0_": "Vehicle_Coverage_ValuationAgreedAmountIndicator_D[0]",
            "vehicle_coverage_valuation_stated_amount_indicator_a_0_": "Vehicle_Coverage_ValuationStatedAmountIndicator_A[0]",
            "vehicle_coverage_valuation_stated_amount_indicator_b_0_": "Vehicle_Coverage_ValuationStatedAmountIndicator_B[0]",
            "vehicle_coverage_valuation_stated_amount_indicator_c_0_": "Vehicle_Coverage_ValuationStatedAmountIndicator_C[0]",
            "vehicle_coverage_valuation_stated_amount_indicator_d_0_": "Vehicle_Coverage_ValuationStatedAmountIndicator_D[0]",
            "vehicle_farthest_zone_code_a_0_": "Vehicle_FarthestZoneCode_A[0]",
            "vehicle_farthest_zone_code_b_0_": "Vehicle_FarthestZoneCode_B[0]",
            "vehicle_farthest_zone_code_c_0_": "Vehicle_FarthestZoneCode_C[0]",
            "vehicle_farthest_zone_code_d_0_": "Vehicle_FarthestZoneCode_D[0]",
            "vehicle_gross_vehicle_weight_a_0_": "Vehicle_GrossVehicleWeight_A[0]",
            "vehicle_gross_vehicle_weight_b_0_": "Vehicle_GrossVehicleWeight_B[0]",
            "vehicle_gross_vehicle_weight_c_0_": "Vehicle_GrossVehicleWeight_C[0]",
            "vehicle_gross_vehicle_weight_d_0_": "Vehicle_GrossVehicleWeight_D[0]",
            "vehicle_manufacturers_name_a_0_": "Vehicle_ManufacturersName_A[0]",
            "vehicle_manufacturers_name_b_0_": "Vehicle_ManufacturersName_B[0]",
            "vehicle_manufacturers_name_c_0_": "Vehicle_ManufacturersName_C[0]",
            "vehicle_manufacturers_name_d_0_": "Vehicle_ManufacturersName_D[0]",
            "vehicle_model_name_a_0_": "Vehicle_ModelName_A[0]",
            "vehicle_model_name_b_0_": "Vehicle_ModelName_B[0]",
            "vehicle_model_name_c_0_": "Vehicle_ModelName_C[0]",
            "vehicle_model_name_d_0_": "Vehicle_ModelName_D[0]",
            "vehicle_model_year_a_0_": "Vehicle_ModelYear_A[0]",
            "vehicle_model_year_b_0_": "Vehicle_ModelYear_B[0]",
            "vehicle_model_year_c_0_": "Vehicle_ModelYear_C[0]",
            "vehicle_model_year_d_0_": "Vehicle_ModelYear_D[0]",
            "vehicle_net_rating_factor_a_0_": "Vehicle_NetRatingFactor_A[0]",
            "vehicle_net_rating_factor_b_0_": "Vehicle_NetRatingFactor_B[0]",
            "vehicle_net_rating_factor_c_0_": "Vehicle_NetRatingFactor_C[0]",
            "vehicle_net_rating_factor_d_0_": "Vehicle_NetRatingFactor_D[0]",
            "vehicle_physical_address_city_name_a_0_": "Vehicle_PhysicalAddress_CityName_A[0]",
            "vehicle_physical_address_city_name_b_0_": "Vehicle_PhysicalAddress_CityName_B[0]",
            "vehicle_physical_address_city_name_c_0_": "Vehicle_PhysicalAddress_CityName_C[0]",
            "vehicle_physical_address_city_name_d_0_": "Vehicle_PhysicalAddress_CityName_D[0]",
            "vehicle_physical_address_county_name_a_0_": "Vehicle_PhysicalAddress_CountyName_A[0]",
            "vehicle_physical_address_county_name_b_0_": "Vehicle_PhysicalAddress_CountyName_B[0]",
            "vehicle_physical_address_county_name_c_0_": "Vehicle_PhysicalAddress_CountyName_C[0]",
            "vehicle_physical_address_county_name_d_0_": "Vehicle_PhysicalAddress_CountyName_D[0]",
            "vehicle_physical_address_line_one_a_0_": "Vehicle_PhysicalAddress_LineOne_A[0]",
            "vehicle_physical_address_line_one_b_0_": "Vehicle_PhysicalAddress_LineOne_B[0]",
            "vehicle_physical_address_line_one_c_0_": "Vehicle_PhysicalAddress_LineOne_C[0]",
            "vehicle_physical_address_line_one_d_0_": "Vehicle_PhysicalAddress_LineOne_D[0]",
            "vehicle_physical_address_postal_code_a_0_": "Vehicle_PhysicalAddress_PostalCode_A[0]",
            "vehicle_physical_address_postal_code_b_0_": "Vehicle_PhysicalAddress_PostalCode_B[0]",
            "vehicle_physical_address_postal_code_c_0_": "Vehicle_PhysicalAddress_PostalCode_C[0]",
            "vehicle_physical_address_postal_code_d_0_": "Vehicle_PhysicalAddress_PostalCode_D[0]",
            "vehicle_physical_address_state_or_province_code_a_0_": "Vehicle_PhysicalAddress_StateOrProvinceCode_A[0]",
            "vehicle_physical_address_state_or_province_code_b_0_": "Vehicle_PhysicalAddress_StateOrProvinceCode_B[0]",
            "vehicle_physical_address_state_or_province_code_c_0_": "Vehicle_PhysicalAddress_StateOrProvinceCode_C[0]",
            "vehicle_physical_address_state_or_province_code_d_0_": "Vehicle_PhysicalAddress_StateOrProvinceCode_D[0]",
            "vehicle_primary_liability_rating_factor_a_0_": "Vehicle_PrimaryLiabilityRatingFactor_A[0]",
            "vehicle_primary_liability_rating_factor_b_0_": "Vehicle_PrimaryLiabilityRatingFactor_B[0]",
            "vehicle_primary_liability_rating_factor_c_0_": "Vehicle_PrimaryLiabilityRatingFactor_C[0]",
            "vehicle_primary_liability_rating_factor_d_0_": "Vehicle_PrimaryLiabilityRatingFactor_D[0]",
            "vehicle_producer_identifier_a_0_": "Vehicle_ProducerIdentifier_A[0]",
            "vehicle_producer_identifier_aa_0_": "Vehicle_ProducerIdentifier_AA[0]",
            "vehicle_producer_identifier_ab_0_": "Vehicle_ProducerIdentifier_AB[0]",
            "vehicle_producer_identifier_ac_0_": "Vehicle_ProducerIdentifier_AC[0]",
            "vehicle_producer_identifier_ad_0_": "Vehicle_ProducerIdentifier_AD[0]",
            "vehicle_producer_identifier_b_0_": "Vehicle_ProducerIdentifier_B[0]",
            "vehicle_producer_identifier_c_0_": "Vehicle_ProducerIdentifier_C[0]",
            "vehicle_producer_identifier_d_0_": "Vehicle_ProducerIdentifier_D[0]",
            "vehicle_question_modified_equipment_cost_amount_a_0_": "Vehicle_Question_ModifiedEquipmentCostAmount_A[0]",
            "vehicle_question_modified_equipment_cost_amount_b_0_": "Vehicle_Question_ModifiedEquipmentCostAmount_B[0]",
            "vehicle_question_modified_equipment_description_a_0_": "Vehicle_Question_ModifiedEquipmentDescription_A[0]",
            "vehicle_question_modified_equipment_description_b_0_": "Vehicle_Question_ModifiedEquipmentDescription_B[0]",
            "vehicle_radius_of_use_a_0_": "Vehicle_RadiusOfUse_A[0]",
            "vehicle_radius_of_use_b_0_": "Vehicle_RadiusOfUse_B[0]",
            "vehicle_radius_of_use_c_0_": "Vehicle_RadiusOfUse_C[0]",
            "vehicle_radius_of_use_d_0_": "Vehicle_RadiusOfUse_D[0]",
            "vehicle_rate_class_code_a_0_": "Vehicle_RateClassCode_A[0]",
            "vehicle_rate_class_code_b_0_": "Vehicle_RateClassCode_B[0]",
            "vehicle_rate_class_code_c_0_": "Vehicle_RateClassCode_C[0]",
            "vehicle_rate_class_code_d_0_": "Vehicle_RateClassCode_D[0]",
            "vehicle_rating_territory_code_a_0_": "Vehicle_RatingTerritoryCode_A[0]",
            "vehicle_rating_territory_code_b_0_": "Vehicle_RatingTerritoryCode_B[0]",
            "vehicle_rating_territory_code_c_0_": "Vehicle_RatingTerritoryCode_C[0]",
            "vehicle_rating_territory_code_d_0_": "Vehicle_RatingTerritoryCode_D[0]",
            "vehicle_registration_state_or_province_code_a_0_": "Vehicle_Registration_StateOrProvinceCode_A[0]",
            "vehicle_registration_state_or_province_code_b_0_": "Vehicle_Registration_StateOrProvinceCode_B[0]",
            "vehicle_registration_state_or_province_code_c_0_": "Vehicle_Registration_StateOrProvinceCode_C[0]",
            "vehicle_registration_state_or_province_code_d_0_": "Vehicle_Registration_StateOrProvinceCode_D[0]",
            "vehicle_seating_capacity_count_a_0_": "Vehicle_SeatingCapacityCount_A[0]",
            "vehicle_seating_capacity_count_b_0_": "Vehicle_SeatingCapacityCount_B[0]",
            "vehicle_seating_capacity_count_c_0_": "Vehicle_SeatingCapacityCount_C[0]",
            "vehicle_seating_capacity_count_d_0_": "Vehicle_SeatingCapacityCount_D[0]",
            "vehicle_special_industry_class_code_a_0_": "Vehicle_SpecialIndustryClassCode_A[0]",
            "vehicle_special_industry_class_code_b_0_": "Vehicle_SpecialIndustryClassCode_B[0]",
            "vehicle_special_industry_class_code_c_0_": "Vehicle_SpecialIndustryClassCode_C[0]",
            "vehicle_special_industry_class_code_d_0_": "Vehicle_SpecialIndustryClassCode_D[0]",
            "vehicle_symbol_code_a_0_": "Vehicle_SymbolCode_A[0]",
            "vehicle_symbol_code_b_0_": "Vehicle_SymbolCode_B[0]",
            "vehicle_symbol_code_c_0_": "Vehicle_SymbolCode_C[0]",
            "vehicle_symbol_code_d_0_": "Vehicle_SymbolCode_D[0]",
            "vehicle_total_premium_amount_a_0_": "Vehicle_TotalPremiumAmount_A[0]",
            "vehicle_total_premium_amount_b_0_": "Vehicle_TotalPremiumAmount_B[0]",
            "vehicle_total_premium_amount_c_0_": "Vehicle_TotalPremiumAmount_C[0]",
            "vehicle_total_premium_amount_d_0_": "Vehicle_TotalPremiumAmount_D[0]",
            "vehicle_use_commercial_indicator_a_0_": "Vehicle_Use_CommercialIndicator_A[0]",
            "vehicle_use_commercial_indicator_b_0_": "Vehicle_Use_CommercialIndicator_B[0]",
            "vehicle_use_commercial_indicator_c_0_": "Vehicle_Use_CommercialIndicator_C[0]",
            "vehicle_use_commercial_indicator_d_0_": "Vehicle_Use_CommercialIndicator_D[0]",
            "vehicle_use_farm_indicator_a_0_": "Vehicle_Use_FarmIndicator_A[0]",
            "vehicle_use_farm_indicator_b_0_": "Vehicle_Use_FarmIndicator_B[0]",
            "vehicle_use_farm_indicator_c_0_": "Vehicle_Use_FarmIndicator_C[0]",
            "vehicle_use_farm_indicator_d_0_": "Vehicle_Use_FarmIndicator_D[0]",
            "vehicle_use_fifteen_miles_or_over_indicator_a_0_": "Vehicle_Use_FifteenMilesOrOverIndicator_A[0]",
            "vehicle_use_fifteen_miles_or_over_indicator_b_0_": "Vehicle_Use_FifteenMilesOrOverIndicator_B[0]",
            "vehicle_use_fifteen_miles_or_over_indicator_c_0_": "Vehicle_Use_FifteenMilesOrOverIndicator_C[0]",
            "vehicle_use_fifteen_miles_or_over_indicator_d_0_": "Vehicle_Use_FifteenMilesOrOverIndicator_D[0]",
            "vehicle_use_for_hire_indicator_a_0_": "Vehicle_Use_ForHireIndicator_A[0]",
            "vehicle_use_for_hire_indicator_b_0_": "Vehicle_Use_ForHireIndicator_B[0]",
            "vehicle_use_for_hire_indicator_c_0_": "Vehicle_Use_ForHireIndicator_C[0]",
            "vehicle_use_for_hire_indicator_d_0_": "Vehicle_Use_ForHireIndicator_D[0]",
            "vehicle_use_other_description_a_0_": "Vehicle_Use_OtherDescription_A[0]",
            "vehicle_use_other_description_b_0_": "Vehicle_Use_OtherDescription_B[0]",
            "vehicle_use_other_description_c_0_": "Vehicle_Use_OtherDescription_C[0]",
            "vehicle_use_other_description_d_0_": "Vehicle_Use_OtherDescription_D[0]",
            "vehicle_use_other_indicator_a_0_": "Vehicle_Use_OtherIndicator_A[0]",
            "vehicle_use_other_indicator_b_0_": "Vehicle_Use_OtherIndicator_B[0]",
            "vehicle_use_other_indicator_c_0_": "Vehicle_Use_OtherIndicator_C[0]",
            "vehicle_use_other_indicator_d_0_": "Vehicle_Use_OtherIndicator_D[0]",
            "vehicle_use_pleasure_indicator_a_0_": "Vehicle_Use_PleasureIndicator_A[0]",
            "vehicle_use_pleasure_indicator_b_0_": "Vehicle_Use_PleasureIndicator_B[0]",
            "vehicle_use_pleasure_indicator_c_0_": "Vehicle_Use_PleasureIndicator_C[0]",
            "vehicle_use_pleasure_indicator_d_0_": "Vehicle_Use_PleasureIndicator_D[0]",
            "vehicle_use_retail_indicator_a_0_": "Vehicle_Use_RetailIndicator_A[0]",
            "vehicle_use_retail_indicator_b_0_": "Vehicle_Use_RetailIndicator_B[0]",
            "vehicle_use_retail_indicator_c_0_": "Vehicle_Use_RetailIndicator_C[0]",
            "vehicle_use_retail_indicator_d_0_": "Vehicle_Use_RetailIndicator_D[0]",
            "vehicle_use_service_indicator_a_0_": "Vehicle_Use_ServiceIndicator_A[0]",
            "vehicle_use_service_indicator_b_0_": "Vehicle_Use_ServiceIndicator_B[0]",
            "vehicle_use_service_indicator_c_0_": "Vehicle_Use_ServiceIndicator_C[0]",
            "vehicle_use_service_indicator_d_0_": "Vehicle_Use_ServiceIndicator_D[0]",
            "vehicle_use_under_fifteen_miles_indicator_a_0_": "Vehicle_Use_UnderFifteenMilesIndicator_A[0]",
            "vehicle_use_under_fifteen_miles_indicator_b_0_": "Vehicle_Use_UnderFifteenMilesIndicator_B[0]",
            "vehicle_use_under_fifteen_miles_indicator_c_0_": "Vehicle_Use_UnderFifteenMilesIndicator_C[0]",
            "vehicle_use_under_fifteen_miles_indicator_d_0_": "Vehicle_Use_UnderFifteenMilesIndicator_D[0]",
            "vehicle_vehicle_type_commercial_indicator_a_0_": "Vehicle_VehicleType_CommercialIndicator_A[0]",
            "vehicle_vehicle_type_commercial_indicator_b_0_": "Vehicle_VehicleType_CommercialIndicator_B[0]",
            "vehicle_vehicle_type_commercial_indicator_c_0_": "Vehicle_VehicleType_CommercialIndicator_C[0]",
            "vehicle_vehicle_type_commercial_indicator_d_0_": "Vehicle_VehicleType_CommercialIndicator_D[0]",
            "vehicle_vehicle_type_private_passenger_indicator_a_0_": "Vehicle_VehicleType_PrivatePassengerIndicator_A[0]",
            "vehicle_vehicle_type_private_passenger_indicator_b_0_": "Vehicle_VehicleType_PrivatePassengerIndicator_B[0]",
            "vehicle_vehicle_type_private_passenger_indicator_c_0_": "Vehicle_VehicleType_PrivatePassengerIndicator_C[0]",
            "vehicle_vehicle_type_private_passenger_indicator_d_0_": "Vehicle_VehicleType_PrivatePassengerIndicator_D[0]",
            "vehicle_vehicle_type_special_indicator_a_0_": "Vehicle_VehicleType_SpecialIndicator_A[0]",
            "vehicle_vehicle_type_special_indicator_b_0_": "Vehicle_VehicleType_SpecialIndicator_B[0]",
            "vehicle_vehicle_type_special_indicator_c_0_": "Vehicle_VehicleType_SpecialIndicator_C[0]",
            "vehicle_vehicle_type_special_indicator_d_0_": "Vehicle_VehicleType_SpecialIndicator_D[0]",
            "vehicle_vin_identifier_a_0_": "Vehicle_VINIdentifier_A[0]",
            "vehicle_vin_identifier_b_0_": "Vehicle_VINIdentifier_B[0]",
            "vehicle_vin_identifier_c_0_": "Vehicle_VINIdentifier_C[0]",
            "vehicle_vin_identifier_d_0_": "Vehicle_VINIdentifier_D[0]",
        }


class Acord129Data(BaseModel):
    """Auto-generated schema for ACORD 129"""
    form_completion_date_a: Optional[str] = Field(None, description="Enter date: The date on which the form is completed. ")
    form_edition_identifier_a: Optional[str] = Field(None, description="The edition identifier of the form including the form number and edition (the date is typically formatted YYYY/MM).")
    insurer_full_name_a: Optional[str] = Field(None, description="Enter text: The insurer's full legal company name(s) as found in the file copy of the policy.  Use the actual name of the company within the group to which the policy has been issued.  This is not ...")
    insurer_naic_code_a: Optional[str] = Field(None, description="Enter code: The identification code assigned to the insurer by the NAIC. ")
    named_insured_full_name_a: Optional[str] = Field(None, description="Enter text: The named insured(s) as it/they will appear on the policy declarations page. ")
    policy_effective_date_a: Optional[str] = Field(None, description="Enter date: The effective date of the policy.  The date that the terms and conditions of the policy commence. ")
    policy_policy_number_identifier_a: Optional[str] = Field(None, description="Enter identifier: The identifier assigned by the insurer to the policy, or submission, being referenced exactly as it appears on the policy, including prefix and suffix symbols. If required for sel...")
    producer_customer_identifier_a: Optional[str] = Field(None, description="Enter identifier: The customer's identification number assigned by the producer (e.g. agency or brokerage). ")
    producer_full_name_a: Optional[str] = Field(None, description="Enter text: The full name of the producer/agency. ")
    vehicle_body_code_a: Optional[str] = Field(None, description="Enter code: The body type of the vehicle. ")
    vehicle_body_code_b: Optional[str] = Field(None, description="Enter code: The body type of the vehicle. ")
    vehicle_body_code_c: Optional[str] = Field(None, description="Enter code: The body type of the vehicle. ")
    vehicle_body_code_d: Optional[str] = Field(None, description="Enter code: The body type of the vehicle. ")
    vehicle_body_code_e: Optional[str] = Field(None, description="Enter code: The body type of the vehicle. ")
    vehicle_collision_deductible_amount_a: Optional[str] = Field(None, description="Enter deductible: The collision deductible amount. ")
    vehicle_collision_deductible_amount_b: Optional[str] = Field(None, description="Enter deductible: The collision deductible amount. ")
    vehicle_collision_deductible_amount_c: Optional[str] = Field(None, description="Enter deductible: The collision deductible amount. ")
    vehicle_collision_deductible_amount_d: Optional[str] = Field(None, description="Enter deductible: The collision deductible amount. ")
    vehicle_collision_deductible_amount_e: Optional[str] = Field(None, description="Enter deductible: The collision deductible amount. ")
    vehicle_collision_symbol_code_a: Optional[str] = Field(None, description="Enter code: The symbol required for collision coverage. ")
    vehicle_collision_symbol_code_b: Optional[str] = Field(None, description="Enter code: The symbol required for collision coverage. ")
    vehicle_collision_symbol_code_c: Optional[str] = Field(None, description="Enter code: The symbol required for collision coverage. ")
    vehicle_collision_symbol_code_d: Optional[str] = Field(None, description="Enter code: The symbol required for collision coverage. ")
    vehicle_collision_symbol_code_e: Optional[str] = Field(None, description="Enter code: The symbol required for collision coverage. ")
    vehicle_comprehensive_symbol_code_a: Optional[str] = Field(None, description="Enter code: The symbol required for comprehensive / other than collision coverage. ")
    vehicle_comprehensive_symbol_code_b: Optional[str] = Field(None, description="Enter code: The symbol required for comprehensive / other than collision coverage. ")
    vehicle_comprehensive_symbol_code_c: Optional[str] = Field(None, description="Enter code: The symbol required for comprehensive / other than collision coverage. ")
    vehicle_comprehensive_symbol_code_d: Optional[str] = Field(None, description="Enter code: The symbol required for comprehensive / other than collision coverage. ")
    vehicle_comprehensive_symbol_code_e: Optional[str] = Field(None, description="Enter code: The symbol required for comprehensive / other than collision coverage. ")
    vehicle_cost_new_amount_a: Optional[str] = Field(None, description="Enter amount: The original cost of the vehicle. ")
    vehicle_cost_new_amount_b: Optional[str] = Field(None, description="Enter amount: The original cost of the vehicle. ")
    vehicle_cost_new_amount_c: Optional[str] = Field(None, description="Enter amount: The original cost of the vehicle. ")
    vehicle_cost_new_amount_d: Optional[str] = Field(None, description="Enter amount: The original cost of the vehicle. ")
    vehicle_cost_new_amount_e: Optional[str] = Field(None, description="Enter amount: The original cost of the vehicle. ")
    vehicle_coverage_additional_no_fault_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has additional no-fault coverage. ")
    vehicle_coverage_additional_no_fault_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has additional no-fault coverage. ")
    vehicle_coverage_additional_no_fault_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has additional no-fault coverage. ")
    vehicle_coverage_additional_no_fault_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has additional no-fault coverage. ")
    vehicle_coverage_additional_no_fault_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has additional no-fault coverage. ")
    vehicle_coverage_agreed_or_stated_amount_a: Optional[str] = Field(None, description="Enter amount: The agreed or stated amount used in determining the value of the vehicle at the time of loss. ")
    vehicle_coverage_agreed_or_stated_amount_b: Optional[str] = Field(None, description="Enter amount: The agreed or stated amount used in determining the value of the vehicle at the time of loss. ")
    vehicle_coverage_agreed_or_stated_amount_c: Optional[str] = Field(None, description="Enter amount: The agreed or stated amount used in determining the value of the vehicle at the time of loss. ")
    vehicle_coverage_agreed_or_stated_amount_d: Optional[str] = Field(None, description="Enter amount: The agreed or stated amount used in determining the value of the vehicle at the time of loss. ")
    vehicle_coverage_agreed_or_stated_amount_e: Optional[str] = Field(None, description="Enter amount: The agreed or stated amount used in determining the value of the vehicle at the time of loss. ")
    vehicle_coverage_collision_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has collision coverage. ")
    vehicle_coverage_collision_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has collision coverage. ")
    vehicle_coverage_collision_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has collision coverage. ")
    vehicle_coverage_collision_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has collision coverage. ")
    vehicle_coverage_collision_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has collision coverage. ")
    vehicle_coverage_comprehensive_deductible_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_deductible_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_deductible_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_deductible_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_deductible_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has comprehensive or other than collision coverage. ")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_a: Optional[str] = Field(None, description="Enter amount: The comprehensive or specified cause of loss deductible amount. ")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_b: Optional[str] = Field(None, description="Enter amount: The comprehensive or specified cause of loss deductible amount. ")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_c: Optional[str] = Field(None, description="Enter amount: The comprehensive or specified cause of loss deductible amount. ")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_d: Optional[str] = Field(None, description="Enter amount: The comprehensive or specified cause of loss deductible amount. ")
    vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_e: Optional[str] = Field(None, description="Enter amount: The comprehensive or specified cause of loss deductible amount. ")
    vehicle_coverage_fire_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire and theft is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire and theft is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire and theft is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire and theft is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire and theft is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_windstorm_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire, theft and windstorm is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_windstorm_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire, theft and windstorm is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_windstorm_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire, theft and windstorm is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_windstorm_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire, theft and windstorm is a specified cause of loss on this vehicle. ")
    vehicle_coverage_fire_theft_windstorm_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates fire, theft and windstorm is a specified cause of loss on this vehicle. ")
    vehicle_coverage_full_glass_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has full glass coverage. ")
    vehicle_coverage_full_glass_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has full glass coverage. ")
    vehicle_coverage_full_glass_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has full glass coverage. ")
    vehicle_coverage_full_glass_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has full glass coverage. ")
    vehicle_coverage_full_glass_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has full glass coverage. ")
    vehicle_coverage_liability_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has liability coverage. ")
    vehicle_coverage_liability_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has liability coverage. ")
    vehicle_coverage_liability_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has liability coverage. ")
    vehicle_coverage_liability_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has liability coverage. ")
    vehicle_coverage_liability_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has liability coverage. ")
    vehicle_coverage_limited_specified_perils_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates limited specified perils is a specified cause of loss on this vehicle. ")
    vehicle_coverage_limited_specified_perils_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates limited specified perils is a specified cause of loss on this vehicle. ")
    vehicle_coverage_limited_specified_perils_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates limited specified perils is a specified cause of loss on this vehicle. ")
    vehicle_coverage_limited_specified_perils_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates limited specified perils is a specified cause of loss on this vehicle. ")
    vehicle_coverage_limited_specified_perils_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates limited specified perils is a specified cause of loss on this vehicle. ")
    vehicle_coverage_medical_payments_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has medical payments coverage. ")
    vehicle_coverage_medical_payments_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has medical payments coverage. ")
    vehicle_coverage_medical_payments_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has medical payments coverage. ")
    vehicle_coverage_medical_payments_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has medical payments coverage. ")
    vehicle_coverage_medical_payments_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has medical payments coverage. ")
    vehicle_coverage_no_fault_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has no-fault coverage. ")
    vehicle_coverage_no_fault_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has no-fault coverage. ")
    vehicle_coverage_no_fault_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has no-fault coverage. ")
    vehicle_coverage_no_fault_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has no-fault coverage. ")
    vehicle_coverage_no_fault_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has no-fault coverage. ")
    vehicle_coverage_other_description_a: Optional[str] = Field(None, description="Enter text: The description of the other type of coverage on the vehicle. ")
    vehicle_coverage_other_description_b: Optional[str] = Field(None, description="Enter text: The description of the other type of coverage on the vehicle. ")
    vehicle_coverage_other_description_c: Optional[str] = Field(None, description="Enter text: The description of the other type of coverage on the vehicle. ")
    vehicle_coverage_other_description_d: Optional[str] = Field(None, description="Enter text: The description of the other type of coverage on the vehicle. ")
    vehicle_coverage_other_description_e: Optional[str] = Field(None, description="Enter text: The description of the other type of coverage on the vehicle. ")
    vehicle_coverage_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has a type of coverage not specifically listed. ")
    vehicle_coverage_other_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has a type of coverage not specifically listed. ")
    vehicle_coverage_other_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has a type of coverage not specifically listed. ")
    vehicle_coverage_other_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has a type of coverage not specifically listed. ")
    vehicle_coverage_other_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has a type of coverage not specifically listed. ")
    vehicle_coverage_rental_reimbursement_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has rental reimbursement or transportation expense coverage. ")
    vehicle_coverage_rental_reimbursement_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has rental reimbursement or transportation expense coverage. ")
    vehicle_coverage_rental_reimbursement_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has rental reimbursement or transportation expense coverage. ")
    vehicle_coverage_rental_reimbursement_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has rental reimbursement or transportation expense coverage. ")
    vehicle_coverage_rental_reimbursement_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has rental reimbursement or transportation expense coverage. ")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for specified causes of loss.  The Specified Cause of Loss Codes are:  SCL        Specified Cause of Loss F            Fire F&T        Fir...")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for specified causes of loss.  The Specified Cause of Loss Codes are:  SCL        Specified Cause of Loss F            Fire F&T        Fir...")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for specified causes of loss.  The Specified Cause of Loss Codes are:  SCL        Specified Cause of Loss F            Fire F&T        Fir...")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for specified causes of loss.  The Specified Cause of Loss Codes are:  SCL        Specified Cause of Loss F            Fire F&T        Fir...")
    vehicle_coverage_specified_cause_of_loss_deductible_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the deductible is for specified causes of loss.  The Specified Cause of Loss Codes are:  SCL        Specified Cause of Loss F            Fire F&T        Fir...")
    vehicle_coverage_specified_cause_of_loss_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has specified cause of loss coverage. ")
    vehicle_coverage_specified_cause_of_loss_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has specified cause of loss coverage. ")
    vehicle_coverage_specified_cause_of_loss_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has specified cause of loss coverage. ")
    vehicle_coverage_specified_cause_of_loss_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has specified cause of loss coverage. ")
    vehicle_coverage_specified_cause_of_loss_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has specified cause of loss coverage. ")
    vehicle_coverage_towing_and_labour_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has towing and labor coverage. ")
    vehicle_coverage_towing_and_labour_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has towing and labor coverage. ")
    vehicle_coverage_towing_and_labour_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has towing and labor coverage. ")
    vehicle_coverage_towing_and_labour_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has towing and labor coverage. ")
    vehicle_coverage_towing_and_labour_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has towing and labor coverage. ")
    vehicle_coverage_underinsured_motorists_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has underinsured motorists coverage. ")
    vehicle_coverage_underinsured_motorists_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has underinsured motorists coverage. ")
    vehicle_coverage_underinsured_motorists_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has underinsured motorists coverage. ")
    vehicle_coverage_underinsured_motorists_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has underinsured motorists coverage. ")
    vehicle_coverage_underinsured_motorists_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has underinsured motorists coverage. ")
    vehicle_coverage_uninsured_motorists_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has uninsured motorists coverage. ")
    vehicle_coverage_uninsured_motorists_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has uninsured motorists coverage. ")
    vehicle_coverage_uninsured_motorists_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has uninsured motorists coverage. ")
    vehicle_coverage_uninsured_motorists_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has uninsured motorists coverage. ")
    vehicle_coverage_uninsured_motorists_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle has uninsured motorists coverage. ")
    vehicle_coverage_valuation_actual_cash_value_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the actual cash value or market value. ")
    vehicle_coverage_valuation_actual_cash_value_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the actual cash value or market value. ")
    vehicle_coverage_valuation_actual_cash_value_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the actual cash value or market value. ")
    vehicle_coverage_valuation_actual_cash_value_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the actual cash value or market value. ")
    vehicle_coverage_valuation_actual_cash_value_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the actual cash value or market value. ")
    vehicle_coverage_valuation_agreed_amount_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the agreed amount. ")
    vehicle_coverage_valuation_agreed_amount_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the agreed amount. ")
    vehicle_coverage_valuation_agreed_amount_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the agreed amount. ")
    vehicle_coverage_valuation_agreed_amount_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the agreed amount. ")
    vehicle_coverage_valuation_agreed_amount_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the agreed amount. ")
    vehicle_coverage_valuation_stated_amount_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the stated amount. ")
    vehicle_coverage_valuation_stated_amount_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the stated amount. ")
    vehicle_coverage_valuation_stated_amount_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the stated amount. ")
    vehicle_coverage_valuation_stated_amount_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the stated amount. ")
    vehicle_coverage_valuation_stated_amount_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the valuation method used in determining the value of the vehicle at the time of loss is the stated amount. ")
    vehicle_farthest_zone_code_a: Optional[str] = Field(None, description="Enter code: Identifies the location of the farthest zone from the vehicle's base of operation in which the vehicle is operated. The source of this code is the Insurance Services Office Zone code li...")
    vehicle_farthest_zone_code_b: Optional[str] = Field(None, description="Enter code: Identifies the location of the farthest zone from the vehicle's base of operation in which the vehicle is operated. The source of this code is the Insurance Services Office Zone code li...")
    vehicle_farthest_zone_code_c: Optional[str] = Field(None, description="Enter code: Identifies the location of the farthest zone from the vehicle's base of operation in which the vehicle is operated. The source of this code is the Insurance Services Office Zone code li...")
    vehicle_farthest_zone_code_d: Optional[str] = Field(None, description="Enter code: Identifies the location of the farthest zone from the vehicle's base of operation in which the vehicle is operated. The source of this code is the Insurance Services Office Zone code li...")
    vehicle_farthest_zone_code_e: Optional[str] = Field(None, description="Enter code: Identifies the location of the farthest zone from the vehicle's base of operation in which the vehicle is operated. The source of this code is the Insurance Services Office Zone code li...")
    vehicle_gross_vehicle_weight_a: Optional[str] = Field(None, description="Enter number: The actual weight of the vehicle or the combined weight of tractor and trailer in pounds. ")
    vehicle_gross_vehicle_weight_b: Optional[str] = Field(None, description="Enter number: The actual weight of the vehicle or the combined weight of tractor and trailer in pounds. ")
    vehicle_gross_vehicle_weight_c: Optional[str] = Field(None, description="Enter number: The actual weight of the vehicle or the combined weight of tractor and trailer in pounds. ")
    vehicle_gross_vehicle_weight_d: Optional[str] = Field(None, description="Enter number: The actual weight of the vehicle or the combined weight of tractor and trailer in pounds. ")
    vehicle_gross_vehicle_weight_e: Optional[str] = Field(None, description="Enter number: The actual weight of the vehicle or the combined weight of tractor and trailer in pounds. ")
    vehicle_manufacturers_name_a: Optional[str] = Field(None, description="Enter text: The manufacturer of the vehicle (e.g. Ford, Chevy). ")
    vehicle_manufacturers_name_b: Optional[str] = Field(None, description="Enter text: The manufacturer of the vehicle (e.g. Ford, Chevy). ")
    vehicle_manufacturers_name_c: Optional[str] = Field(None, description="Enter text: The manufacturer of the vehicle (e.g. Ford, Chevy). ")
    vehicle_manufacturers_name_d: Optional[str] = Field(None, description="Enter text: The manufacturer of the vehicle (e.g. Ford, Chevy). ")
    vehicle_manufacturers_name_e: Optional[str] = Field(None, description="Enter text: The manufacturer of the vehicle (e.g. Ford, Chevy). ")
    vehicle_model_name_a: Optional[str] = Field(None, description="Enter text: The manufacturer's model name for the vehicle. ")
    vehicle_model_name_b: Optional[str] = Field(None, description="Enter text: The manufacturer's model name for the vehicle. ")
    vehicle_model_name_c: Optional[str] = Field(None, description="Enter text: The manufacturer's model name for the vehicle. ")
    vehicle_model_name_d: Optional[str] = Field(None, description="Enter text: The manufacturer's model name for the vehicle. ")
    vehicle_model_name_e: Optional[str] = Field(None, description="Enter text: The manufacturer's model name for the vehicle. ")
    vehicle_model_year_a: Optional[str] = Field(None, description="Enter year: The model year of the vehicle. ")
    vehicle_model_year_b: Optional[str] = Field(None, description="Enter year: The model year of the vehicle. ")
    vehicle_model_year_c: Optional[str] = Field(None, description="Enter year: The model year of the vehicle. ")
    vehicle_model_year_d: Optional[str] = Field(None, description="Enter year: The model year of the vehicle. ")
    vehicle_model_year_e: Optional[str] = Field(None, description="Enter year: The model year of the vehicle. ")
    vehicle_net_rating_factor_a: Optional[str] = Field(None, description="Enter rate: The net rating factor that applies to this vehicle. Do not include debits or credits that apply on a policy level. Provide under remarks a description of each debit or credit used in th...")
    vehicle_net_rating_factor_b: Optional[str] = Field(None, description="Enter rate: The net rating factor that applies to this vehicle. Do not include debits or credits that apply on a policy level. Provide under remarks a description of each debit or credit used in th...")
    vehicle_net_rating_factor_c: Optional[str] = Field(None, description="Enter rate: The net rating factor that applies to this vehicle. Do not include debits or credits that apply on a policy level. Provide under remarks a description of each debit or credit used in th...")
    vehicle_net_rating_factor_d: Optional[str] = Field(None, description="Enter rate: The net rating factor that applies to this vehicle. Do not include debits or credits that apply on a policy level. Provide under remarks a description of each debit or credit used in th...")
    vehicle_net_rating_factor_e: Optional[str] = Field(None, description="Enter rate: The net rating factor that applies to this vehicle. Do not include debits or credits that apply on a policy level. Provide under remarks a description of each debit or credit used in th...")
    vehicle_physical_address_city_name_a: Optional[str] = Field(None, description="Enter text: The vehicle's physical address city name. ")
    vehicle_physical_address_city_name_b: Optional[str] = Field(None, description="Enter text: The vehicle's physical address city name. ")
    vehicle_physical_address_city_name_c: Optional[str] = Field(None, description="Enter text: The vehicle's physical address city name. ")
    vehicle_physical_address_city_name_d: Optional[str] = Field(None, description="Enter text: The vehicle's physical address city name. ")
    vehicle_physical_address_city_name_e: Optional[str] = Field(None, description="Enter text: The vehicle's physical address city name. ")
    vehicle_physical_address_county_name_a: Optional[str] = Field(None, description="Enter text: The vehicle's physical address county name. ")
    vehicle_physical_address_county_name_b: Optional[str] = Field(None, description="Enter text: The vehicle's physical address county name. ")
    vehicle_physical_address_county_name_c: Optional[str] = Field(None, description="Enter text: The vehicle's physical address county name. ")
    vehicle_physical_address_county_name_d: Optional[str] = Field(None, description="Enter text: The vehicle's physical address county name. ")
    vehicle_physical_address_county_name_e: Optional[str] = Field(None, description="Enter text: The vehicle's physical address county name. ")
    vehicle_physical_address_line_one_a: Optional[str] = Field(None, description="Enter text: The vehicle's physical address line one. ")
    vehicle_physical_address_line_one_b: Optional[str] = Field(None, description="Enter text: The vehicle's physical address line one. ")
    vehicle_physical_address_line_one_c: Optional[str] = Field(None, description="Enter text: The vehicle's physical address line one. ")
    vehicle_physical_address_line_one_d: Optional[str] = Field(None, description="Enter text: The vehicle's physical address line one. ")
    vehicle_physical_address_line_one_e: Optional[str] = Field(None, description="Enter text: The vehicle's physical address line one. ")
    vehicle_physical_address_postal_code_a: Optional[str] = Field(None, description="Enter code: The vehicle's physical address postal code. ")
    vehicle_physical_address_postal_code_b: Optional[str] = Field(None, description="Enter code: The vehicle's physical address postal code. ")
    vehicle_physical_address_postal_code_c: Optional[str] = Field(None, description="Enter code: The vehicle's physical address postal code. ")
    vehicle_physical_address_postal_code_d: Optional[str] = Field(None, description="Enter code: The vehicle's physical address postal code. ")
    vehicle_physical_address_postal_code_e: Optional[str] = Field(None, description="Enter code: The vehicle's physical address postal code. ")
    vehicle_physical_address_state_or_province_code_a: Optional[str] = Field(None, description="Enter code: The vehicle's physical address state or province code. ")
    vehicle_physical_address_state_or_province_code_b: Optional[str] = Field(None, description="Enter code: The vehicle's physical address state or province code. ")
    vehicle_physical_address_state_or_province_code_c: Optional[str] = Field(None, description="Enter code: The vehicle's physical address state or province code. ")
    vehicle_physical_address_state_or_province_code_d: Optional[str] = Field(None, description="Enter code: The vehicle's physical address state or province code. ")
    vehicle_physical_address_state_or_province_code_e: Optional[str] = Field(None, description="Enter code: The vehicle's physical address state or province code. ")
    vehicle_primary_liability_rating_factor_a: Optional[str] = Field(None, description="Enter rate: The primary liability rating factor contains the number which is used, along with the secondary rating factor, in determining the liability premium.  The primary rating factor which is ...")
    vehicle_primary_liability_rating_factor_b: Optional[str] = Field(None, description="Enter rate: The primary liability rating factor contains the number which is used, along with the secondary rating factor, in determining the liability premium.  The primary rating factor which is ...")
    vehicle_primary_liability_rating_factor_c: Optional[str] = Field(None, description="Enter rate: The primary liability rating factor contains the number which is used, along with the secondary rating factor, in determining the liability premium.  The primary rating factor which is ...")
    vehicle_primary_liability_rating_factor_d: Optional[str] = Field(None, description="Enter rate: The primary liability rating factor contains the number which is used, along with the secondary rating factor, in determining the liability premium.  The primary rating factor which is ...")
    vehicle_primary_liability_rating_factor_e: Optional[str] = Field(None, description="Enter rate: The primary liability rating factor contains the number which is used, along with the secondary rating factor, in determining the liability premium.  The primary rating factor which is ...")
    vehicle_producer_identifier_a: Optional[str] = Field(None, description="Enter number: The producer assigned vehicle number. ")
    vehicle_producer_identifier_b: Optional[str] = Field(None, description="Enter number: The producer assigned vehicle number. ")
    vehicle_producer_identifier_c: Optional[str] = Field(None, description="Enter number: The producer assigned vehicle number. ")
    vehicle_producer_identifier_d: Optional[str] = Field(None, description="Enter number: The producer assigned vehicle number. ")
    vehicle_producer_identifier_e: Optional[str] = Field(None, description="Enter number: The producer assigned vehicle number. ")
    vehicle_radius_of_use_a: Optional[str] = Field(None, description="Enter number: The radius in whole numbers within which this vehicle is operated. ")
    vehicle_radius_of_use_b: Optional[str] = Field(None, description="Enter number: The radius in whole numbers within which this vehicle is operated. ")
    vehicle_radius_of_use_c: Optional[str] = Field(None, description="Enter number: The radius in whole numbers within which this vehicle is operated. ")
    vehicle_radius_of_use_d: Optional[str] = Field(None, description="Enter number: The radius in whole numbers within which this vehicle is operated. ")
    vehicle_radius_of_use_e: Optional[str] = Field(None, description="Enter number: The radius in whole numbers within which this vehicle is operated. ")
    vehicle_rate_class_code_a: Optional[str] = Field(None, description="Enter code: The rate class of the vehicle.  If two rate classes are required, this element should be used to enter the liability code. ")
    vehicle_rate_class_code_b: Optional[str] = Field(None, description="Enter code: The rate class of the vehicle.  If two rate classes are required, this element should be used to enter the liability code. ")
    vehicle_rate_class_code_c: Optional[str] = Field(None, description="Enter code: The rate class of the vehicle.  If two rate classes are required, this element should be used to enter the liability code. ")
    vehicle_rate_class_code_d: Optional[str] = Field(None, description="Enter code: The rate class of the vehicle.  If two rate classes are required, this element should be used to enter the liability code. ")
    vehicle_rate_class_code_e: Optional[str] = Field(None, description="Enter code: The rate class of the vehicle.  If two rate classes are required, this element should be used to enter the liability code. ")
    vehicle_rating_territory_code_a: Optional[str] = Field(None, description="Enter code: The rating territory code where the vehicle is principally garaged. ")
    vehicle_rating_territory_code_b: Optional[str] = Field(None, description="Enter code: The rating territory code where the vehicle is principally garaged. ")
    vehicle_rating_territory_code_c: Optional[str] = Field(None, description="Enter code: The rating territory code where the vehicle is principally garaged. ")
    vehicle_rating_territory_code_d: Optional[str] = Field(None, description="Enter code: The rating territory code where the vehicle is principally garaged. ")
    vehicle_rating_territory_code_e: Optional[str] = Field(None, description="Enter code: The rating territory code where the vehicle is principally garaged. ")
    vehicle_registration_state_or_province_code_a: Optional[str] = Field(None, description="Enter code: The state or province in which the vehicle is registered. ")
    vehicle_registration_state_or_province_code_b: Optional[str] = Field(None, description="Enter code: The state or province in which the vehicle is registered. ")
    vehicle_registration_state_or_province_code_c: Optional[str] = Field(None, description="Enter code: The state or province in which the vehicle is registered. ")
    vehicle_registration_state_or_province_code_d: Optional[str] = Field(None, description="Enter code: The state or province in which the vehicle is registered. ")
    vehicle_registration_state_or_province_code_e: Optional[str] = Field(None, description="Enter code: The state or province in which the vehicle is registered. ")
    vehicle_seating_capacity_count_a: Optional[str] = Field(None, description="Enter number: The seating capacity of the vehicle.  Required for rating public passenger vehicles. ")
    vehicle_seating_capacity_count_b: Optional[str] = Field(None, description="Enter number: The seating capacity of the vehicle.  Required for rating public passenger vehicles. ")
    vehicle_seating_capacity_count_c: Optional[str] = Field(None, description="Enter number: The seating capacity of the vehicle.  Required for rating public passenger vehicles. ")
    vehicle_seating_capacity_count_d: Optional[str] = Field(None, description="Enter number: The seating capacity of the vehicle.  Required for rating public passenger vehicles. ")
    vehicle_seating_capacity_count_e: Optional[str] = Field(None, description="Enter number: The seating capacity of the vehicle.  Required for rating public passenger vehicles. ")
    vehicle_special_industry_class_code_a: Optional[str] = Field(None, description="Enter code: The secondary Special Industry Class code which applies to commercial vehicles as determined by industry rating manuals. ")
    vehicle_special_industry_class_code_b: Optional[str] = Field(None, description="Enter code: The secondary Special Industry Class code which applies to commercial vehicles as determined by industry rating manuals. ")
    vehicle_special_industry_class_code_c: Optional[str] = Field(None, description="Enter code: The secondary Special Industry Class code which applies to commercial vehicles as determined by industry rating manuals. ")
    vehicle_special_industry_class_code_d: Optional[str] = Field(None, description="Enter code: The secondary Special Industry Class code which applies to commercial vehicles as determined by industry rating manuals. ")
    vehicle_special_industry_class_code_e: Optional[str] = Field(None, description="Enter code: The secondary Special Industry Class code which applies to commercial vehicles as determined by industry rating manuals. ")
    vehicle_symbol_code_a: Optional[str] = Field(None, description="Enter code: The symbol required for physical damage coverage. ")
    vehicle_symbol_code_b: Optional[str] = Field(None, description="Enter code: The symbol required for physical damage coverage. ")
    vehicle_symbol_code_c: Optional[str] = Field(None, description="Enter code: The symbol required for physical damage coverage. ")
    vehicle_symbol_code_d: Optional[str] = Field(None, description="Enter code: The symbol required for physical damage coverage. ")
    vehicle_symbol_code_e: Optional[str] = Field(None, description="Enter code: The symbol required for physical damage coverage. ")
    vehicle_total_premium_amount_a: Optional[str] = Field(None, description="Enter amount: The total amount for the vehicle. ")
    vehicle_total_premium_amount_b: Optional[str] = Field(None, description="Enter amount: The total amount for the vehicle. ")
    vehicle_total_premium_amount_c: Optional[str] = Field(None, description="Enter amount: The total amount for the vehicle. ")
    vehicle_total_premium_amount_d: Optional[str] = Field(None, description="Enter amount: The total amount for the vehicle. ")
    vehicle_total_premium_amount_e: Optional[str] = Field(None, description="Enter amount: The total amount for the vehicle. ")
    vehicle_use_commercial_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for commercial purposes. ")
    vehicle_use_commercial_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for commercial purposes. ")
    vehicle_use_commercial_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for commercial purposes. ")
    vehicle_use_commercial_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for commercial purposes. ")
    vehicle_use_commercial_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for commercial purposes. ")
    vehicle_use_farm_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for farming. ")
    vehicle_use_farm_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for farming. ")
    vehicle_use_farm_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for farming. ")
    vehicle_use_farm_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for farming. ")
    vehicle_use_farm_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for farming. ")
    vehicle_use_fifteen_miles_or_over_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school 15 miles or over one way. ")
    vehicle_use_fifteen_miles_or_over_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school 15 miles or over one way. ")
    vehicle_use_fifteen_miles_or_over_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school 15 miles or over one way. ")
    vehicle_use_fifteen_miles_or_over_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school 15 miles or over one way. ")
    vehicle_use_fifteen_miles_or_over_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school 15 miles or over one way. ")
    vehicle_use_for_hire_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for hire. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_for_hire_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for hire. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_for_hire_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for hire. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_for_hire_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for hire. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_for_hire_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for hire. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_other_description_a: Optional[str] = Field(None, description="Enter text: The description of the other vehicle usage. 11/24/2009 - added field to 11/2009 version")
    vehicle_use_other_description_b: Optional[str] = Field(None, description="Enter text: The description of the other vehicle usage. 11/24/2009 - added field to 11/2009 version")
    vehicle_use_other_description_c: Optional[str] = Field(None, description="Enter text: The description of the other vehicle usage. 11/24/2009 - added field to 11/2009 version")
    vehicle_use_other_description_d: Optional[str] = Field(None, description="Enter text: The description of the other vehicle usage. 11/24/2009 - added field to 11/2009 version")
    vehicle_use_other_description_e: Optional[str] = Field(None, description="Enter text: The description of the other vehicle usage. 11/24/2009 - added field to 11/2009 version")
    vehicle_use_other_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for other purposes. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_other_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for other purposes. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_other_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for other purposes. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_other_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for other purposes. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_other_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for other purposes. 11/9/2009 - added field to 11/2009 version")
    vehicle_use_pleasure_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for pleasure. ")
    vehicle_use_pleasure_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for pleasure. ")
    vehicle_use_pleasure_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for pleasure. ")
    vehicle_use_pleasure_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for pleasure. ")
    vehicle_use_pleasure_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for pleasure. ")
    vehicle_use_retail_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the retail industry. ")
    vehicle_use_retail_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the retail industry. ")
    vehicle_use_retail_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the retail industry. ")
    vehicle_use_retail_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the retail industry. ")
    vehicle_use_retail_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the retail industry. ")
    vehicle_use_service_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the service industry. ")
    vehicle_use_service_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the service industry. ")
    vehicle_use_service_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the service industry. ")
    vehicle_use_service_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the service industry. ")
    vehicle_use_service_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the primary use for the vehicle is for the service industry. ")
    vehicle_use_under_fifteen_miles_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school under 15 miles one way. ")
    vehicle_use_under_fifteen_miles_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school under 15 miles one way. ")
    vehicle_use_under_fifteen_miles_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school under 15 miles one way. ")
    vehicle_use_under_fifteen_miles_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school under 15 miles one way. ")
    vehicle_use_under_fifteen_miles_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the vehicle is used for commuting purposes to work or school, and is driven to work or school under 15 miles one way. ")
    vehicle_vehicle_type_commercial_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is commercial. ")
    vehicle_vehicle_type_commercial_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is commercial. ")
    vehicle_vehicle_type_commercial_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is commercial. ")
    vehicle_vehicle_type_commercial_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is commercial. ")
    vehicle_vehicle_type_commercial_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is commercial. ")
    vehicle_vehicle_type_private_passenger_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is private passenger. ")
    vehicle_vehicle_type_private_passenger_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is private passenger. ")
    vehicle_vehicle_type_private_passenger_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is private passenger. ")
    vehicle_vehicle_type_private_passenger_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is private passenger. ")
    vehicle_vehicle_type_private_passenger_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is private passenger. ")
    vehicle_vehicle_type_special_indicator_a: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is special (e.g. classic, antique automobile). ")
    vehicle_vehicle_type_special_indicator_b: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is special (e.g. classic, antique automobile). ")
    vehicle_vehicle_type_special_indicator_c: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is special (e.g. classic, antique automobile). ")
    vehicle_vehicle_type_special_indicator_d: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is special (e.g. classic, antique automobile). ")
    vehicle_vehicle_type_special_indicator_e: Optional[str] = Field(None, description="Check the box (if applicable): Indicates the predominant type of the vehicle is special (e.g. classic, antique automobile). ")
    vehicle_vin_identifier_a: Optional[str] = Field(None, description="Enter identifier: The vehicle identification number (VIN) or serial number assigned by the manufacturer. ")
    vehicle_vin_identifier_b: Optional[str] = Field(None, description="Enter identifier: The vehicle identification number (VIN) or serial number assigned by the manufacturer. ")
    vehicle_vin_identifier_c: Optional[str] = Field(None, description="Enter identifier: The vehicle identification number (VIN) or serial number assigned by the manufacturer. ")
    vehicle_vin_identifier_d: Optional[str] = Field(None, description="Enter identifier: The vehicle identification number (VIN) or serial number assigned by the manufacturer. ")
    vehicle_vin_identifier_e: Optional[str] = Field(None, description="Enter identifier: The vehicle identification number (VIN) or serial number assigned by the manufacturer. ")

    @classmethod
    def get_field_mapping(cls) -> Dict[str, str]:
        return {
            "form_completion_date_a": "Form_CompletionDate_A",
            "form_edition_identifier_a": "Form_EditionIdentifier_A",
            "insurer_full_name_a": "Insurer_FullName_A",
            "insurer_naic_code_a": "Insurer_NAICCode_A",
            "named_insured_full_name_a": "NamedInsured_FullName_A",
            "policy_effective_date_a": "Policy_EffectiveDate_A",
            "policy_policy_number_identifier_a": "Policy_PolicyNumberIdentifier_A",
            "producer_customer_identifier_a": "Producer_CustomerIdentifier_A",
            "producer_full_name_a": "Producer_FullName_A",
            "vehicle_body_code_a": "Vehicle_BodyCode_A",
            "vehicle_body_code_b": "Vehicle_BodyCode_B",
            "vehicle_body_code_c": "Vehicle_BodyCode_C",
            "vehicle_body_code_d": "Vehicle_BodyCode_D",
            "vehicle_body_code_e": "Vehicle_BodyCode_E",
            "vehicle_collision_deductible_amount_a": "Vehicle_Collision_DeductibleAmount_A",
            "vehicle_collision_deductible_amount_b": "Vehicle_Collision_DeductibleAmount_B",
            "vehicle_collision_deductible_amount_c": "Vehicle_Collision_DeductibleAmount_C",
            "vehicle_collision_deductible_amount_d": "Vehicle_Collision_DeductibleAmount_D",
            "vehicle_collision_deductible_amount_e": "Vehicle_Collision_DeductibleAmount_E",
            "vehicle_collision_symbol_code_a": "Vehicle_CollisionSymbolCode_A",
            "vehicle_collision_symbol_code_b": "Vehicle_CollisionSymbolCode_B",
            "vehicle_collision_symbol_code_c": "Vehicle_CollisionSymbolCode_C",
            "vehicle_collision_symbol_code_d": "Vehicle_CollisionSymbolCode_D",
            "vehicle_collision_symbol_code_e": "Vehicle_CollisionSymbolCode_E",
            "vehicle_comprehensive_symbol_code_a": "Vehicle_ComprehensiveSymbolCode_A",
            "vehicle_comprehensive_symbol_code_b": "Vehicle_ComprehensiveSymbolCode_B",
            "vehicle_comprehensive_symbol_code_c": "Vehicle_ComprehensiveSymbolCode_C",
            "vehicle_comprehensive_symbol_code_d": "Vehicle_ComprehensiveSymbolCode_D",
            "vehicle_comprehensive_symbol_code_e": "Vehicle_ComprehensiveSymbolCode_E",
            "vehicle_cost_new_amount_a": "Vehicle_CostNewAmount_A",
            "vehicle_cost_new_amount_b": "Vehicle_CostNewAmount_B",
            "vehicle_cost_new_amount_c": "Vehicle_CostNewAmount_C",
            "vehicle_cost_new_amount_d": "Vehicle_CostNewAmount_D",
            "vehicle_cost_new_amount_e": "Vehicle_CostNewAmount_E",
            "vehicle_coverage_additional_no_fault_indicator_a": "Vehicle_Coverage_AdditionalNoFaultIndicator_A",
            "vehicle_coverage_additional_no_fault_indicator_b": "Vehicle_Coverage_AdditionalNoFaultIndicator_B",
            "vehicle_coverage_additional_no_fault_indicator_c": "Vehicle_Coverage_AdditionalNoFaultIndicator_C",
            "vehicle_coverage_additional_no_fault_indicator_d": "Vehicle_Coverage_AdditionalNoFaultIndicator_D",
            "vehicle_coverage_additional_no_fault_indicator_e": "Vehicle_Coverage_AdditionalNoFaultIndicator_E",
            "vehicle_coverage_agreed_or_stated_amount_a": "Vehicle_Coverage_AgreedOrStatedAmount_A",
            "vehicle_coverage_agreed_or_stated_amount_b": "Vehicle_Coverage_AgreedOrStatedAmount_B",
            "vehicle_coverage_agreed_or_stated_amount_c": "Vehicle_Coverage_AgreedOrStatedAmount_C",
            "vehicle_coverage_agreed_or_stated_amount_d": "Vehicle_Coverage_AgreedOrStatedAmount_D",
            "vehicle_coverage_agreed_or_stated_amount_e": "Vehicle_Coverage_AgreedOrStatedAmount_E",
            "vehicle_coverage_collision_indicator_a": "Vehicle_Coverage_CollisionIndicator_A",
            "vehicle_coverage_collision_indicator_b": "Vehicle_Coverage_CollisionIndicator_B",
            "vehicle_coverage_collision_indicator_c": "Vehicle_Coverage_CollisionIndicator_C",
            "vehicle_coverage_collision_indicator_d": "Vehicle_Coverage_CollisionIndicator_D",
            "vehicle_coverage_collision_indicator_e": "Vehicle_Coverage_CollisionIndicator_E",
            "vehicle_coverage_comprehensive_deductible_indicator_a": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_A",
            "vehicle_coverage_comprehensive_deductible_indicator_b": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_B",
            "vehicle_coverage_comprehensive_deductible_indicator_c": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_C",
            "vehicle_coverage_comprehensive_deductible_indicator_d": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_D",
            "vehicle_coverage_comprehensive_deductible_indicator_e": "Vehicle_Coverage_ComprehensiveDeductibleIndicator_E",
            "vehicle_coverage_comprehensive_indicator_a": "Vehicle_Coverage_ComprehensiveIndicator_A",
            "vehicle_coverage_comprehensive_indicator_b": "Vehicle_Coverage_ComprehensiveIndicator_B",
            "vehicle_coverage_comprehensive_indicator_c": "Vehicle_Coverage_ComprehensiveIndicator_C",
            "vehicle_coverage_comprehensive_indicator_d": "Vehicle_Coverage_ComprehensiveIndicator_D",
            "vehicle_coverage_comprehensive_indicator_e": "Vehicle_Coverage_ComprehensiveIndicator_E",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_a": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_A",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_b": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_B",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_c": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_C",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_d": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_D",
            "vehicle_coverage_comprehensive_or_specified_cause_of_loss_deductible_amount_e": "Vehicle_Coverage_ComprehensiveOrSpecifiedCauseOfLossDeductibleAmount_E",
            "vehicle_coverage_fire_indicator_a": "Vehicle_Coverage_FireIndicator_A",
            "vehicle_coverage_fire_indicator_b": "Vehicle_Coverage_FireIndicator_B",
            "vehicle_coverage_fire_indicator_c": "Vehicle_Coverage_FireIndicator_C",
            "vehicle_coverage_fire_indicator_d": "Vehicle_Coverage_FireIndicator_D",
            "vehicle_coverage_fire_indicator_e": "Vehicle_Coverage_FireIndicator_E",
            "vehicle_coverage_fire_theft_indicator_a": "Vehicle_Coverage_FireTheftIndicator_A",
            "vehicle_coverage_fire_theft_indicator_b": "Vehicle_Coverage_FireTheftIndicator_B",
            "vehicle_coverage_fire_theft_indicator_c": "Vehicle_Coverage_FireTheftIndicator_C",
            "vehicle_coverage_fire_theft_indicator_d": "Vehicle_Coverage_FireTheftIndicator_D",
            "vehicle_coverage_fire_theft_indicator_e": "Vehicle_Coverage_FireTheftIndicator_E",
            "vehicle_coverage_fire_theft_windstorm_indicator_a": "Vehicle_Coverage_FireTheftWindstormIndicator_A",
            "vehicle_coverage_fire_theft_windstorm_indicator_b": "Vehicle_Coverage_FireTheftWindstormIndicator_B",
            "vehicle_coverage_fire_theft_windstorm_indicator_c": "Vehicle_Coverage_FireTheftWindstormIndicator_C",
            "vehicle_coverage_fire_theft_windstorm_indicator_d": "Vehicle_Coverage_FireTheftWindstormIndicator_D",
            "vehicle_coverage_fire_theft_windstorm_indicator_e": "Vehicle_Coverage_FireTheftWindstormIndicator_E",
            "vehicle_coverage_full_glass_indicator_a": "Vehicle_Coverage_FullGlassIndicator_A",
            "vehicle_coverage_full_glass_indicator_b": "Vehicle_Coverage_FullGlassIndicator_B",
            "vehicle_coverage_full_glass_indicator_c": "Vehicle_Coverage_FullGlassIndicator_C",
            "vehicle_coverage_full_glass_indicator_d": "Vehicle_Coverage_FullGlassIndicator_D",
            "vehicle_coverage_full_glass_indicator_e": "Vehicle_Coverage_FullGlassIndicator_E",
            "vehicle_coverage_liability_indicator_a": "Vehicle_Coverage_LiabilityIndicator_A",
            "vehicle_coverage_liability_indicator_b": "Vehicle_Coverage_LiabilityIndicator_B",
            "vehicle_coverage_liability_indicator_c": "Vehicle_Coverage_LiabilityIndicator_C",
            "vehicle_coverage_liability_indicator_d": "Vehicle_Coverage_LiabilityIndicator_D",
            "vehicle_coverage_liability_indicator_e": "Vehicle_Coverage_LiabilityIndicator_E",
            "vehicle_coverage_limited_specified_perils_indicator_a": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_A",
            "vehicle_coverage_limited_specified_perils_indicator_b": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_B",
            "vehicle_coverage_limited_specified_perils_indicator_c": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_C",
            "vehicle_coverage_limited_specified_perils_indicator_d": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_D",
            "vehicle_coverage_limited_specified_perils_indicator_e": "Vehicle_Coverage_LimitedSpecifiedPerilsIndicator_E",
            "vehicle_coverage_medical_payments_indicator_a": "Vehicle_Coverage_MedicalPaymentsIndicator_A",
            "vehicle_coverage_medical_payments_indicator_b": "Vehicle_Coverage_MedicalPaymentsIndicator_B",
            "vehicle_coverage_medical_payments_indicator_c": "Vehicle_Coverage_MedicalPaymentsIndicator_C",
            "vehicle_coverage_medical_payments_indicator_d": "Vehicle_Coverage_MedicalPaymentsIndicator_D",
            "vehicle_coverage_medical_payments_indicator_e": "Vehicle_Coverage_MedicalPaymentsIndicator_E",
            "vehicle_coverage_no_fault_indicator_a": "Vehicle_Coverage_NoFaultIndicator_A",
            "vehicle_coverage_no_fault_indicator_b": "Vehicle_Coverage_NoFaultIndicator_B",
            "vehicle_coverage_no_fault_indicator_c": "Vehicle_Coverage_NoFaultIndicator_C",
            "vehicle_coverage_no_fault_indicator_d": "Vehicle_Coverage_NoFaultIndicator_D",
            "vehicle_coverage_no_fault_indicator_e": "Vehicle_Coverage_NoFaultIndicator_E",
            "vehicle_coverage_other_description_a": "Vehicle_Coverage_OtherDescription_A",
            "vehicle_coverage_other_description_b": "Vehicle_Coverage_OtherDescription_B",
            "vehicle_coverage_other_description_c": "Vehicle_Coverage_OtherDescription_C",
            "vehicle_coverage_other_description_d": "Vehicle_Coverage_OtherDescription_D",
            "vehicle_coverage_other_description_e": "Vehicle_Coverage_OtherDescription_E",
            "vehicle_coverage_other_indicator_a": "Vehicle_Coverage_OtherIndicator_A",
            "vehicle_coverage_other_indicator_b": "Vehicle_Coverage_OtherIndicator_B",
            "vehicle_coverage_other_indicator_c": "Vehicle_Coverage_OtherIndicator_C",
            "vehicle_coverage_other_indicator_d": "Vehicle_Coverage_OtherIndicator_D",
            "vehicle_coverage_other_indicator_e": "Vehicle_Coverage_OtherIndicator_E",
            "vehicle_coverage_rental_reimbursement_indicator_a": "Vehicle_Coverage_RentalReimbursementIndicator_A",
            "vehicle_coverage_rental_reimbursement_indicator_b": "Vehicle_Coverage_RentalReimbursementIndicator_B",
            "vehicle_coverage_rental_reimbursement_indicator_c": "Vehicle_Coverage_RentalReimbursementIndicator_C",
            "vehicle_coverage_rental_reimbursement_indicator_d": "Vehicle_Coverage_RentalReimbursementIndicator_D",
            "vehicle_coverage_rental_reimbursement_indicator_e": "Vehicle_Coverage_RentalReimbursementIndicator_E",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_a": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_A",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_b": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_B",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_c": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_C",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_d": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_D",
            "vehicle_coverage_specified_cause_of_loss_deductible_indicator_e": "Vehicle_Coverage_SpecifiedCauseOfLossDeductibleIndicator_E",
            "vehicle_coverage_specified_cause_of_loss_indicator_a": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_A",
            "vehicle_coverage_specified_cause_of_loss_indicator_b": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_B",
            "vehicle_coverage_specified_cause_of_loss_indicator_c": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_C",
            "vehicle_coverage_specified_cause_of_loss_indicator_d": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_D",
            "vehicle_coverage_specified_cause_of_loss_indicator_e": "Vehicle_Coverage_SpecifiedCauseOfLossIndicator_E",
            "vehicle_coverage_towing_and_labour_indicator_a": "Vehicle_Coverage_TowingAndLabourIndicator_A",
            "vehicle_coverage_towing_and_labour_indicator_b": "Vehicle_Coverage_TowingAndLabourIndicator_B",
            "vehicle_coverage_towing_and_labour_indicator_c": "Vehicle_Coverage_TowingAndLabourIndicator_C",
            "vehicle_coverage_towing_and_labour_indicator_d": "Vehicle_Coverage_TowingAndLabourIndicator_D",
            "vehicle_coverage_towing_and_labour_indicator_e": "Vehicle_Coverage_TowingAndLabourIndicator_E",
            "vehicle_coverage_underinsured_motorists_indicator_a": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_A",
            "vehicle_coverage_underinsured_motorists_indicator_b": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_B",
            "vehicle_coverage_underinsured_motorists_indicator_c": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_C",
            "vehicle_coverage_underinsured_motorists_indicator_d": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_D",
            "vehicle_coverage_underinsured_motorists_indicator_e": "Vehicle_Coverage_UnderinsuredMotoristsIndicator_E",
            "vehicle_coverage_uninsured_motorists_indicator_a": "Vehicle_Coverage_UninsuredMotoristsIndicator_A",
            "vehicle_coverage_uninsured_motorists_indicator_b": "Vehicle_Coverage_UninsuredMotoristsIndicator_B",
            "vehicle_coverage_uninsured_motorists_indicator_c": "Vehicle_Coverage_UninsuredMotoristsIndicator_C",
            "vehicle_coverage_uninsured_motorists_indicator_d": "Vehicle_Coverage_UninsuredMotoristsIndicator_D",
            "vehicle_coverage_uninsured_motorists_indicator_e": "Vehicle_Coverage_UninsuredMotoristsIndicator_E",
            "vehicle_coverage_valuation_actual_cash_value_indicator_a": "Vehicle_Coverage_ValuationActualCashValueIndicator_A",
            "vehicle_coverage_valuation_actual_cash_value_indicator_b": "Vehicle_Coverage_ValuationActualCashValueIndicator_B",
            "vehicle_coverage_valuation_actual_cash_value_indicator_c": "Vehicle_Coverage_ValuationActualCashValueIndicator_C",
            "vehicle_coverage_valuation_actual_cash_value_indicator_d": "Vehicle_Coverage_ValuationActualCashValueIndicator_D",
            "vehicle_coverage_valuation_actual_cash_value_indicator_e": "Vehicle_Coverage_ValuationActualCashValueIndicator_E",
            "vehicle_coverage_valuation_agreed_amount_indicator_a": "Vehicle_Coverage_ValuationAgreedAmountIndicator_A",
            "vehicle_coverage_valuation_agreed_amount_indicator_b": "Vehicle_Coverage_ValuationAgreedAmountIndicator_B",
            "vehicle_coverage_valuation_agreed_amount_indicator_c": "Vehicle_Coverage_ValuationAgreedAmountIndicator_C",
            "vehicle_coverage_valuation_agreed_amount_indicator_d": "Vehicle_Coverage_ValuationAgreedAmountIndicator_D",
            "vehicle_coverage_valuation_agreed_amount_indicator_e": "Vehicle_Coverage_ValuationAgreedAmountIndicator_E",
            "vehicle_coverage_valuation_stated_amount_indicator_a": "Vehicle_Coverage_ValuationStatedAmountIndicator_A",
            "vehicle_coverage_valuation_stated_amount_indicator_b": "Vehicle_Coverage_ValuationStatedAmountIndicator_B",
            "vehicle_coverage_valuation_stated_amount_indicator_c": "Vehicle_Coverage_ValuationStatedAmountIndicator_C",
            "vehicle_coverage_valuation_stated_amount_indicator_d": "Vehicle_Coverage_ValuationStatedAmountIndicator_D",
            "vehicle_coverage_valuation_stated_amount_indicator_e": "Vehicle_Coverage_ValuationStatedAmountIndicator_E",
            "vehicle_farthest_zone_code_a": "Vehicle_FarthestZoneCode_A",
            "vehicle_farthest_zone_code_b": "Vehicle_FarthestZoneCode_B",
            "vehicle_farthest_zone_code_c": "Vehicle_FarthestZoneCode_C",
            "vehicle_farthest_zone_code_d": "Vehicle_FarthestZoneCode_D",
            "vehicle_farthest_zone_code_e": "Vehicle_FarthestZoneCode_E",
            "vehicle_gross_vehicle_weight_a": "Vehicle_GrossVehicleWeight_A",
            "vehicle_gross_vehicle_weight_b": "Vehicle_GrossVehicleWeight_B",
            "vehicle_gross_vehicle_weight_c": "Vehicle_GrossVehicleWeight_C",
            "vehicle_gross_vehicle_weight_d": "Vehicle_GrossVehicleWeight_D",
            "vehicle_gross_vehicle_weight_e": "Vehicle_GrossVehicleWeight_E",
            "vehicle_manufacturers_name_a": "Vehicle_ManufacturersName_A",
            "vehicle_manufacturers_name_b": "Vehicle_ManufacturersName_B",
            "vehicle_manufacturers_name_c": "Vehicle_ManufacturersName_C",
            "vehicle_manufacturers_name_d": "Vehicle_ManufacturersName_D",
            "vehicle_manufacturers_name_e": "Vehicle_ManufacturersName_E",
            "vehicle_model_name_a": "Vehicle_ModelName_A",
            "vehicle_model_name_b": "Vehicle_ModelName_B",
            "vehicle_model_name_c": "Vehicle_ModelName_C",
            "vehicle_model_name_d": "Vehicle_ModelName_D",
            "vehicle_model_name_e": "Vehicle_ModelName_E",
            "vehicle_model_year_a": "Vehicle_ModelYear_A",
            "vehicle_model_year_b": "Vehicle_ModelYear_B",
            "vehicle_model_year_c": "Vehicle_ModelYear_C",
            "vehicle_model_year_d": "Vehicle_ModelYear_D",
            "vehicle_model_year_e": "Vehicle_ModelYear_E",
            "vehicle_net_rating_factor_a": "Vehicle_NetRatingFactor_A",
            "vehicle_net_rating_factor_b": "Vehicle_NetRatingFactor_B",
            "vehicle_net_rating_factor_c": "Vehicle_NetRatingFactor_C",
            "vehicle_net_rating_factor_d": "Vehicle_NetRatingFactor_D",
            "vehicle_net_rating_factor_e": "Vehicle_NetRatingFactor_E",
            "vehicle_physical_address_city_name_a": "Vehicle_PhysicalAddress_CityName_A",
            "vehicle_physical_address_city_name_b": "Vehicle_PhysicalAddress_CityName_B",
            "vehicle_physical_address_city_name_c": "Vehicle_PhysicalAddress_CityName_C",
            "vehicle_physical_address_city_name_d": "Vehicle_PhysicalAddress_CityName_D",
            "vehicle_physical_address_city_name_e": "Vehicle_PhysicalAddress_CityName_E",
            "vehicle_physical_address_county_name_a": "Vehicle_PhysicalAddress_CountyName_A",
            "vehicle_physical_address_county_name_b": "Vehicle_PhysicalAddress_CountyName_B",
            "vehicle_physical_address_county_name_c": "Vehicle_PhysicalAddress_CountyName_C",
            "vehicle_physical_address_county_name_d": "Vehicle_PhysicalAddress_CountyName_D",
            "vehicle_physical_address_county_name_e": "Vehicle_PhysicalAddress_CountyName_E",
            "vehicle_physical_address_line_one_a": "Vehicle_PhysicalAddress_LineOne_A",
            "vehicle_physical_address_line_one_b": "Vehicle_PhysicalAddress_LineOne_B",
            "vehicle_physical_address_line_one_c": "Vehicle_PhysicalAddress_LineOne_C",
            "vehicle_physical_address_line_one_d": "Vehicle_PhysicalAddress_LineOne_D",
            "vehicle_physical_address_line_one_e": "Vehicle_PhysicalAddress_LineOne_E",
            "vehicle_physical_address_postal_code_a": "Vehicle_PhysicalAddress_PostalCode_A",
            "vehicle_physical_address_postal_code_b": "Vehicle_PhysicalAddress_PostalCode_B",
            "vehicle_physical_address_postal_code_c": "Vehicle_PhysicalAddress_PostalCode_C",
            "vehicle_physical_address_postal_code_d": "Vehicle_PhysicalAddress_PostalCode_D",
            "vehicle_physical_address_postal_code_e": "Vehicle_PhysicalAddress_PostalCode_E",
            "vehicle_physical_address_state_or_province_code_a": "Vehicle_PhysicalAddress_StateOrProvinceCode_A",
            "vehicle_physical_address_state_or_province_code_b": "Vehicle_PhysicalAddress_StateOrProvinceCode_B",
            "vehicle_physical_address_state_or_province_code_c": "Vehicle_PhysicalAddress_StateOrProvinceCode_C",
            "vehicle_physical_address_state_or_province_code_d": "Vehicle_PhysicalAddress_StateOrProvinceCode_D",
            "vehicle_physical_address_state_or_province_code_e": "Vehicle_PhysicalAddress_StateOrProvinceCode_E",
            "vehicle_primary_liability_rating_factor_a": "Vehicle_PrimaryLiabilityRatingFactor_A",
            "vehicle_primary_liability_rating_factor_b": "Vehicle_PrimaryLiabilityRatingFactor_B",
            "vehicle_primary_liability_rating_factor_c": "Vehicle_PrimaryLiabilityRatingFactor_C",
            "vehicle_primary_liability_rating_factor_d": "Vehicle_PrimaryLiabilityRatingFactor_D",
            "vehicle_primary_liability_rating_factor_e": "Vehicle_PrimaryLiabilityRatingFactor_E",
            "vehicle_producer_identifier_a": "Vehicle_ProducerIdentifier_A",
            "vehicle_producer_identifier_b": "Vehicle_ProducerIdentifier_B",
            "vehicle_producer_identifier_c": "Vehicle_ProducerIdentifier_C",
            "vehicle_producer_identifier_d": "Vehicle_ProducerIdentifier_D",
            "vehicle_producer_identifier_e": "Vehicle_ProducerIdentifier_E",
            "vehicle_radius_of_use_a": "Vehicle_RadiusOfUse_A",
            "vehicle_radius_of_use_b": "Vehicle_RadiusOfUse_B",
            "vehicle_radius_of_use_c": "Vehicle_RadiusOfUse_C",
            "vehicle_radius_of_use_d": "Vehicle_RadiusOfUse_D",
            "vehicle_radius_of_use_e": "Vehicle_RadiusOfUse_E",
            "vehicle_rate_class_code_a": "Vehicle_RateClassCode_A",
            "vehicle_rate_class_code_b": "Vehicle_RateClassCode_B",
            "vehicle_rate_class_code_c": "Vehicle_RateClassCode_C",
            "vehicle_rate_class_code_d": "Vehicle_RateClassCode_D",
            "vehicle_rate_class_code_e": "Vehicle_RateClassCode_E",
            "vehicle_rating_territory_code_a": "Vehicle_RatingTerritoryCode_A",
            "vehicle_rating_territory_code_b": "Vehicle_RatingTerritoryCode_B",
            "vehicle_rating_territory_code_c": "Vehicle_RatingTerritoryCode_C",
            "vehicle_rating_territory_code_d": "Vehicle_RatingTerritoryCode_D",
            "vehicle_rating_territory_code_e": "Vehicle_RatingTerritoryCode_E",
            "vehicle_registration_state_or_province_code_a": "Vehicle_Registration_StateOrProvinceCode_A",
            "vehicle_registration_state_or_province_code_b": "Vehicle_Registration_StateOrProvinceCode_B",
            "vehicle_registration_state_or_province_code_c": "Vehicle_Registration_StateOrProvinceCode_C",
            "vehicle_registration_state_or_province_code_d": "Vehicle_Registration_StateOrProvinceCode_D",
            "vehicle_registration_state_or_province_code_e": "Vehicle_Registration_StateOrProvinceCode_E",
            "vehicle_seating_capacity_count_a": "Vehicle_SeatingCapacityCount_A",
            "vehicle_seating_capacity_count_b": "Vehicle_SeatingCapacityCount_B",
            "vehicle_seating_capacity_count_c": "Vehicle_SeatingCapacityCount_C",
            "vehicle_seating_capacity_count_d": "Vehicle_SeatingCapacityCount_D",
            "vehicle_seating_capacity_count_e": "Vehicle_SeatingCapacityCount_E",
            "vehicle_special_industry_class_code_a": "Vehicle_SpecialIndustryClassCode_A",
            "vehicle_special_industry_class_code_b": "Vehicle_SpecialIndustryClassCode_B",
            "vehicle_special_industry_class_code_c": "Vehicle_SpecialIndustryClassCode_C",
            "vehicle_special_industry_class_code_d": "Vehicle_SpecialIndustryClassCode_D",
            "vehicle_special_industry_class_code_e": "Vehicle_SpecialIndustryClassCode_E",
            "vehicle_symbol_code_a": "Vehicle_SymbolCode_A",
            "vehicle_symbol_code_b": "Vehicle_SymbolCode_B",
            "vehicle_symbol_code_c": "Vehicle_SymbolCode_C",
            "vehicle_symbol_code_d": "Vehicle_SymbolCode_D",
            "vehicle_symbol_code_e": "Vehicle_SymbolCode_E",
            "vehicle_total_premium_amount_a": "Vehicle_TotalPremiumAmount_A",
            "vehicle_total_premium_amount_b": "Vehicle_TotalPremiumAmount_B",
            "vehicle_total_premium_amount_c": "Vehicle_TotalPremiumAmount_C",
            "vehicle_total_premium_amount_d": "Vehicle_TotalPremiumAmount_D",
            "vehicle_total_premium_amount_e": "Vehicle_TotalPremiumAmount_E",
            "vehicle_use_commercial_indicator_a": "Vehicle_Use_CommercialIndicator_A",
            "vehicle_use_commercial_indicator_b": "Vehicle_Use_CommercialIndicator_B",
            "vehicle_use_commercial_indicator_c": "Vehicle_Use_CommercialIndicator_C",
            "vehicle_use_commercial_indicator_d": "Vehicle_Use_CommercialIndicator_D",
            "vehicle_use_commercial_indicator_e": "Vehicle_Use_CommercialIndicator_E",
            "vehicle_use_farm_indicator_a": "Vehicle_Use_FarmIndicator_A",
            "vehicle_use_farm_indicator_b": "Vehicle_Use_FarmIndicator_B",
            "vehicle_use_farm_indicator_c": "Vehicle_Use_FarmIndicator_C",
            "vehicle_use_farm_indicator_d": "Vehicle_Use_FarmIndicator_D",
            "vehicle_use_farm_indicator_e": "Vehicle_Use_FarmIndicator_E",
            "vehicle_use_fifteen_miles_or_over_indicator_a": "Vehicle_Use_FifteenMilesOrOverIndicator_A",
            "vehicle_use_fifteen_miles_or_over_indicator_b": "Vehicle_Use_FifteenMilesOrOverIndicator_B",
            "vehicle_use_fifteen_miles_or_over_indicator_c": "Vehicle_Use_FifteenMilesOrOverIndicator_C",
            "vehicle_use_fifteen_miles_or_over_indicator_d": "Vehicle_Use_FifteenMilesOrOverIndicator_D",
            "vehicle_use_fifteen_miles_or_over_indicator_e": "Vehicle_Use_FifteenMilesOrOverIndicator_E",
            "vehicle_use_for_hire_indicator_a": "Vehicle_Use_ForHireIndicator_A",
            "vehicle_use_for_hire_indicator_b": "Vehicle_Use_ForHireIndicator_B",
            "vehicle_use_for_hire_indicator_c": "Vehicle_Use_ForHireIndicator_C",
            "vehicle_use_for_hire_indicator_d": "Vehicle_Use_ForHireIndicator_D",
            "vehicle_use_for_hire_indicator_e": "Vehicle_Use_ForHireIndicator_E",
            "vehicle_use_other_description_a": "Vehicle_Use_OtherDescription_A",
            "vehicle_use_other_description_b": "Vehicle_Use_OtherDescription_B",
            "vehicle_use_other_description_c": "Vehicle_Use_OtherDescription_C",
            "vehicle_use_other_description_d": "Vehicle_Use_OtherDescription_D",
            "vehicle_use_other_description_e": "Vehicle_Use_OtherDescription_E",
            "vehicle_use_other_indicator_a": "Vehicle_Use_OtherIndicator_A",
            "vehicle_use_other_indicator_b": "Vehicle_Use_OtherIndicator_B",
            "vehicle_use_other_indicator_c": "Vehicle_Use_OtherIndicator_C",
            "vehicle_use_other_indicator_d": "Vehicle_Use_OtherIndicator_D",
            "vehicle_use_other_indicator_e": "Vehicle_Use_OtherIndicator_E",
            "vehicle_use_pleasure_indicator_a": "Vehicle_Use_PleasureIndicator_A",
            "vehicle_use_pleasure_indicator_b": "Vehicle_Use_PleasureIndicator_B",
            "vehicle_use_pleasure_indicator_c": "Vehicle_Use_PleasureIndicator_C",
            "vehicle_use_pleasure_indicator_d": "Vehicle_Use_PleasureIndicator_D",
            "vehicle_use_pleasure_indicator_e": "Vehicle_Use_PleasureIndicator_E",
            "vehicle_use_retail_indicator_a": "Vehicle_Use_RetailIndicator_A",
            "vehicle_use_retail_indicator_b": "Vehicle_Use_RetailIndicator_B",
            "vehicle_use_retail_indicator_c": "Vehicle_Use_RetailIndicator_C",
            "vehicle_use_retail_indicator_d": "Vehicle_Use_RetailIndicator_D",
            "vehicle_use_retail_indicator_e": "Vehicle_Use_RetailIndicator_E",
            "vehicle_use_service_indicator_a": "Vehicle_Use_ServiceIndicator_A",
            "vehicle_use_service_indicator_b": "Vehicle_Use_ServiceIndicator_B",
            "vehicle_use_service_indicator_c": "Vehicle_Use_ServiceIndicator_C",
            "vehicle_use_service_indicator_d": "Vehicle_Use_ServiceIndicator_D",
            "vehicle_use_service_indicator_e": "Vehicle_Use_ServiceIndicator_E",
            "vehicle_use_under_fifteen_miles_indicator_a": "Vehicle_Use_UnderFifteenMilesIndicator_A",
            "vehicle_use_under_fifteen_miles_indicator_b": "Vehicle_Use_UnderFifteenMilesIndicator_B",
            "vehicle_use_under_fifteen_miles_indicator_c": "Vehicle_Use_UnderFifteenMilesIndicator_C",
            "vehicle_use_under_fifteen_miles_indicator_d": "Vehicle_Use_UnderFifteenMilesIndicator_D",
            "vehicle_use_under_fifteen_miles_indicator_e": "Vehicle_Use_UnderFifteenMilesIndicator_E",
            "vehicle_vehicle_type_commercial_indicator_a": "Vehicle_VehicleType_CommercialIndicator_A",
            "vehicle_vehicle_type_commercial_indicator_b": "Vehicle_VehicleType_CommercialIndicator_B",
            "vehicle_vehicle_type_commercial_indicator_c": "Vehicle_VehicleType_CommercialIndicator_C",
            "vehicle_vehicle_type_commercial_indicator_d": "Vehicle_VehicleType_CommercialIndicator_D",
            "vehicle_vehicle_type_commercial_indicator_e": "Vehicle_VehicleType_CommercialIndicator_E",
            "vehicle_vehicle_type_private_passenger_indicator_a": "Vehicle_VehicleType_PrivatePassengerIndicator_A",
            "vehicle_vehicle_type_private_passenger_indicator_b": "Vehicle_VehicleType_PrivatePassengerIndicator_B",
            "vehicle_vehicle_type_private_passenger_indicator_c": "Vehicle_VehicleType_PrivatePassengerIndicator_C",
            "vehicle_vehicle_type_private_passenger_indicator_d": "Vehicle_VehicleType_PrivatePassengerIndicator_D",
            "vehicle_vehicle_type_private_passenger_indicator_e": "Vehicle_VehicleType_PrivatePassengerIndicator_E",
            "vehicle_vehicle_type_special_indicator_a": "Vehicle_VehicleType_SpecialIndicator_A",
            "vehicle_vehicle_type_special_indicator_b": "Vehicle_VehicleType_SpecialIndicator_B",
            "vehicle_vehicle_type_special_indicator_c": "Vehicle_VehicleType_SpecialIndicator_C",
            "vehicle_vehicle_type_special_indicator_d": "Vehicle_VehicleType_SpecialIndicator_D",
            "vehicle_vehicle_type_special_indicator_e": "Vehicle_VehicleType_SpecialIndicator_E",
            "vehicle_vin_identifier_a": "Vehicle_VINIdentifier_A",
            "vehicle_vin_identifier_b": "Vehicle_VINIdentifier_B",
            "vehicle_vin_identifier_c": "Vehicle_VINIdentifier_C",
            "vehicle_vin_identifier_d": "Vehicle_VINIdentifier_D",
            "vehicle_vin_identifier_e": "Vehicle_VINIdentifier_E",
        }


class FullFormsData(BaseModel):
    """Aggregate schema for all forms"""
    form_125: Acord125Data = Field(default_factory=Acord125Data)
    form_127: Acord127Data = Field(default_factory=Acord127Data)
    form_129: Acord129Data = Field(default_factory=Acord129Data)