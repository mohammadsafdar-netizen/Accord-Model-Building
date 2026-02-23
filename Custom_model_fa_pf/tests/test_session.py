"""Tests for session management."""

import time
import pytest
from Custom_model_fa_pf.session import Session, SessionStatus, SessionStore


class TestSession:
    def test_create_session(self):
        s = Session(id="test123")
        assert s.id == "test123"
        assert s.status == SessionStatus.CREATED
        assert s.messages == []

    def test_add_message(self):
        s = Session(id="test123")
        msg = s.add_message("user", "Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert len(s.messages) == 1

    def test_get_full_text(self):
        s = Session(id="test123")
        s.add_message("user", "First message")
        s.add_message("system", "System response")
        s.add_message("user", "Second message")
        text = s.get_full_text()
        assert "First message" in text
        assert "Second message" in text
        assert "System response" not in text

    def test_summary(self):
        s = Session(id="test123")
        summary = s.summary()
        assert summary["id"] == "test123"
        assert summary["status"] == "created"
        assert summary["message_count"] == 0

    def test_to_dict(self):
        s = Session(id="test123")
        s.add_message("user", "Test")
        d = s.to_dict()
        assert d["id"] == "test123"
        assert len(d["messages"]) == 1


class TestSessionStore:
    def test_create_session(self):
        store = SessionStore()
        session = store.create()
        assert session.id is not None
        assert len(session.id) == 12

    def test_get_session(self):
        store = SessionStore()
        session = store.create()
        retrieved = store.get(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id

    def test_get_nonexistent(self):
        store = SessionStore()
        assert store.get("nonexistent") is None

    def test_delete_session(self):
        store = SessionStore()
        session = store.create()
        assert store.delete(session.id) is True
        assert store.get(session.id) is None

    def test_delete_nonexistent(self):
        store = SessionStore()
        assert store.delete("nonexistent") is False

    def test_expired_session_not_returned(self):
        store = SessionStore(timeout_seconds=0)
        session = store.create()
        time.sleep(0.01)
        assert store.get(session.id) is None

    def test_cleanup_expired(self):
        store = SessionStore(timeout_seconds=0)
        store.create()
        store.create()
        time.sleep(0.01)
        removed = store.cleanup_expired()
        assert removed == 2

    def test_list_sessions(self):
        store = SessionStore()
        store.create()
        store.create()
        sessions = store.list_sessions()
        assert len(sessions) == 2
