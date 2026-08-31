"""
Integration tests for FastAPI endpoints (audit trail, blacklist, and health).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

AUTH_HEADERS = {"X-API-Key": "test-api-key"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_blacklist_crud_and_history(client):
    # 1. Add blacklisted doc
    res = client.post(
        "/api/registry/blacklist",
        json={
            "document_number": "FLAGGED123",
            "reason": "Interpol stolen travel doc",
            "country": "FRA",
        },
        headers=AUTH_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["document_number"] == "FLAGGED123"

    # 2. List blacklist
    list_res = client.get("/api/registry/blacklist", headers=AUTH_HEADERS)
    assert list_res.status_code == 200
    assert any(item["document_number"] == "FLAGGED123" for item in list_res.json())

    # 3. Query history endpoint
    hist_res = client.get("/api/history?limit=10", headers=AUTH_HEADERS)
    assert hist_res.status_code == 200
    assert "total" in hist_res.json()
    assert "items" in hist_res.json()
