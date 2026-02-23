"""LLM-powered 3-phase field mapper: deterministic → indexed arrays → LLM batch.

Replaces hardcoded field_maps/ with a dynamic mapping strategy that works with
any AcroForm PDF read by form_reader.py.

Phase 1: Deterministic regex patterns (~80+ common fields, instant)
Phase 2: Suffix-indexed array mapping (drivers[0..12], vehicles[0..3], etc.)
Phase 3: LLM batch mapping (remaining fields, ~5 calls)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from Custom_model_fa_pf.entity_schema import CustomerSubmission
from Custom_model_fa_pf.form_reader import FormCatalog, FormField
from Custom_model_fa_pf.prompts import FIELD_MAPPING_SYSTEM, FIELD_MAPPING_PROMPT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase 1: Deterministic patterns — regex → entity path
# ---------------------------------------------------------------------------

# Maps a regex pattern matching field names to a dot-path into CustomerSubmission.
# The resolver function _resolve_entity_path() navigates the entity tree.
DETERMINISTIC_PATTERNS: List[Tuple[str, str]] = [
    # Named Insured / Business
    (r"NamedInsured_FullName_A$", "business.business_name"),
    (r"NamedInsured_DBA_A$", "business.dba"),
    (r"NamedInsured_MailingAddress_LineOne_A$", "business.mailing_address.line_one"),
    (r"NamedInsured_MailingAddress_LineTwo_A$", "business.mailing_address.line_two"),
    (r"NamedInsured_MailingAddress_CityName_A$", "business.mailing_address.city"),
    (r"NamedInsured_MailingAddress_StateOrProvinceCode_A$", "business.mailing_address.state"),
    (r"NamedInsured_MailingAddress_PostalCode_A$", "business.mailing_address.zip_code"),
    (r"NamedInsured_TaxIdentifier_A$", "business.tax_id"),
    (r"NamedInsured_NAICS_A$", "business.naics"),
    (r"NamedInsured_SIC_A$", "business.sic"),
    (r"NamedInsured_BusinessStartDate_A$", "business.business_start_date"),
    (r"NamedInsured_Description_A$", "business.operations_description"),
    (r"NamedInsured_AnnualRevenue_A$", "business.annual_revenue"),
    (r"NamedInsured_EmployeeCount_A$", "business.employee_count"),
    (r"NamedInsured_YearsInBusiness_A$", "business.years_in_business"),
    (r"NamedInsured_Website_A$", "business.website"),
    (r"NamedInsured_NatureOfBusiness_A$", "business.nature_of_business"),
    (r"NamedInsured_AnnualPayroll_A$", "business.annual_payroll"),
    (r"NamedInsured_PartTimeEmployees_A$", "business.part_time_employees"),
    (r"NamedInsured_SubcontractorCost_A$", "business.subcontractor_cost"),
    # Contact info (generic Contact_ prefix)
    (r"Contact_FullName_A$", "business.contacts[0].full_name"),
    (r"Contact_PhoneNumber_A$", "business.contacts[0].phone"),
    (r"Contact_EmailAddress_A$", "business.contacts[0].email"),
    # Contact info (Form 125 NamedInsured_Contact_ prefix)
    (r"NamedInsured_Contact_FullName", "business.contacts[0].full_name"),
    (r"NamedInsured_Contact_PrimaryPhoneNumber", "business.contacts[0].phone"),
    (r"NamedInsured_Contact_EmailAddress", "business.contacts[0].email"),
    # Form 125 NamedInsured extras
    (r"NamedInsured_SICCode", "business.sic"),
    (r"NamedInsured_NAICSCode", "business.naics"),
    (r"NamedInsured_OperationsDescription", "business.operations_description"),
    # Form 125 Insurer fields
    (r"Insurer_FullName_A$", "insurer.name"),
    (r"Insurer_NAICCode_A$", "insurer.naic_code"),

    # Producer
    (r"Producer_FullName_A$", "producer.agency_name"),
    (r"Producer_ContactName_A$", "producer.contact_name"),
    (r"Producer_PhoneNumber_A$", "producer.phone"),
    (r"Producer_FaxNumber_A$", "producer.fax"),
    (r"Producer_EmailAddress_A$", "producer.email"),
    (r"Producer_MailingAddress_LineOne_A$", "producer.mailing_address.line_one"),
    (r"Producer_MailingAddress_CityName_A$", "producer.mailing_address.city"),
    (r"Producer_MailingAddress_StateOrProvinceCode_A$", "producer.mailing_address.state"),
    (r"Producer_MailingAddress_PostalCode_A$", "producer.mailing_address.zip_code"),
    (r"Producer_ProducerCode_A$", "producer.producer_code"),
    (r"Producer_LicenseNumber_A$", "producer.license_number"),

    # Policy
    (r"Policy_PolicyNumber_A$", "policy.policy_number"),
    (r"Policy_EffectiveDate_A$", "policy.effective_date"),
    (r"Policy_ExpirationDate_A$", "policy.expiration_date"),
    (r"Policy_DepositAmount_A$", "policy.deposit_amount"),
    (r"Policy_EstimatedPremium_A$", "policy.estimated_premium"),

    # Completion date (special — current date)
    (r"Form_CompletionDate_A$", "_today"),
]

# Phase 1b: Checkbox deterministic resolution
# Maps field name pattern to (entity_path, match_value)
# If entity value matches match_value → "1", else → "Off"
CHECKBOX_ENTITY_MAP: List[Tuple[str, str, str]] = [
    # Entity type checkboxes (order matters — more specific patterns first)
    (r"LimitedLiabilityCorporationIndicator", "business.entity_type", "llc"),
    (r"(?<!LimitedLiability)CorporationIndicator", "business.entity_type", "corporation"),
    (r"PartnershipIndicator", "business.entity_type", "partnership"),
    (r"IndividualIndicator", "business.entity_type", "individual"),
    (r"SubchapterSIndicator", "business.entity_type", "subchapter_s"),
    (r"JointVentureIndicator", "business.entity_type", "joint_venture"),
    (r"NotForProfitIndicator", "business.entity_type", "not_for_profit"),

    # Policy status checkboxes
    (r"NewIndicator|QuoteIndicator", "policy.status", "new"),
    (r"RenewalIndicator", "policy.status", "renewal"),
    (r"RewriteIndicator", "policy.status", "rewrite"),

    # Billing plan checkboxes
    (r"DirectBillIndicator", "policy.billing_plan", "direct"),
    (r"AgencyBillIndicator", "policy.billing_plan", "agency"),

    # LOB checkboxes (match against _lobs list)
    (r"BusinessAutoIndicator|CommercialAutoIndicator", "_lob", "commercial_auto"),
    (r"GeneralLiabilityIndicator", "_lob", "general_liability"),
    (r"CommercialPropertyIndicator", "_lob", "commercial_property"),
    (r"WorkersCompensationIndicator", "_lob", "workers_compensation"),
    (r"UmbrellaIndicator|CommercialUmbrellaIndicator", "_lob", "commercial_umbrella"),
    (r"BOPIndicator|BusinessOwnersIndicator", "_lob", "bop"),
    (r"CyberIndicator", "_lob", "cyber"),

    # Coverage type checkboxes
    (r"LiabilityIndicator", "_coverage_type", "liability"),
    (r"CollisionIndicator", "_coverage_type", "collision"),
    (r"ComprehensiveIndicator", "_coverage_type", "comprehensive"),
    (r"MedicalPaymentsIndicator", "_coverage_type", "medical_payments"),
    (r"UninsuredMotoristIndicator", "_coverage_type", "uninsured_motorist"),
    (r"TowingIndicator", "_coverage_type", "towing"),

    # Additional interest type checkboxes
    (r"AdditionalInsuredIndicator", "_ai_type", "additional_insured"),
    (r"MortgageeIndicator", "_ai_type", "mortgagee"),
    (r"LienholderIndicator", "_ai_type", "lienholder"),
    (r"LossPayeeIndicator", "_ai_type", "loss_payee"),
    (r"LendersLossPayableIndicator", "_ai_type", "lenders_loss_payable"),
    (r"CertificateRequiredIndicator", "_cert_required", "true"),
]

# ---------------------------------------------------------------------------
# Phase 2: Suffix-indexed array mapping
# ---------------------------------------------------------------------------

SUFFIX_TO_INDEX = {
    "_A": 0, "_B": 1, "_C": 2, "_D": 3, "_E": 4, "_F": 5, "_G": 6,
    "_H": 7, "_I": 8, "_J": 9, "_K": 10, "_L": 11, "_M": 12,
}

# Base field name (without suffix) → attribute on DriverInfo
# Includes both canonical PDF names (from Form 127) and common aliases.
_DRIVER_FIELD_MAP = {
    # Name
    "Driver_GivenName": "get_first_name()",
    "Driver_Surname": "get_last_name()",
    "Driver_OtherGivenNameInitial": "middle_initial",  # actual PDF name
    "Driver_MiddleInitial": "middle_initial",           # alias
    "Driver_FullName": "full_name",
    # Personal
    "Driver_BirthDate": "dob",
    "Driver_GenderCode": "sex",                         # actual PDF name
    "Driver_SexCode": "sex",                            # alias
    "Driver_MaritalStatusCode": "marital_status",
    # License
    "Driver_LicenseNumberIdentifier": "license_number", # actual PDF name
    "Driver_LicenseNumber": "license_number",           # alias
    "Driver_LicensedStateOrProvinceCode": "license_state",  # actual PDF name
    "Driver_LicenseStateOrProvinceCode": "license_state",   # alias
    "Driver_ExperienceYearCount": "years_experience",   # actual PDF name
    "Driver_YearsExperience": "years_experience",       # alias
    "Driver_LicensedYear": "licensed_year",
    # Employment
    "Driver_HiredDate": "hire_date",                    # actual PDF name
    "Driver_HireDate": "hire_date",                     # alias
    "Driver_Occupation": "occupation",
    "Driver_Relationship": "relationship",
    # Vehicle assignment
    "Driver_Vehicle_ProducerIdentifier": "vehicle_assigned",  # actual PDF name
    "Driver_VehicleAssigned": "vehicle_assigned",             # alias
    "Driver_Vehicle_UsePercent": "pct_use",             # actual PDF name
    "Driver_PercentUse": "pct_use",                     # alias
    # Address
    "Driver_MailingAddress_LineOne": "mailing_address.line_one",
    "Driver_MailingAddress_CityName": "mailing_address.city",
    "Driver_MailingAddress_StateOrProvinceCode": "mailing_address.state",
    "Driver_MailingAddress_PostalCode": "mailing_address.zip_code",
}

# Base field name → attribute on VehicleInfo
# Includes both canonical PDF names (from Forms 127/137) and common aliases.
_VEHICLE_FIELD_MAP = {
    # Identity
    "Vehicle_VINIdentifier": "vin",                     # actual PDF name
    "Vehicle_VIN": "vin",                               # alias
    "Vehicle_ModelYear": "year",
    "Vehicle_ManufacturersName": "make",                # actual PDF name
    "Vehicle_Make": "make",                             # alias
    "Vehicle_ModelName": "model",                       # actual PDF name
    "Vehicle_Model": "model",                           # alias
    "Vehicle_BodyCode": "body_type",                    # actual PDF name
    "Vehicle_BodyTypeCode": "body_type",                # alias
    # Weight / cost
    "Vehicle_GrossVehicleWeight": "gvw",                # actual PDF name
    "Vehicle_GVW": "gvw",                               # alias
    "Vehicle_CostNewAmount": "cost_new",                # actual PDF name
    "Vehicle_CostNew": "cost_new",                      # alias
    "Vehicle_SeatingCapacityCount": "seating_capacity",
    # Rating / territory
    "Vehicle_RadiusOfUse": "radius_of_travel",          # actual PDF name
    "Vehicle_RadiusOfTravel": "radius_of_travel",       # alias
    "Vehicle_FarthestZoneCode": "farthest_zone",        # actual PDF name
    "Vehicle_FarthestZone": "farthest_zone",            # alias
    "Vehicle_RatingTerritoryCode": "territory",         # actual PDF name
    "Vehicle_Territory": "territory",                   # alias
    "Vehicle_RateClassCode": "class_code",              # actual PDF name
    "Vehicle_SpecialIndustryClassCode": "class_code",   # alternate PDF name
    "Vehicle_ClassCode": "class_code",                  # alias
    "Vehicle_SymbolCode": "symbol",
    # Deductibles
    "Vehicle_Collision_DeductibleAmount": "deductible_collision",
    "Vehicle_Comprehensive_DeductibleAmount": "deductible_comprehensive",
    # Registration
    "Vehicle_Registration_StateOrProvinceCode": "registration_state",
    # Garaging / physical address
    "Vehicle_PhysicalAddress_LineOne": "garaging_address.line_one",   # actual PDF name
    "Vehicle_PhysicalAddress_CityName": "garaging_address.city",     # actual PDF name
    "Vehicle_PhysicalAddress_StateOrProvinceCode": "garaging_address.state",  # actual
    "Vehicle_PhysicalAddress_PostalCode": "garaging_address.zip_code",        # actual
    "Vehicle_PhysicalAddress_CountyName": "garaging_address.county",
    "Vehicle_Garaging_CityName": "garaging_address.city",            # alias
    "Vehicle_Garaging_StateOrProvinceCode": "garaging_address.state",# alias
    "Vehicle_Garaging_PostalCode": "garaging_address.zip_code",      # alias
}

# Base field name → attribute on LocationInfo
_LOCATION_FIELD_MAP = {
    "Location_Address_LineOne": "address.line_one",
    "Location_Address_CityName": "address.city",
    "Location_Address_StateOrProvinceCode": "address.state",
    "Location_Address_PostalCode": "address.zip_code",
    "Location_BuildingArea": "building_area",
    "Location_ConstructionType": "construction_type",
    "Location_YearBuilt": "year_built",
    "Location_Occupancy": "occupancy",
}

# Base field name → attribute on LossHistoryEntry
_LOSS_FIELD_MAP = {
    "LossHistory_Date": "date",
    "LossHistory_OccurrenceDate": "date",
    "LossHistory_ClaimDate": "date",
    "LossHistory_LOB": "lob",
    "LossHistory_LineOfBusiness": "lob",
    "LossHistory_Description": "description",
    "LossHistory_OccurrenceDescription": "description",
    "LossHistory_Amount": "amount",
    "LossHistory_PaidAmount": "amount",
    "LossHistory_TotalAmount": "amount",
    "LossHistory_ClaimStatus": "claim_status",
    "LossHistory_ClaimStatus_OpenCode": "claim_status",
    "LossHistory_ReservedAmount": "reserved_amount",
    "LossHistory_InformationYearCount": "years",
    "Loss_Date": "date",
    "Loss_Description": "description",
    "Loss_Amount": "amount",
}

# Base field name → attribute on AdditionalInterest
_AI_FIELD_MAP = {
    "AdditionalInterest_FullName": "name",
    "AdditionalInterest_Address_LineOne": "address.line_one",
    "AdditionalInterest_Address_CityName": "address.city",
    "AdditionalInterest_Address_StateOrProvinceCode": "address.state",
    "AdditionalInterest_Address_PostalCode": "address.zip_code",
    "AdditionalInterest_MailingAddress_LineOne": "address.line_one",
    "AdditionalInterest_MailingAddress_CityName": "address.city",
    "AdditionalInterest_MailingAddress_StateOrProvinceCode": "address.state",
    "AdditionalInterest_MailingAddress_PostalCode": "address.zip_code",
    "AdditionalInterest_MailingAddress_LineTwo": "address.line_two",
    "AdditionalInterest_AccountNumber": "account_number",
    "AdditionalInterest_AccountNumberIdentifier": "account_number",
    "AdditionalInterest_InterestType": "interest_type",
    "AdditionalInterest_PhoneNumber": "phone",
    "AdditionalInterest_EmailAddress": "email",
    "AdditionalInterest_FaxNumber": "fax",
    "AdditionalInterest_LoanAmount": "loan_amount",
}

# All indexed maps with their entity list name
_INDEXED_MAPS = [
    (_DRIVER_FIELD_MAP, "drivers"),
    (_VEHICLE_FIELD_MAP, "vehicles"),
    (_LOCATION_FIELD_MAP, "locations"),
    (_LOSS_FIELD_MAP, "loss_history"),
    (_AI_FIELD_MAP, "additional_interests"),
]

# ---------------------------------------------------------------------------
# Phase 3: LLM batch size
# ---------------------------------------------------------------------------
LLM_BATCH_SIZE = 75


@dataclass
class MappingResult:
    """Result of mapping entities to form fields."""
    mappings: Dict[str, str] = field(default_factory=dict)
    phase1_count: int = 0
    phase2_count: int = 0
    phase3_count: int = 0
    unmapped_fields: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_mapped(self) -> int:
        return len(self.mappings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_mapped": self.total_mapped,
            "phase1_count": self.phase1_count,
            "phase2_count": self.phase2_count,
            "phase3_count": self.phase3_count,
            "unmapped_count": len(self.unmapped_fields),
            "errors": self.errors,
        }


def _resolve_entity_path(submission: CustomerSubmission, path: str) -> Optional[str]:
    """Navigate the entity tree by dot-path and return the value as a string.

    Handles:
      - Simple paths: "business.business_name"
      - Nested: "business.mailing_address.city"
      - Array indexed: "business.contacts[0].full_name"
      - Method calls: "get_first_name()" on the current object
    """
    if path == "_today":
        return datetime.now().strftime("%m/%d/%Y")

    parts = path.split(".")
    obj: Any = submission

    for part in parts:
        if obj is None:
            return None

        # Handle array index: contacts[0]
        idx_match = re.match(r"^(\w+)\[(\d+)\]$", part)
        if idx_match:
            attr_name = idx_match.group(1)
            idx = int(idx_match.group(2))
            arr = getattr(obj, attr_name, None)
            if not arr or idx >= len(arr):
                return None
            obj = arr[idx]
            continue

        # Handle method call: get_first_name()
        if part.endswith("()"):
            method_name = part[:-2]
            method = getattr(obj, method_name, None)
            if callable(method):
                obj = method()
            else:
                return None
            continue

        # Simple attribute
        obj = getattr(obj, part, None)

    if obj is None:
        return None
    val = str(obj).strip()
    return val if val else None


def _resolve_checkbox(
    submission: CustomerSubmission,
    entity_path: str,
    match_value: str,
    lobs: Optional[List[str]] = None,
    coverage_types: Optional[Set[str]] = None,
    ai_types: Optional[Set[str]] = None,
) -> Optional[str]:
    """Resolve a checkbox field to "1" or "Off" based on entity matching."""

    # Special paths for LOB matching
    if entity_path == "_lob":
        if lobs and match_value in lobs:
            return "1"
        return "Off"

    # Coverage type matching (from coverages list)
    if entity_path == "_coverage_type":
        if coverage_types and match_value in coverage_types:
            return "1"
        return "Off"

    # Additional interest type matching
    if entity_path == "_ai_type":
        if ai_types and match_value in ai_types:
            return "1"
        return "Off"

    # Certificate required
    if entity_path == "_cert_required":
        if submission.additional_interests:
            for ai in submission.additional_interests:
                if ai.certificate_required:
                    return "1"
        return "Off"

    # Standard entity path comparison
    actual = _resolve_entity_path(submission, entity_path)
    if actual is None:
        return None  # Skip — don't set checkbox if we don't have the data

    if actual.lower() == match_value.lower():
        return "1"
    return "Off"


def _resolve_indexed_field(
    submission: CustomerSubmission,
    base_name: str,
    index: int,
    list_name: str,
    field_map: Dict[str, str],
) -> Optional[str]:
    """Resolve a suffix-indexed field like Driver_GivenName_C → drivers[2].first_name."""
    if base_name not in field_map:
        return None

    entity_list = getattr(submission, list_name, [])
    if index >= len(entity_list):
        return None

    attr_path = field_map[base_name]
    entity = entity_list[index]

    # Handle method calls
    if attr_path.endswith("()"):
        method_name = attr_path[:-2]
        method = getattr(entity, method_name, None)
        if callable(method):
            val = method()
            return str(val).strip() if val else None
        return None

    # Handle nested paths (mailing_address.city)
    parts = attr_path.split(".")
    obj = entity
    for part in parts:
        if obj is None:
            return None
        obj = getattr(obj, part, None)

    if obj is None:
        return None
    val = str(obj).strip()
    return val if val else None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def map_fields(
    entities: CustomerSubmission,
    catalog: FormCatalog,
    lobs: Optional[List[str]] = None,
    llm_engine=None,
) -> MappingResult:
    """Map extracted entities to form fields using 3-phase strategy.

    Args:
        entities: Extracted customer submission
        catalog: Form catalog from form_reader
        lobs: List of LOB IDs (for checkbox resolution)
        llm_engine: Optional LLMEngine for Phase 3

    Returns:
        MappingResult with all mappings and statistics
    """
    result = MappingResult()
    mapped_names: Set[str] = set()

    # Precompute coverage types and AI types for checkbox resolution
    coverage_types = {c.coverage_type for c in entities.coverages if c.coverage_type}
    ai_types = {ai.interest_type for ai in entities.additional_interests if ai.interest_type}

    # ---------------------------------------------------------------
    # Phase 1: Deterministic pattern matching
    # ---------------------------------------------------------------
    logger.info("Phase 1: Deterministic pattern matching")

    for field_name, form_field in catalog.fields.items():
        # Text field patterns
        for pattern, entity_path in DETERMINISTIC_PATTERNS:
            if re.search(pattern, field_name):
                value = _resolve_entity_path(entities, entity_path)
                if value:
                    result.mappings[field_name] = value
                    mapped_names.add(field_name)
                    result.phase1_count += 1
                break

        # Checkbox patterns (only for checkbox fields)
        if form_field.field_type == "checkbox" and field_name not in mapped_names:
            for pattern, entity_path, match_value in CHECKBOX_ENTITY_MAP:
                if re.search(pattern, field_name):
                    value = _resolve_checkbox(
                        entities, entity_path, match_value,
                        lobs=lobs, coverage_types=coverage_types, ai_types=ai_types,
                    )
                    if value is not None:
                        result.mappings[field_name] = value
                        mapped_names.add(field_name)
                        result.phase1_count += 1
                    break

    logger.info(f"Phase 1: {result.phase1_count} fields mapped")

    # ---------------------------------------------------------------
    # Phase 2: Suffix-indexed array mapping
    # ---------------------------------------------------------------
    logger.info("Phase 2: Suffix-indexed array mapping")

    for field_name, form_field in catalog.fields.items():
        if field_name in mapped_names:
            continue

        suffix = form_field.suffix
        base_name = form_field.base_name

        if not suffix or not base_name:
            continue

        index = SUFFIX_TO_INDEX.get(suffix)
        if index is None:
            # Try numeric suffix (_1, _2, etc.)
            num_match = re.match(r"_(\d+)$", suffix)
            if num_match:
                index = int(num_match.group(1)) - 1  # 1-based to 0-based
            else:
                continue

        # Try each indexed map
        for field_map, list_name in _INDEXED_MAPS:
            value = _resolve_indexed_field(entities, base_name, index, list_name, field_map)
            if value:
                result.mappings[field_name] = value
                mapped_names.add(field_name)
                result.phase2_count += 1
                break

    logger.info(f"Phase 2: {result.phase2_count} fields mapped")

    # ---------------------------------------------------------------
    # Phase 3: LLM batch mapping
    # ---------------------------------------------------------------
    if llm_engine is None:
        logger.info("Phase 3: Skipped (no LLM engine)")
        result.unmapped_fields = [
            f.name for f in catalog.fields.values()
            if f.name not in mapped_names
        ]
        return result

    # Handle Form 163 special case: generic TextNN[0] names
    # For Form 163, skip LLM mapping and use row-offset logic
    if catalog.form_number == "163":
        logger.info("Phase 3: Form 163 detected — using row-offset mapping")
        _map_form_163_rows(entities, catalog, result, mapped_names)
        result.unmapped_fields = [
            f.name for f in catalog.fields.values()
            if f.name not in mapped_names
        ]
        return result

    logger.info("Phase 3: LLM batch mapping")

    unmapped_fields = [
        f for f in catalog.fields.values()
        if f.name not in mapped_names and f.field_type not in ("signature",)
    ]

    if not unmapped_fields:
        logger.info("Phase 3: No unmapped fields remaining")
        return result

    # Build entity JSON summary
    entity_json = json.dumps(entities.to_dict(), indent=2, default=str)

    # Build already-mapped sample (give LLM context of what's been mapped)
    mapped_sample = {}
    sample_keys = list(result.mappings.keys())[:30]
    for k in sample_keys:
        mapped_sample[k] = result.mappings[k]
    mapped_sample_str = json.dumps(mapped_sample, indent=2)

    # Batch unmapped fields by category
    batches = _create_batches(unmapped_fields, LLM_BATCH_SIZE)

    for batch_idx, batch in enumerate(batches):
        try:
            # Build field list for prompt
            field_lines = []
            for f in batch:
                tooltip_str = f": \"{f.tooltip}\"" if f.tooltip else ""
                field_lines.append(f"- {f.name} ({f.field_type}){tooltip_str}")
            field_list = "\n".join(field_lines)

            prompt = FIELD_MAPPING_PROMPT.format(
                entity_json=entity_json[:6000],  # Truncate if very large
                field_list=field_list,
                already_mapped_sample=mapped_sample_str[:2000],
            )

            response = llm_engine.generate(
                prompt=prompt,
                system=FIELD_MAPPING_SYSTEM,
                temperature=0.0,
            )

            parsed = llm_engine.parse_json(response)
            mappings = parsed.get("mappings", {})

            for fname, value in mappings.items():
                if fname in catalog.fields and value and str(value).strip():
                    val_str = str(value).strip()
                    # Skip "null", "N/A", "unknown" etc
                    if val_str.lower() in ("null", "none", "n/a", "unknown", ""):
                        continue
                    result.mappings[fname] = val_str
                    mapped_names.add(fname)
                    result.phase3_count += 1

            logger.info(f"Phase 3 batch {batch_idx + 1}/{len(batches)}: {len(mappings)} fields from LLM")

        except Exception as e:
            error_msg = f"Phase 3 batch {batch_idx + 1} failed: {e}"
            logger.warning(error_msg)
            result.errors.append(error_msg)

    result.unmapped_fields = [
        f.name for f in catalog.fields.values()
        if f.name not in mapped_names
    ]

    logger.info(
        f"Mapping complete: {result.total_mapped} total "
        f"(P1:{result.phase1_count} P2:{result.phase2_count} P3:{result.phase3_count}), "
        f"{len(result.unmapped_fields)} unmapped"
    )

    return result


def _create_batches(fields: List[FormField], batch_size: int) -> List[List[FormField]]:
    """Create batches grouped by category for better LLM context."""
    # Sort by category to group related fields
    sorted_fields = sorted(fields, key=lambda f: (f.category, f.page, f.name))

    batches = []
    current_batch = []

    for f in sorted_fields:
        current_batch.append(f)
        if len(current_batch) >= batch_size:
            batches.append(current_batch)
            current_batch = []

    if current_batch:
        batches.append(current_batch)

    return batches


def _map_form_163_rows(
    entities: CustomerSubmission,
    catalog: FormCatalog,
    result: MappingResult,
    mapped_names: Set[str],
):
    """Special mapping for Form 163 with generic TextNN[0] field names.

    Form 163 uses row-offset logic:
    - Header: Text13[0]=insured name, Text14[0]=address, etc.
    - Driver rows: Text15[0]=driver1, Text35[0]=driver2, etc. (+20 per row)
    - 20 fields per driver row with column offsets
    """
    _BASE_FIELD = 15
    _FIELDS_PER_ROW = 20
    _MAX_DRIVERS = 24

    # Header mapping
    _HEADER_MAP = {
        "Text13[0]": "business.business_name",
        "Text14[0]": "business.mailing_address.line_one",
        "Text8[0]": "producer.agency_name",
        "Text9[0]": "producer.contact_name",
        "Text2[0]": "producer.phone",
        "Text4[0]": "producer.email",
        "Text3[0]": "producer.fax",
        "Text1[0]": "policy.effective_date",
    }

    # Column offsets within a driver row
    _COL_OFFSETS = {
        0: None,  # driver_num (auto-generated)
        1: "get_first_name()",
        2: "middle_initial",
        3: "get_last_name()",
        4: "mailing_address.line_one",
        5: "mailing_address.city",
        6: "mailing_address.state",
        7: "mailing_address.zip_code",
        8: "sex",
        9: "dob",
        10: "years_experience",
        11: "licensed_year",
        12: "license_number",
        13: None,  # SSN — skip
        14: "license_state",
        15: "hire_date",
        16: None,  # flag1
        17: None,  # flag2
        18: "vehicle_assigned",
        19: "pct_use",
    }

    # Map headers
    for field_name, entity_path in _HEADER_MAP.items():
        if field_name in catalog.fields and field_name not in mapped_names:
            value = _resolve_entity_path(entities, entity_path)
            if value:
                result.mappings[field_name] = value
                mapped_names.add(field_name)
                result.phase3_count += 1

    # Map driver rows
    for driver_idx, driver in enumerate(entities.drivers[:_MAX_DRIVERS]):
        row_base = _BASE_FIELD + (driver_idx * _FIELDS_PER_ROW)

        for col_offset, attr_path in _COL_OFFSETS.items():
            field_num = row_base + col_offset
            field_name = f"Text{field_num}[0]"

            if field_name not in catalog.fields or field_name in mapped_names:
                continue

            if col_offset == 0:
                # Auto-generated driver number
                result.mappings[field_name] = str(driver_idx + 1)
                mapped_names.add(field_name)
                result.phase3_count += 1
                continue

            if attr_path is None:
                continue

            # Handle method calls
            if attr_path.endswith("()"):
                method_name = attr_path[:-2]
                method = getattr(driver, method_name, None)
                if callable(method):
                    value = method()
                    if value:
                        result.mappings[field_name] = str(value)
                        mapped_names.add(field_name)
                        result.phase3_count += 1
                continue

            # Handle nested paths
            parts = attr_path.split(".")
            obj = driver
            for part in parts:
                if obj is None:
                    break
                obj = getattr(obj, part, None)

            if obj is not None:
                val = str(obj).strip()
                if val:
                    result.mappings[field_name] = val
                    mapped_names.add(field_name)
                    result.phase3_count += 1

        # Marital status (special field names)
        marital_field = "marital[0]" if driver_idx == 0 else f"maritalstatus{driver_idx}[0]"
        if marital_field in catalog.fields and marital_field not in mapped_names:
            if driver.marital_status:
                result.mappings[marital_field] = driver.marital_status
                mapped_names.add(marital_field)
                result.phase3_count += 1


# ---------------------------------------------------------------------------
# Convenience wrapper for the old pipeline interface
# ---------------------------------------------------------------------------

def map_all(
    submission: CustomerSubmission,
    assignments,
    catalogs: Optional[Dict[str, FormCatalog]] = None,
    lobs: Optional[List[str]] = None,
    llm_engine=None,
    schema_registry=None,
) -> Dict[str, Dict[str, str]]:
    """Map extracted entities to field values for all assigned forms.

    Drop-in replacement for field_mapper.map_all() that uses dynamic mapping.

    Args:
        submission: Extracted customer submission
        assignments: List of FormAssignment
        catalogs: Pre-read form catalogs (optional — reads templates if not provided)
        lobs: LOB IDs for checkbox resolution
        llm_engine: Optional LLMEngine for Phase 3
        schema_registry: Optional SchemaRegistry for field name validation

    Returns:
        Dict of form_number -> {field_name: value}
    """
    from Custom_model_fa_pf.form_reader import find_template, read_pdf_form

    all_mappings: Dict[str, Dict[str, str]] = {}

    # Collect LOB IDs if not provided
    if lobs is None:
        lobs = []
        for assignment in assignments:
            for lob_id in assignment.lobs:
                if lob_id not in lobs:
                    lobs.append(lob_id)

    for assignment in assignments:
        form_num = assignment.form_number

        # Get or read catalog
        if catalogs and form_num in catalogs:
            catalog = catalogs[form_num]
        else:
            template_path = find_template(form_num)
            if not template_path:
                logger.warning(f"Form {form_num}: no template PDF found, skipping")
                continue
            catalog = read_pdf_form(template_path)

        if not catalog.fields:
            logger.warning(f"Form {form_num}: no fields found in catalog")
            continue

        # Run 3-phase mapping
        mapping_result = map_fields(
            entities=submission,
            catalog=catalog,
            lobs=lobs,
            llm_engine=llm_engine,
        )

        fields = mapping_result.mappings

        # Add completion date
        today = datetime.now().strftime("%m/%d/%Y")
        if "Form_CompletionDate_A" in catalog.fields:
            fields["Form_CompletionDate_A"] = today

        # Validate field names against schema if available
        if schema_registry:
            try:
                validated = schema_registry.validate_field_names(form_num, fields)
                invalid = set(fields.keys()) - set(validated.keys())
                if invalid:
                    logger.warning(
                        f"Form {form_num}: {len(invalid)} invalid field names removed"
                    )
                fields = validated
            except Exception:
                pass  # Schema validation is optional

        # Remove empty/None values
        fields = {k: str(v) for k, v in fields.items() if v is not None and str(v).strip()}

        all_mappings[form_num] = fields
        logger.info(
            f"Form {form_num}: {len(fields)} fields mapped "
            f"(P1:{mapping_result.phase1_count} P2:{mapping_result.phase2_count} "
            f"P3:{mapping_result.phase3_count})"
        )

    return all_mappings
