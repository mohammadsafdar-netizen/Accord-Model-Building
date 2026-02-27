"""
Scenario generator for agent fine-tuning dataset.

Produces 500+ ConversationScenario instances by loading 3 base entity
templates and applying parametric variations (state/city, business type,
vehicle fleet, drivers, revenue/headcount, LOB combos, delivery style,
user persona).

Usage:
    from finetune.agent.scenario_generator import generate_scenarios
    scenarios = generate_scenarios()   # list[ConversationScenario]
"""

from __future__ import annotations

import copy
import json
import random
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# LOB -> form mapping (self-contained, mirrors lob_rules.py)
# ---------------------------------------------------------------------------

LOB_FORMS: Dict[str, List[str]] = {
    "commercial_auto": ["125", "127", "137"],
    "general_liability": ["125", "126"],
    "commercial_property": ["125", "140"],
    "workers_compensation": ["125", "130"],
    "commercial_umbrella": ["125", "163"],
    "bop": ["125"],
    "cyber": ["125"],
}

ALL_LOBS = list(LOB_FORMS.keys())

# ---------------------------------------------------------------------------
# ConversationScenario dataclass
# ---------------------------------------------------------------------------


@dataclass
class ConversationScenario:
    scenario_id: str
    business: dict
    policy: dict
    vehicles: list
    drivers: list
    coverages: list
    locations: list
    loss_history: list
    prior_insurance: list
    lobs: list
    assigned_forms: list
    delivery_style: str
    user_persona: str
    document_uploads: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Base entity templates
# ---------------------------------------------------------------------------

# Paths are relative to the Accord-Model-Building root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # finetune/../..
_ENTITY_DIR = _PROJECT_ROOT / "Custom_model_fa_pf" / "output"

_ENTITY_FILE_1 = _ENTITY_DIR / "20260226_090440" / "entities.json"
_ENTITY_FILE_2 = _ENTITY_DIR / "20260226_093309" / "entities.json"


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _sample_entities_fixture() -> dict:
    """Hardcoded version of tests/test_quoting_pipeline.py:sample_entities."""
    return {
        "business": {
            "business_name": "Pinnacle Logistics LLC",
            "dba": "",
            "entity_type": "llc",
            "tax_id": "75-1234567",
            "mailing_address": {
                "line_one": "4500 Commerce Street Suite 200",
                "city": "Dallas",
                "state": "TX",
                "zip_code": "75226",
            },
            "nature_of_business": "Freight trucking",
            "years_in_business": "8",
            "employee_count": "45",
            "annual_revenue": "12500000",
            "annual_payroll": "2000000",
        },
        "policy": {
            "effective_date": "04/01/2026",
            "expiration_date": "04/01/2027",
        },
        "vehicles": [
            {"vin": "1FTFW1E80NFA00001", "year": "2023", "make": "Ford", "model": "F-150"},
            {"vin": "1FTFW1E80NFA00002", "year": "2022", "make": "Ford", "model": "F-250"},
            {"vin": "3AKJGLDR5KSLA0003", "year": "2021", "make": "Freightliner", "model": "Cascadia"},
        ],
        "drivers": [
            {"full_name": "John Doe", "dob": "01/15/1985", "license_number": "TX12345", "license_state": "TX"},
            {"full_name": "Jane Smith", "dob": "03/22/1990", "license_number": "TX67890", "license_state": "TX"},
        ],
        "prior_insurance": [
            {"carrier_name": "Old Guard Insurance", "premium": "25000"},
        ],
        "loss_history": [
            {"date": "06/15/2024", "amount": "5000", "description": "Minor fender bender"},
        ],
        "coverages": [],
        "locations": [],
    }


def _load_base_entities() -> List[dict]:
    """Return the 3 base entity dicts (2 from files, 1 hardcoded)."""
    bases: List[dict] = []
    for p in (_ENTITY_FILE_1, _ENTITY_FILE_2):
        if p.exists():
            bases.append(_load_json(p))
        else:
            # Fallback: use fixture if JSON not on disk (CI, etc.)
            bases.append(_sample_entities_fixture())
    bases.append(_sample_entities_fixture())
    return bases


# ---------------------------------------------------------------------------
# Variation pools
# ---------------------------------------------------------------------------

