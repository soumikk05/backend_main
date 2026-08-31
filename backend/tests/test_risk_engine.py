"""
Unit tests for Risk Scoring Engine (Module 5).
"""

import pytest
from app.services.risk_engine import compute_risk_score


def test_clean_screening_returns_low_risk():
    val_res = {"checks": [{"name": "mrz_checksum", "passed": True}], "fail_count": 0}
    tamp_res = {"tampering_score": 0.0, "checks": []}
    face_res = {"match": True, "distance": 0.15, "threshold": 0.40}
    reg_res = {"is_blacklisted": False, "is_duplicate": False, "registry_score": 0.0, "flags": []}

    res = compute_risk_score(val_res, tamp_res, face_res, reg_res)
    assert res["risk_score"] <= 30
    assert res["risk_label"] == "LOW"


def test_blacklist_hit_overrides_to_high_risk():
    val_res = {"checks": [{"name": "mrz_checksum", "passed": True}], "fail_count": 0}
    tamp_res = {"tampering_score": 0.0, "checks": []}
    face_res = {"match": True}
    reg_res = {
        "is_blacklisted": True,
        "is_duplicate": False,
        "registry_score": 100.0,
        "flags": ["BLACKLIST HIT: Stolen document"],
    }

    res = compute_risk_score(val_res, tamp_res, face_res, reg_res)
    assert res["risk_score"] >= 85
    assert res["risk_label"] == "HIGH"
    assert any("BLACKLIST" in f for f in res["flags"])


def test_face_mismatch_and_tampering_elevates_risk():
    val_res = {"checks": [{"name": "mrz_checksum", "passed": True}], "fail_count": 0}
    tamp_res = {"tampering_score": 80.0, "checks": [{"name": "ela", "triggered": True, "detail": "ELA high error"}]}
    face_res = {"match": False, "distance": 0.85, "threshold": 0.40}

    res = compute_risk_score(val_res, tamp_res, face_res, None)
    assert res["risk_label"] in ["MEDIUM", "HIGH"]
    assert res["risk_score"] > 30
