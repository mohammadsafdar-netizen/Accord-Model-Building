"""LOB definitions, form assignments, and required field rules."""

from typing import Dict, List, Set, Any
from dataclasses import dataclass, field


@dataclass
class LOBDefinition:
    lob_id: str
    display_name: str
    forms: List[str]
    lob_checkbox_125: str | None  # Field name on Form 125 to check for this LOB
    required_entity_types: List[str]  # Entity types required (vehicles, drivers, etc.)
    description: str = ""


LOB_DEFINITIONS: Dict[str, LOBDefinition] = {
    "commercial_auto": LOBDefinition(
        lob_id="commercial_auto",
        display_name="Commercial Auto",
        forms=["125", "127", "137"],
        lob_checkbox_125="Policy_LineOfBusiness_BusinessAutoIndicator_A",
        required_entity_types=["vehicles", "drivers"],
        description="Commercial vehicle insurance covering business-owned autos, trucks, and fleets",
    ),
    "general_liability": LOBDefinition(
        lob_id="general_liability",
        display_name="General Liability",
        forms=["125", "126"],
        lob_checkbox_125="Policy_LineOfBusiness_CommercialGeneralLiability_A",
        required_entity_types=[],
        description="Coverage for bodily injury, property damage, and personal/advertising injury",
    ),
    "commercial_property": LOBDefinition(
        lob_id="commercial_property",
        display_name="Commercial Property",
        forms=["125", "140"],
        lob_checkbox_125="Policy_LineOfBusiness_CommercialProperty_A",
        required_entity_types=["locations"],
        description="Coverage for business-owned buildings, equipment, and inventory",
    ),
    "workers_compensation": LOBDefinition(
        lob_id="workers_compensation",
        display_name="Workers' Compensation",
        forms=["125", "130"],
        lob_checkbox_125=None,
        required_entity_types=[],
        description="Coverage for employee work-related injuries and illnesses",
    ),
    "commercial_umbrella": LOBDefinition(
        lob_id="commercial_umbrella",
        display_name="Commercial Umbrella",
        forms=["125", "163"],
        lob_checkbox_125="Policy_LineOfBusiness_UmbrellaIndicator_A",
        required_entity_types=[],
        description="Excess liability coverage above primary policy limits",
    ),
    "bop": LOBDefinition(
        lob_id="bop",
        display_name="Business Owners Policy (BOP)",
        forms=["125"],
        lob_checkbox_125="Policy_LineOfBusiness_BusinessOwnersIndicator_A",
        required_entity_types=["locations"],
        description="Bundled package policy combining general liability and commercial property for small/mid businesses",
    ),
    "cyber": LOBDefinition(
        lob_id="cyber",
        display_name="Cyber & Privacy Liability",
        forms=["125"],
        lob_checkbox_125="Policy_LineOfBusiness_CyberAndPrivacy_A",
        required_entity_types=[],
        description="Coverage for data breaches, network security failures, privacy violations, and cyber extortion",
    ),
}

# Forms we have schemas for (can fill programmatically)
AVAILABLE_SCHEMAS: Set[str] = {"125", "127", "137", "163"}

# LOB keywords for classification hints
LOB_KEYWORDS: Dict[str, List[str]] = {
    "commercial_auto": [
        "auto", "vehicle", "truck", "fleet", "car", "van", "trailer",
        "commercial auto", "business auto", "driver", "VIN", "CDL",
        "motor vehicle", "automobile", "cargo", "hauling", "delivery",
    ],
    "general_liability": [
        "general liability", "GL", "CGL", "bodily injury", "property damage",
        "premises liability", "products liability", "completed operations",
        "slip and fall", "third party", "advertising injury",
    ],
    "commercial_property": [
        "commercial property", "building", "contents", "equipment",
        "business personal property", "BPP", "real property",
        "fire", "theft", "windstorm", "flood",
    ],
    "workers_compensation": [
        "workers comp", "workers compensation", "work comp", "WC",
        "employee injury", "workplace injury", "occupational",
        "payroll", "class code", "experience mod",
    ],
    "commercial_umbrella": [
        "umbrella", "excess liability", "excess coverage",
        "umbrella policy", "excess policy", "additional limits",
    ],
    "bop": [
        "business owner", "BOP", "business owners policy",
        "property and liability", "general liability and property",
        "package policy", "small business insurance",
    ],
    "cyber": [
        "cyber", "data breach", "network security", "privacy liability",
        "cyber insurance", "cyber liability", "ransomware", "phishing",
        "privacy", "data protection", "cyber extortion", "PII", "PHI",
    ],
}

# Required fields per LOB for gap analysis
REQUIRED_FIELDS_BY_LOB: Dict[str, Dict[str, List[str]]] = {
    "commercial_auto": {
        "critical": [
            "business.business_name",
            "business.mailing_address",
            "policy.effective_date",
            "vehicles",  # at least one vehicle
            "drivers",   # at least one driver
        ],
        "important": [
            "business.tax_id",
            "business.entity_type",
            "business.operations_description",
            "vehicles[].vin",
            "vehicles[].year",
            "vehicles[].make",
            "vehicles[].model",
            "drivers[].full_name",
            "drivers[].dob",
            "drivers[].license_number",
            "drivers[].license_state",
        ],
    },
    "general_liability": {
        "critical": [
            "business.business_name",
            "business.mailing_address",
            "policy.effective_date",
        ],
        "important": [
            "business.tax_id",
            "business.entity_type",
            "business.operations_description",
            "business.annual_revenue",
            "business.employee_count",
        ],
    },
    "commercial_property": {
        "critical": [
            "business.business_name",
            "business.mailing_address",
            "policy.effective_date",
            "locations",  # at least one location
        ],
        "important": [
            "business.tax_id",
            "locations[].building_area",
            "locations[].construction_type",
            "locations[].year_built",
        ],
    },
    "workers_compensation": {
        "critical": [
            "business.business_name",
            "business.mailing_address",
            "policy.effective_date",
        ],
        "important": [
            "business.tax_id",
            "business.entity_type",
            "business.employee_count",
            "business.operations_description",
        ],
    },
    "commercial_umbrella": {
        "critical": [
            "business.business_name",
            "business.mailing_address",
            "policy.effective_date",
        ],
        "important": [
            "business.tax_id",
            "coverages",  # underlying coverages
        ],
    },
    "bop": {
        "critical": [
            "business.business_name",
            "business.mailing_address",
            "policy.effective_date",
            "locations",
        ],
        "important": [
            "business.tax_id",
            "business.entity_type",
            "business.operations_description",
            "business.annual_revenue",
            "business.employee_count",
            "locations[].building_area",
            "locations[].construction_type",
            "locations[].year_built",
        ],
    },
    "cyber": {
        "critical": [
            "business.business_name",
            "business.mailing_address",
            "policy.effective_date",
        ],
        "important": [
            "business.tax_id",
            "business.employee_count",
            "business.annual_revenue",
            "business.operations_description",
        ],
    },
}
