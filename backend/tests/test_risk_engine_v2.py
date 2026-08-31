from app.services.risk_engine import compute_risk_score


def test_risk_v2_returns_decision_evidence_and_explanation():
    result = compute_risk_score(
        {"checks": [{"passed": True}], "fail_count": 0},
        {"tampering_score": 0, "checks": []}, None,
        {"registry_score": 0, "flags": []},
        quality_result={"quality_score": 90, "issues": ["glare"]},
        ocr_result={"fields": {"name": {"confidence": .9}}},
    )
    assert result["risk_category"] in {"CLEAR", "REVIEW", "HOLD"}
    assert result["decision"]
    assert result["explanation"]
    assert "quality" in result["component_scores"]
