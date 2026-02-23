"""Session management for multi-turn form assignment conversations."""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional

from Custom_model_fa_pf.entity_schema import CustomerSubmission
from Custom_model_fa_pf.form_assigner import FormAssignment
from Custom_model_fa_pf.gap_analyzer import GapReport
from Custom_model_fa_pf.lob_classifier import LOBClassification
from Custom_model_fa_pf.validation_engine import ValidationResult

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    AWAITING_INFO = "awaiting_info"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class Message:
    role: str  # "user" or "system"
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class Session:
    id: str
    status: SessionStatus = SessionStatus.CREATED
    messages: List[Message] = field(default_factory=list)
    lobs: List[LOBClassification] = field(default_factory=list)
    entities: Optional[CustomerSubmission] = None
    assignments: List[FormAssignment] = field(default_factory=list)
    field_values: Dict[str, Dict[str, str]] = field(default_factory=dict)
    gap_report: Optional[GapReport] = None
    validation_results: Dict[str, ValidationResult] = field(default_factory=dict)
    conversation_turn: int = 0
    pending_corrections: Dict[str, Dict[str, str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None

    def add_message(self, role: str, content: str) -> Message:
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        self.updated_at = time.time()
        return msg

    def get_full_text(self) -> str:
        """Concatenate all user messages into a single text for extraction."""
        return "\n\n".join(
            msg.content for msg in self.messages if msg.role == "user"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "messages": [m.to_dict() for m in self.messages],
            "lobs": [l.to_dict() for l in self.lobs],
            "entities": self.entities.to_dict() if self.entities else None,
            "assignments": [a.to_dict() for a in self.assignments],
            "field_values": self.field_values,
            "gap_report": self.gap_report.to_dict() if self.gap_report else None,
            "validation_results": {k: v.to_dict() for k, v in self.validation_results.items()},
            "conversation_turn": self.conversation_turn,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    def summary(self) -> Dict[str, Any]:
        """Compact status summary without full field values."""
        return {
            "id": self.id,
            "status": self.status.value,
            "lobs": [l.display_name for l in self.lobs],
            "forms_assigned": [a.form_number for a in self.assignments],
            "fields_mapped": {k: len(v) for k, v in self.field_values.items()},
            "gaps_remaining": len(self.gap_report.missing_critical) if self.gap_report else 0,
            "completeness_pct": self.gap_report.completeness_pct if self.gap_report else 0.0,
            "validation_errors": sum(v.error_count for v in self.validation_results.values()),
            "conversation_turn": self.conversation_turn,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }


class SessionStore:
    """In-memory session store. Replace with Redis for production."""

    def __init__(self, timeout_seconds: int = 3600):
        self._sessions: Dict[str, Session] = {}
        self._lock = Lock()
        self._timeout = timeout_seconds

    def create(self) -> Session:
        session_id = uuid.uuid4().hex[:12]
        session = Session(id=session_id)
        with self._lock:
            self._sessions[session_id] = session
        logger.info(f"Created session {session_id}")
        return session

    def get(self, session_id: str) -> Optional[Session]:
        with self._lock:
            session = self._sessions.get(session_id)
        if session and (time.time() - session.updated_at) > self._timeout:
            self.delete(session_id)
            return None
        return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        now = time.time()
        expired = []
        with self._lock:
            for sid, session in self._sessions.items():
                if (now - session.updated_at) > self._timeout:
                    expired.append(sid)
            for sid in expired:
                del self._sessions[sid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        return len(expired)

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.summary() for s in self._sessions.values()]
