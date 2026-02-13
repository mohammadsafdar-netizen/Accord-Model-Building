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
  - COMPANY/INSURER (right side, near top): The insurance CARRIER providing coverage + 5-digit NAIC code. PRODUCT/PROGRAM CODE (if present) is a separate code (e.g. CGL-12345), NOT the policy number.
  - NAMED INSURED/APPLICANT: The customer buying insurance - business name, mailing address
  - POLICY: Policy number, effective date, expiration date. STATUS row: Quote / Bound / Issue / Cancel / Renew / Change (each has a checkbox; return 1 if marked, Off if not). Status date = Policy_Status_EffectiveDate_A; status time = Policy_Status_EffectiveTime_A as 4-digit HHMM (e.g. 1000), never a date.
  - LINE OF BUSINESS: Checkboxes for CGL, Commercial Property, Business Auto, Umbrella, etc. with premium amounts
Page 2: Premises/location, Nature of business, Legal entity. In tables (employee count, annual revenue, area): use the VALUE in the cell, not the column header label.
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
  - DRIVER TABLE (middle/bottom of page 1): 13 rows, suffix _A to _M.
    Use BBox X positions to assign columns: # (x<180), First Name (~200-280), City (~285-500), Last Name/State (~560-700), Zip (~700-780), Sex (~850-930), DOB (~1080-1160), License# (~1500-1620), License State (~1830-1920). Row order = driver number: row 1=_A, row 2=_B, etc.
CRITICAL: "ACORD" or "ACORD CORPORATION" is the FORM PUBLISHER, not the insurer!
NAIC code is a 5-digit number (not a tax ID which has format XX-XXXXXXX).
DRIVER SUFFIX: #1=_A, #2=_B, #3=_C ... #13=_M."""

