from typing import List, Dict, Any, Tuple
import uuid
from datetime import datetime

# Mock In-Memory Mailbox
SENT_BOX = []
INBOX = []

def send_email_with_forms(recipient: str, subject: str, body: str, attachments: List[str]) -> Tuple[str, str, bool]:
    """
    Sends email with attached forms (Mock).
    """
    msg_id = str(uuid.uuid4())
    ts = datetime.now().isoformat()
    
    SENT_BOX.append({
        "id": msg_id,
        "to": recipient,
        "subject": subject,
        "attachments": attachments,
        "timestamp": ts
    })
    
    return msg_id, ts, True

def check_for_new_emails(folder: str = "INBOX") -> Tuple[List[Dict], int]:
    """
    Checks inbox for new emails (Mock).
    """
    # Simply return what's in our mock inbox
    return INBOX, len(INBOX)

def parse_email_message(raw_email: Dict) -> Dict:
    """
    Parses mock email structure.
    """
    return {
        "from": raw_email.get("from"),
        "subject": raw_email.get("subject"),
        "body": raw_email.get("body"),
        "attachments": raw_email.get("attachments", [])
    }

# Helper to inject email for testing
def inject_incoming_email(sender: str, subject: str, attachments: List[str]):
    INBOX.append({
        "id": str(uuid.uuid4()),
        "from": sender,
        "subject": subject,
        "body": "Here is the filled form",
        "attachments": attachments
    })
