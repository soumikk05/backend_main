"""Integration tests for End-to-End Screening Pipeline & 3 Demo Cases (Requirement 54 & Section 42)."""
import pytest
from app.services.validation_service import validate_document
from app.services.tampering_service import analyze_tampering
from app.services.risk_engine import compute_risk_score
from app.services.registry_service import screen_registry, detect_identity_cluster


def test_demo_case_1_genuine():
    """
    CASE 1 — GENUINE
    Expected: OCR ✓, Validation ✓, Tampering LOW, Face MATCH, Liveness PASS, Registry CLEAR, Risk LOW, Decision CLEAR.
    """
    ocr_result = {
        "document_type": "passport",
        "fields": {
            "name": {"value": "RAHUL SHARMA", "confidence": 0.98, "source": "mrz", "validated": True},
            "document_number": {"value": "Z1234567", "confidence": 0.99, "source": "mrz", "validated": True},
            "nationality": {"value": "IND", "confidence": 0.98, "source": "mrz", "validated": True},
            "date_of_birth": {"value": "1992-06-15", "confidence": 0.98, "source": "mrz", "validated": True},
            "expiration_date": {"value": "2032-06-15", "confidence": 0.98, "source": "mrz", "validated": True},
        },
        "confidence": {"overall_composite": 1, "document_number": 1, "date_of_birth": 1, "expiration_date": 1},
    }

    validation_result = validate_document(ocr_result)
    assert validation_result["valid"] is True

    tampering_result = {
        "tampering_score": 8.5,
        "tampered": False,
        "signals": {"ela": 10.0, "photo_region": 5.0, "copy_move": 0.0, "stamp": 10.0, "cnn": 12.0, "metadata": 0.0},
        "checks": [],
    }

    face_result = {
        "face_detected_document": True,
        "face_detected_selfie": True,
        "match": True,
        "matched": True,
        "similarity": 0.96,
        "distance": 0.12,
        "threshold": 0.40,
    }

    liveness_result = {
        "challenge": "blink",
        "liveness_score": 88.0,
        "passed": True,
    }

    registry_result = {
        "registry_score": 0.0,
        "is_blacklisted": False,
        "is_duplicate": False,
        "flags": [],
    }

    risk_res = compute_risk_score(
        validation_result=validation_result,
        tampering_result=tampering_result,
        face_result=face_result,
        registry_result=registry_result,
        quality_result={"quality_score": 92.0, "acceptable": True, "issues": []},
        liveness_result=liveness_result,
        ocr_result=ocr_result,
    )

    assert risk_res["risk_score"] <= 30.0
    assert risk_res["risk_label"] == "LOW"
    assert risk_res["decision"] == "CLEAR"


def test_demo_case_2_tampered():
    """
    CASE 2 — TAMPERED
    Expected: OCR ✓, Validation WARNING/FAIL, Tampering HIGH, Localization available, Risk HIGH, Decision HOLD.
    """
    ocr_result = {
        "document_type": "passport",
        "fields": {
            "name": {"value": "ALEX FORGER", "confidence": 0.95, "source": "mrz", "validated": True},
            "document_number": {"value": "A9999999", "confidence": 0.95, "source": "mrz", "validated": True},
            "nationality": {"value": "USA", "confidence": 0.95, "source": "mrz", "validated": True},
            "date_of_birth": {"value": "1990-01-01", "confidence": 0.95, "source": "mrz", "validated": True},
            "expiration_date": {"value": "2018-01-01", "confidence": 0.95, "source": "mrz", "validated": True},  # EXPIRED
        },
        "confidence": {"overall_composite": 0, "document_number": 1, "date_of_birth": 1, "expiration_date": 0},
    }

    validation_result = validate_document(ocr_result)
    assert validation_result["valid"] is False  # Expired & composite failed

    tampering_result = {
        "tampering_score": 85.0,
        "tampered": True,
        "signals": {"ela": 88.0, "photo_region": 92.0, "copy_move": 40.0, "stamp": 75.0, "cnn": 82.0, "metadata": 70.0},
        "checks": [
            {"name": "photo_region_analysis", "triggered": True, "score": 92.0, "detail": "Photo perimeter seam detected"},
            {"name": "error_level_analysis", "triggered": True, "score": 88.0, "detail": "High ELA compression variance"},
        ],
        "heatmap": {"heatmap_available": True, "regions": [{"x": 50, "y": 80, "width": 100, "height": 120, "score": 0.92}]},
    }

    risk_res = compute_risk_score(
        validation_result=validation_result,
        tampering_result=tampering_result,
        face_result=None,
        registry_result={"registry_score": 0.0, "is_blacklisted": False, "is_duplicate": False, "flags": []},
        quality_result={"quality_score": 85.0, "acceptable": True, "issues": []},
        ocr_result=ocr_result,
    )

    assert risk_res["risk_score"] >= 65.0
    assert risk_res["risk_label"] == "HIGH"
    assert risk_res["decision"] == "HOLD"
    assert len(risk_res["evidence"]["hard_security_flags"]) > 0


def test_demo_case_3_identity_conflict():
    """
    CASE 3 — IDENTITY CONFLICT
    Expected: Document structurally valid, Tampering LOW, Face mismatch OR identity conflict, Multiple identity detected, Risk HIGH, Decision HOLD.
    """
    ocr_result = {
        "document_type": "passport",
        "fields": {
            "name": {"value": "VIKRAM SINGH", "confidence": 0.98, "source": "mrz", "validated": True},
            "document_number": {"value": "P8888888", "confidence": 0.98, "source": "mrz", "validated": True},
            "nationality": {"value": "IND", "confidence": 0.98, "source": "mrz", "validated": True},
            "date_of_birth": {"value": "1988-11-20", "confidence": 0.98, "source": "mrz", "validated": True},
            "expiration_date": {"value": "2030-11-20", "confidence": 0.98, "source": "mrz", "validated": True},
        },
        "confidence": {"overall_composite": 1, "document_number": 1, "date_of_birth": 1, "expiration_date": 1},
    }

    validation_result = validate_document(ocr_result)
    assert validation_result["valid"] is True

    tampering_result = {
        "tampering_score": 10.0,
        "tampered": False,
        "signals": {"ela": 10.0, "photo_region": 0.0, "copy_move": 0.0, "stamp": 0.0, "cnn": 10.0, "metadata": 0.0},
        "checks": [],
    }

    # Face mismatch
    face_result = {
        "face_detected_document": True,
        "face_detected_selfie": True,
        "match": False,
        "matched": False,
        "similarity": 0.28,
        "distance": 0.72,
        "threshold": 0.40,
    }

    registry_result = {
        "registry_score": 80.0,
        "is_blacklisted": False,
        "is_duplicate": True,
        "flags": ["DUPLICATE IDENTITY CONFLICT: Document number P8888888 previously screened under name 'AMIT VERMA'"],
    }

    risk_res = compute_risk_score(
        validation_result=validation_result,
        tampering_result=tampering_result,
        face_result=face_result,
        registry_result=registry_result,
        quality_result={"quality_score": 90.0, "acceptable": True, "issues": []},
        ocr_result=ocr_result,
    )

    assert risk_res["risk_score"] >= 65.0
    assert risk_res["risk_label"] == "HIGH"
    assert risk_res["decision"] == "HOLD"
    assert any("DUPLICATE" in r or "MISMATCH" in r for r in risk_res["reasons"])