ACORD_137_LAYOUT = """ACORD 137 - Commercial Auto Section (Vehicle Schedule)
Page 1: Named Insured, Policy effective date, Insurer, NAIC code.
         Vehicle schedule with coverage symbols/limits (suffixes _A to _F).
         Business Auto Symbols 1-9 are CHECKBOXES (1=Any Auto, 2=Owned, 3=Hired, etc.): use BBox to see which symbol column is marked; return 1 or Off.
Page 2+: Same layout for Truckers (_B) and Motor Carrier (_C). Coverage amounts and deductibles appear in fixed X regions; use BBox Y to match labels to values.
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
        "CRITICAL: The Producer/Agent name is a PERSON or AGENCY. The Insurer is the INSURANCE COMPANY. "
        "UNDERWRITER = a PERSON's name at the carrier (e.g. John Doe), NOT the company name. "
        "Insurer_Underwriter_FullName_A = person; Insurer_FullName_A = company name. "
        "Insurer_ProductCode_A = PRODUCT or PROGRAM code (e.g. CGL-12345), separate from POLICY NUMBER; do NOT use the policy number here."
    ),
    "producer": (
        "PRODUCER/AGENT/AGENCY = the broker/agent selling the policy. "
        "NOT the insurance company (Insurer) and NOT the customer (Named Insured). "
        "Look for 'AGENCY', 'PRODUCER', 'AGENT' labels. "
        "Contact person = the individual at the agency. Phone/fax/email belong to the agency. "
        "Underwriter office = address (street, city, state, zip). Do not put 'Monthly' or payment terms there."
    ),
    "named_insured": (
        "NAMED INSURED/APPLICANT = the business or person BUYING insurance. "
        "NOT the agent and NOT the carrier. "
        "Look for 'NAMED INSURED', 'APPLICANT', 'FIRST NAMED INSURED' labels. "
        "Their MAILING ADDRESS is separate from the producer/agent address. "
        "ZIP CODE is a 5-digit number (NOT a phone number). "
        "Occupancy = type of occupancy (e.g. owned, leased); do not put a full street address in an Occupancy field. Address fields get street/city/state/zip; Occupancy gets a single word or short phrase."
    ),
    "policy": (
        "POLICY fields: policy number, effective/expiration dates, "
        "status indicators (Quote/Bound/Issue/Cancel/Renew). Dates in MM/DD/YYYY. "
        "Policy_Status_EffectiveDate_A = the date in the STATUS OF / TRANSACTION block (next to Quote/Bound/Cancel). "
        "Policy_EffectiveDate_A = PROPOSED EFF DATE in the policy block (proposed effective date). Do NOT confuse the two. "
        "Policy_Status_EffectiveTime_A = TIME only as 4-digit HHMM (e.g. 1000 for 10:00 AM). NEVER put a date in a time field. "
        "EffectiveTime / ExpirationTime when they are TIME (not date): use 4-digit HHMM only. "
        "For any field with 'Indicator' in the name or schema type checkbox/radio: return only the string '1' (checked) or 'Off' (unchecked). Do not put dates, times, amounts, or addresses in these fields. "
        "Line of Business premium fields (e.g. GeneralLiabilityLineOfBusiness_TotalPremiumAmount_A) must be numeric dollar amounts only. LOB description or name goes in description fields, not in premium/amount fields."
    ),
    "driver": (
        "DRIVER fields from the driver table. Each row is one driver. "
        "Suffix _A = Driver #1, _B = Driver #2 ... _M = Driver #13. "
        "Use BBox row order (Y) for driver number and BBox X positions for columns: "
        "First Name (~200-280), City (~285-500), Last Name/State (~560-700), Zip (~700-780), Sex (~850), Marital Status, DOB (~1080-1160), % Use (Use Veh #), DOC (Driver Other Car), Broadened No-Fault, License# (~1500-1620), License State (~1830). "
        "Driver_Vehicle_UsePercent_* = percentage in '% Use' column (e.g. 100, 50). Driver_Coverage_DriverOtherCarCode_* and Driver_Coverage_BroadenedNoFaultCode_* = N/Y or 1/Off from DOC and Broadened No-Fault columns. "
        "Docling may merge first name+city or state+zip; prefer BBox for correct assignment. Do not put phone numbers or percentages in ZIP or License#; do not put ZIP in phone fields. Do NOT put % Use or ZIP in checkbox/indicator fields."
    ),
    "vehicle": (
        "VEHICLE fields: Year, Make, Model, VIN, body type, GVW, cost new, "
        "radius of use, garaging location. Suffixes _A-_E (127) or _A-_F (137). "
        "Business Auto Symbol and Indicator fields are checkboxes (1/Off); limits and deductibles are numeric."
    ),
    "coverage": (
        "COVERAGE fields: Business Auto symbols (1-9), liability limits, "
        "deductibles, physical damage, other coverages. "
        "Symbol values: 1=Any Auto, 2=Owned Autos Only, 7=Specifically Described, 8=Hired, 9=Non-Owned. "
        "Form 137: Vehicle_BusinessAutoSymbol_*Indicator and Vehicle_BusinessAutoSymbol_OtherSymbolCode are per vehicle row (_A to _F); use BBox to see which symbol column is marked. "
        "Business Auto Symbol and Indicator fields are CHECKBOXES: output only '1' or 'Off'. Limits and deductibles are numeric. "
        "For any field with 'Indicator' in the name or schema type checkbox/radio: return only '1' (checked) or 'Off' (unchecked). Do not put dates, times, amounts, or addresses in these fields."
    ),
    "checkbox": (
        "For any field with 'Indicator' in the name or schema type checkbox/radio: return only the string '1' (checked) or 'Off' (unchecked). "
        "Do not put dates, times, amounts, or addresses in these fields. "
        "CHECKBOX/INDICATOR fields: return ONLY '1' if checked (X, checkmark, filled box), 'Off' if unchecked or empty box. Never text or numbers."
    ),
    "location": (
        "LOCATION/PREMISES fields: physical address, city, state, zip of the insured business. "
        "ZIP is a 5-digit or 9-digit postal code, NOT a phone number. "
        "Occupancy = type of occupancy (e.g. owned, leased); do not put a full street address in an Occupancy field. Address fields get street/city/state/zip; Occupancy gets a single word or short phrase. "
        "In TABLES/SCHEDULES: the value for each field is the CELL CONTENT under the column header, NOT the header label. "
        "E.g. '#FULL TIME EMPL' and '#PART TIME EMPL' are column headers; the value is the number in that column (e.g. 30, 10). "
        "'$ANNUAL REVENUES:' is a label; the value is the dollar amount. 'OCCUPIED AREA' is a header; the value is the square footage number."
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
    section_scoped: bool = False,
    few_shot_examples: str = "",
) -> str:
    """
    Build a category-specific extraction prompt.

    Combines form layout, category hint, field tooltips, and dual OCR text.
    """
    layout = _layout_hint(form_type)
    cat_hint = _category_hint(category)
    section_note = (
        "The text below is limited to the relevant form section(s); use it together with BBox positions for correct field assignment."
        if section_scoped
        else ""
    )
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
{section_note}

=== FIELDS TO EXTRACT ===
{field_block}
{f"{chr(10)}{few_shot_examples}{chr(10)}" if few_shot_examples else ""}
=== DOCLING OCR TEXT (structured markdown) ===
{docling_text[:max_docling]}

=== BBOX OCR TEXT (with X,Y positions for spatial disambiguation) ===
{bbox_text[:max_bbox]}

{f"=== LABEL-VALUE PAIRS ==={chr(10)}{label_value_text[:2000]}" if label_value_text else ""}

CRITICAL RULES:
1. You MUST use EXACTLY the field key names shown above. Do NOT rename or invent keys.
2. Fill in the JSON template below - replace null with the extracted value (as a string).
3. If a field is blank/missing, remove it from output (do not return null or empty string).
4. Use BOTH OCR sources: Docling for structure, BBox for spatial positions. When the same information appears in both, BBox X,Y positions decide which field a value belongs to (e.g. status row, driver columns, LOB columns).
5. Dates: MM/DD/YYYY. Numbers: as strings.
6. {checkbox_rule or 'For checkboxes/indicators: "1" if checked, "Off" if not. NEVER put text in Indicator fields.'}
7. Do NOT paraphrase - use the exact text from the OCR.
8. ZIP codes are 5-digit numbers, NOT phone numbers. Phone numbers have dashes (xxx-xxx-xxxx).

Indicator/checkbox fields: output exactly "1" or "Off"; never text or numbers.

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
    few_shot_examples: str = "",
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
{f"{chr(10)}{few_shot_examples}{chr(10)}" if few_shot_examples else ""}
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
    few_shot_examples: str = "",
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
{f"{chr(10)}{few_shot_examples}{chr(10)}" if few_shot_examples else ""}
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
    few_shot_examples: str = "",
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
{f"{chr(10)}{few_shot_examples}{chr(10)}" if few_shot_examples else ""}
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


def build_vision_extraction_prompt(
    form_type: str,
    missing_fields: List[str],
    tooltips: Dict[str, str],
) -> str:
    """
    Prompt for a vision LLM: look at the form image(s) and extract the listed fields.
    Kept short so the model focuses on the image; tooltips give hints.
    """
    field_block = _format_fields_with_tooltips(missing_fields, tooltips)
    layout = _layout_hint(form_type)
    json_tmpl = _json_template(missing_fields)
    # List exact keys so the model can copy them
    keys_list = ", ".join(f'"{f}"' for f in missing_fields[:25])
    if len(missing_fields) > 25:
        keys_list += f", ... ({len(missing_fields)} total)"
    prompt = f"""Look at this scanned ACORD {form_type} form image and extract the requested fields.

