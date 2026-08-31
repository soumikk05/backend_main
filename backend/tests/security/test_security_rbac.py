"""Security and Role-Based Access Control Tests (Requirements 28 & 32)."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_access_token

client = TestClient(app)


def test_unauthorized_when_auth_enforced(monkeypatch):
    monkeypatch.setattr("app.auth.REQUIRE_AUTH", True)
    response = client.get("/api/history")
    assert response.status_code == 401


def test_jwt_role_authorization():
    officer_token = create_access_token("test_officer", "officer")
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Officer can access standard screening routes
    resp = client.get("/api/history", headers=headers)
    assert resp.status_code == 200

    # Officer cannot access admin-only purge route
    admin_resp = client.post("/api/privacy/purge", headers=headers)
    assert admin_resp.status_code == 403


def test_admin_role_access():
    admin_token = create_access_token("test_admin", "admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.post("/api/privacy/purge", headers=headers)
    assert resp.status_code == 200
    assert "removed_files" in resp.json()
