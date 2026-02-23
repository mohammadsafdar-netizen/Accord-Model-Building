"""Tests for the FastAPI endpoints (no LLM required — mock pipeline stages)."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from Custom_model_fa_pf.api import app, store
from Custom_model_fa_pf.session import SessionStatus


@pytest.fixture(autouse=True)
def _clear_sessions():
    """Reset session store between tests."""
    store._sessions.clear()
    yield
    store._sessions.clear()


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "sessions_active" in data


class TestSubmitEndpoint:
    @patch("Custom_model_fa_pf.api._run_pipeline_stages")
    def test_submit_creates_session(self, mock_pipeline):
        resp = client.post("/api/v1/submit", json={"text": "I need auto insurance for my 2024 Ford F-350."})
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["status"] in [s.value for s in SessionStatus]

    def test_submit_rejects_short_text(self):
        resp = client.post("/api/v1/submit", json={"text": "hi"})
        assert resp.status_code == 422

    def test_submit_rejects_empty(self):
        resp = client.post("/api/v1/submit", json={"text": ""})
        assert resp.status_code == 422


class TestSessionEndpoints:
    def _create_session_with_data(self):
        """Helper to create a session with mock pipeline data."""
        session = store.create()
        session.add_message("user", "Test insurance request")
        session.status = SessionStatus.AWAITING_INFO
        return session

    def test_get_status_existing_session(self):
        session = self._create_session_with_data()
        resp = client.get(f"/api/v1/session/{session.id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session.id
        assert data["status"] == "awaiting_info"

    def test_get_status_nonexistent_session(self):
        resp = client.get("/api/v1/session/nonexistent123/status")
        assert resp.status_code == 404

    def test_get_result_existing_session(self):
        session = self._create_session_with_data()
        session.field_values = {"125": {"NamedInsured_FullName_A": "Test Corp"}}
        resp = client.get(f"/api/v1/session/{session.id}/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["forms"]["125"]["NamedInsured_FullName_A"] == "Test Corp"

    def test_get_result_nonexistent_session(self):
        resp = client.get("/api/v1/session/nonexistent123/result")
        assert resp.status_code == 404

    @patch("Custom_model_fa_pf.api._run_pipeline_stages")
    def test_send_message_adds_to_session(self, mock_pipeline):
        session = self._create_session_with_data()
        resp = client.post(
            f"/api/v1/session/{session.id}/message",
            json={"text": "VIN is 1HGCM82633A004352"},
        )
        assert resp.status_code == 200
        assert len(session.messages) == 2

    def test_send_message_nonexistent_session(self):
        resp = client.post(
            "/api/v1/session/nonexistent123/message",
            json={"text": "more info"},
        )
        assert resp.status_code == 404

    def test_finalize_no_fields(self):
        session = self._create_session_with_data()
        resp = client.post(f"/api/v1/session/{session.id}/finalize")
        assert resp.status_code == 400