=== LAYOUT ===
{layout}

=== FIELDS (copy these EXACT key names into your JSON) ===
{field_block}

RULES:
- Use ONLY the exact field names above (e.g. {keys_list}). Copy them character-for-character; do NOT use slashes (use underscores) or rename.
- Dates: MM/DD/YYYY. Checkboxes: "1" or "Off".
- Output ONLY valid JSON. No markdown, no ```, no explanation before or after.
- Include only keys you can read clearly from the image.

JSON (use these exact keys):
{json_tmpl}
"""
    return prompt


def build_vision_extraction_prompt_with_region_descriptions(
    form_type: str,
    missing_fields: List[str],
    tooltips: Dict[str, str],
    region_descriptions: List[str],
) -> str:
    """
    Prompt for main VLM when using describe-then-extract: the images attached are
    cropped regions; each region has a short description below. The model should
    use both the crop images and the descriptions to extract the requested fields.
    """
    field_block = _format_fields_with_tooltips(missing_fields, tooltips)
    layout = _layout_hint(form_type)
    json_tmpl = _json_template(missing_fields)
    keys_list = ", ".join(f'"{f}"' for f in missing_fields[:25])
    if len(missing_fields) > 25:
        keys_list += f", ... ({len(missing_fields)} total)"
    desc_block = "\n".join(region_descriptions)
    prompt = f"""The attached images are CROPPED REGIONS of an ACORD {form_type} form (in order: Region 1, Region 2, ...).
Use both the images and the descriptions below to extract the requested fields.

=== REGION DESCRIPTIONS ===
{desc_block}

=== LAYOUT HINT ===
{layout}

=== FIELDS (copy these EXACT key names into your JSON) ===
{field_block}

RULES:
- Use ONLY the exact field names above (e.g. {keys_list}).
- Dates: MM/DD/YYYY. Checkboxes: "1" or "Off".
- Output ONLY valid JSON. No markdown, no ```, no explanation.
- Use the region images and descriptions together to find each value.

