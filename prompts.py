#!/usr/bin/env python3
"""
Prompt Builders: Form-specific, category-specific prompts
==========================================================
Builds structured prompts for text-only LLM extraction from ACORD forms 125, 127, 137.

Each prompt combines:
  1. Form layout hint (where fields appear on the form)
  2. Category-specific disambiguation rules
  3. Field names with tooltips
  4. Dual OCR text (Docling structured + BBox positional)
  5. Extraction rules and output format
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ===========================================================================
# Form layout hints
# ===========================================================================

ACORD_125_LAYOUT = """ACORD 125 - Commercial Insurance Application
Page 1 (top-to-bottom):
  - DATE (top right): Form completion date in MM/DD/YYYY
  - AGENCY/PRODUCER (left side): The agent/broker selling the policy - company name, contact person, phone, email, address
  - COMPANY/INSURER (right side, near top): The insurance CARRIER providing coverage + 5-digit NAIC code
  - NAMED INSURED/APPLICANT: The customer buying insurance - business name, mailing address
  - POLICY: Policy number, effective date, expiration date, status checkboxes (Quote/Bound/Issue)
  - LINE OF BUSINESS: Checkboxes for CGL, Commercial Property, Business Auto, Umbrella, etc. with premium amounts
Page 2: Premises/location, Nature of business, Legal entity.
Page 3+: Prior coverage, Loss history, Attachments.
CRITICAL: "ACORD" or "ACORD CORPORATION" is the FORM PUBLISHER, not the insurer or producer!
Carrier/Insurer != Agent/Producer != Customer/Named Insured. NAIC = 5 digits."""

ACORD_127_LAYOUT = """ACORD 127 - Business Auto Section
Page 1 (top-to-bottom):
  - DATE (top right): Form completion date
  - COMPANY/INSURER (top): Insurance carrier name + 5-digit NAIC code
  - NAMED INSURED: The customer/business buying insurance
  - POLICY NUMBER: Starts with letters then numbers (e.g., BA-12345678)
  - PRODUCER/AGENT: The broker
  - DRIVER TABLE (middle/bottom of page 1):
    13 rows (suffix _A to _M), columns left-to-right:
    #, First Name, City, Last Name, State, Zip, Sex, DOB, License#, License State
CRITICAL: "ACORD" or "ACORD CORPORATION" is the FORM PUBLISHER, not the insurer!
NAIC code is a 5-digit number (not a tax ID which has format XX-XXXXXXX).
DRIVER SUFFIX: #1=_A, #2=_B, #3=_C ... #13=_M."""

ACORD_137_LAYOUT = """ACORD 137 - Commercial Auto Section (Vehicle Schedule)
Page 1: Named Insured, Policy effective date, Insurer, NAIC code.
         Vehicle schedule with coverage symbols/limits (suffixes _A to _F).
         Business Auto Symbols: 1=Any Auto, 2=Owned, 3=Hired, etc.
Page 2+: Coverage details, deductibles, liability limits.
VEHICLE SUFFIX: _A to _F for different vehicle/coverage rows."""


def _layout_hint(form_type: str) -> str:
    return {
        "125": ACORD_125_LAYOUT,
        "127": ACORD_127_LAYOUT,
        "137": ACORD_137_LAYOUT,
    }.get(form_type, "ACORD form. Header at top; sections labeled by headings.")


# ===========================================================================
# Category-specific hints
# ===========================================================================