# 55 US state/city/zip triples
STATE_CITY_ZIP: List[tuple] = [
    ("AL", "Birmingham", "35203"),
    ("AK", "Anchorage", "99501"),
    ("AZ", "Phoenix", "85001"),
    ("AR", "Little Rock", "72201"),
    ("CA", "Los Angeles", "90001"),
    ("CA", "San Francisco", "94102"),
    ("CA", "San Diego", "92101"),
    ("CO", "Denver", "80201"),
    ("CT", "Hartford", "06101"),
    ("DE", "Wilmington", "19801"),
    ("FL", "Miami", "33101"),
    ("FL", "Orlando", "32801"),
    ("FL", "Tampa", "33601"),
    ("GA", "Atlanta", "30301"),
    ("HI", "Honolulu", "96801"),
    ("ID", "Boise", "83701"),
    ("IL", "Chicago", "60601"),
    ("IN", "Indianapolis", "46201"),
    ("IA", "Des Moines", "50301"),
    ("KS", "Wichita", "67201"),
    ("KY", "Louisville", "40201"),
    ("LA", "New Orleans", "70112"),
    ("ME", "Portland", "04101"),
    ("MD", "Baltimore", "21201"),
    ("MA", "Boston", "02101"),
    ("MI", "Detroit", "48201"),
    ("MN", "Minneapolis", "55401"),
    ("MS", "Jackson", "39201"),
    ("MO", "Kansas City", "64101"),
    ("MT", "Billings", "59101"),
    ("NE", "Omaha", "68101"),
    ("NV", "Las Vegas", "89101"),
    ("NH", "Manchester", "03101"),
    ("NJ", "Newark", "07101"),
    ("NM", "Albuquerque", "87101"),
    ("NY", "New York", "10001"),
    ("NY", "Buffalo", "14201"),
    ("NC", "Charlotte", "28201"),
    ("ND", "Fargo", "58101"),
    ("OH", "Columbus", "43201"),
    ("OK", "Oklahoma City", "73101"),
    ("OR", "Portland", "97201"),
    ("PA", "Philadelphia", "19101"),
    ("PA", "Pittsburgh", "15201"),
    ("RI", "Providence", "02901"),
    ("SC", "Charleston", "29401"),
    ("SD", "Sioux Falls", "57101"),
    ("TN", "Nashville", "37201"),
    ("TX", "Houston", "77001"),
    ("TX", "Dallas", "75201"),
    ("TX", "Austin", "78701"),
    ("UT", "Salt Lake City", "84101"),
    ("VT", "Burlington", "05401"),
    ("VA", "Richmond", "23218"),
    ("WA", "Seattle", "98101"),
    ("WI", "Milwaukee", "53201"),
    ("WV", "Charleston", "25301"),
    ("WY", "Cheyenne", "82001"),
    ("DC", "Washington", "20001"),
]