JSON (use these exact keys):
{json_tmpl}
"""
    return prompt


def build_vision_unified_prompt(
    form_type: str,
    missing_fields: List[str],
    tooltips: Dict[str, str],
    docling_text: str,
    bbox_text: str,
    label_value_text: str = "",
    max_docling: int = 10000,
    max_bbox: int = 8000,
    max_lv: int = 3000,
) -> str:
    """
    Unified VLM prompt: use the attached form image(s) together with the Docling document
    and spatial/OCR text to fill the remaining fields. Schema-derived field list and
    tooltips tell the model exactly which keys to output.
    """
    layout = _layout_hint(form_type)
    field_block = _format_fields_with_tooltips(missing_fields, tooltips)
    json_tmpl = _json_template(missing_fields)
    keys_list = ", ".join(f'"{f}"' for f in missing_fields[:30])
    if len(missing_fields) > 30:
        keys_list += f", ... ({len(missing_fields)} total)"

    docling_block = (docling_text or "")[:max_docling]
    if len(docling_text or "") > max_docling:
        docling_block += "\n... [truncated]"

    bbox_block = (bbox_text or "")[:max_bbox]
    if len(bbox_text or "") > max_bbox:
        bbox_block += "\n... [truncated]"

    lv_block = (label_value_text or "")[:max_lv]
    if len(label_value_text or "") > max_lv:
        lv_block += "\n... [truncated]"

    prompt = f"""You are extracting data from a scanned ACORD {form_type} form. You have:
1. The FORM IMAGE(S) attached – use them as the primary source to read handwritten or unclear text.
2. The DOCLING DOCUMENT below – structured text from document layout analysis.
3. The SPATIAL/BBOX OCR below – positional text (label/value with coordinates) for disambiguation (e.g. status row, columns, LOB).
4. The LABEL-VALUE PAIRS – OCR-derived "label -> value" pairs.

Some fields were already filled using high-confidence spatial mapping. Your task is to fill ONLY the REMAINING fields listed below. Use the image + Docling + spatial info together. Output JSON with exactly the keys listed; use "1" or "Off" for checkboxes.

=== FORM LAYOUT ===
{layout}

=== DOCLING DOCUMENT (structured layout text) ===
{docling_block}

=== SPATIAL / BBOX OCR (positional text – use for column/row disambiguation) ===
{bbox_block}
"""
    if lv_block.strip():
        prompt += f"""
