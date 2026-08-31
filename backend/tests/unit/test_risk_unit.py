"""Unit tests for Risk Engine V2 and Uncertainty Handling (Requirements 21, 22, 43)."""
import pytest
from app.services.risk_engine import compute_risk_score


def test_risk_clean_document_clear_decision():
    res = compute_risk_score(
        validation_result={"checks": [{"passed": True, "name": "c1"}], "fail_count": 0},
        tampering_result={"tampering_score": 5.0, "checks": []},
        face_result={"match": True, "similarity": 0.95},
        registry_result={"registry_score": 0.0, "is_blacklisted": False, "is_duplicate": False, "flags": []},
        quality_result={"quality_score": 95.0, "issues": []},
        ocr_result={"fields": {"document_number": {"confidence": 0.98}}},
    )
    assert res["risk_score"] <= 30.0
    assert res["risk_label"] == "LOW"
    assert res["decision"] == "CLEAR"
    assert "breakdown" in res
    assert "evidence" in res


def test_risk_blacklist_hit_triggers_hold():
    res = compute_risk_score(
        validation_result={"checks": [{"passed": True}], "fail_count": 0},
        tampering_result={"tampering_score": 0.0, "checks": []},
        face_result=None,
        registry_result={"registry_score": 100.0, "is_blacklisted": True, "is_duplicate": False, "flags": ["BLACKLIST HIT"]},
    )
    assert res["risk_score"] >= 80.0
    assert res["risk_label"] == "HIGH"
    assert res["decision"] == "HOLD"


def test_risk_uncertainty_no_selfie_not_treated_as_mismatch():
    res = compute_risk_score(
        validation_result={"checks": [{"passed": True}], "fail_count": 0},
        tampering_result={"tampering_score": 0.0, "checks": []},
        face_result=None,
        registry_result={"registry_score": 0.0, "is_blacklisted": False, "is_duplicate": False, "flags": []},
    )
    # Score should remain low/clear because missing selfie is not a mismatch
    assert res["risk_score"] <= 30.0
    assert "FACE_VERIFICATION_NOT_PERFORMED" in res["evidence"]["unperformed_checks"][0]
