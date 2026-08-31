"""Unit tests for Validation, Cross-Field Consistency, and Country Rules (Requirements 18, 19, 20)."""
import pytest
from app.services.validation_service import validate_document


def test_cross_field_expiry_before_issue():
    payload = {
        "document_type": "passport",
        "fields": {
            "document_number": {"value": "A1234567", "confidence": 0.95},
            "nationality": {"value": "USA", "confidence": 0.95},
            "issue_date": {"value": "2024-01-01", "confidence": 0.95},
            "expiry_date": {"value": "2020-01-01", "confidence": 0.95},
            "date_of_birth": {"value": "1990-01-01", "confidence": 0.95},
        },
        "confidence": {"document_number": 1, "date_of_birth": 1, "expiration_date": 1, "overall_composite": 1},
    }
    result = validate_document(payload)
    failed_rules = [c["rule"] for c in result["failed_rules"]]
    assert "expiry_after_issue" in failed_rules or "expiry_date_not_expired" in failed_rules


def test_cross_field_future_dob():
    payload = {
        "document_type": "passport",
        "fields": {
            "document_number": {"value": "A1234567", "confidence": 0.95},
            "nationality": {"value": "USA", "confidence": 0.95},
            "date_of_birth": {"value": "2099-01-01", "confidence": 0.95},
            "expiration_date": {"value": "2030-01-01", "confidence": 0.95},
        },
        "confidence": {"document_number": 1, "date_of_birth": 1, "expiration_date": 1, "overall_composite": 1},
    }
    result = validate_document(payload)
    failed_rules = [c["rule"] for c in result["failed_rules"]]
    assert "date_of_birth_plausible" in failed_rules


def test_india_passport_format():
    payload = {
        "document_type": "passport",
        "fields": {
            "document_number": {"value": "Z1234567", "confidence": 0.95},
            "nationality": {"value": "IND", "confidence": 0.95},
            "date_of_birth": {"value": "1995-05-15", "confidence": 0.95},
            "expiration_date": {"value": "2032-05-15", "confidence": 0.95},
        },
        "confidence": {"document_number": 1, "date_of_birth": 1, "expiration_date": 1, "overall_composite": 1},
    }
    result = validate_document(payload)
    assert result["valid"] is True
    assert result["consistency_score"] >= 80.0