=== LABEL-VALUE PAIRS (OCR marker output) ===
{lv_block}
"""
    prompt += f"""
=== REMAINING FIELDS TO FILL (use these EXACT key names: {keys_list}) ===
{field_block}

RULES:
- Use ONLY the exact field names above. Copy them character-for-character.
- Dates: MM/DD/YYYY. Checkboxes/indicators: "1" or "Off" only.
- Output ONLY valid JSON. No markdown, no ```, no explanation.
- Prefer the form image when text is unclear; use Docling and BBox for structure and disambiguation.

JSON (use these exact keys):
{json_tmpl}
"""
    return prompt


def build_vision_checkbox_prompt(
    form_type: str,
    missing_fields: List[str],
    tooltips: Dict[str, str],
) -> str:
    """
    Prompt for a vision LLM: look at the form image and determine for each
    checkbox field whether it is checked or not. Optimized for checkbox-only extraction.
    """
    field_block = _format_fields_with_tooltips(missing_fields, tooltips)
    keys_list = ", ".join(f'"{f}"' for f in missing_fields[:30])
    if len(missing_fields) > 30:
        keys_list += f", ... ({len(missing_fields)} checkboxes total)"
    lines = ["{"]
    for i, name in enumerate(missing_fields):
        comma = "," if i < len(missing_fields) - 1 else ""
        lines.append(f'  "{name}": null{comma}  // "1" if checked, "Off" if not')
    lines.append("}")
    json_tmpl = "\n".join(lines)
    prompt = f"""Look at this ACORD {form_type} form image. Your task is ONLY to report whether each CHECKBOX below is CHECKED or NOT CHECKED.

Each field is a checkbox on the form. If the box has an X, checkmark, or is filled in, the value is "1". Otherwise the value is "Off".

=== CHECKBOX FIELDS (use these EXACT key names) ===
{field_block}

RULES:
- Use ONLY these exact field names: {keys_list}
- Value must be exactly "1" (checked) or "Off" (not checked). No other text.
- Output ONLY valid JSON. No markdown, no explanation.

JSON:
{json_tmpl}
"""
    return prompt


# ===========================================================================
# Phase 1: one-shot fill-nulls prompt (text LLM only)
# ===========================================================================

def build_fill_nulls_prompt(
    form_type: str,
    missing_fields: List[str],
    tooltips: Dict[str, str],
    docling_text: str,
    bbox_text: str,
    label_value_text: str = "",
    prefilled_summary: str = "",
    max_docling: int = 6000,
    max_bbox: int = 4000,
    max_lv: int = 2000,
) -> str:
    """
    One-shot prompt for Phase 1: given form text and label-value pairs,
    fill only the null keys. Use when prefill is strong and you want fewer LLM calls.
    """
    layout = _layout_hint(form_type)
    field_block = _format_fields_with_tooltips(missing_fields, tooltips)
    json_tmpl = _json_template(missing_fields)

    prompt = f"""You are filling missing fields on an ACORD {form_type} form. Some fields were already extracted (spatial/layout); you must fill ONLY the keys listed below using the form text.

=== FORM LAYOUT ===
{layout}

=== ALREADY FILLED (for context; do not change these) ===
{prefilled_summary[:1500] if prefilled_summary else "(none)"}

=== FIELDS YOU MUST FILL (replace null with value from form text) ===
{field_block}

=== DOCLING OCR TEXT ===
{docling_text[:max_docling]}

=== BBOX OCR TEXT (positions) ===
{bbox_text[:max_bbox]}

{f"=== LABEL-VALUE PAIRS ==={chr(10)}{label_value_text[:max_lv]}" if label_value_text else ""}

RULES:
- Use EXACTLY the field key names above. Return ONLY a JSON object with those keys.
- Replace null with the value found in the form text. If not found, omit the key.
- Dates: MM/DD/YYYY. Checkboxes: "1" or "Off".
- No markdown, no explanation. Valid JSON only.

JSON to fill:
{json_tmpl}
"""
    return prompt
