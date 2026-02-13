"""
Value Normalizer — Post-extraction cleanup for field values.
============================================================
High-impact accuracy: consistent checkbox/date/money/phone normalization
and label stripping so extracted values match ground-truth format.

Handles:
  - Checkbox normalization (true/false, 1/Off matching GT)
  - Date normalization (MM/DD/YYYY)
  - Label prefix stripping
  - OCR error correction for monetary values
  - Phone/email cleanup
  - General text cleanup
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Set


def normalize_all(
    extracted: Dict[str, Any],
    field_types: Dict[str, str],
    checkbox_fields: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Normalize all extracted field values based on their types.

    Args:
        extracted: {field_name: raw_value}
        field_types: {field_name: 'text'|'checkbox'|'radio'}
        checkbox_fields: optional set of field names that are checkboxes (overrides field_types)

    Returns:
        Normalized dict with cleaned values.
    """
    result: Dict[str, Any] = {}
    checkboxes = checkbox_fields or set()
    for name, ftype in field_types.items():
        if ftype in ("checkbox", "radio"):
            checkboxes.add(name)

    for field_name, value in extracted.items():
        ftype = field_types.get(field_name, "text")
        if field_name in checkboxes:
            ftype = "checkbox"
        result[field_name] = normalize_value(value, ftype, field_name)
    return result


def normalize_value(value: Any, field_type: str, field_name: str) -> Any:
    """Normalize a single extracted value based on its field type."""
    if value is None:
        return None

    str_val = str(value).strip()
    if not str_val or str_val.lower() in ("null", "none", "n/a", "na", ""):
        return None

    if field_type == "checkbox":
        return normalize_checkbox(str_val)

    str_val = strip_label_prefixes(str_val, field_name)

    if is_date_field(field_name):
        normalized = normalize_date(str_val)
        if normalized:
            return normalized

    if is_monetary_field(field_name):
        return fix_ocr_monetary(str_val)

    if is_phone_field(field_name):
        return fix_ocr_phone(str_val)

    return clean_text(str_val)


def normalize_checkbox(value: str) -> Any:
    """
    Normalize checkbox to '1' (checked) or 'Off' (unchecked) for ACORD schema consistency.
    """
    val_lower = str(value).strip().lower()
    if val_lower in ("1", "true", "yes", "x", "checked", "on", "✓", "✔", "y", "s"):
        return "1"
    if val_lower in ("0", "false", "no", "off", "unchecked", "", "null", "none"):
        return "Off"
    if re.match(r"^\d{3,}$", value) or re.match(r"\d{1,2}/\d{1,2}/\d{4}", value):
        return "Off"
    return "Off"


def normalize_date(value: str) -> Optional[str]:
    """Try to normalize date to MM/DD/YYYY format."""
    if not value:
        return None
    if re.match(r"^\d{2}/\d{2}/\d{4}$", value):
        return value
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(value, dayfirst=False)
        return dt.strftime("%m/%d/%Y")
    except Exception:
        pass
    m = re.match(r"(\d{1,2})[-./](\d{1,2})[-./](\d{2,4})", value)
    if m:
        month, day, year = m.groups()
        if len(year) == 2:
            year = "20" + year if int(year) < 50 else "19" + year
        return f"{int(month):02d}/{int(day):02d}/{year}"
    return value


def is_date_field(field_name: str) -> bool:
    name_lower = field_name.lower()
    return any(kw in name_lower for kw in ["date", "birth", "hired", "effective", "expiration", "completion"])


def strip_label_prefixes(value: str, field_name: str) -> str:
    patterns = [
        r"^(?:Name|Address|City|State|ZIP|Phone|Fax|Email|Date|Code|No\.?|Number|#)\s*[:：]\s*",
        r"^(?:NAIC|VIN|SSN|FEIN|DOB)\s*[:：]\s*",
    ]
    for pat in patterns:
        value = re.sub(pat, "", value, flags=re.IGNORECASE)
    value = re.sub(r"_+$", "", value)
    return value.strip()


def is_phone_field(field_name: str) -> bool:
    return any(kw in field_name.lower() for kw in ["phone", "fax", "tel"])


def is_monetary_field(field_name: str) -> bool:
    keywords = ["amount", "limit", "premium", "deductible", "cost", "value", "price", "rate", "charge"]
    return any(kw in field_name.lower() for kw in keywords)


def fix_ocr_phone(value: str) -> str:
    cleaned = re.sub(
        r"^(?:PHONE|TEL|FAX|TELEPHONE)\s*[#:]\s*",
        "", value, flags=re.IGNORECASE
    )
    return cleaned.strip()


def fix_ocr_monetary(value: str) -> Any:
    if not value:
        return None
    cleaned = value.replace("$", "").replace(",", "").replace(" ", "").strip()
    cleaned = re.sub(r"(?<=\d)O(?=\d)", "0", cleaned)
    cleaned = re.sub(r"(?<=\d)[lI](?=\d)", "1", cleaned)
    try:
        if "." in cleaned:
            num = float(cleaned)
            return int(num) if num == int(num) else num
        return int(cleaned)
    except (ValueError, TypeError):
        return cleaned


def clean_text(value: str) -> str:
    if not value:
        return value
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return value