# Business type templates keyed by primary LOB affinity
BUSINESS_TEMPLATES: List[Dict[str, Any]] = [
    # --- commercial_auto heavy ---
    {"ops": "Long-haul freight trucking operations", "nature": "Freight trucking", "lob_affinity": "commercial_auto"},
    {"ops": "Same-day courier and delivery services", "nature": "Courier services", "lob_affinity": "commercial_auto"},
    {"ops": "Last-mile package delivery for e-commerce", "nature": "Package delivery", "lob_affinity": "commercial_auto"},
    {"ops": "Refrigerated food transport and logistics", "nature": "Refrigerated transport", "lob_affinity": "commercial_auto"},
    {"ops": "Moving and relocation services", "nature": "Moving company", "lob_affinity": "commercial_auto"},
    {"ops": "Auto parts wholesale and distribution", "nature": "Auto parts distribution", "lob_affinity": "commercial_auto"},
    {"ops": "Towing and roadside assistance services", "nature": "Towing services", "lob_affinity": "commercial_auto"},
    {"ops": "Bus and shuttle transportation services", "nature": "Passenger transport", "lob_affinity": "commercial_auto"},
    # --- general_liability heavy ---
    {"ops": "Full-service restaurant and catering", "nature": "Restaurant", "lob_affinity": "general_liability"},
    {"ops": "Residential and commercial cleaning services", "nature": "Cleaning services", "lob_affinity": "general_liability"},
    {"ops": "Landscaping and lawn care services", "nature": "Landscaping", "lob_affinity": "general_liability"},
    {"ops": "Event planning and management", "nature": "Event management", "lob_affinity": "general_liability"},
    {"ops": "Hair salon and beauty services", "nature": "Salon", "lob_affinity": "general_liability"},
    {"ops": "Fitness center and personal training", "nature": "Fitness center", "lob_affinity": "general_liability"},
    {"ops": "Pet grooming and boarding services", "nature": "Pet services", "lob_affinity": "general_liability"},
    # --- commercial_property heavy ---
    {"ops": "Commercial real estate management", "nature": "Property management", "lob_affinity": "commercial_property"},
    {"ops": "Retail clothing store", "nature": "Retail", "lob_affinity": "commercial_property"},
    {"ops": "Warehouse and storage facility operations", "nature": "Warehousing", "lob_affinity": "commercial_property"},
    {"ops": "Manufacturing of industrial components", "nature": "Manufacturing", "lob_affinity": "commercial_property"},
    # --- workers_compensation heavy ---
    {"ops": "General contracting and construction", "nature": "Construction", "lob_affinity": "workers_compensation"},
    {"ops": "Roofing installation and repair", "nature": "Roofing contractor", "lob_affinity": "workers_compensation"},
    {"ops": "Electrical contracting services", "nature": "Electrical contractor", "lob_affinity": "workers_compensation"},
    {"ops": "Plumbing and HVAC services", "nature": "Plumbing/HVAC", "lob_affinity": "workers_compensation"},
    # --- cyber heavy ---
    {"ops": "IT consulting and managed services", "nature": "IT consulting", "lob_affinity": "cyber"},
    {"ops": "Software development and SaaS platform", "nature": "Software company", "lob_affinity": "cyber"},
    {"ops": "Healthcare data analytics", "nature": "Health tech", "lob_affinity": "cyber"},
    {"ops": "E-commerce platform operations", "nature": "E-commerce", "lob_affinity": "cyber"},
    # --- bop / general ---
    {"ops": "Accounting and tax preparation services", "nature": "Accounting firm", "lob_affinity": "bop"},
    {"ops": "Law firm and legal services", "nature": "Law firm", "lob_affinity": "bop"},
    {"ops": "Real estate brokerage", "nature": "Real estate broker", "lob_affinity": "bop"},
    {"ops": "Dental practice", "nature": "Dental office", "lob_affinity": "bop"},
    {"ops": "Veterinary clinic", "nature": "Veterinary clinic", "lob_affinity": "bop"},
    # --- umbrella ---
    {"ops": "Large-scale general contractor", "nature": "General contractor", "lob_affinity": "commercial_umbrella"},
    {"ops": "National trucking fleet operations", "nature": "Trucking fleet", "lob_affinity": "commercial_umbrella"},
]

# Vehicle make/model pools
VEHICLE_COMBOS: List[Dict[str, str]] = [
    {"make": "Ford", "model": "F-150"},
    {"make": "Ford", "model": "F-250"},
    {"make": "Ford", "model": "Transit"},
    {"make": "Ford", "model": "E-350"},
    {"make": "Chevrolet", "model": "Silverado 1500"},
    {"make": "Chevrolet", "model": "Silverado 2500HD"},
    {"make": "Chevrolet", "model": "Express"},
    {"make": "RAM", "model": "1500"},
    {"make": "RAM", "model": "2500"},
    {"make": "RAM", "model": "ProMaster"},
    {"make": "Toyota", "model": "Camry"},
    {"make": "Toyota", "model": "Tacoma"},
    {"make": "Toyota", "model": "Tundra"},
    {"make": "Honda", "model": "Accord"},
    {"make": "Nissan", "model": "NV200"},
    {"make": "Nissan", "model": "Frontier"},
    {"make": "Mercedes", "model": "Sprinter"},
    {"make": "Freightliner", "model": "Cascadia"},
    {"make": "Freightliner", "model": "M2 106"},
    {"make": "Kenworth", "model": "T680"},
    {"make": "Peterbilt", "model": "579"},
    {"make": "International", "model": "LT"},
    {"make": "Isuzu", "model": "NPR-HD"},
    {"make": "GMC", "model": "Sierra 1500"},
    {"make": "GMC", "model": "Savana"},
]

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Christopher", "Karen",
    "Charles", "Lisa", "Daniel", "Nancy", "Matthew", "Betty", "Anthony",
    "Margaret", "Mark", "Sandra", "Donald", "Ashley", "Steven", "Kimberly",
    "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle", "Kenneth",
    "Carol", "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa",
    "Timothy", "Deborah", "Carlos", "Rosa", "Miguel", "Maria", "Jose",
    "Lucia", "Wei", "Mei", "Raj", "Priya",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Chen", "Patel", "Kim", "Shah", "Wang",
]

ENTITY_TYPES = ["llc", "corporation", "partnership", "sole_proprietor", "s_corp"]

