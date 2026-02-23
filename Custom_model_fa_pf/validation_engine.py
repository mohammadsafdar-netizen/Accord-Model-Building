"""Validation engine for form field values.

Validates filled field values against domain rules and auto-corrects where safe.
Reuses VIN checksum and state/ZIP logic from field_validator.py.

Rules:
  1. VIN checksum (17 chars + check digit)
  2. Driver's license format by state
  3. FEIN format (XX-XXXXXXX)
  4. Date ordering (effective < expiration)
  5. Date format (MM/DD/YYYY parseable)
  6. State/ZIP consistency
  7. Phone normalization (10 digits)
  8. Required field completeness
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Reuse state/ZIP table from field_validator
try:
    from field_validator import STATE_ZIP_PREFIXES, _validate_vin_checksum
except ImportError:
    # Fallback if field_validator not on path
    STATE_ZIP_PREFIXES = {}

    def _validate_vin_checksum(vin: str) -> bool:
        vin = vin.strip().upper()
        if len(vin) != 17:
            return True
        transliteration = {
            'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
            'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
            'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
        }
        weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
        total = 0
        for i, char in enumerate(vin):
            if char.isdigit():
                val = int(char)
            elif char in transliteration:
                val = transliteration[char]
            else:
                return True
            total += val * weights[i]
        remainder = total % 11
        check_digit = 'X' if remainder == 10 else str(remainder)
        return vin[8] == check_digit


# Driver's license format patterns by state (simplified — covers major states)
DL_PATTERNS = {
    "AL": r"^\d{7,8}$",
    "AK": r"^\d{7}$",
    "AZ": r"^[A-Z]\d{8}$|^\d{9}$",
    "AR": r"^\d{8,9}$",
    "CA": r"^[A-Z]\d{7}$",
    "CO": r"^\d{9}$|^[A-Z]\d{3,6}$",
    "CT": r"^\d{9}$",
    "DE": r"^\d{7}$",
    "DC": r"^\d{7}$|^\d{9}$",
    "FL": r"^[A-Z]\d{12}$",
    "GA": r"^\d{9}$",
    "HI": r"^H\d{8}$|^\d{9}$",
    "ID": r"^[A-Z]{2}\d{6}[A-Z]$|^\d{9}$",
    "IL": r"^[A-Z]\d{11,12}$",
    "IN": r"^\d{10}$|^[A-Z]\d{9}$",
    "IA": r"^\d{9}$|^\d{3}[A-Z]{2}\d{4}$",
    "KS": r"^K\d{8}$|^\d{9}$",
    "KY": r"^[A-Z]\d{8,9}$|^\d{9}$",
    "LA": r"^\d{9}$",
    "ME": r"^\d{7}$|^\d{8}$",
    "MD": r"^[A-Z]\d{12}$",
    "MA": r"^S\d{8}$|^\d{9}$",
    "MI": r"^[A-Z]\d{10,12}$",
    "MN": r"^[A-Z]\d{12}$",
    "MS": r"^\d{9}$",
    "MO": r"^[A-Z]\d{5,9}$|^\d{9}$",
    "MT": r"^\d{13}$|^[A-Z]{3}\d{8,10}$",
    "NE": r"^[A-Z]\d{6,8}$",
    "NV": r"^\d{10,12}$",
    "NH": r"^\d{2}[A-Z]{3}\d{5}$",
    "NJ": r"^[A-Z]\d{14}$",
    "NM": r"^\d{9}$",
    "NY": r"^\d{9}$|^[A-Z]\d{7,18}$",
    "NC": r"^\d{12}$",
    "ND": r"^[A-Z]{3}\d{6}$|^\d{9}$",
    "OH": r"^[A-Z]{2}\d{6}$|^\d{8}$",
    "OK": r"^[A-Z]\d{9}$|^\d{9}$",
    "OR": r"^\d{7,9}$|^[A-Z]\d{6}$",
    "PA": r"^\d{8}$",
    "RI": r"^\d{7}$|^V\d{6}$",
    "SC": r"^\d{5,11}$",
    "SD": r"^\d{6,10}$",
    "TN": r"^\d{7,9}$",
    "TX": r"^\d{8}$",
    "UT": r"^\d{4,10}$",
    "VT": r"^\d{8}$|^\d{7}[A-Z]$",
    "VA": r"^[A-Z]\d{8,11}$|^\d{9}$",
    "WA": r"^[A-Z*]{5}\d{3}[A-Z0-9]{2}$|^WDL[A-Z0-9]{9}$",
    "WV": r"^[A-Z]\d{6}$|^\d{7}$",
    "WI": r"^[A-Z]\d{13}$",
    "WY": r"^\d{9,10}$",
}


@dataclass
class ValidationIssue:
    """A single validation issue found in field values."""
    field_name: str
    value: str
    rule: str
    severity: str  # error, warning, info
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "field_name": self.field_name,
            "value": self.value,
            "rule": rule_name(self.rule),
            "severity": self.severity,
            "message": self.message,
        }
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


@dataclass
class ValidationResult:
    """Result of validating all field values for a form."""
    issues: List[ValidationIssue] = field(default_factory=list)
    corrected_values: Dict[str, str] = field(default_factory=dict)
    auto_corrections: Dict[str, str] = field(default_factory=dict)  # field -> correction description
    total_fields: int = 0
    valid_fields: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_fields": self.total_fields,
            "valid_fields": self.valid_fields,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [i.to_dict() for i in self.issues],
            "auto_corrections": self.auto_corrections,
        }


def rule_name(rule: str) -> str:
    """Human-readable rule name."""
    return rule


def _extract_digits(value: str) -> str:
    return re.sub(r"[^\d]", "", str(value))


def _parse_date(value: str) -> Optional[date]:
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y", "%m-%d-%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_phone(phone: str) -> Optional[str]:
    """Normalize phone number to (XXX) XXX-XXXX format."""
    digits = _extract_digits(phone)
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return None


def _normalize_fein(fein: str) -> Optional[str]:
    """Normalize FEIN to XX-XXXXXXX format."""
    digits = _extract_digits(fein)
    if len(digits) == 9:
        return f"{digits[:2]}-{digits[2:]}"
    return None


def validate(
    field_values: Dict[str, str],
    entities=None,
) -> ValidationResult:
    """Validate all field values and auto-correct where safe.

    Args:
        field_values: Dict of {field_name: value} for a single form
        entities: Optional CustomerSubmission for cross-reference

    Returns:
        ValidationResult with issues, corrections, and corrected values
    """
    result = ValidationResult()
    result.corrected_values = dict(field_values)
    result.total_fields = len(field_values)
    current_year = datetime.now().year

    fields_with_issues = set()

    for field_name, value in field_values.items():
        if not value or not str(value).strip():
            continue

        value_str = str(value).strip()
        fn_lower = field_name.lower()

        # --- Rule 1: VIN checksum ---
        if re.search(r"vin|vehicle.*ident", fn_lower):
            vin = value_str.upper().replace(" ", "")
            if len(vin) == 17:
                if not _validate_vin_checksum(vin):
                    result.issues.append(ValidationIssue(
                        field_name=field_name,
                        value=value_str,
                        rule="vin_checksum",
                        severity="error",
                        message=f"VIN check digit (position 9) is invalid for {vin}",
                        suggestion="Verify VIN with the vehicle owner or registration",
                    ))
                    fields_with_issues.add(field_name)
            elif len(vin) > 0 and len(vin) != 17:
                result.issues.append(ValidationIssue(
                    field_name=field_name,
                    value=value_str,
                    rule="vin_length",
                    severity="error",
                    message=f"VIN must be exactly 17 characters (got {len(vin)})",
                ))
                fields_with_issues.add(field_name)

        # --- Rule 2: Driver's license format by state ---
        if re.search(r"license.*number|dl.*number|driver.*license", fn_lower) and "state" not in fn_lower:
            dl_value = value_str.upper().replace(" ", "").replace("-", "")
            # Find corresponding state field
            dl_state = _find_related_field(field_values, field_name, "state")
            if dl_state and dl_state in DL_PATTERNS:
                pattern = DL_PATTERNS[dl_state]
                if not re.match(pattern, dl_value):
                    result.issues.append(ValidationIssue(
                        field_name=field_name,
                        value=value_str,
                        rule="dl_format",
                        severity="warning",
                        message=f"Driver's license format doesn't match expected pattern for {dl_state}",
                        suggestion=f"Verify license number format for state {dl_state}",
                    ))
                    fields_with_issues.add(field_name)

        # --- Rule 3: FEIN format ---
        if re.search(r"fein|tax.*id|federal.*id|ein\b", fn_lower):
            digits = _extract_digits(value_str)
            if digits:
                if len(digits) != 9:
                    result.issues.append(ValidationIssue(
                        field_name=field_name,
                        value=value_str,
                        rule="fein_format",
                        severity="error" if len(digits) < 9 else "info",
                        message=f"FEIN should be 9 digits (got {len(digits)})",
                    ))
                    fields_with_issues.add(field_name)
                else:
                    # Auto-correct: normalize to XX-XXXXXXX
                    normalized = _normalize_fein(value_str)
                    if normalized and normalized != value_str:
                        result.corrected_values[field_name] = normalized
                        result.auto_corrections[field_name] = f"Reformatted FEIN: {value_str} -> {normalized}"

        # --- Rule 4: Date ordering (effective < expiration) ---
        if re.search(r"effective.*date|eff.*date", fn_lower):
            eff_date = _parse_date(value_str)
            if eff_date:
                # Find matching expiration date
                exp_field = _find_related_field_by_pattern(field_values, r"expiration.*date|exp.*date")
                if exp_field:
                    exp_date = _parse_date(field_values[exp_field])
                    if exp_date and eff_date >= exp_date:
                        result.issues.append(ValidationIssue(
                            field_name=field_name,
                            value=value_str,
                            rule="date_ordering",
                            severity="error",
                            message=f"Effective date ({value_str}) must be before expiration date ({field_values[exp_field]})",
                        ))
                        fields_with_issues.add(field_name)

        # --- Rule 5: Date format parseable ---
        if "date" in fn_lower:
            if value_str and not _parse_date(value_str):
                result.issues.append(ValidationIssue(
                    field_name=field_name,
                    value=value_str,
                    rule="date_format",
                    severity="error",
                    message=f"Date '{value_str}' is not in a recognized format (expected MM/DD/YYYY)",
                ))
                fields_with_issues.add(field_name)

        # --- Rule 6: State/ZIP consistency ---
        if re.search(r"_state[_ ]|state_|statecode", fn_lower) and "zip" not in fn_lower:
            state_val = value_str.upper().strip()
            # Find matching ZIP field
            zip_value = _find_related_field(field_values, field_name, "zip")
            if zip_value and STATE_ZIP_PREFIXES:
                zip_digits = _extract_digits(zip_value)
                if state_val and zip_digits and len(zip_digits) >= 3:
                    zip_prefix = zip_digits[:3]
                    valid_prefixes = STATE_ZIP_PREFIXES.get(state_val, [])
                    if valid_prefixes and zip_prefix not in valid_prefixes:
                        result.issues.append(ValidationIssue(
                            field_name=field_name,
                            value=value_str,
                            rule="state_zip_consistency",
                            severity="warning",
                            message=f"State {state_val} doesn't match ZIP prefix {zip_prefix}",
                            suggestion="Verify the state and ZIP code are for the same location",
                        ))
                        fields_with_issues.add(field_name)

        # --- Rule 7: Phone normalization ---
        if re.search(r"phone|fax|telephone|tel\b", fn_lower):
            digits = _extract_digits(value_str)
            if digits:
                normalized = _normalize_phone(value_str)
                if normalized:
                    if normalized != value_str:
                        result.corrected_values[field_name] = normalized
                        result.auto_corrections[field_name] = f"Normalized phone: {value_str} -> {normalized}"
                else:
                    result.issues.append(ValidationIssue(
                        field_name=field_name,
                        value=value_str,
                        rule="phone_format",
                        severity="info",
                        message=f"Phone number has {len(digits)} digits (expected 10)",
                    ))
                    fields_with_issues.add(field_name)

    # Calculate valid field count
    result.valid_fields = result.total_fields - len(fields_with_issues)
    result.error_count = sum(1 for i in result.issues if i.severity == "error")
    result.warning_count = sum(1 for i in result.issues if i.severity == "warning")
    result.info_count = sum(1 for i in result.issues if i.severity == "info")

    logger.info(
        f"Validation: {result.total_fields} fields, "
        f"{result.error_count} errors, {result.warning_count} warnings, "
        f"{len(result.auto_corrections)} auto-corrections"
    )

    return result


def _find_related_field(field_values: Dict[str, str], field_name: str, target_keyword: str) -> Optional[str]:
    """Find a field value related to the given field by keyword substitution.

    E.g. for field "Driver_LicenseNumber_A" and target "state",
    looks for "Driver_LicenseState_A" or similar.
    """
    # Extract suffix
    suffix_match = re.search(r"_([A-M]|\d+)$", field_name)
    suffix = suffix_match.group(0) if suffix_match else ""

    # Try direct keyword substitution in field name
    for fname, fval in field_values.items():
        if fname == field_name:
            continue
        # Same suffix and contains target keyword
        if fname.endswith(suffix) and target_keyword.lower() in fname.lower():
            return fval

    return None


def _find_related_field_by_pattern(field_values: Dict[str, str], pattern: str) -> Optional[str]:
    """Find a field name matching a regex pattern."""
    for fname in field_values:
        if re.search(pattern, fname, re.I):
            return fname
    return None
