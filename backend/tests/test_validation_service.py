"""
Unit tests for Document Validation rules (Module 2).
"""

import pytest
from app.services.validation_service import validate_document


def test_validation_valid_passport():
    payload = {
        "document_type": "passport",
        "fields": {
            "document_number": "A1234567",
            "nationality": "USA",
            "date_of_birth": "1990-01-01",
            "expiration_date": "2030-01-01",
        },
        "confidence": {
            "overall_composite": 1,
            "document_number": 1,
            "date_of_birth": 1,
            "expiration_date": 1,
        },
    }
    res = validate_document(payload)
    assert res["valid"] is True
    assert res["overall_valid"] is True
    assert res["fail_count"] == 0
    assert len(res["checks"]) > 0


def test_validation_expired_passport():
    payload = {
        "document_type": "passport",
        "fields": {
            "document_number": "A1234567",
            "nationality": "USA",
            "date_of_birth": "1990-01-01",
            "expiration_date": "2015-01-01",  # Expired in 2015
        },
        "confidence": {
            "overall_composite": 1,
            "document_number": 1,
            "date_of_birth": 1,
            "expiration_date": 1,
        },
    }
    res = validate_document(payload)
    assert res["valid"] is False
    assert res["fail_count"] >= 1
    expiry_check = next((c for c in res["checks"] if c["name"] == "expiry_date_not_expired"), None)
    assert expiry_check is not None
    assert expiry_check["passed"] is False


def test_validation_empty_input_graceful():
    res = validate_document({})
    assert "checks" in res
    assert res["valid"] is False