_CATEGORY_HINTS = {
    "header": (
        "HEADER fields are at the very top of the form: "
        "form date (MM/DD/YYYY), form edition identifier. "
        "The FORM COMPLETION DATE is usually the date the form was filled out (top-right area)."
    ),
    "insurer": (
        "INSURER = the insurance COMPANY (carrier) providing coverage. "
        "NOT the agent/producer and NOT the customer/named insured. "
        "Look for the COMPANY field or 'INSURER' label at the top of the form. "
        "NAIC code is a 5-digit number next to the carrier name. "
        "CRITICAL: The Producer/Agent name is a PERSON or AGENCY. The Insurer is the INSURANCE COMPANY."
    ),
    "producer": (
        "PRODUCER/AGENT/AGENCY = the broker/agent selling the policy. "
        "NOT the insurance company (Insurer) and NOT the customer (Named Insured). "
        "Look for 'AGENCY', 'PRODUCER', 'AGENT' labels. "
        "Contact person = the individual at the agency. Phone/fax/email belong to the agency."
    ),
    "named_insured": (
        "NAMED INSURED/APPLICANT = the business or person BUYING insurance. "
        "NOT the agent and NOT the carrier. "
        "Look for 'NAMED INSURED', 'APPLICANT', 'FIRST NAMED INSURED' labels. "
        "Their MAILING ADDRESS is separate from the producer/agent address. "
        "ZIP CODE is a 5-digit number (NOT a phone number)."
    ),
    "policy": (
        "POLICY fields: policy number, effective/expiration dates, "
        "status indicators (Quote/Bound/Issue). Dates in MM/DD/YYYY. "
        "CRITICAL: 'Indicator' fields are CHECKBOXES - return ONLY '1' (checked) or 'Off' (not checked). "
        "Do NOT put text values or dollar amounts in Indicator fields. "
        "LineOfBusiness Indicator = is that line of business selected? '1' if checkbox is marked."
    ),
    "driver": (
        "DRIVER fields from the driver table. Each row is one driver. "
        "Suffix _A = Driver #1, _B = Driver #2 ... _M = Driver #13. "
        "Use BBox X positions to disambiguate columns: "
        "first name, city, last name, state, DOB may run together in Docling OCR."
    ),
    "vehicle": (
        "VEHICLE fields: Year, Make, Model, VIN, body type, GVW, cost new, "
        "radius of use, garaging location. Suffixes _A-_E (127) or _A-_F (137)."
    ),
    "coverage": (
        "COVERAGE fields: Business Auto symbols (1-9), liability limits, "
        "deductibles, physical damage, other coverages. "
        "Symbol values: 1=Any Auto, 2=Owned Autos Only, 7=Specifically Described, 8=Hired, 9=Non-Owned."
    ),
    "checkbox": (
        "CHECKBOX/INDICATOR fields: return ONLY \"1\" if checked (X, checkmark, filled box), "
        "\"Off\" if unchecked or empty box. "
        "NEVER return text values, dollar amounts, or descriptions for Indicator fields."
    ),
    "location": (
        "LOCATION/PREMISES fields: physical address, city, state, zip of the insured business. "
        "ZIP is a 5-digit or 9-digit postal code, NOT a phone number."
    ),
    "loss_history": (
        "LOSS HISTORY fields: prior claims, dates, amounts, descriptions."
    ),
}


def _category_hint(category: str) -> str:
    return _CATEGORY_HINTS.get(category, "")


# ===========================================================================
# Tooltip formatting
# ===========================================================================

def _format_fields_with_tooltips(
    field_names: List[str],
    tooltips: Dict[str, str],
    max_tooltip_len: int = 80,
) -> str:
    """Format field list with tooltips for prompt injection."""
    lines: List[str] = []
    for name in field_names:
        tip = tooltips.get(name, "")
        if tip:
            lines.append(f"  - {name}: {tip[:max_tooltip_len]}")
        else:
            lines.append(f"  - {name}")
    return "\n".join(lines)


def _json_template(field_names: List[str]) -> str:
    """Build a JSON template with exact field names as keys, all set to null.
    
    Annotates Indicator fields with comments to guide the LLM.
    """
    lines = ["{"]
    for i, name in enumerate(field_names):
        comma = "," if i < len(field_names) - 1 else ""
        is_indicator = "indicator" in name.lower() or name.lower().startswith("chk")
        if is_indicator:
            lines.append(f'  "{name}": null{comma}  // CHECKBOX: "1" or "Off" only')
        else:
            lines.append(f'  "{name}": null{comma}')
    lines.append("}")
    return "\n".join(lines)


# ===========================================================================
# Core extraction prompt
# ===========================================================================

