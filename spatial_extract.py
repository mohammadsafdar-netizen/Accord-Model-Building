#!/usr/bin/env python3
"""
Spatial Pre-Extraction: Extract high-confidence fields directly from BBox positions
====================================================================================
Bypasses the LLM for fields that can be reliably located using spatial layout rules
derived from the actual ACORD form templates.

Both ACORD 125 and 127 share the same header layout:
  Row 1 labels:   AGENCY (x<500)  |  CARRIER (x≈1300-1800)  |  NAIC CODE (x>2200)
  Row 1 values:   <agency name>   |  <carrier name>          |  <5-digit code>

This module detects and extracts:
  - Form completion date (top-right corner)
  - Carrier/Insurer name and NAIC code
  - Agency/Producer name
  - Policy number, effective date, expiration date
  - Named insured
  - Driver table rows (Form 127)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# ===========================================================================
# Dynamic label-finding helpers (robust to layout shifts)
# ===========================================================================

def _find_label(
    bbox_data: List[Dict],
    label_text: str,
    y_min: int = 0,
    y_max: int = 9999,
    x_min: int = 0,
    x_max: int = 9999,
) -> Optional[Dict]:
    """
    Find a label block matching the given text (case-insensitive).
    Uses substring matching so 'CARRIER' matches 'CARRIER' label.
    Returns the topmost match within the region, or None.
    """
    label_lower = label_text.lower()
    candidates = []
    for b in bbox_data:
        if y_min <= b["y"] <= y_max and x_min <= b["x"] <= x_max:
            text = b["text"].strip().lower()
            if label_lower == text or label_lower in text:
                candidates.append(b)
    if not candidates:
        return None
    # Return topmost match (lowest y)
    return min(candidates, key=lambda b: b["y"])


def _region_below_label(
    bbox_data: List[Dict],
    label: Optional[Dict],
    fallback_region: Tuple[int, int, int, int],
    y_offset: int = 20,
    y_range: int = 80,
    x_left: Optional[int] = None,
    x_right: Optional[int] = None,
) -> List[Dict]:
    """
    Find value blocks below a label. If label is None, use fallback_region.

    Args:
        label: The label bbox dict (or None for fallback).
        fallback_region: (x_min, x_max, y_min, y_max) used when label is None.
        y_offset: How far below the label Y to start searching.
        y_range: Height of the search window below y_offset.
        x_left/x_right: Override column boundaries (default: label_x-100 to label_x+800).
    """
    if label is None:
        return _find_in_region(bbox_data, *fallback_region)
    lx = label["x"]
    return _find_in_region(
        bbox_data,
        x_left if x_left is not None else max(0, lx - 100),
        x_right if x_right is not None else lx + 800,
        label["y"] + y_offset,
        label["y"] + y_offset + y_range,
    )


# ===========================================================================
# Region search helpers
# ===========================================================================

def _find_in_region(
    bbox_data: List[Dict],
    x_min: int, x_max: int,
    y_min: int, y_max: int,
    exclude_labels: bool = True,
) -> List[Dict]:
    """Find all bbox blocks within a rectangular region."""
    results = []
    for b in bbox_data:
        if x_min <= b["x"] <= x_max and y_min <= b["y"] <= y_max:
            text = b["text"].strip()
            if exclude_labels and _is_common_label(text):
                continue
            if text:
                results.append(b)
    return sorted(results, key=lambda b: (b["y"], b["x"]))


def _is_common_label(text: str) -> bool:
    """Check if text is a common form label (not a value)."""
    labels = {
        "agency", "carrier", "naic code", "naic", "code", "date",
        "policy number", "effective date", "expiration date",
        "named insured", "named insured(s)", "producer",
        "date (mmiddiyyyy)", "date (mm/dd/yyyy)", "company",
        "proposed eff date", "proposed exp date", "billing plan",
        "payment plan", "method of payment", "audit", "deposit",
        "premium", "minimum", "policy premium", "premium minimum",
        "applicant information section", "commercial insurance application",
        "business auto section", "agency customer id:", "agency customer id",
        "acord", "status of", "transaction", "underwriter",
        "underwriter office", "program code", "subcode",
        "name (first named insured) and mailing address (including zip+4)",
        "gl code", "sic", "naics", "fein or soc sec #",
        "coverages", "limits", "indicate lines of business",
        "company policy or program name",
    }
    return text.strip().lower() in labels


def _best_text(blocks: List[Dict], min_len: int = 1) -> Optional[str]:
    """Get the best (longest, highest confidence) text from blocks."""
    if not blocks:
        return None
    # Filter by min length
    valid = [b for b in blocks if len(b["text"].strip()) >= min_len]
    if not valid:
        return None
    # Prefer longer, higher confidence
    best = max(valid, key=lambda b: (len(b["text"].strip()), b.get("confidence", 0)))
    return best["text"].strip()


def _clean_amount(text: str) -> Optional[str]:
    """Clean OCR misreads in dollar amounts: S→$, trailing C/O→0."""
    # Remove leading S (OCR for $)
    text = text.strip()
    if text.startswith("S"):
        text = "$" + text[1:]
    if not text.startswith("$"):
        text = "$" + text
    # Fix trailing OCR misreads: C→0, O→0
    text = re.sub(r'[CO]$', '0', text)
    # Verify it looks like a valid amount
    if re.match(r'^\$[\d,]+\.?\d*$', text):
        return text
    return None


def _find_date_value(blocks: List[Dict]) -> Optional[str]:
    """Find a date-formatted value (MM/DD/YYYY) from blocks."""
    for b in blocks:
        text = b["text"].strip()
        # Match date patterns
        m = re.search(r'\d{1,2}/\d{1,2}/\d{4}', text)
        if m:
            return m.group(0)
    return None


def _find_naic(blocks: List[Dict]) -> Optional[str]:
    """Find a 5-digit NAIC code from blocks."""
    for b in blocks:
        text = b["text"].strip()
        if re.match(r'^\d{5}$', text):
            return text
    return None


def _find_policy_number(blocks: List[Dict]) -> Optional[str]:
    """Find a policy number (letters + digits, often with dash)."""
    for b in blocks:
        text = b["text"].strip()
        if re.match(r'^[A-Z]{1,4}-?\d{5,}$', text):
            return text
    return None


# ===========================================================================
# Form 125 spatial extraction
# ===========================================================================

def extract_125_header(page1_bbox: List[Dict]) -> Dict[str, Any]:
    """
    Pre-extract header fields from Form 125 page 1 using DYNAMIC label-finding.

    Strategy: Find label text first, then search relative to label position.
    Falls back to hardcoded regions if a label isn't found.
    This makes extraction robust to layout shifts across different scans.
    """
    result: Dict[str, Any] = {}

    # ---- Step 1: Discover label positions --------------------------------
    date_lbl = _find_label(page1_bbox, "DATE", y_max=300, x_min=1800)
    agency_lbl = _find_label(page1_bbox, "AGENCY", y_max=400, x_max=600)
    carrier_lbl = _find_label(page1_bbox, "CARRIER", y_max=400, x_min=900)
    naic_lbl = _find_label(page1_bbox, "NAIC CODE", y_max=400, x_min=1800)
    policy_lbl = _find_label(page1_bbox, "POLICY NUMBER", y_max=600, x_min=900)
    eff_lbl = _find_label(page1_bbox, "PROPOSED EFF DATE", y_min=1700, y_max=2000)
    exp_lbl = _find_label(page1_bbox, "PROPOSED EXP DATE", y_min=1700, y_max=2000)
    billing_lbl = _find_label(page1_bbox, "BILLING PLAN", y_min=1700, y_max=2000)
    payment_lbl = _find_label(page1_bbox, "PAYMENT PLAN", y_min=1700, y_max=2000)
    method_lbl = _find_label(page1_bbox, "METHOD OF PAYMENT", y_min=1700, y_max=2000)
    ni_name_lbl = _find_label(page1_bbox, "NAME (FIRST NAMED", y_min=1900, y_max=2200)

    # Column boundaries from discovered labels (with hardcoded defaults)
    carrier_x = carrier_lbl["x"] if carrier_lbl else 1366
    naic_x = naic_lbl["x"] if naic_lbl else 2347

    # ---- Step 2: Extract header values using label-relative regions ------

    # --- Form completion date (below DATE label) ---
    date_region = _region_below_label(
        page1_bbox, date_lbl, (2100, 2500, 100, 250),
        y_offset=20, y_range=80, x_left=2100, x_right=2500,
    )
    date_val = _find_date_value(date_region)
    if date_val:
        result["Form_CompletionDate_A"] = date_val

    # --- Carrier/Insurer (below CARRIER label, within carrier column) ---
    carrier_region = _region_below_label(
        page1_bbox, carrier_lbl, (1200, 2100, 250, 370),
        y_offset=20, y_range=100,
        x_left=carrier_x - 200, x_right=naic_x - 100,
    )
    carrier_name = _best_text(carrier_region, min_len=3)
    if carrier_name:
        carrier_name = carrier_name.rstrip("_").strip()
        result["Insurer_FullName_A"] = carrier_name

    # --- NAIC code (below NAIC CODE label, right column) ---
    naic_region = _region_below_label(
        page1_bbox, naic_lbl, (2200, 2500, 250, 370),
        y_offset=20, y_range=100,
        x_left=naic_x - 100, x_right=naic_x + 200,
    )
    naic = _find_naic(naic_region)
    if naic:
        result["Insurer_NAICCode_A"] = naic

    # --- Agency/Producer name (below AGENCY label, left column) ---
    agency_region = _region_below_label(
        page1_bbox, agency_lbl, (100, 600, 270, 370),
        y_offset=20, y_range=100,
        x_left=50, x_right=carrier_x - 200,
    )
    agency_name = _best_text(agency_region, min_len=3)
    if agency_name:
        result["Producer_FullName_A"] = agency_name

    # --- Policy number (below POLICY NUMBER label) ---
    policy_region = _region_below_label(
        page1_bbox, policy_lbl, (1200, 2000, 430, 520),
        y_offset=20, y_range=80,
        x_left=policy_lbl["x"] - 200 if policy_lbl else 1200,
        x_right=policy_lbl["x"] + 600 if policy_lbl else 2000,
    )
    policy_num = _find_policy_number(policy_region)
    if policy_num:
        result["Policy_PolicyNumberIdentifier_A"] = policy_num

    # --- Agent contact info (below agent name area) ---
    # Use agency label Y to anchor contact search region
    contact_y_base = (agency_lbl["y"] + 280) if agency_lbl else 540
    contact_region = _find_in_region(
        page1_bbox, 300, 700, contact_y_base, contact_y_base + 120,
    )
    for b in contact_region:
        text = b["text"].strip()
        # Phone number
        if re.match(r'\d{3}-\d{3}-\d{4}', text):
            if "Producer_ContactPerson_PhoneNumber_A" not in result:
                result["Producer_ContactPerson_PhoneNumber_A"] = text
            else:
                result["Producer_FaxNumber_A"] = text
        # Email
        elif "@" in text and "." in text:
            result["Producer_ContactPerson_EmailAddress_A"] = text

    # Agent contact person name (first block in contact region)
    agent_contact = _find_in_region(
        page1_bbox, 300, 600, contact_y_base - 5, contact_y_base + 35,
    )
    agent_name = _best_text(agent_contact, min_len=3)
    if agent_name:
        result["Producer_ContactPerson_FullName_A"] = agent_name

    # Email (may be on a lower row)
    email_region = _find_in_region(
        page1_bbox, 400, 900, contact_y_base + 80, contact_y_base + 130,
    )
    for b in email_region:
        text = b["text"].strip()
        if "@" in text and "." in text:
            result["Producer_ContactPerson_EmailAddress_A"] = text
            break

    # --- Producer address (between agency name and contact area) ---
    addr_y_base = (agency_lbl["y"] + 80) if agency_lbl else 340
    addr_region = _find_in_region(
        page1_bbox, 100, 1000, addr_y_base, addr_y_base + 130,
    )
    for b in addr_region:
        text = b["text"].strip()
        # City detection (lower portion of address block)
        if b["y"] > addr_y_base + 90 and b["x"] < 400:
            if re.match(r'^[A-Z][a-z]+$', text) and len(text) > 3:
                result["Producer_MailingAddress_CityName_A"] = text
        # State code
        if re.match(r'^[A-Z]{2}$', text) and b["x"] < 1100:
            result["Producer_MailingAddress_StateOrProvinceCode_A"] = text
        # Zip code - 5 digits near state
        m = re.search(r'\b(\d{5})\b', text)
        if m and b["y"] > addr_y_base + 90:
            result["Producer_MailingAddress_PostalCode_A"] = m.group(1)

    # --- Policy dates (below PROPOSED EFF/EXP DATE labels) ---
    eff_region = _region_below_label(
        page1_bbox, eff_lbl, (100, 450, 1920, 1980),
        y_offset=20, y_range=80,
        x_left=eff_lbl["x"] - 100 if eff_lbl else 100,
        x_right=eff_lbl["x"] + 300 if eff_lbl else 450,
    )
    eff_date = _find_date_value(eff_region)
    if eff_date:
        result["Policy_EffectiveDate_A"] = eff_date

    exp_region = _region_below_label(
        page1_bbox, exp_lbl, (450, 750, 1920, 1980),
        y_offset=20, y_range=80,
        x_left=exp_lbl["x"] - 100 if exp_lbl else 450,
        x_right=exp_lbl["x"] + 300 if exp_lbl else 750,
    )
    exp_date = _find_date_value(exp_region)
    if exp_date:
        result["Policy_ExpirationDate_A"] = exp_date

    # --- Billing and payment plans (below their labels) ---
    # Use neighboring labels to define tight column boundaries
    billing_x_left = (billing_lbl["x"] - 100) if billing_lbl else 700
    billing_x_right = (payment_lbl["x"] - 50) if payment_lbl else 1050
    billing_region = _region_below_label(
        page1_bbox, billing_lbl, (700, 1050, 1920, 1980),
        y_offset=20, y_range=80,
        x_left=billing_x_left, x_right=billing_x_right,
    )
    for b in billing_region:
        text = b["text"].strip()
        if text and text not in ("$", "S") and len(text) > 2:
            result["Billing_Plan"] = text
            break

    payment_x_left = (payment_lbl["x"] - 100) if payment_lbl else 1050
    payment_x_right = (method_lbl["x"] - 50) if method_lbl else 1400
    payment_region = _region_below_label(
        page1_bbox, payment_lbl, (1050, 1400, 1920, 1980),
        y_offset=20, y_range=80,
        x_left=payment_x_left, x_right=payment_x_right,
    )
    for b in payment_region:
        text = b["text"].strip()
        if text and text not in ("$", "S") and len(text) > 2:
            result["Payment_Plan"] = text
            break

    # --- Named Insured (below NAME label) ---
    if ni_name_lbl:
        insured_region = _find_in_region(
            page1_bbox, 100, 800,
            ni_name_lbl["y"] + 20, ni_name_lbl["y"] + 100,
        )
    else:
        insured_region = _find_in_region(page1_bbox, 100, 800, 2100, 2160)
    for b in insured_region:
        text = b["text"].strip()
        if re.match(r'^\d', text):
            continue
        if _is_common_label(text):
            continue
        if len(text) >= 3:
            result["NamedInsured_FullName_A"] = text
            break

    # Named insured address (anchored relative to NAME label)
    ni_city_y = (ni_name_lbl["y"] + 165) if ni_name_lbl else 2240
    ni_city = _find_in_region(page1_bbox, 100, 500, ni_city_y, ni_city_y + 60)
    for b in ni_city:
        text = b["text"].strip()
        if re.match(r'^[A-Z][a-z]+$', text) and len(text) > 3:
            result["NamedInsured_MailingAddress_CityName_A"] = text
            break

    ni_state = _find_in_region(page1_bbox, 900, 1200, ni_city_y, ni_city_y + 60)
    for b in ni_state:
        text = b["text"].strip()
        m = re.match(r'^([A-Z]{2})\s+(\d{5})', text)
        if m:
            result["NamedInsured_MailingAddress_StateOrProvinceCode_A"] = m.group(1)
            result["NamedInsured_MailingAddress_PostalCode_A"] = m.group(2)
            break

    # Tax ID (anchored relative to NAME label)
    tax_y = (ni_name_lbl["y"] + 25) if ni_name_lbl else 2100
    tax_region = _find_in_region(page1_bbox, 2100, 2500, tax_y, tax_y + 100)
    for b in tax_region:
        text = b["text"].strip()
        if re.match(r'^\d{2}-\d{7}$', text):
            result["NamedInsured_TaxIdentifier_A"] = text
            break

    # --- Lines of business detection ---
    lob_fields = _extract_125_lob(page1_bbox)
    result.update(lob_fields)

    # --- Policy status (y≈800-830) ---
    # FUTURE: Vision LLM will handle this much better

    return result


def _extract_125_lob(page1_bbox: List[Dict]) -> Dict[str, Any]:
    """
    Extract Lines of Business checkboxes and premiums from Form 125.
    
    Layout: y≈850-1250, three columns of LOBs.
    A LOB is "checked" if there's a dollar amount to its right.
    """
    result: Dict[str, Any] = {}

    # LOB name -> (field_name_indicator, field_name_premium)
    LOB_MAP = {
        "BOILER & MACHINERY": ("Policy_LineOfBusiness_BoilerAndMachineryIndicator_A", "BoilerAndMachineryLineOfBusiness_PremiumAmount_A"),
        "BUSINESS AUTO": ("Policy_LineOfBusiness_BusinessAutoIndicator_A", "CommercialVehicleLineOfBusiness_PremiumAmount_A"),
        "BUSINESS OWNERS": ("Policy_LineOfBusiness_BusinessOwnersIndicator_A", "BusinessOwnersLineOfBusiness_PremiumAmount_A"),
        "COMMERCIAL GENERAL LIABILITY": ("Policy_LineOfBusiness_CommercialGeneralLiability_A", "GeneralLiabilityLineOfBusiness_TotalPremiumAmount_A"),
        "COMMERCIAL INLAND MARINE": ("Policy_LineOfBusiness_CommercialInlandMarineIndicator_A", "CommercialInlandMarineLineOfBusiness_PremiumAmount_A"),
        "COMMERCIAL PROPERTY": ("Policy_LineOfBusiness_CommercialProperty_A", "CommercialPropertyLineOfBusiness_PremiumAmount_A"),
        "CRIME": ("Policy_LineOfBusiness_CrimeIndicator_A", "CrimeLineOfBusiness_PremiumAmount_A"),
        "CYBER AND PRIVACY": ("Policy_LineOfBusiness_CyberAndPrivacy_A", "CyberAndPrivacyLineOfBusiness_PremiumAmount_A"),
        "FIDUCIARY LIABILITY": ("Policy_LineOfBusiness_FiduciaryLiabilityIndicator_A", "FiduciaryLineOfBusiness_PremiumAmount_A"),
        "GARAGE AND DEALERS": ("Policy_LineOfBusiness_GarageAndDealersIndicator_A", "GarageAndDealersLineOfBusiness_PremiumAmount_A"),
        "LIQUOR LIABILITY": ("Policy_LineOfBusiness_LiquorLiabilityIndicator_A", "LiquorLiabilityLineOfBusiness_PremiumAmount_A"),
        "MOTOR CARRIER": ("Policy_LineOfBusiness_MotorCarrierIndicator_A", "MotorCarrierLineOfBusiness_PremiumAmount_A"),
        "TRUCKERS": ("Policy_LineOfBusiness_TruckersIndicator_A", "TruckersLineOfBusiness_PremiumAmount_A"),
        "UMBRELLA": ("Policy_LineOfBusiness_UmbrellaIndicator_A", "CommercialUmbrellaLineOfBusiness_PremiumAmount_A"),
        "YACHT": ("Policy_LineOfBusiness_YachtIndicator_A", "YachtLineOfBusiness_PremiumAmount_A"),
    }

    # Group bbox by rows in the LOB section (y≈900-1270)
    lob_blocks = [b for b in page1_bbox if 890 <= b["y"] <= 1270]
    if not lob_blocks:
        return result

    # Cluster into rows
    lob_blocks.sort(key=lambda b: b["y"])
    rows: List[List[Dict]] = []
    cur_row: List[Dict] = [lob_blocks[0]]
    cur_y = lob_blocks[0]["y"]
    for b in lob_blocks[1:]:
        if abs(b["y"] - cur_y) <= 30:
            cur_row.append(b)
        else:
            rows.append(sorted(cur_row, key=lambda b: b["x"]))
            cur_row = [b]
            cur_y = b["y"]
    if cur_row:
        rows.append(sorted(cur_row, key=lambda b: b["x"]))

    # Pre-process: find all bare "$" or "S" at checkbox column positions
    # Checkbox column 1: x ≈ 620-660 (left LOB column)
    # Checkbox column 2: x ≈ 1430-1460 (middle LOB column)
    # Checkbox column 3: x ≈ 2225-2260 (right LOB column)
    checkbox_positions = set()
    for b in lob_blocks:
        text = b["text"].strip()
        if text in ("$", "S") and (
            620 <= b["x"] <= 660 or 1430 <= b["x"] <= 1460 or 2225 <= b["x"] <= 2260
        ):
            # This is a checkbox marker at this Y position
            checkbox_positions.add((b["y"], b["x"]))

    for row in rows:
        avg_y = sum(b["y"] for b in row) / len(row)

        for lob_name, (indicator_field, premium_field) in LOB_MAP.items():
            for i, b in enumerate(row):
                if lob_name.lower() in b["text"].strip().lower():
                    lob_x = b["x"]

                    # Determine which checkbox column this LOB belongs to
                    if lob_x < 900:
                        checkbox_x_range = (620, 660)
                    elif lob_x < 1700:
                        checkbox_x_range = (1430, 1460)
                    else:
                        checkbox_x_range = (2225, 2260)

                    # Check if there's a "$" or "S" marker at this row's checkbox column
                    has_checkbox_marker = any(
                        abs(cy - avg_y) <= 30 and checkbox_x_range[0] <= cx <= checkbox_x_range[1]
                        for (cy, cx) in checkbox_positions
                    )

                    if has_checkbox_marker:
                        result[indicator_field] = "1"

                    # Look for premium amount to the right
                    premium_val = None
                    for j in range(i + 1, min(i + 4, len(row))):
                        raw = row[j]["text"].strip()
                        # Skip bare $ or S (checkbox markers)
                        if raw in ("$", "S"):
                            continue
                        # Dollar amount (may start with $ or S due to OCR)
                        cleaned = _clean_amount(raw)
                        if cleaned:
                            num = cleaned.replace("$", "").replace(",", "")
                            try:
                                if float(num) > 0:
                                    premium_val = cleaned
                                    break
                            except ValueError:
                                pass

                    if premium_val:
                        result[premium_field] = premium_val
                    break

    # Also detect policy status (y≈800-830)
    # Look for BOUND, QUOTE checkmarks
    status_blocks = [b for b in page1_bbox if 780 <= b["y"] <= 830]
    # These are usually too complex for spatial extraction, skip

    return result


# ===========================================================================
# Form 127 spatial extraction
# ===========================================================================

def extract_127_header(page1_bbox: List[Dict]) -> Dict[str, Any]:
    """
    Pre-extract header fields from Form 127 page 1 using DYNAMIC label-finding.

    Strategy: Find label text first, then search relative to label position.
    Falls back to hardcoded regions if a label isn't found.

    Layout: Two label rows:
      Row 1: AGENCY | CARRIER | NAIC CODE   (values one row below)
      Row 2: POLICY NUMBER | EFFECTIVE DATE | NAMED INSURED(S) (values one row below)
    """
    result: Dict[str, Any] = {}

    # ---- Step 1: Discover label positions --------------------------------
    date_lbl = _find_label(page1_bbox, "DATE", y_max=300, x_min=1800)
    agency_lbl = _find_label(page1_bbox, "AGENCY", y_max=400, x_max=600)
    carrier_lbl = _find_label(page1_bbox, "CARRIER", y_max=400, x_min=900)
    naic_lbl = _find_label(page1_bbox, "NAIC CODE", y_max=400, x_min=1800)
    policy_lbl = _find_label(page1_bbox, "POLICY NUMBER", y_max=500, x_max=600)
    eff_lbl = _find_label(page1_bbox, "EFFECTIVE DATE", y_max=500, x_min=900, x_max=1400)
    insured_lbl = _find_label(page1_bbox, "NAMED INSURED", y_max=500, x_min=1200)

    # Column boundaries from discovered labels
    carrier_x = carrier_lbl["x"] if carrier_lbl else 1366
    naic_x = naic_lbl["x"] if naic_lbl else 2347
    # Row 2 column boundaries
    eff_x = eff_lbl["x"] if eff_lbl else 1155
    insured_x = insured_lbl["x"] if insured_lbl else 1410

    # ---- Step 2: Extract header values -----------------------------------

    # --- Form completion date (below DATE label) ---
    date_region = _region_below_label(
        page1_bbox, date_lbl, (2100, 2500, 150, 260),
        y_offset=20, y_range=80, x_left=2100, x_right=2500,
    )
    date_val = _find_date_value(date_region)
    if date_val:
        result["Form_CompletionDate_A"] = date_val

    # --- Carrier/Insurer (below CARRIER label, carrier column) ---
    carrier_region = _region_below_label(
        page1_bbox, carrier_lbl, (1200, 2200, 300, 400),
        y_offset=20, y_range=80,
        x_left=carrier_x - 200, x_right=naic_x - 100,
    )
    carrier_name = _best_text(carrier_region, min_len=5)
    if carrier_name:
        carrier_name = carrier_name.rstrip("_").strip()
        result["Insurer_FullName_A"] = carrier_name

    # --- NAIC code (below NAIC CODE label, right column) ---
    naic_region = _region_below_label(
        page1_bbox, naic_lbl, (2200, 2500, 300, 400),
        y_offset=20, y_range=80,
        x_left=naic_x - 100, x_right=naic_x + 200,
    )
    naic = _find_naic(naic_region)
    if naic:
        result["Insurer_NAICCode_A"] = naic

    # --- Agency/Producer (below AGENCY label, left column) ---
    agency_region = _region_below_label(
        page1_bbox, agency_lbl, (100, 600, 310, 400),
        y_offset=20, y_range=80,
        x_left=50, x_right=carrier_x - 200,
    )
    agency_name = _best_text(agency_region, min_len=3)
    if agency_name:
        result["Producer_FullName_A"] = agency_name

    # --- Policy number (below POLICY NUMBER label) ---
    policy_region = _region_below_label(
        page1_bbox, policy_lbl, (100, 600, 420, 480),
        y_offset=20, y_range=80,
        x_left=policy_lbl["x"] - 100 if policy_lbl else 100,
        x_right=eff_x - 100,
    )
    policy_num = _find_policy_number(policy_region)
    if policy_num:
        result["Policy_PolicyNumberIdentifier_A"] = policy_num

    # --- Effective date (below EFFECTIVE DATE label) ---
    eff_region = _region_below_label(
        page1_bbox, eff_lbl, (1000, 1350, 420, 480),
        y_offset=20, y_range=80,
        x_left=eff_x - 100, x_right=insured_x - 50,
    )
    eff_date = _find_date_value(eff_region)
    if eff_date:
        result["Policy_EffectiveDate_A"] = eff_date

    # --- Named Insured (below NAMED INSURED label) ---
    insured_region = _region_below_label(
        page1_bbox, insured_lbl, (1350, 2200, 420, 480),
        y_offset=20, y_range=80,
        x_left=insured_x - 50, x_right=naic_x - 100,
    )
    insured_name = _best_text(insured_region, min_len=3)
    if insured_name:
        result["NamedInsured_FullName_A"] = insured_name

    return result


# ===========================================================================
# Form 137 spatial extraction
# ===========================================================================

def extract_137_header(page1_bbox: List[Dict]) -> Dict[str, Any]:
    """
    Pre-extract header fields from Form 137 page 1 using DYNAMIC label-finding.

    NOTE: 137 layout differs from 125/127!
      Row 1: AGENCY (left) | NAMED INSURED(S) (right)
      Row 2: POLICY NUMBER | EFFECTIVE DATE | CARRIER | NAIC CODE
    """
    result: Dict[str, Any] = {}

    # ---- Step 1: Discover label positions --------------------------------
    date_lbl = _find_label(page1_bbox, "DATE", y_max=300, x_min=1800)
    agency_lbl = _find_label(page1_bbox, "AGENCY", y_max=400, x_max=600)
    insured_lbl = _find_label(page1_bbox, "NAMED INSURED", y_max=400, x_min=1200)
    policy_lbl = _find_label(page1_bbox, "POLICY NUMBER", y_max=500, x_max=600)
    eff_lbl = _find_label(page1_bbox, "EFFECTIVE DATE", y_max=500, x_min=900, x_max=1400)
    carrier_lbl = _find_label(page1_bbox, "CARRIER", y_max=500, x_min=1200)
    naic_lbl = _find_label(page1_bbox, "NAIC CODE", y_max=500, x_min=1800)

    # Column boundaries
    insured_x = insured_lbl["x"] if insured_lbl else 1400
    eff_x = eff_lbl["x"] if eff_lbl else 1150
    carrier_mid_x = carrier_lbl["x"] if carrier_lbl else 1500
    naic_x = naic_lbl["x"] if naic_lbl else 2300

    # ---- Step 2: Extract header values -----------------------------------

    # --- Form completion date (below DATE label) ---
    date_region = _region_below_label(
        page1_bbox, date_lbl, (2100, 2500, 200, 270),
        y_offset=20, y_range=80, x_left=2100, x_right=2500,
    )
    date_val = _find_date_value(date_region)
    if date_val:
        result["Form_CompletionDate_A"] = date_val

    # --- Agency/Producer (below AGENCY label) ---
    agency_region = _region_below_label(
        page1_bbox, agency_lbl, (100, 600, 310, 400),
        y_offset=20, y_range=80,
        x_left=50, x_right=insured_x - 100,
    )
    agency_name = _best_text(agency_region, min_len=3)
    if agency_name:
        result["Producer_FullName_A"] = agency_name

    # --- Named Insured (below NAMED INSURED label, same row as AGENCY) ---
    insured_region = _region_below_label(
        page1_bbox, insured_lbl, (1300, 2200, 310, 400),
        y_offset=20, y_range=80,
        x_left=insured_x - 100, x_right=2400,
    )
    insured_name = _best_text(insured_region, min_len=3)
    if insured_name:
        insured_name = insured_name.replace(";", ",")
        result["NamedInsured_FullName_A"] = insured_name

    # --- Policy number (below POLICY NUMBER label) ---
    policy_region = _region_below_label(
        page1_bbox, policy_lbl, (100, 600, 420, 480),
        y_offset=20, y_range=80,
        x_left=policy_lbl["x"] - 100 if policy_lbl else 100,
        x_right=eff_x - 100,
    )
    policy_num = _find_policy_number(policy_region)
    if policy_num:
        result["Policy_PolicyNumberIdentifier_A"] = policy_num

    # --- Effective date (below EFFECTIVE DATE label) ---
    eff_region = _region_below_label(
        page1_bbox, eff_lbl, (1000, 1350, 420, 480),
        y_offset=20, y_range=80,
        x_left=eff_x - 100, x_right=carrier_mid_x - 50,
    )
    eff_date = _find_date_value(eff_region)
    if eff_date:
        result["Policy_EffectiveDate_A"] = eff_date

    # --- Carrier/Insurer (below CARRIER label, row 2) ---
    carrier_region = _region_below_label(
        page1_bbox, carrier_lbl, (1350, 2200, 420, 480),
        y_offset=20, y_range=80,
        x_left=carrier_mid_x - 150, x_right=naic_x - 100,
    )
    carrier_name = _best_text(carrier_region, min_len=3)
    if carrier_name:
        carrier_name = carrier_name.rstrip("_").strip()
        result["Insurer_FullName_A"] = carrier_name

    # --- NAIC code (below NAIC CODE label, far right) ---
    naic_region = _region_below_label(
        page1_bbox, naic_lbl, (2200, 2500, 420, 480),
        y_offset=20, y_range=80,
        x_left=naic_x - 100, x_right=naic_x + 200,
    )
    naic = _find_naic(naic_region)
    if naic:
        result["Insurer_NAICCode_A"] = naic

    # --- Agency Customer ID (top-right, y≈100-170) ---
    custid_lbl = _find_label(page1_bbox, "AGENCY CUSTOMER ID", y_max=200, x_min=1200)
    if custid_lbl:
        custid_region = _find_in_region(
            page1_bbox, custid_lbl["x"] + 100, 2500,
            custid_lbl["y"] - 20, custid_lbl["y"] + 40,
        )
    else:
        custid_region = _find_in_region(page1_bbox, 1800, 2500, 100, 170)
    for b in custid_region:
        text = b["text"].strip()
        if re.match(r'^\d{2}-\d{7}$', text):
            result["Producer_CustomerIdentifier_A"] = text
            break

    return result


# ===========================================================================
# Form 137 vehicle coverage extraction
# ===========================================================================

def extract_137_coverage(bbox_pages: List[List[Dict]]) -> Dict[str, Any]:
    """
    Extract vehicle coverage fields from Form 137 pages.
    
    Form 137 has up to 3 pages, each with the same coverage table layout
    but for different sections:
      Page 1 = Business Auto Section  → suffix _A
      Page 2 = Truckers Section       → suffix _B
      Page 3 = Motor Carrier Section  → suffix _C
    
    Uses a three-pass approach per page:
      1. LEFT SIDE scan (x<1300): liability amounts by label matching
      2. RIGHT SIDE scan (x>1400): physical damage deductibles by label matching
      3. BOTTOM section scan: hired/borrowed, non-owned, hired physical damage
    """
    result: Dict[str, Any] = {}

    # Page → suffix mapping
    page_suffix = {0: "_A", 1: "_B", 2: "_C"}

    for page_idx in range(min(3, len(bbox_pages))):
        page_data = bbox_pages[page_idx]
        if not page_data:
            continue
        suffix = page_suffix[page_idx]

        # Coverage table starts at y ≈ 500 on page 1, y ≈ 150 on pages 2-3
        min_y = 490 if page_idx == 0 else 150

        # === PASS 1: Left-side liability amounts ===
        result.update(_extract_137_left_coverage(page_data, suffix, min_y))

        # === PASS 2: Right-side physical damage deductibles ===
        result.update(_extract_137_right_coverage(page_data, suffix, min_y))

        # === PASS 3: Hired/Borrowed, Non-Owned, Hired Physical Damage ===
        result.update(_extract_137_hired_nonowned(page_data, suffix, min_y))

    return result


def _extract_137_left_coverage(
    page_data: List[Dict], suffix: str, min_y: int,
) -> Dict[str, Any]:
    """
    Extract left-side coverage amounts (LIABILITY, PD, MED PAY, UM).
    
    Uses a section-based approach:
      1. Find coverage label Y positions (LIABILITY, PROPERTY DAMAGE, etc.)
      2. Define section Y ranges between labels
      3. Collect all amounts (x≈1050-1260) within each section range
    
    This avoids row-clustering issues where labels and amounts can be
    on slightly different Y positions (up to 60px apart).
    """
    result: Dict[str, Any] = {}

    # --- Step 1: Find all amounts in the left-side value column ---
    amounts_with_y: List[Tuple[int, int]] = []
    for b in page_data:
        if b["y"] >= min_y and b["y"] <= 1400 and 1050 <= b["x"] <= 1260:
            text = b["text"].strip().replace(",", "").replace("$", "")
            # Skip OCR noise: "$", "S", single digits
            if text in ("S", "$", "5", "") or len(text) < 2:
                continue
            try:
                val = int(float(text))
                if val >= 100:
                    amounts_with_y.append((b["y"], val))
            except (ValueError, OverflowError):
                pass
    amounts_with_y.sort(key=lambda t: t[0])

    if not amounts_with_y:
        return result

    # --- Step 2: Find coverage label Y positions ---
    labels: Dict[str, int] = {}
    for b in page_data:
        if b["y"] >= min_y and b["y"] <= 1400 and b["x"] < 1050:
            text = b["text"].strip().upper()
            if text == "LIABILITY" and "liability" not in labels:
                labels["liability"] = b["y"]
            elif text == "PROPERTY DAMAGE" and "pd" not in labels:
                labels["pd"] = b["y"]
            elif text in ("MEDICAL", "PAYMENTS"):
                if "medpay" not in labels or b["y"] < labels["medpay"]:
                    labels["medpay"] = b["y"]
            elif text in ("UNINSURED", "MOTORIST"):
                if "um" not in labels or b["y"] < labels["um"]:
                    labels["um"] = b["y"]

    # --- Step 3: Define section Y ranges ---
    # Each section extends from (label_y - 80) to (next_label_y - 1)
    # The -80 captures amounts that appear above the label text
    ordered_sections = []
    if "liability" in labels:
        ordered_sections.append(("liability", labels["liability"]))
    if "pd" in labels:
        ordered_sections.append(("pd", labels["pd"]))
    if "medpay" in labels:
        ordered_sections.append(("medpay", labels["medpay"]))
    if "um" in labels:
        ordered_sections.append(("um", labels["um"]))
    ordered_sections.sort(key=lambda s: s[1])

    sections: List[Tuple[str, int, int]] = []
    for i, (name, label_y) in enumerate(ordered_sections):
        # First section starts 80px above its label
        # Subsequent sections start right after previous section ends
        if i == 0:
            y_start = label_y - 80
        else:
            y_start = sections[-1][2] + 1

        if i + 1 < len(ordered_sections):
            # Use midpoint between this label and the next as boundary
            next_y = ordered_sections[i + 1][1]
            y_end = (label_y + next_y) // 2
        else:
            y_end = label_y + 150
        sections.append((name, y_start, y_end))

    # --- Step 4: Assign amounts to sections ---
    for section_name, y_start, y_end in sections:
        section_amounts = [val for y, val in amounts_with_y if y_start <= y <= y_end]

        if section_name == "liability":
            if len(section_amounts) >= 2:
                result[f"Vehicle_BodilyInjury_PerPersonLimitAmount{suffix}"] = str(section_amounts[0])
                result[f"Vehicle_BodilyInjury_PerAccidentLimitAmount{suffix}"] = str(section_amounts[1])
            elif len(section_amounts) == 1:
                result[f"Vehicle_BodilyInjury_PerPersonLimitAmount{suffix}"] = str(section_amounts[0])

        elif section_name == "pd":
            if section_amounts:
                result[f"Vehicle_PropertyDamage_PerAccidentLimitAmount{suffix}"] = str(section_amounts[0])

        elif section_name == "medpay":
            if section_amounts:
                result[f"Vehicle_MedicalPayments_PerPersonLimitAmount{suffix}"] = str(section_amounts[0])

        elif section_name == "um":
            if len(section_amounts) >= 3:
                result[f"Vehicle_UninsuredMotorists_BodilyInjuryPerPersonLimitAmount{suffix}"] = str(section_amounts[0])
                result[f"Vehicle_UninsuredMotorists_BodilyInjuryPerAccidentLimitAmount{suffix}"] = str(section_amounts[1])
                result[f"Vehicle_UninsuredMotorists_PropertyDamagePerAccidentLimit{suffix}"] = str(section_amounts[2])
            elif len(section_amounts) == 2:
                result[f"Vehicle_UninsuredMotorists_BodilyInjuryPerPersonLimitAmount{suffix}"] = str(section_amounts[0])
                result[f"Vehicle_UninsuredMotorists_BodilyInjuryPerAccidentLimitAmount{suffix}"] = str(section_amounts[1])
            elif len(section_amounts) == 1:
                result[f"Vehicle_UninsuredMotorists_BodilyInjuryPerPersonLimitAmount{suffix}"] = str(section_amounts[0])

    return result


def _extract_137_right_coverage(
    page_data: List[Dict], suffix: str, min_y: int,
) -> Dict[str, Any]:
    """
    Extract right-side physical damage deductibles and towing limit.
    
    Uses a hybrid approach:
      1. Row-based label matching for TOWING, COMP, SPECIFIED, COLLISION
      2. Positional fallback: if SCOL label is OCR-corrupted, assign
         unmatched deductible between COMP and COLL as SCOL
    
    Note: On page 1, the right-side physical damage section extends
    further down (y≈800-1600) past the left-side coverage table, because
    the deductibles appear in a separate column below the main table.
    """
    result: Dict[str, Any] = {}

    # Right-side blocks: x > 1400, extended Y range for physical damage
    max_y = 1600 if suffix == "_A" else 1400
    right_blocks = [b for b in page_data
                    if b["y"] >= min_y and b["y"] <= max_y and b["x"] >= 1400]
    if not right_blocks:
        return result

    rows = _cluster_bbox_rows(right_blocks, tolerance=40)

    # Track Y positions for positional fallback
    comp_y: Optional[int] = None
    coll_y: Optional[int] = None
    matched_ys: set = set()  # Y positions of already-matched deductible rows

    for row in rows:
        row_text = " ".join(b["text"].strip().upper() for b in row)
        avg_y = int(sum(b["y"] for b in row) / len(row))

        # --- TOWING & LABOR ---
        if "TOWING" in row_text or ("LABOR" in row_text and avg_y < 1000):
            amounts = _get_amounts_in_xrange(row, 2050, 2250)
            if amounts:
                result[f"Vehicle_TowingAndLabour_LimitAmount{suffix}"] = str(amounts[-1])
                matched_ys.add(avg_y)
            continue

        # --- COMPREHENSIVE (COMP/OTC or standalone COMP) ---
        if ("COMP" in row_text and "COLL" not in row_text and "COLLISION" not in row_text):
            amounts = _get_amounts_in_xrange(row, 2200, 2450)
            if amounts and f"Vehicle_Comprehensive_DeductibleAmount{suffix}" not in result:
                result[f"Vehicle_Comprehensive_DeductibleAmount{suffix}"] = str(amounts[0])
                comp_y = avg_y
                matched_ys.add(avg_y)
            continue

        # --- SPECIFIED CAUSES OF LOSS ---
        if "SPECIFIED" in row_text and ("CAUSE" in row_text or "LOSS" in row_text):
            amounts = _get_amounts_in_xrange(row, 2200, 2450)
            if amounts:
                result[f"Vehicle_SpecifiedCauseOfLoss_DeductibleAmount{suffix}"] = str(amounts[-1])
                matched_ys.add(avg_y)
            continue

        # --- COLLISION ---
        if "COLLISION" in row_text or "COLL" in row_text:
            amounts = _get_amounts_in_xrange(row, 2200, 2450)
            if amounts and f"Vehicle_Collision_DeductibleAmount{suffix}" not in result:
                result[f"Vehicle_Collision_DeductibleAmount{suffix}"] = str(amounts[0])
                coll_y = avg_y
                matched_ys.add(avg_y)
            continue

    # --- Positional fallback for SCOL ---
    # If SCOL wasn't found by label but COMP and COLL were, look for an
    # unmatched deductible amount between their Y positions
    if f"Vehicle_SpecifiedCauseOfLoss_DeductibleAmount{suffix}" not in result \
       and comp_y is not None and coll_y is not None:
        for row in rows:
            avg_y = int(sum(b["y"] for b in row) / len(row))
            if comp_y < avg_y < coll_y and avg_y not in matched_ys:
                amounts = _get_amounts_in_xrange(row, 2200, 2450)
                if amounts:
                    result[f"Vehicle_SpecifiedCauseOfLoss_DeductibleAmount{suffix}"] = str(amounts[0])
                    break

    return result


def _extract_137_hired_nonowned(
    page_data: List[Dict], suffix: str, min_y: int,
) -> Dict[str, Any]:
    """
    Extract HIRED/BORROWED, NON-OWNED, and HIRED PHYSICAL DAMAGE fields.
    
    These appear in the bottom section of each page (y > 1300 on page 1,
    y > 900 on pages 2-3).
    
    Key positions:
      HIRED/BORROWED: state at x≈500-700, cost at x≈750-900
      NON-OWNED: employee/volunteer/partner counts at x≈1100-1200
      HIRED PHYSICAL DAMAGE: state at x≈1580-1700, #VEH at x≈1850-1920,
                              #DAYS at x≈1750-1830
    """
    result: Dict[str, Any] = {}

    # Bottom section starts lower on page 1 vs pages 2-3
    bottom_min_y = 1380 if suffix == "_A" else 950
    bottom_blocks = [b for b in page_data
                     if b["y"] >= bottom_min_y and b["y"] <= 1700]
    if not bottom_blocks:
        return result

    rows = _cluster_bbox_rows(bottom_blocks, tolerance=40)

    found_hired = False
    found_nonowned = False
    hired_row_idx = -1

    for row_idx, row in enumerate(rows):
        row_text = " ".join(b["text"].strip().upper() for b in row)

        # --- HIRED / BORROWED ---
        # The label row ("HIRED", "BORROWED") and the value row (state codes,
        # cost amount) are often on SEPARATE rows due to Y clustering.
        # So we mark the label row, then look for values on the SAME row
        # AND the next row.
        if "HIRED" in row_text and ("BORROWED" in row_text or "LIABILITY" in row_text) and \
           "PHYSICAL" not in row_text and "DAMAGE" not in row_text:
            found_hired = True
            hired_row_idx = row_idx
            # Try extracting values from this row first (in case labels+values are together)
            states, cost_val = _extract_hired_values(row)
            if states:
                result[f"Vehicle_HiredBorrowed_StateOrProvinceCode{suffix}"] = states[0]
            if cost_val:
                result[f"Vehicle_HiredBorrowed_HiredCostAmount{suffix}"] = cost_val
            continue

        # --- Value row(s) after HIRED label ---
        # Contains: NO/YES, state codes (NC, VA), cost (500), and
        # right-side Hired Physical Damage fields
        if found_hired and not found_nonowned and row_idx <= hired_row_idx + 2 \
           and "NON-OWNED" not in row_text and "NON OWNED" not in row_text:
            # Extract hired state + cost if not already found
            if f"Vehicle_HiredBorrowed_StateOrProvinceCode{suffix}" not in result or \
               f"Vehicle_HiredBorrowed_HiredCostAmount{suffix}" not in result:
                states, cost_val = _extract_hired_values(row)
                if states and f"Vehicle_HiredBorrowed_StateOrProvinceCode{suffix}" not in result:
                    result[f"Vehicle_HiredBorrowed_StateOrProvinceCode{suffix}"] = states[0]
                if cost_val and f"Vehicle_HiredBorrowed_HiredCostAmount{suffix}" not in result:
                    result[f"Vehicle_HiredBorrowed_HiredCostAmount{suffix}"] = cost_val

            # Hired Physical Damage: state at x≈1580-1720
            for b in row:
                text = b["text"].strip()
                if re.match(r'^[A-Z]{2}$', text) and text in _US_STATES and 1550 <= b["x"] <= 1720:
                    if f"Vehicle_HiredPhysicalDamage_StateOrProvinceCode{suffix}" not in result:
                        result[f"Vehicle_HiredPhysicalDamage_StateOrProvinceCode{suffix}"] = text
                        break

            # Hired Physical Damage: #VEH at x≈1860-1960, #DAYS at x≈1750-1850
            for b in row:
                text = b["text"].strip()
                if re.match(r'^\d{1,3}$', text):
                    if 1860 <= b["x"] <= 1970:
                        if f"Vehicle_HiredPhysicalDamage_VehicleCount{suffix}" not in result:
                            result[f"Vehicle_HiredPhysicalDamage_VehicleCount{suffix}"] = text
                    elif 1750 <= b["x"] <= 1860:
                        if f"Vehicle_HiredPhysicalDamage_DayCount{suffix}" not in result:
                            result[f"Vehicle_HiredPhysicalDamage_DayCount{suffix}"] = text
            continue

        # --- NON-OWNED ---
        if "NON-OWNED" in row_text or "NON OWNED" in row_text:
            found_nonowned = True
            # Employee count: look for number at x≈1100-1200
            for b in sorted(row, key=lambda b: b["x"]):
                text = b["text"].strip()
                if re.match(r'^\d+$', text) and 1100 <= b["x"] <= 1200:
                    # Check if EMPLOYEES label is in the row
                    if "EMPLOYEE" in row_text:
                        result[f"Vehicle_NonOwnedGroup_EmployeeCount{suffix}"] = text
                    break

            # Volunteer count (if VOLUNTEERS label in same row)
            if "VOLUNTEER" in row_text:
                # Find the numeric value closest to VOLUNTEERS label
                vol_idx = None
                for i, b in enumerate(row):
                    if "VOLUNTEER" in b["text"].strip().upper():
                        vol_idx = i
                        break
                if vol_idx is not None:
                    vol_count = _find_next_number(row, vol_idx, x_range=(1100, 1200))
                    if vol_count:
                        result[f"Vehicle_NonOwnedGroup_VolunteerCount{suffix}"] = vol_count
            continue

        # --- EMPLOYEE/VOLUNTEER counts on their own rows ---
        if "EMPLOYEE" in row_text and found_nonowned:
            emp = _find_next_number(row, 0, x_range=(1100, 1200))
            if emp:
                result[f"Vehicle_NonOwnedGroup_EmployeeCount{suffix}"] = emp
            # Volunteer count may be on the same row
            if "VOLUNTEER" in row_text:
                vol = None
                # If both labels present, employees at x≈1138, volunteers at x≈1125
                # Use position to disambiguate
                nums_in_range = [(b["x"], b["text"].strip()) for b in row
                                 if 1100 <= b["x"] <= 1200 and re.match(r'^\d+$', b["text"].strip())]
                nums_in_range.sort(key=lambda t: t[0])
                if len(nums_in_range) >= 2:
                    # First number = volunteers (lower x), second = employees (higher x)
                    result[f"Vehicle_NonOwnedGroup_VolunteerCount{suffix}"] = nums_in_range[0][1]
                    result[f"Vehicle_NonOwnedGroup_EmployeeCount{suffix}"] = nums_in_range[1][1]
                elif len(nums_in_range) == 1:
                    result[f"Vehicle_NonOwnedGroup_EmployeeCount{suffix}"] = nums_in_range[0][1]
            continue

        if "VOLUNTEER" in row_text and found_nonowned:
            vol = _find_next_number(row, 0, x_range=(1100, 1200))
            if vol:
                result[f"Vehicle_NonOwnedGroup_VolunteerCount{suffix}"] = vol
            continue

        # --- PARTNERS ---
        if "PARTNER" in row_text:
            part_count = _find_next_number(row, 0, x_range=(1100, 1200))
            if part_count:
                result[f"Vehicle_NonOwnedGroup_PartnerCount{suffix}"] = part_count
            continue

    return result


def _extract_hired_values(row: List[Dict]) -> Tuple[List[str], Optional[str]]:
    """Extract state codes and cost of hire from a hired/borrowed row."""
    states: List[str] = []
    cost_val: Optional[str] = None
    for b in sorted(row, key=lambda b: b["x"]):
        text = b["text"].strip()
        # State codes at x≈450-750
        if re.match(r'^[A-Z]{2}$', text) and text in _US_STATES and 450 <= b["x"] <= 750:
            if text not in states:
                states.append(text)
        # Cost of hire at x≈750-870
        if 750 <= b["x"] <= 870 and cost_val is None:
            m = re.match(r'^[\d,]+$', text)
            if m:
                val = text.replace(",", "")
                try:
                    if int(val) > 0:
                        cost_val = val
                except ValueError:
                    pass
    return states, cost_val


def _cluster_bbox_rows(blocks: List[Dict], tolerance: int = 35) -> List[List[Dict]]:
    """Cluster bbox blocks into rows based on Y proximity."""
    if not blocks:
        return []
    sorted_blocks = sorted(blocks, key=lambda b: b["y"])
    rows: List[List[Dict]] = []
    cur_row: List[Dict] = [sorted_blocks[0]]
    cur_y = sorted_blocks[0]["y"]
    for b in sorted_blocks[1:]:
        if abs(b["y"] - cur_y) <= tolerance:
            cur_row.append(b)
            cur_y = sum(bb["y"] for bb in cur_row) / len(cur_row)
        else:
            rows.append(sorted(cur_row, key=lambda b: b["x"]))
            cur_row = [b]
            cur_y = b["y"]
    if cur_row:
        rows.append(sorted(cur_row, key=lambda b: b["x"]))
    return rows


def _get_amounts_in_xrange(row: List[Dict], x_min: int, x_max: int) -> List[int]:
    """Extract numeric amounts from blocks in a given X range, sorted by X."""
    amounts = []
    for b in sorted(row, key=lambda b: b["x"]):
        if x_min <= b["x"] <= x_max:
            text = b["text"].strip()
            # Skip labels and symbols
            if text in ("$", "S", "5", "BA", "PER", "peR", "pER"):
                continue
            # Clean and parse numeric
            cleaned = text.replace(",", "").replace("$", "").replace("S", "")
            try:
                val = int(float(cleaned))
                if val > 0:
                    amounts.append(val)
            except (ValueError, OverflowError):
                pass
    return amounts


def _find_next_number(row: List[Dict], after_idx: int, x_range: Tuple[int, int] = (1050, 1200)) -> Optional[str]:
    """Find the next numeric value in a row after a given index, within X range."""
    for b in sorted(row, key=lambda b: b["x"]):
        if b["x"] >= x_range[0] and b["x"] <= x_range[1]:
            text = b["text"].strip()
            if re.match(r'^\d+$', text):
                return text
    return None


# ===========================================================================
# Driver table extraction (Form 127)
# ===========================================================================

def extract_127_drivers(page1_bbox: List[Dict]) -> Dict[str, Any]:
    """
    Extract driver table rows from Form 127 page 1 using precise X positions.
    
    Column positions (from actual OCR analysis):
      x ≈ 127-130:  Driver # (row number)
      x ≈ 239-274:  First Name (GivenName)
      x ≈ 291-320:  City
      x ≈ 596-660:  Last Name (Surname) 
      x ≈ 608:      State (always 2-letter, overlaps with surname X range)
      x ≈ 706-710:  Zip code (5 digits)
      x ≈ 885-893:  Sex (M/F)
      x ≈ 950-955:  Marital Status
      x ≈ 1110-1125: Date of Birth
      x ≈ 1289-1293: Years Experience
      x ≈ 1376-1380: Year Licensed
      x ≈ 1527-1585: License Number / Other IDs
    
    Driver rows span y ≈ 700-2000, each row ~80-120 pixels apart.
    """
    result: Dict[str, Any] = {}

    # Find driver table region (y between DRIVER INFORMATION header and GENERAL INFORMATION)
    driver_blocks = [b for b in page1_bbox if 700 <= b["y"] <= 2050]
    if not driver_blocks:
        return result

    # Cluster into rows
    driver_blocks.sort(key=lambda b: b["y"])
    rows: List[List[Dict]] = []
    cur_row: List[Dict] = [driver_blocks[0]]
    cur_y = driver_blocks[0]["y"]
    for b in driver_blocks[1:]:
        if abs(b["y"] - cur_y) <= 35:
            cur_row.append(b)
            cur_y = sum(bb["y"] for bb in cur_row) / len(cur_row)
        else:
            if len(cur_row) >= 3:  # Valid data rows have at least 3 blocks
                rows.append(sorted(cur_row, key=lambda b: b["x"]))
            cur_row = [b]
            cur_y = b["y"]
    if len(cur_row) >= 3:
        rows.append(sorted(cur_row, key=lambda b: b["x"]))

    # Skip header row(s) - rows with mostly label text
    data_rows = []
    for row in rows:
        # Check if this looks like a data row (has numeric/date values)
        has_data = any(
            re.match(r'\d{2}/\d{2}/\d{4}', b["text"].strip()) or  # DOB
            re.match(r'^[MF]$', b["text"].strip()) or  # Sex
            re.match(r'^\d{5}$', b["text"].strip())  # Zip
            for b in row
        )
        if has_data:
            data_rows.append(row)

    # Map each data row to a driver number
    suffixes = "ABCDEFGHIJKLM"
    for driver_idx, row in enumerate(data_rows):
        if driver_idx >= 13:
            break
        suffix = suffixes[driver_idx]

        # Extract fields from each block based on X position
        parsed = _parse_driver_row(row)

        # Map to field names
        field_map = {
            "given_name": f"Driver_GivenName_{suffix}",
            "surname": f"Driver_Surname_{suffix}",
            "city": f"Driver_MailingAddress_CityName_{suffix}",
            "state": f"Driver_MailingAddress_StateOrProvinceCode_{suffix}",
            "zip": f"Driver_MailingAddress_PostalCode_{suffix}",
            "sex": f"Driver_GenderCode_{suffix}",
            "marital": f"Driver_MaritalStatusCode_{suffix}",
            "dob": f"Driver_BirthDate_{suffix}",
            "years_exp": f"Driver_ExperienceYearCount_{suffix}",
            "year_licensed": f"Driver_LicensedYear_{suffix}",
            "license_num": f"Driver_LicenseNumberIdentifier_{suffix}",
            "license_state": f"Driver_LicensedStateOrProvinceCode_{suffix}",
            "tax_id": f"Driver_TaxIdentifier_{suffix}",
        }

        for key, field_name in field_map.items():
            val = parsed.get(key)
            if val:
                result[field_name] = val

    return result


def _parse_driver_row(row: List[Dict]) -> Dict[str, str]:
    """
    Parse a single driver row into named fields using X-position ranges.
    
    This is the core spatial disambiguation logic.
    """
    parsed: Dict[str, str] = {}

    for b in row:
        x = b["x"]
        text = b["text"].strip()
        if not text:
            continue

        # Driver # (x < 180)
        if x < 180 and re.match(r'^\d{1,2}$', text):
            parsed["driver_num"] = text
            continue

        # First Name (x ≈ 200-290, but NOT a city name or number)
        if 190 <= x <= 290:
            # Distinguish first name from city
            # First names: x closer to 240-275, typically shorter
            # Cities: x closer to 290-320, often longer
            # Handle multi-word names like "David French"
            if x <= 280 and _is_person_name_or_multi(text):
                parsed["given_name"] = text
            elif x > 275 or _is_city_name(text):
                parsed["city"] = text
            elif _is_person_name_or_multi(text):
                parsed["given_name"] = text
            else:
                parsed["city"] = text
            continue

        # City (x ≈ 290-500)
        if 285 <= x <= 500:
            if _is_city_name(text):
                parsed["city"] = text
            elif _is_person_name_or_multi(text) and "given_name" not in parsed:
                # Sometimes OCR merges name+city as one text block
                parsed["given_name"] = text
            continue

        # State / Surname region (x ≈ 560-700)
        if 560 <= x <= 700:
            # State code: exactly 2 uppercase letters
            if re.match(r'^[A-Z]{2}$', text) and text in _US_STATES:
                parsed["state"] = text
            elif _is_person_name(text):
                parsed["surname"] = text
            continue

        # Zip (x ≈ 700-780)
        if 695 <= x <= 780:
            if re.match(r'^\d{5}$', text):
                parsed["zip"] = text
            continue

        # Sex (x ≈ 850-920)
        if 850 <= x <= 930:
            if text in ("M", "F"):
                parsed["sex"] = text
            continue

        # Marital status (x ≈ 940-970)
        if 935 <= x <= 975:
            if text in ("S", "M", "D", "W"):
                parsed["marital"] = text
            continue

        # DOB (x ≈ 1080-1160)
        if 1080 <= x <= 1160:
            m = re.search(r'\d{2}/\d{2}/\d{4}', text)
            if m:
                parsed["dob"] = m.group(0)
            continue

        # Years experience (x ≈ 1270-1310)
        if 1270 <= x <= 1310:
            if re.match(r'^\d{1,2}$', text):
                parsed["years_exp"] = text
            continue

        # Year licensed (x ≈ 1360-1400)
        if 1360 <= x <= 1400:
            if re.match(r'^\d{4}$', text):
                parsed["year_licensed"] = text
            continue

        # License number (x ≈ 1500-1620)
        if 1500 <= x <= 1620:
            # License numbers are alphanumeric, often with dashes
            if re.match(r'^[A-Z]{2}-\d+$', text) or re.match(r'^[A-Z]?\d{6,}$', text):
                if "license_num" not in parsed:
                    parsed["license_num"] = text
            # Also capture license state from state-prefixed numbers
            m = re.match(r'^([A-Z]{2})-(\d+)$', text)
            if m:
                parsed["license_state"] = m.group(1)
                parsed["license_num"] = text
            continue

        # Tax ID (x ≈ 1520-1600, format NN-NNNNNNN)
        if 1520 <= x <= 1610:
            if re.match(r'^\d{2}-\d{7}$', text):
                parsed["tax_id"] = text
            continue

        # License STATE (far right column, x ≈ 1830-1900)
        if 1830 <= x <= 1920:
            if re.match(r'^[A-Z]{2}$', text) and text in _US_STATES:
                parsed["license_state"] = text
            continue

    return parsed


def _is_person_name(text: str) -> bool:
    """Check if text looks like a person's first or last name (single word)."""
    if not text or len(text) < 2:
        return False
    # Person names: capitalized, alphabetic, not a known city/state
    if not re.match(r'^[A-Z][a-z]+$', text):
        return False
    if text.lower() in _KNOWN_CITIES:
        return False
    return True


