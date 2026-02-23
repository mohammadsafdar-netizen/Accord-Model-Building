"""Multi-source input parser for email, chat, and raw text normalization.

Parses structured emails (subject + body), chat messages, and raw text into
a common CustomerMessage format for consistent entity extraction downstream.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CustomerMessage:
    """Normalized message format for the extraction pipeline."""
    text: str                        # Clean text content for extraction
    source_type: str = "raw"         # "email", "chat", "raw"
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    subject: Optional[str] = None
    timestamp: Optional[str] = None
    original_raw: Optional[str] = None  # Preserve original input

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}


# Common email header patterns
_EMAIL_PATTERNS = {
    "from": re.compile(r"^From:\s*(.+)", re.IGNORECASE),
    "to": re.compile(r"^To:\s*(.+)", re.IGNORECASE),
    "subject": re.compile(r"^Subject:\s*(.+)", re.IGNORECASE),
    "date": re.compile(r"^Date:\s*(.+)", re.IGNORECASE),
    "sent": re.compile(r"^Sent:\s*(.+)", re.IGNORECASE),
}

# Email address extraction
_EMAIL_ADDR_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Name from "Name <email>" pattern
_NAME_EMAIL_RE = re.compile(r"^(.+?)\s*<(.+?)>")

# Chat platform markers
_CHAT_MARKERS = [
    "sent a message",
    "says:",
    "wrote:",
    "[message]",
    "chat transcript",
]

# Informal number normalization
_NUMBER_WORDS = {
    "1 mil": "1000000", "1mil": "1000000",
    "2 mil": "2000000", "2mil": "2000000",
    "3 mil": "3000000", "3mil": "3000000",
    "5 mil": "5000000", "5mil": "5000000",
    "1 million": "1000000", "2 million": "2000000",
    "500k": "500000", "250k": "250000", "100k": "100000",
    "50k": "50000", "25k": "25000", "10k": "10000",
}


def parse(raw_input: str) -> CustomerMessage:
    """Parse raw input text into a normalized CustomerMessage.

    Detects input type (email, chat, raw text) and extracts metadata.

    Args:
        raw_input: Raw text from any source

    Returns:
        Normalized CustomerMessage ready for entity extraction
    """
    raw_input = raw_input.strip()

    # Detect source type
    if _looks_like_email(raw_input):
        return _parse_email(raw_input)
    elif _looks_like_chat(raw_input):
        return _parse_chat(raw_input)
    else:
        return _parse_raw(raw_input)


def _looks_like_email(text: str) -> bool:
    """Check if text looks like a structured email."""
    first_lines = text[:500].lower()
    email_headers = ["from:", "subject:", "to:", "sent:"]
    return sum(1 for h in email_headers if h in first_lines) >= 2


def _looks_like_chat(text: str) -> bool:
    """Check if text looks like a chat message."""
    first_lines = text[:500].lower()
    return any(marker in first_lines for marker in _CHAT_MARKERS)


def _parse_email(raw: str) -> CustomerMessage:
    """Parse a structured email into header + body."""
    lines = raw.split("\n")
    headers = {}
    body_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            # Empty line typically separates headers from body
            if headers:
                body_start = i + 1
                break
            continue

        matched = False
        for key, pattern in _EMAIL_PATTERNS.items():
            m = pattern.match(stripped)
            if m:
                headers[key] = m.group(1).strip()
                matched = True
                break

        if not matched and headers:
            # Non-header line after headers → body starts here
            body_start = i
            break

    body = "\n".join(lines[body_start:]).strip()

    # Extract sender info
    sender_name = None
    sender_email = None
    from_field = headers.get("from", "")
    if from_field:
        name_match = _NAME_EMAIL_RE.match(from_field)
        if name_match:
            sender_name = name_match.group(1).strip().strip('"')
            sender_email = name_match.group(2).strip()
        else:
            email_match = _EMAIL_ADDR_RE.search(from_field)
            if email_match:
                sender_email = email_match.group(0)
            else:
                sender_name = from_field

    # Build clean text: subject provides context + body
    text_parts = []
    if headers.get("subject"):
        text_parts.append(f"Subject: {headers['subject']}")
    text_parts.append(body)
    clean_text = "\n\n".join(text_parts)

    return CustomerMessage(
        text=_normalize_text(clean_text),
        source_type="email",
        sender_name=sender_name,
        sender_email=sender_email,
        subject=headers.get("subject"),
        timestamp=headers.get("date") or headers.get("sent"),
        original_raw=raw,
    )


def _parse_chat(raw: str) -> CustomerMessage:
    """Parse a chat message, stripping platform artifacts."""
    lines = raw.split("\n")
    clean_lines = []
    sender_name = None

    for line in lines:
        stripped = line.strip()
        # Skip common chat artifacts
        if any(marker in stripped.lower() for marker in ["chat transcript", "[system]", "---"]):
            continue
        # Extract sender from "Name:" or "Name says:" patterns
        if not sender_name:
            for pattern in [r"^(.+?)\s+says:", r"^(.+?)\s+wrote:", r"^(.+?):\s"]:
                m = re.match(pattern, stripped)
                if m and len(m.group(1)) < 50:
                    sender_name = m.group(1).strip()
                    # Remove the prefix from this line
                    stripped = stripped[m.end():].strip()
                    break
        if stripped:
            clean_lines.append(stripped)

    return CustomerMessage(
        text=_normalize_text("\n".join(clean_lines)),
        source_type="chat",
        sender_name=sender_name,
        original_raw=raw,
    )


def _parse_raw(raw: str) -> CustomerMessage:
    """Parse raw text with minimal processing."""
    return CustomerMessage(
        text=_normalize_text(raw),
        source_type="raw",
        original_raw=raw,
    )


def _normalize_text(text: str) -> str:
    """Normalize informal language and formatting.

    Converts shorthand numbers, cleans up whitespace, etc.
    """
    result = text

    # Normalize informal numbers (case-insensitive)
    for pattern, replacement in _NUMBER_WORDS.items():
        # Use word boundary to avoid partial matches
        result = re.sub(
            rf"\b{re.escape(pattern)}\b",
            replacement,
            result,
            flags=re.IGNORECASE,
        )

    # Normalize "next month" / "next year" relative dates
    # (leave as-is for LLM to interpret — just flag that they're relative)

    # Clean up excessive whitespace
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r" {2,}", " ", result)

    return result.strip()