def build_extraction_prompt(
    form_type: str,
    category: str,
    field_names: List[str],
    tooltips: Dict[str, str],
    docling_text: str,
    bbox_text: str,
    label_value_text: str = "",
    max_docling: int = 8000,
    max_bbox: int = 5000,
) -> str:
    """
    Build a category-specific extraction prompt.

    Combines form layout, category hint, field tooltips, and dual OCR text.
    """
    layout = _layout_hint(form_type)
    cat_hint = _category_hint(category)
    field_block = _format_fields_with_tooltips(field_names, tooltips)

    has_indicators = category == "checkbox" or any(
        "indicator" in k.lower() or k.lower().startswith("chk") for k in field_names
    )
    checkbox_rule = ""
    if has_indicators:
        checkbox_rule = (
            'CHECKBOX/INDICATOR RULE: Any field containing "Indicator" in its name is a CHECKBOX. '
            'Return ONLY "1" (checked/marked/X) or "Off" (empty/unchecked). '
            'NEVER return text, dollar amounts, or descriptions for Indicator fields.'
        )

    json_tmpl = _json_template(field_names)

    prompt = f"""You are extracting {category.upper()} fields from an ACORD {form_type} form.

=== FORM LAYOUT ===
{layout}

=== SECTION CONTEXT ===
{cat_hint}

=== FIELDS TO EXTRACT ===
{field_block}

=== DOCLING OCR TEXT (structured markdown) ===
{docling_text[:max_docling]}

=== BBOX OCR TEXT (with X,Y positions for spatial disambiguation) ===
{bbox_text[:max_bbox]}

{f"=== LABEL-VALUE PAIRS ==={chr(10)}{label_value_text[:2000]}" if label_value_text else ""}

CRITICAL RULES:
1. You MUST use EXACTLY the field key names shown above. Do NOT rename or invent keys.
2. Fill in the JSON template below - replace null with the extracted value (as a string).
3. If a field is blank/missing, remove it from output (do not return null or empty string).
4. Use BOTH OCR sources: Docling for structure, BBox for spatial positions.
5. Dates: MM/DD/YYYY. Numbers: as strings.
6. {checkbox_rule or 'For checkboxes/indicators: "1" if checked, "Off" if not. NEVER put text in Indicator fields.'}
7. Do NOT paraphrase - use the exact text from the OCR.
8. ZIP codes are 5-digit numbers, NOT phone numbers. Phone numbers have dashes (xxx-xxx-xxxx).

JSON TEMPLATE (use these EXACT keys):
{json_tmpl}

Return ONLY a valid JSON object. No explanation, no markdown fences, just JSON.
"""
    return prompt


# ===========================================================================
# Driver-specific prompt
# ===========================================================================

def build_driver_row_prompt(
    driver_num: int,
    suffix: str,
    field_names: List[str],
    tooltips: Dict[str, str],
    docling_text: str,
    bbox_text: str,
    column_map: Optional[Dict[str, int]] = None,
    row_data: str = "",
) -> str:
    """
    Build a prompt for extracting a single driver row.

    Args:
        driver_num: 1-based driver number.
        suffix: The suffix letter (A, B, C, ...).
        column_map: Optional {column_name: x_center} from dynamic column detection.
        row_data: Pre-extracted row text with X positions from spatial index.
    """
    field_block = _format_fields_with_tooltips(field_names, tooltips)

    # Build dynamic column hint
    if column_map:
        col_lines = [f"  - {name}: X ≈ {x}" for name, x in sorted(column_map.items(), key=lambda t: t[1])]
        col_hint = "DETECTED COLUMN X-POSITIONS:\n" + "\n".join(col_lines)
    else:
        col_hint = """TYPICAL COLUMN ORDER (left to right):
  1. Driver # (row number)
  2. First Name (GivenName) - a person's first name
  3. City - a city name like Indianapolis, Greenfield, etc.
  4. Last Name (Surname) - a person's last name  
  5. State - 2-letter code (IN, CA, TX...)
  6. Zip - 5-digit postal code
  7. Sex - M or F
  8. DOB - date MM/DD/YYYY
  9. License # - alphanumeric license identifier
  10. License State - 2-letter code"""

    # Pre-extracted row data takes priority
    row_section = ""
    if row_data:
        row_section = f"""
=== PRE-EXTRACTED ROW {driver_num} DATA (with X positions) ===
{row_data}

Use the X positions above to determine which column each value belongs to.
Values at similar X positions as column headers go in that column.
"""

    json_tmpl = _json_template(field_names)

    prompt = f"""Extract DRIVER #{driver_num} (suffix _{suffix}) from ACORD 127.

{col_hint}
{row_section}
CRITICAL DISAMBIGUATION:
- City names (Indianapolis, Greenfield, Columbus, etc.) are in the CITY column, NOT the name columns.
- "IN", "MD", "VA", "OH" etc. are STATE CODES, NOT last names or first names.
- First names are PERSON names: Thomas, Lisa, Bruce, Daniel, etc.
- Last names are PERSON surnames: Mooney, Green, Spence, etc.
- ZIP codes are 5-digit numbers: 46140, 46250, etc.
- DOB is a date: MM/DD/YYYY format.

FIELDS (suffix _{suffix}):
{field_block}

=== BBOX OCR (use X positions to identify columns) ===
{bbox_text[:5000]}

CRITICAL: Use EXACTLY these field key names. Fill in the template below:
{json_tmpl}

Return ONLY valid JSON. No explanation, no markdown fences:
"""
    return prompt


