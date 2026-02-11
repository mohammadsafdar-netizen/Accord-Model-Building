import pytest
from src.tools.guidewire import (
    call_guidewire_api,
    build_quote_request_payload,
    check_quote_status
)

def test_api_call():
    resp, code = call_guidewire_api("/quote", "POST", {})
    assert code == 200
    assert "amount" in resp
    assert resp["amount"] == 1500.00

def test_payload_builder():
    p = build_quote_request_payload({"insured": "Me"}, {"data": "1"})
    assert p["account"] == "Me"

def test_check_status():
    status, amt = check_quote_status("id")
    assert status == "ready"
