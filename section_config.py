#!/usr/bin/env python3
"""
Form-specific section configuration for ACORD 125, 127, 137.
=============================================================
Defines section headers (keywords to detect in OCR) and mapping from
extraction category to section(s). Used for header-based clustering of
bbox blocks and section-scoped extraction + VLM crops.
"""

from __future__ import annotations

from typing import Dict, List, Set

# Section IDs used across forms (form-specific headers define what text to look for)
# Order of headers within a form defines section boundaries (first match wins by Y position)

# ACORD 125 - Commercial Insurance Application (page 1 layout)
# Headers: text that starts or contains a section; we search bbox blocks for these (case-insensitive)
ACORD_125_HEADERS: List[Dict[str, str]] = [
    {"id": "header_date", "keywords": ["DATE (MM", "DATE(MM", "FORM COMPLETION"]},
    {"id": "agency_carrier", "keywords": ["AGENCY", "CARRIER", "NAIC CODE"]},
    {"id": "policy_underwriter", "keywords": ["COMPANY POLICY OR PROGRAM", "POLICY NUMBER", "UNDERWRITER", "UNDERWRITER OFFICE"]},
    {"id": "status_transaction", "keywords": ["STATUS OF", "TRANSACTION", "QUOTE", "BOUND", "CANCEL", "AGENCY CUSTOMER ID"]},
    {"id": "lines_of_business", "keywords": ["LINES OF BUSINESS", "INDICATE LINES OF BUSINESS", "PREMIUM"]},  # LOB table
    {"id": "attachments", "keywords": ["ATTACHMENTS", "ACCOUNTS RECEIVABLE", "VALUABLE PAPERS"]},
    {"id": "policy_info", "keywords": ["PROPOSED EFF DATE", "POLICY INFORMATION", "BILLING PLAN", "PAYMENT PLAN", "METHOD OF PAYMENT"]},
    {"id": "applicant_info", "keywords": ["NAME (First Named Insured)", "NAME (Other Named Insured)", "AND MAILING ADDRESS (including ZIP"]},
    # Page 2+ sections
    {"id": "premises_location", "keywords": ["PREMISES", "LOCATION", "BUILDING", "OCCUPIED AREA", "ANNUAL REVENUES"]},
    {"id": "nature_of_business", "keywords": ["NATURE OF BUSINESS", "DESCRIPTION OF OPERATIONS", "SIC", "NAICS", "FEIN"]},
    {"id": "prior_coverage", "keywords": ["PRIOR COVERAGE", "PRIOR CARRIER", "PRIOR POLICY"]},
    {"id": "loss_history_section", "keywords": ["LOSS HISTORY", "CLAIMS", "DATE OF LOSS", "AMOUNT PAID"]},
]

# Category -> section(s) for ACORD 125 (extraction category from schema_registry.EXTRACTION_ORDER)
ACORD_125_CATEGORY_SECTIONS: Dict[str, List[str]] = {
    "header": ["header_date", "agency_carrier"],
    "insurer": ["agency_carrier", "policy_underwriter"],
    "producer": ["agency_carrier", "policy_underwriter"],
    "named_insured": ["applicant_info"],
    "policy": ["policy_underwriter", "status_transaction", "policy_info"],
    "checkbox": ["status_transaction", "lines_of_business", "attachments"],
    "location": ["premises_location", "applicant_info"],
    "loss_history": ["loss_history_section", "prior_coverage", "attachments"],
    "remarks": ["attachments", "applicant_info"],
    "general": ["premises_location", "nature_of_business", "applicant_info", "policy_info", "lines_of_business", "attachments"],
}

# ACORD 127 - Business Auto Section
ACORD_127_HEADERS: List[Dict[str, str]] = [
    {"id": "header_date", "keywords": ["DATE", "COMMERCIAL AUTO", "BUSINESS AUTO"]},
    {"id": "insurer_policy", "keywords": ["COMPANY", "CARRIER", "NAIC", "POLICY NUMBER", "NAMED INSURED"]},
    {"id": "producer", "keywords": ["PRODUCER", "AGENCY", "AGENT"]},
    {"id": "driver_table", "keywords": ["DRIVER", "FIRST NAME", "LAST NAME", "DOB", "LICENSE"]},
    {"id": "vehicle", "keywords": ["VEHICLE", "YEAR", "MAKE", "MODEL", "VIN"]},
]

ACORD_127_CATEGORY_SECTIONS: Dict[str, List[str]] = {
    "header": ["header_date"],
    "insurer": ["insurer_policy"],
    "producer": ["producer", "insurer_policy"],
    "named_insured": ["insurer_policy"],
    "policy": ["insurer_policy"],
    "driver": ["driver_table"],
    "vehicle": ["vehicle"],
    "checkbox": ["insurer_policy", "vehicle"],
    "location": ["insurer_policy", "producer"],
    "general": ["insurer_policy", "driver_table", "vehicle"],
}

# ACORD 137 - Commercial Auto Section (Vehicle Schedule)
ACORD_137_HEADERS: List[Dict[str, str]] = [
    {"id": "header_date", "keywords": ["DATE", "COMMERCIAL AUTO", "VEHICLE SCHEDULE"]},
    {"id": "insurer_named", "keywords": ["NAMED INSURED", "POLICY", "EFFECTIVE", "INSURER", "NAIC"]},
    {"id": "vehicle_schedule", "keywords": ["VEHICLE", "YEAR", "MAKE", "VIN", "COVERAGE", "SYMBOL"]},
]

ACORD_137_CATEGORY_SECTIONS: Dict[str, List[str]] = {
    "header": ["header_date"],
    "insurer": ["insurer_named"],
    "producer": ["insurer_named"],
    "named_insured": ["insurer_named"],
    "policy": ["insurer_named"],
    "vehicle": ["vehicle_schedule"],
    "coverage": ["vehicle_schedule"],
    "checkbox": ["vehicle_schedule"],
    "general": ["insurer_named", "vehicle_schedule"],
}


def get_headers_for_form(form_type: str) -> List[Dict[str, str]]:
    """Return ordered list of {id, keywords} for form type."""
    if form_type == "125":
        return ACORD_125_HEADERS
    if form_type == "127":
        return ACORD_127_HEADERS
    if form_type == "137":
        return ACORD_137_HEADERS
    return []


def get_category_sections_for_form(form_type: str) -> Dict[str, List[str]]:
    """Return category -> list of section_ids for form type."""
    if form_type == "125":
        return ACORD_125_CATEGORY_SECTIONS
    if form_type == "127":
        return ACORD_127_CATEGORY_SECTIONS
    if form_type == "137":
        return ACORD_137_CATEGORY_SECTIONS
    return {}


def get_section_ids_for_category(form_type: str, category: str) -> List[str]:
    """Return section IDs to use when extracting this category."""
    mapping = get_category_sections_for_form(form_type)
    return mapping.get(category, [])