# ===========================================================================
# Vehicle-specific prompt
# ===========================================================================

def build_vehicle_prompt(
    form_type: str,
    suffix: str,
    field_names: List[str],
    tooltips: Dict[str, str],
    docling_text: str,
    bbox_text: str,
) -> str:
    """Build a prompt for extracting vehicle fields for a specific suffix."""
    field_block = _format_fields_with_tooltips(field_names, tooltips)

    if form_type == "137":
        context = (
            "ACORD 137 vehicle schedule. "
            "Vehicle rows use suffixes _A through _F. "
            "Fields include Business Auto Symbols (1-9), coverage descriptions, "
            "limit amounts, deductibles."
        )
    else:
        context = (
            "ACORD 127 vehicle information. "
            "Vehicle rows use suffixes _A through _E. "
            "Fields include Year, Make, Model, VIN, body type, GVW, cost new, "
            "radius of use, garaging location."
        )

    json_tmpl = _json_template(field_names)

    prompt = f"""Extract VEHICLE fields (suffix _{suffix}) from ACORD {form_type}.

{context}

FIELDS (suffix _{suffix}):
{field_block}

=== DOCLING OCR ===
{docling_text[:6000]}

=== BBOX OCR ===
{bbox_text[:4000]}

CRITICAL: Use EXACTLY these field key names. Fill in the template below:
{json_tmpl}

Return ONLY valid JSON. No explanation, no markdown fences:
"""
    return prompt


# ===========================================================================
# Gap-fill prompt (second pass)
# ===========================================================================

def build_gap_fill_prompt(
    form_type: str,
    missing_fields: List[str],
    tooltips: Dict[str, str],
    bbox_text: str,
    label_value_text: str = "",
) -> str:
    """
    Second-pass prompt to fill fields missed in the first extraction.
    Uses BBox text (spatial) for targeted extraction.
    """
    field_block = _format_fields_with_tooltips(missing_fields, tooltips)
    layout = _layout_hint(form_type)

    json_tmpl = _json_template(missing_fields)

    prompt = f"""Some fields were not extracted in the first pass. Try to find them.

=== FORM LAYOUT ===
{layout}

=== MISSING FIELDS ===
{field_block}

=== BBOX OCR TEXT (positional text - search carefully) ===
{bbox_text[:8000]}

{f"=== LABEL-VALUE PAIRS ==={chr(10)}{label_value_text[:3000]}" if label_value_text else ""}

CRITICAL RULES:
- You MUST use EXACTLY the field key names listed above. Do NOT rename or invent keys.
- Fill in the JSON template below - replace null with the value found in OCR.
- Only return fields you can confidently find. Remove keys you cannot find.
- Dates: MM/DD/YYYY. Checkboxes: "1" or "Off".

JSON TEMPLATE (use these EXACT keys):
{json_tmpl}

Return ONLY valid JSON:
"""
    return prompt
