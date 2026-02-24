"""Entity-to-field mapping for ACORD Form 137 (Commercial Auto Section).

Maps coverage symbols and limits to Form 137 PDF widget field names.
Form 137 is for COVERAGE INFORMATION ONLY — vehicle physical details
(VIN, make, model, year) belong on Form 127, not here.

Coverage amount fields use suffixes _A, _B, _C (3 columns max).
Symbol indicator fields have varying suffix patterns per the schema.
"""

from typing import Dict
from Custom_model_fa_pf.entity_schema import CustomerSubmission

# Form 137 has 3 coverage columns (A, B, C)
COVERAGE_SUFFIXES = list("ABC")

# Symbol number → word for BusinessAutoSymbol indicator field names
SYMBOL_NAMES = {
    "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five",
    "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine",
}

# Coverage type keywords → (field_name_template, value_type)
# value_type: "limit" = uses cov.limit, "deductible" = uses cov.deductible,
#             "indicator" = set to "1", None = handled specially
COVERAGE_FIELD_MAP = {
    "liability": ("Vehicle_CombinedSingleLimit_LimitIndicator", "indicator"),
    "csl": ("Vehicle_CombinedSingleLimit_LimitIndicator", "indicator"),
    "bodily_injury": (None, None),  # handled specially (per-person + per-accident)
    "property_damage": ("Vehicle_PropertyDamage_PerAccidentLimitAmount", "limit"),
    "collision": ("Vehicle_Collision_DeductibleAmount", "deductible"),
    "comprehensive": ("Vehicle_Comprehensive_DeductibleAmount", "deductible"),
    "medical_payments": ("Vehicle_MedicalPayments_PerPersonLimitAmount", "limit"),
    "uninsured": (None, None),  # handled specially (BI per-person + per-accident + PD)
    "towing": ("Vehicle_TowingAndLabour_LimitAmount", "limit"),
    "specified_cause": ("Vehicle_SpecifiedCauseOfLoss_DeductibleAmount", "deductible"),
}


def map_fields(submission: CustomerSubmission) -> Dict[str, str]:
    """Map extracted entities to Form 137 field names.

    Args:
        submission: Extracted customer submission data

    Returns:
        Dict of field_name -> value for Form 137
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

    # --- Business Auto Symbol (use coverage symbol if available, default to "1" = Any Auto) ---
    num_vehicles = min(len(submission.vehicles), len(COVERAGE_SUFFIXES))
    # Collect symbols from coverages (first symbol found per column wins)
    coverage_symbols = set()
    for cov in submission.coverages:
        if cov.symbol:
            coverage_symbols.add(cov.symbol.strip())
    # If coverages specify symbols, use them; otherwise default to "1" (Any Auto)
    if coverage_symbols:
        for sym in coverage_symbols:
            word = SYMBOL_NAMES.get(sym)
            if word:
                for i in range(max(1, num_vehicles)):
                    sfx = f"_{COVERAGE_SUFFIXES[i]}"
                    fields[f"Vehicle_BusinessAutoSymbol_{word}Indicator{sfx}"] = "1"
    else:
        for i in range(max(1, num_vehicles)):
            sfx = f"_{COVERAGE_SUFFIXES[i]}"
            fields[f"Vehicle_BusinessAutoSymbol_OneIndicator{sfx}"] = "1"

    # --- Coverage fields ---
    for cov in submission.coverages:
        if not cov.coverage_type:
            continue

        ct = cov.coverage_type.lower().replace(" ", "_")

        # Determine which coverage columns to apply to
        target_suffixes = [f"_{COVERAGE_SUFFIXES[j]}" for j in range(max(1, num_vehicles))]

        for sfx in target_suffixes:
            # Bodily injury: per-person and per-accident split
            if ct in ("bodily_injury", "bodily_injury"):
                pp = cov.per_person_limit or (cov.limit.split("/")[0].strip() if cov.limit and "/" in cov.limit else cov.limit)
                pa = cov.per_accident_limit or (cov.limit.split("/")[1].strip() if cov.limit and "/" in cov.limit else cov.limit)
                if pp:
                    fields[f"Vehicle_BodilyInjury_PerPersonLimitAmount{sfx}"] = pp
                if pa:
                    fields[f"Vehicle_BodilyInjury_PerAccidentLimitAmount{sfx}"] = pa
                continue

            # Uninsured motorists: split into BI per-person/per-accident + PD
            if ct in ("uninsured", "uninsured_motorists"):
                pp = cov.per_person_limit or (cov.limit.split("/")[0].strip() if cov.limit and "/" in cov.limit else cov.limit)
                pa = cov.per_accident_limit or (cov.limit.split("/")[1].strip() if cov.limit and "/" in cov.limit else cov.limit)
                if pp:
                    fields[f"Vehicle_UninsuredMotorists_BodilyInjuryPerPersonLimitAmount{sfx}"] = pp
                if pa:
                    fields[f"Vehicle_UninsuredMotorists_BodilyInjuryPerAccidentLimitAmount{sfx}"] = pa
                if cov.limit and "/" in cov.limit:
                    parts = cov.limit.split("/")
                    if len(parts) > 2:
                        fields[f"Vehicle_UninsuredMotorists_PropertyDamagePerAccidentLimit{sfx}"] = parts[2].strip()
                continue

            # Standard coverage types
            for key, (field_tmpl, value_type) in COVERAGE_FIELD_MAP.items():
                if key in ct and field_tmpl:
                    if value_type == "limit" and cov.limit:
                        fields[f"{field_tmpl}{sfx}"] = cov.limit
                    elif value_type == "deductible" and cov.deductible:
                        fields[f"{field_tmpl}{sfx}"] = cov.deductible
                    elif value_type == "indicator":
                        fields[f"{field_tmpl}{sfx}"] = "1"
                    break

    return fields
