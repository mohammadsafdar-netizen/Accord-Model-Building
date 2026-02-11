import pytest
from src.tools.email import (
    send_email_with_forms,
    check_for_new_emails,
    inject_incoming_email,
    SENT_BOX,
    INBOX
)

def setup_function():
    SENT_BOX.clear()
    INBOX.clear()

def test_send_email():
    msg_id, _, success = send_email_with_forms("user@test.com", "Forms", "Body", ["form.pdf"])
    assert success is True
    assert len(SENT_BOX) == 1
    assert SENT_BOX[0]["to"] == "user@test.com"

def test_receive_email():
    assert len(check_for_new_emails()[0]) == 0
    
    inject_incoming_email("user@test.com", "Re: Forms", ["filled.pdf"])
    
    emails, count = check_for_new_emails()
    assert count == 1
    assert emails[0]["from"] == "user@test.com"
