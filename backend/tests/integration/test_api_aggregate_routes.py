"""Integration tests for Operations, Audit Integrity, and Aggregate Screening APIs."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "test-api-key"}


def test_audit_integrity_endpoint():
    response = client.get("/api/audit/integrity", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data
    assert "records_checked" in data


def test_audit_integrity_root_alias():
    response = client.get("/audit/integrity", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data


def test_aggregate_screening_not_found():
    response = client.get("/api/screening/non-existent-id", headers=AUTH_HEADERS)
    assert response.status_code == 404
