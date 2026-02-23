"""Entity-to-field mapping for ACORD Form 163 (Commercial Auto / Driver Schedule).

Form 163 uses generic field names (TextNN[0]) rather than semantic names.
Driver table: 24 rows × 20 TextNN columns + 1 marital status field per row.

Field layout per driver row:
  Offset 0: driver_num     Offset 10: years_licensed
  Offset 1: first_name     Offset 11: year_licensed
  Offset 2: middle_initial Offset 12: license_number
  Offset 3: last_name      Offset 13: ssn
  Offset 4: address        Offset 14: license_state
  Offset 5: city           Offset 15: date_hired
  Offset 6: state          Offset 16: flag1
  Offset 7: zip            Offset 17: flag2
  Offset 8: sex            Offset 18: vehicle_num
  Offset 9: dob            Offset 19: pct_use

  Marital status: marital[0] (row 1), maritalstatusN[0] (rows 2-24, N=1..23)

Driver 1 starts at Text15[0], each subsequent driver increments by 20.
"""

from typing import Dict, List
from Custom_model_fa_pf.entity_schema import CustomerSubmission

MAX_DRIVERS = 24
_BASE_FIELD = 15
_FIELDS_PER_ROW = 20

# Column name → offset within driver row
_COL_OFFSETS = {
    "driver_num": 0,
    "first_name": 1,
    "middle_initial": 2,
    "last_name": 3,
    "address": 4,
    "city": 5,
    "state": 6,
    "zip": 7,
    "sex": 8,
    "dob": 9,
    "years_licensed": 10,
    "year_licensed": 11,
    "license_number": 12,
    "ssn": 13,
    "license_state": 14,
    "date_hired": 15,
    "flag1": 16,
    "flag2": 17,
    "vehicle_num": 18,
    "pct_use": 19,
}


def _build_row_map() -> List[Dict[str, str]]:
    """Build the 24-row driver field lookup table."""
    rows = []
    for row_idx in range(MAX_DRIVERS):
        base = _BASE_FIELD + row_idx * _FIELDS_PER_ROW
        row = {col: f"Text{base + offset}[0]" for col, offset in _COL_OFFSETS.items()}
        # Marital status is a separate field series
        if row_idx == 0:
            row["marital_status"] = "marital[0]"
        else:
            row["marital_status"] = f"maritalstatus{row_idx}[0]"
        rows.append(row)
    return rows


DRIVER_ROW_MAP = _build_row_map()


def map_fields(submission: CustomerSubmission) -> Dict[str, str]:
    """Map extracted entities to Form 163 field names.

    Args:
        submission: Extracted customer submission data

    Returns:
        Dict of field_name -> value for Form 163
    """
    fields: Dict[str, str] = {}

    # --- Header: Named Insured ---
    biz = submission.business
    if biz:
        if biz.business_name:
            fields["Text13[0]"] = biz.business_name

        addr = biz.mailing_address
        if addr:
            addr_parts = []
            if addr.line_one:
                addr_parts.append(addr.line_one)
            if addr.line_two:
                addr_parts.append(addr.line_two)
            city_state = ""
            if addr.city:
                city_state = addr.city
            if addr.state:
                city_state += f", {addr.state}" if city_state else addr.state
            if addr.zip_code:
                city_state += f" {addr.zip_code}" if city_state else addr.zip_code
            if city_state:
                addr_parts.append(city_state)
            if addr_parts:
                fields["Text14[0]"] = "\n".join(addr_parts)

    # --- Header: Producer ---
    prod = submission.producer
    if prod:
        if prod.agency_name:
            fields["Text8[0]"] = prod.agency_name

        p_addr = prod.mailing_address
        if p_addr:
            if p_addr.line_one:
                fields["Text9[0]"] = p_addr.line_one
            if p_addr.city:
                fields["Text2[0]"] = p_addr.city
            if p_addr.state:
                fields["Text4[0]"] = p_addr.state
            if p_addr.zip_code:
                fields["Text3[0]"] = p_addr.zip_code

    # --- Header: Policy ---
    pol = submission.policy
    if pol and pol.effective_date:
        fields["Text1[0]"] = pol.effective_date

    # --- Driver rows ---
    for i, driver in enumerate(submission.drivers[:MAX_DRIVERS]):
        row = DRIVER_ROW_MAP[i]

        fields[row["driver_num"]] = str(i + 1)

        first = driver.get_first_name()
        last = driver.get_last_name()
        if first:
            fields[row["first_name"]] = first
        if last:
            fields[row["last_name"]] = last
        if driver.middle_initial:
            fields[row["middle_initial"]] = driver.middle_initial

        if driver.sex:
            fields[row["sex"]] = driver.sex
        if driver.marital_status:
            fields[row["marital_status"]] = driver.marital_status
        if driver.dob:
            fields[row["dob"]] = driver.dob
        if driver.license_number:
            fields[row["license_number"]] = driver.license_number
        if driver.license_state:
            fields[row["license_state"]] = driver.license_state
        if driver.hire_date:
            fields[row["date_hired"]] = driver.hire_date
        if driver.years_experience:
            fields[row["years_licensed"]] = driver.years_experience
        if driver.licensed_year:
            fields[row["year_licensed"]] = driver.licensed_year

        # Driver mailing address
        d_addr = driver.mailing_address
        if d_addr:
            if d_addr.line_one:
                fields[row["address"]] = d_addr.line_one
            if d_addr.city:
                fields[row["city"]] = d_addr.city
            if d_addr.state:
                fields[row["state"]] = d_addr.state
            if d_addr.zip_code:
                fields[row["zip"]] = d_addr.zip_code

    return fields
