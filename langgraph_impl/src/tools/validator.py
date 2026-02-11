import re
from typing import Tuple, Optional, Any, Dict
from datetime import datetime
# Ideally we use libraries like phonenumbers, email_validator.
# I will implement simplified regex versions to avoid external dep install issues in this environment,
# but structure it so libraries can be swapped in.

def validate_field_type(field_name: str, field_value: Any, expected_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validates input matches expected type.
    """
    try:
        if expected_type == "int":
            int(field_value)
        elif expected_type == "float":
            float(field_value)
        elif expected_type == "bool":
            if str(field_value).lower() not in ["true", "false", "1", "0"]:
                return False, f"Value {field_value} is not a boolean"
        # String is always valid unless empty check is needed
    except ValueError:
        return False, f"Value {field_value} is not of type {expected_type}"
    
    return True, None

def validate_ssn(ssn_string: str) -> Tuple[bool, Optional[str]]:
    """
    Validates SSN format (XXX-XX-XXXX).
    """
    pattern = r'^\d{3}-\d{2}-\d{4}$'
    if re.match(pattern, ssn_string):
        return True, None
    return False, "Invalid SSN format. Expected XXX-XX-XXXX."

def validate_email(email_string: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates email address.
    """
    # Simple regex for email
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if re.match(pattern, email_string):
        return True, email_string.lower(), None
    return False, email_string, "Invalid email format."

def validate_phone(phone_string: str, default_region: str = "US") -> Tuple[bool, str, Optional[str]]:
    """
    Validates phone number.
    """
    # Remove non-digits
    digits = re.sub(r'\D', '', phone_string)
    if len(digits) == 10:
        return True, f"+1{digits}", "US" # Assume US for 10 digits
    if len(digits) == 11 and digits.startswith('1'):
         return True, f"+{digits}", "US"
         
    return False, phone_string, "Invalid phone number length."

def validate_zip_code(zip_string: str) -> bool:
     pattern = r'^\d{5}(-\d{4})?$'
     return bool(re.match(pattern, zip_string))

def validate_date(date_string: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates and normalizes date. Supporting ISO YYYY-MM-DD.
    """
    try:
        dt = datetime.fromisoformat(date_string)
        return True, dt.isoformat(), "ISO8601"
    except ValueError:
        pass
        
    # Try simple US format MM/DD/YYYY
    try: 
        dt = datetime.strptime(date_string, "%m/%d/%Y")
        return True, dt.isoformat(), "US_DATE"
    except ValueError:
        return False, None, "Unknown date format"

def validate_currency(amount_string: str) -> Tuple[bool, Optional[float], Optional[str]]:
    try:
        # Cleanup $ and ,
        clean = amount_string.replace('$', '').replace(',', '')
        val = float(clean)
        return True, val, None
    except ValueError:
        return False, None, "Invalid currency amount"

class ValidationReport:
    # Dummy class helper if needed
    pass

def generate_validation_report(validation_errors: list) -> Tuple[str, int, str]:
    count = len(validation_errors)
    severity = "high" if count > 0 else "none"
    msg = f"Found {count} errors."
    return msg, count, severity
