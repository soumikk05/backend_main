"""
Unit tests for API Authentication layer.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check_exempt_from_auth(client):
    # Health endpoint must never require auth
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_protected_routes_accept_valid_key(client):
    res = client.get("/api/history", headers={"X-API-Key": "test-api-key"})
    assert res.status_code == 200


def test_protected_routes_reject_invalid_key_when_enforced(client, monkeypatch):
    import app.auth as auth_mod
    monkeypatch.setattr(auth_mod, "REQUIRE_AUTH", True)

    # 1. Missing header
    res = client.get("/api/history")
    assert res.status_code == 401

    # 2. Invalid key
    res_bad = client.get("/api/history", headers={"X-API-Key": "wrong-key-123"})
    assert res_bad.status_code == 401