def _is_person_name_or_multi(text: str) -> bool:
    """Check if text is a person name, possibly multi-word like 'David French'."""
    if _is_person_name(text):
        return True
    # Multi-word name: "FirstName LastName" pattern
    parts = text.split()
    if len(parts) >= 2 and all(re.match(r'^[A-Z][a-z]+$', p) for p in parts):
        # Not a city name
        if text.lower() not in _KNOWN_CITIES:
            return True
    return False


def _is_city_name(text: str) -> bool:
    """Check if text looks like a city name."""
    return text.lower() in _KNOWN_CITIES or (
        len(text) > 5 and re.match(r'^[A-Z][a-z]+$', text) and text.lower() not in _COMMON_NAMES
    )


_KNOWN_CITIES = {
    "indianapolis", "greenfield", "columbus", "chicago", "boston",
    "new york", "los angeles", "houston", "phoenix", "philadelphia",
    "san antonio", "san diego", "dallas", "jacksonville", "austin",
    "fort worth", "charlotte", "san francisco", "seattle", "denver",
    "nashville", "oklahoma", "portland", "tucson", "albuquerque",
    "springfield", "richmond", "raleigh", "memphis", "louisville",
    "milwaukee", "baltimore", "pittsburgh", "sacramento", "mesa",
    "atlanta", "omaha", "miami", "minneapolis", "tampa",
    "cleveland", "cincinnati", "orlando",
}

_COMMON_NAMES = {
    "thomas", "lisa", "bruce", "patrick", "daniel", "jacob", "alicia",
    "kristen", "david", "kristina", "mark", "kevin", "john", "james",
    "robert", "michael", "william", "mary", "jennifer", "linda",
    "elizabeth", "barbara", "susan", "jessica", "sarah", "karen",
    "nancy", "betty", "margaret", "sandra", "ashley", "dorothy",
}

_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


# ===========================================================================
# Public API
# ===========================================================================

def spatial_preextract(
    form_type: str,
    bbox_pages: List[List[Dict]],
) -> Dict[str, Any]:
    """
    Run spatial pre-extraction for a given form type.
    
    Returns {field_name: value} for high-confidence fields.
    """
    if not bbox_pages:
        return {}

    page1 = bbox_pages[0] if len(bbox_pages) > 0 else []

    if form_type == "125":
        return extract_125_header(page1)
    elif form_type == "127":
        header = extract_127_header(page1)
        drivers = extract_127_drivers(page1)
        header.update(drivers)
        return header
    elif form_type == "137":
        header = extract_137_header(page1)
        coverage = extract_137_coverage(bbox_pages)
        header.update(coverage)
        return header
    else:
        return {}
