from typing import List, Dict, Any, Tuple

def check_required_fields(form_data: Dict, required_fields_list: List[str]) -> Tuple[bool, List[str], int]:
    """
    Checks if all required fields are filled.
    """
    missing = []
    for field in required_fields_list:
        if field not in form_data or not form_data[field]:
            missing.append(field)
            
    return len(missing) == 0, missing, len(missing)

def validate_business_rules(form_data: Dict) -> Tuple[bool, List[str]]:
    """
    Custom business rules.
    """
    issues = []
    # Example rule: Coverage > 0
    if form_data.get("coverage_amount", 0) < 0:
        issues.append("Coverage cannot be negative")
        
    return len(issues) == 0, issues

def calculate_submission_readiness(required_status: Dict, validation_errors: List) -> Tuple[int, List[str], bool]:
    """
    Scores how ready the submission is.
    """
    score = 0
    blocking = []
    
    if not required_status.get("missing"):
        score += 50
    else:
        blocking.append("Required fields missing")
        
    if not validation_errors:
        score += 50
    else:
        blocking.append("Validation errors exist")
        
    return score, blocking, score == 100