CARRIER_NAMES = [
    "Progressive Commercial", "The Hartford", "Travelers",
    "EMC Insurance", "National General", "Berkshire Hathaway GUARD",
    "State Farm Commercial", "Liberty Mutual", "Nationwide",
    "CNA Insurance", "Zurich North America", "Old Guard Insurance",
]

LOSS_DESCRIPTIONS = [
    "Minor fender bender in parking lot",
    "Rear-end collision at intersection",
    "Cargo damage during transport",
    "Slip and fall on premises",
    "Water damage from burst pipe",
    "Employee back injury from lifting",
    "Tool theft from job site",
    "Customer property damage during service",
    "Windshield cracked by road debris",
    "Vehicle rollover on highway",
    "Electrical fire in warehouse",
    "Third-party bodily injury claim",
]

# LOB combo presets (ensures all 7 LOBs appear, plus realistic multi-LOB bundles)
LOB_COMBOS: List[List[str]] = [
    # Single LOBs (7)
    ["commercial_auto"],
    ["general_liability"],
    ["commercial_property"],
    ["workers_compensation"],
    ["commercial_umbrella"],
    ["bop"],
    ["cyber"],
    # Common 2-LOB combos
    ["commercial_auto", "general_liability"],
    ["commercial_auto", "workers_compensation"],
    ["commercial_property", "general_liability"],
    ["general_liability", "workers_compensation"],
    ["general_liability", "cyber"],
    ["commercial_property", "workers_compensation"],
    ["commercial_auto", "commercial_umbrella"],
    # Common 3-LOB combos
    ["commercial_auto", "general_liability", "workers_compensation"],
    ["commercial_auto", "general_liability", "commercial_umbrella"],
    ["commercial_property", "general_liability", "workers_compensation"],
    ["general_liability", "commercial_property", "cyber"],
    # Full packages
    ["commercial_auto", "general_liability", "workers_compensation", "commercial_umbrella"],
    ["commercial_auto", "general_liability", "commercial_property", "workers_compensation"],
    ["commercial_auto", "general_liability", "commercial_property", "workers_compensation", "commercial_umbrella"],
]

DELIVERY_STYLES = ["conversational", "bulk_email", "mixed"]
USER_PERSONAS = ["knowledgeable", "novice", "detailed"]

BILLING_PLANS = ["direct", "agency"]
PAYMENT_PLANS = ["annual", "semi-annual", "quarterly", "monthly"]
POLICY_STATUSES = ["new", "renewal", "rewrite"]

CONSTRUCTION_TYPES = [
    "frame", "joisted masonry", "non-combustible", "masonry non-combustible",
    "modified fire resistive", "fire resistive",
]

