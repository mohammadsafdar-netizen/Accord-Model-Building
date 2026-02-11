from typing import Dict, Any, Tuple
import uuid

def call_guidewire_api(endpoint: str, method: str, payload: Dict) -> Tuple[Dict, int]:
    """
    Mock Guidewire API.
    """
    if endpoint == "/quote":
        return {
            "id": f"qw_{uuid.uuid4().hex[:8]}",
            "amount": 1500.00,
            "status": "quoted"
        }, 200
    
    return {"error": "not found"}, 404

def build_quote_request_payload(common_data: Dict, form_1_data: Dict) -> Dict:
    """
    Transforms internal data to GW payload.
    """
    return {
        "account": common_data.get("insured", {}),
        "params": form_1_data
    }

def check_quote_status(quote_id: str) -> Tuple[str, float]:
    """
    Check status (Mock).
    """
    return "ready", 1500.00