STREET_NAMES = [
    "Main St", "Commerce Blvd", "Industrial Pkwy", "Oak Ave",
    "Elm St", "Park Ave", "Broadway", "Market St", "Center Dr",
    "Maple Ln", "Pine St", "Cedar Rd", "Walnut St", "Lake Dr",
    "River Rd", "Airport Blvd", "Technology Dr", "Enterprise Way",
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _random_vin(rng: random.Random) -> str:
    """Generate a plausible 17-character VIN-like string."""
    chars = string.ascii_uppercase.replace("I", "").replace("O", "").replace("Q", "") + string.digits
    return "".join(rng.choice(chars) for _ in range(17))


def _random_date(rng: random.Random, year_lo: int, year_hi: int) -> str:
    """Return MM/DD/YYYY in the given year range."""
    y = rng.randint(year_lo, year_hi)
    m = rng.randint(1, 12)
    d = rng.randint(1, 28)
    return f"{m:02d}/{d:02d}/{y}"


def _random_license(rng: random.Random, state: str) -> str:
    """Generate a plausible license number."""
    num = rng.randint(10000000, 99999999)
    return f"{state}{num}"


def _random_tax_id(rng: random.Random) -> str:
    prefix = rng.randint(10, 99)
    suffix = rng.randint(1000000, 9999999)
    return f"{prefix}-{suffix}"


def _random_phone(rng: random.Random) -> str:
    area = rng.randint(200, 999)
    mid = rng.randint(200, 999)
    last = rng.randint(1000, 9999)
    return f"{area}-{mid}-{last}"


def _forms_for_lobs(lobs: List[str]) -> List[str]:
    """Deduplicated, sorted form list for the given LOBs."""
    forms: set = set()
    for lob in lobs:
        forms.update(LOB_FORMS.get(lob, []))
    return sorted(forms)


def _random_vehicles(rng: random.Random, count: int) -> List[dict]:
    vehicles = []
    for _ in range(count):
        combo = rng.choice(VEHICLE_COMBOS)
        year = str(rng.randint(2018, 2026))
        gvw = str(rng.choice([0, 6000, 8500, 9000, 10000, 11000, 14000, 26000, 33000]))
        vehicles.append({
            "vin": _random_vin(rng),
            "year": year,
            "make": combo["make"],
            "model": combo["model"],
            "use_type": "commercial",
            "gvw": gvw,
        })
    return vehicles


def _random_drivers(rng: random.Random, state: str, count: int) -> List[dict]:
    drivers = []
    used_names: set = set()
    for _ in range(count):
        while True:
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            full = f"{first} {last}"
            if full not in used_names:
                used_names.add(full)
                break
        dob = _random_date(rng, 1960, 2000)
        yob = int(dob.split("/")[2])
        exp = max(0, 2026 - yob - 16)
        drivers.append({
            "full_name": full,
            "first_name": first,
            "last_name": last,
            "dob": dob,
            "license_number": _random_license(rng, state),
            "license_state": state,
            "years_experience": str(min(exp, rng.randint(1, exp) if exp > 0 else 0)),
            "relationship": rng.choice(["employee", "owner", "family_member"]),
        })
    return drivers


def _random_locations(rng: random.Random, state: str, city: str, zip_code: str, count: int) -> List[dict]:
    locations = []
    for i in range(count):
        st_num = rng.randint(100, 9999)
        street = rng.choice(STREET_NAMES)
        loc: Dict[str, Any] = {
            "street": f"{st_num} {street}",
            "city": city,
            "state": state,
            "zip": zip_code,
        }
        # Add building details probabilistically
        if rng.random() < 0.7:
            loc["building_area"] = str(rng.choice([1500, 2500, 5000, 10000, 25000, 50000]))
            loc["construction_type"] = rng.choice(CONSTRUCTION_TYPES)
            loc["year_built"] = str(rng.randint(1960, 2024))
        locations.append(loc)
    return locations


def _random_loss_history(rng: random.Random, lobs: List[str], count: int) -> List[dict]:
    losses = []
    for _ in range(count):
        losses.append({
            "date": _random_date(rng, 2020, 2025),
            "lob": rng.choice(lobs),
            "description": rng.choice(LOSS_DESCRIPTIONS),
            "amount": str(rng.choice([2500, 5000, 7500, 10000, 15000, 25000, 50000, 75000, 100000])),
            "claim_status": rng.choice(["closed", "open", "subrogation"]),
        })
    return losses


def _random_prior_insurance(rng: random.Random, lobs: List[str], count: int) -> List[dict]:
    carriers_pool = list(CARRIER_NAMES)
    rng.shuffle(carriers_pool)
    priors = []
    for i in range(min(count, len(carriers_pool))):
        priors.append({
            "carrier_name": carriers_pool[i],
            "premium": str(rng.choice([8000, 12000, 15000, 20000, 25000, 35000, 50000, 75000])),
            "lob": rng.choice(lobs),
        })
    return priors


def _random_coverages(rng: random.Random, lobs: List[str]) -> List[dict]:
    cov_types = {
        "commercial_auto": ["liability", "collision", "comprehensive", "uninsured_motorist", "medical_payments"],
        "general_liability": ["liability", "products_completed_ops", "personal_advertising_injury"],
        "commercial_property": ["building", "business_personal_property", "business_income"],
        "workers_compensation": ["statutory", "employers_liability"],
        "commercial_umbrella": ["umbrella_liability"],
        "bop": ["liability", "property"],
        "cyber": ["first_party", "third_party", "cyber_extortion"],
    }
    limits = ["100000", "250000", "500000", "1000000", "2000000", "5000000"]
    deductibles = ["0", "250", "500", "1000", "2500", "5000", "10000"]
    covs = []
    for lob in lobs:
        types = cov_types.get(lob, ["liability"])
        # Pick 1-3 coverage types per LOB
        n = min(len(types), rng.randint(1, 3))
        for ct in rng.sample(types, n):
            covs.append({
                "lob": lob,
                "coverage_type": ct,
                "limit": rng.choice(limits),
                "deductible": rng.choice(deductibles),
            })
    return covs


# ---------------------------------------------------------------------------
# Document upload generation
# ---------------------------------------------------------------------------

_FILE_EXTENSIONS = {
    "loss_run": [".pdf", ".pdf", ".pdf", ".xlsx"],
    "drivers_license": [".jpg", ".png", ".jpeg", ".pdf"],
    "vehicle_registration": [".jpg", ".png", ".pdf"],
    "business_certificate": [".pdf", ".pdf", ".jpg"],
    "prior_declaration": [".pdf"],
    "acord_form": [".pdf"],
}


def _generate_document_uploads(
    rng: random.Random,
    loss_history: List[dict],
    drivers: List[dict],
    vehicles: List[dict],
    prior_insurance: List[dict],
) -> List[Dict[str, Any]]:
    """Generate realistic document upload dicts for ~40% of scenarios.

    Returns a list of dicts, each with document_type, file_path, and
    extracted_fields that the document would yield.
    """
    uploads: List[Dict[str, Any]] = []

    # Decide if this scenario gets document uploads (~40% chance)
    if rng.random() > 0.40:
        return uploads

    # Loss run upload if we have loss history
    if loss_history:
        ext = rng.choice(_FILE_EXTENSIONS["loss_run"])
        year = rng.choice(["2023", "2024", "2025"])
        extracted: Dict[str, Any] = {}
        for i, lo in enumerate(loss_history, start=1):
            extracted[f"loss_{i}_date"] = lo.get("date", "")
            extracted[f"loss_{i}_amount"] = lo.get("amount", "")
            extracted[f"loss_{i}_description"] = lo.get("description", "")
        uploads.append({
            "document_type": "loss_run",
            "file_path": f"/uploads/loss_run_{year}{ext}",
            "extracted_fields": extracted,
        })

    # Driver's license uploads (1-2 if we have drivers)
    if drivers:
        dl_count = min(len(drivers), rng.randint(1, 2))
        for di in range(dl_count):
            d = drivers[di]
            ext = rng.choice(_FILE_EXTENSIONS["drivers_license"])
            name_slug = d["full_name"].lower().replace(" ", "_")
            uploads.append({
                "document_type": "drivers_license",
                "file_path": f"/uploads/dl_{name_slug}{ext}",
                "extracted_fields": {
                    f"driver_{di + 1}_name": d["full_name"],
                    f"driver_{di + 1}_dob": d["dob"],
                    f"driver_{di + 1}_license_number": d["license_number"],
                    f"driver_{di + 1}_license_state": d["license_state"],
                },
            })

    # Vehicle registration (optional, ~50% if we have vehicles)
    if vehicles and rng.random() < 0.50:
        v = vehicles[0]
        ext = rng.choice(_FILE_EXTENSIONS["vehicle_registration"])
        uploads.append({
            "document_type": "vehicle_registration",
            "file_path": f"/uploads/vehicle_reg_{v['vin'][-6:]}{ext}",
            "extracted_fields": {
                "vehicle_1_year": v["year"],
                "vehicle_1_make": v["make"],
                "vehicle_1_model": v["model"],
                "vehicle_1_vin": v["vin"],
            },
        })

    # Prior declaration (optional, ~30% if we have prior insurance)
    if prior_insurance and rng.random() < 0.30:
        ext = rng.choice(_FILE_EXTENSIONS["prior_declaration"])
        p = prior_insurance[0]
        uploads.append({
            "document_type": "prior_declaration",
            "file_path": f"/uploads/prior_dec_page{ext}",
            "extracted_fields": {
                "prior_1_carrier": p["carrier_name"],
                "prior_1_premium": p["premium"],
            },
        })

    # Business certificate (optional, ~20%)
    if rng.random() < 0.20:
        ext = rng.choice(_FILE_EXTENSIONS["business_certificate"])
        uploads.append({
            "document_type": "business_certificate",
            "file_path": f"/uploads/business_cert{ext}",
            "extracted_fields": {},
        })

    return uploads


# ---------------------------------------------------------------------------
# Business-name generation
# ---------------------------------------------------------------------------

_BIZ_PREFIXES = [
    "Apex", "Summit", "Pinnacle", "Prime", "Elite", "Atlas", "Vanguard",
    "Meridian", "Horizon", "Keystone", "Sterling", "Cascade", "Frontier",
    "Liberty", "Pacific", "Continental", "Metro", "National", "Heritage",
    "Alliance", "Eagle", "Titan", "Patriot", "Northstar", "Redwood",
    "Ironclad", "Bridgeport", "Lakeview", "Silverline", "Granite",
    "Beacon", "Trident", "Coastal", "Cedar", "Oakridge",
]

_BIZ_SUFFIXES_BY_NATURE: Dict[str, List[str]] = {
    "default": ["Services", "Solutions", "Group", "Enterprises", "Company"],
    "trucking": ["Trucking", "Transport", "Logistics", "Freight", "Hauling"],
    "delivery": ["Delivery", "Courier", "Express", "Dispatch"],
    "construction": ["Construction", "Builders", "Contracting", "Development"],
    "restaurant": ["Catering", "Foods", "Dining"],
    "tech": ["Technologies", "Tech", "Digital", "Systems", "Software"],
    "medical": ["Health", "Medical", "Wellness", "Care"],
    "legal": ["Legal", "Law Group", "Attorneys"],
    "property": ["Properties", "Realty", "Real Estate", "Management"],
    "retail": ["Retail", "Goods", "Supply", "Trading"],
}


def _biz_suffix_key(nature: str) -> str:
    nature_lower = nature.lower()
    for key, keywords in {
        "trucking": ["truck", "freight", "haul", "transport", "logistics"],
        "delivery": ["deliver", "courier", "express", "package"],
        "construction": ["construct", "roof", "electric", "plumb", "hvac", "contract"],
        "restaurant": ["restaurant", "cater", "food", "dining"],
        "tech": ["it ", "software", "saas", "tech", "e-commerce", "analytics", "data"],
        "medical": ["health", "dental", "veterinar", "medical"],
        "legal": ["law", "legal", "attorney"],
        "property": ["real estate", "property", "warehouse", "storage"],
        "retail": ["retail", "store", "clothing", "parts", "wholesale"],
    }.items():
        if any(kw in nature_lower for kw in keywords):
            return key
    return "default"


def _random_biz_name(rng: random.Random, nature: str) -> str:
    prefix = rng.choice(_BIZ_PREFIXES)
    skey = _biz_suffix_key(nature)
    suffix = rng.choice(_BIZ_SUFFIXES_BY_NATURE[skey])
    entity = rng.choice(["LLC", "Inc.", "Corp.", "LP", "Co."])
    return f"{prefix} {suffix} {entity}"


# ---------------------------------------------------------------------------
# Size profiles
# ---------------------------------------------------------------------------

_SIZE_PROFILES = [
    # (label, emp_lo, emp_hi, rev_lo, rev_hi, vehicle_lo, vehicle_hi, driver_lo, driver_hi, location_lo, location_hi)
    ("small",   3,   20,   200_000,   2_000_000,  1,  3,  1, 3,  1, 1),
    ("medium", 20,  100, 2_000_000,  20_000_000,  3, 10,  3, 8,  1, 3),
    ("large", 100,  500, 20_000_000, 100_000_000, 10, 30,  8, 20, 2, 5),
]


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------


def generate_scenarios(seed: int = 42) -> List[ConversationScenario]:
    """
    Generate 500+ parametric ConversationScenario instances.

    Uses a fixed random seed for reproducibility.
    """
    rng = random.Random(seed)
    bases = _load_base_entities()
    scenarios: List[ConversationScenario] = []

    # Phase 1: systematic expansion — iterate over LOB combos x size profiles x bases
    # This guarantees coverage of all LOBs and multi-LOB combos.
    idx = 0
    for lob_combo in LOB_COMBOS:
        for size_label, emp_lo, emp_hi, rev_lo, rev_hi, veh_lo, veh_hi, drv_lo, drv_hi, loc_lo, loc_hi in _SIZE_PROFILES:
            for base in bases:
                scenario = _build_scenario(
                    rng, idx, base, lob_combo,
                    emp_lo, emp_hi, rev_lo, rev_hi,
                    veh_lo, veh_hi, drv_lo, drv_hi,
                    loc_lo, loc_hi,
                )
                scenarios.append(scenario)
                idx += 1

    # Phase 2: random fill to reach 500+ total
    while len(scenarios) < 520:
        base = rng.choice(bases)
        lob_combo = rng.choice(LOB_COMBOS)
        size = rng.choice(_SIZE_PROFILES)
        _, emp_lo, emp_hi, rev_lo, rev_hi, veh_lo, veh_hi, drv_lo, drv_hi, loc_lo, loc_hi = size
        scenario = _build_scenario(
            rng, idx, base, lob_combo,
            emp_lo, emp_hi, rev_lo, rev_hi,
            veh_lo, veh_hi, drv_lo, drv_hi,
            loc_lo, loc_hi,
        )
        scenarios.append(scenario)
        idx += 1

    return scenarios


def _build_scenario(
    rng: random.Random,
    idx: int,
    base: dict,
    lob_combo: List[str],
    emp_lo: int, emp_hi: int,
    rev_lo: int, rev_hi: int,
    veh_lo: int, veh_hi: int,
    drv_lo: int, drv_hi: int,
    loc_lo: int, loc_hi: int,
) -> ConversationScenario:
    """Build a single scenario from a base template + parametric variations."""

    # Pick random location
    state, city, zip_code = rng.choice(STATE_CITY_ZIP)

    # Pick a business template (prefer ones with matching LOB affinity)
    affinity_templates = [t for t in BUSINESS_TEMPLATES if t["lob_affinity"] in lob_combo]
    if not affinity_templates:
        affinity_templates = BUSINESS_TEMPLATES
    biz_template = rng.choice(affinity_templates)

    # Employee / revenue
    emp_count = rng.randint(emp_lo, emp_hi)
    revenue = rng.randint(rev_lo, rev_hi)
    # Round revenue to nearest 10K
    revenue = round(revenue, -4)
    years_biz = rng.randint(1, 40)

    # Business dict
    biz_name = _random_biz_name(rng, biz_template["nature"])
    street_num = rng.randint(100, 9999)
    street = rng.choice(STREET_NAMES)
    business = {
        "business_name": biz_name,
        "mailing_address": {
            "line_one": f"{street_num} {street}",
            "city": city,
            "state": state,
            "zip_code": zip_code,
        },
        "tax_id": _random_tax_id(rng),
        "entity_type": rng.choice(ENTITY_TYPES),
        "operations_description": biz_template["ops"],
        "nature_of_business": biz_template["nature"],
        "annual_revenue": str(revenue),
        "employee_count": str(emp_count),
        "years_in_business": str(years_biz),
        "annual_payroll": str(int(revenue * rng.uniform(0.2, 0.5))),
        "contacts": [{
            "full_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            "phone": _random_phone(rng),
            "email": f"contact@{biz_name.split()[0].lower()}.com",
            "role": rng.choice(["Owner", "Operations Manager", "Office Manager", "CFO", "Insurance Coordinator"]),
        }],
    }

    # Policy
    eff_month = rng.randint(1, 12)
    eff_year = rng.choice([2025, 2026, 2027])
    policy = {
        "effective_date": f"{eff_month:02d}/01/{eff_year}",
        "expiration_date": f"{eff_month:02d}/01/{eff_year + 1}",
        "status": rng.choice(POLICY_STATUSES),
        "billing_plan": rng.choice(BILLING_PLANS),
        "payment_plan": rng.choice(PAYMENT_PLANS),
    }

    # Vehicles — only if commercial_auto in LOBs
    needs_vehicles = "commercial_auto" in lob_combo
    veh_count = rng.randint(veh_lo, veh_hi) if needs_vehicles else 0
    vehicles = _random_vehicles(rng, veh_count)

    # Drivers — only if commercial_auto in LOBs
    drv_count = rng.randint(drv_lo, drv_hi) if needs_vehicles else 0
    drivers = _random_drivers(rng, state, drv_count)

    # Locations — if property or bop in LOBs
    needs_locations = ("commercial_property" in lob_combo) or ("bop" in lob_combo)
    loc_count = rng.randint(loc_lo, loc_hi) if needs_locations else (1 if rng.random() < 0.3 else 0)
    locations = _random_locations(rng, state, city, zip_code, loc_count)

    # Coverages
    coverages = _random_coverages(rng, lob_combo)

    # Loss history (0-3 entries)
    loss_count = rng.choices([0, 1, 2, 3], weights=[30, 40, 20, 10])[0]
    loss_history = _random_loss_history(rng, lob_combo, loss_count)

    # Prior insurance (0-2 entries)
    prior_count = rng.choices([0, 1, 2], weights=[30, 50, 20])[0]
    prior_insurance = _random_prior_insurance(rng, lob_combo, prior_count)

    # Forms
    assigned_forms = _forms_for_lobs(lob_combo)

    # Document uploads (~40% of scenarios)
    document_uploads = _generate_document_uploads(
        rng, loss_history, drivers, vehicles, prior_insurance,
    )

    return ConversationScenario(
        scenario_id=f"scenario_{idx:04d}",
        business=business,
        policy=policy,
        vehicles=vehicles,
        drivers=drivers,
        coverages=coverages,
        locations=locations,
        loss_history=loss_history,
        prior_insurance=prior_insurance,
        lobs=list(lob_combo),
        assigned_forms=assigned_forms,
        delivery_style=rng.choice(DELIVERY_STYLES),
        user_persona=rng.choice(USER_PERSONAS),
        document_uploads=document_uploads,
    )
