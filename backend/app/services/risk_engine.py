"""
Risk Scoring Engine V2 (Module 5).

Consolidates all AI, forensic, OCR, biometric, and registry intelligence into an explainable assessment:
  - Validation & MRZ checksum checks (Module 2)
  - Forensic & CNN tampering signals (Module 3)
  - Biometric face verification & software liveness (Module 4)
  - Intelligence registry & watchlist checks (Module 6)
  - Image quality and OCR confidence intake signals

Threshold Mapping (Configurable):
  0 - 30   : CLEAR   (Action: ALLOW)
  31 - 60  : REVIEW  (Action: MANUAL_REVIEW)
  61 - 100 : HOLD    (Action: HOLD_FOR_INVESTIGATION)

Adheres strictly to AI-Assisted Screening principles: produces risk signals and evidence
for human officer review, never automated extra-judicial decisions.
"""

from typing import Any, Dict, List, Optional

from app.config import (
    RISK_WEIGHT_VALIDATION,
    RISK_WEIGHT_TAMPERING,
    RISK_WEIGHT_FACE_MISMATCH,
    RISK_WEIGHT_REGISTRY,
    FACE_MISMATCH_RISK_POINTS,
    FACE_NO_SELFIE_RISK_POINTS,
    IDENTITY_CLUSTER_THRESHOLD_LOW,
    IDENTITY_CLUSTER_THRESHOLD_MED,
    IDENTITY_CLUSTER_THRESHOLD_HIGH,
    RISK_CLUSTER_LOW_POINTS,
    RISK_CLUSTER_MED_POINTS,
    RISK_CLUSTER_HIGH_POINTS,
)


def compute_risk_score(
    validation_result: Optional[Dict[str, Any]],
    tampering_result: Optional[Dict[str, Any]],
    face_result: Optional[Dict[str, Any]],
    registry_result: Optional[Dict[str, Any]] = None,
    quality_result: Optional[Dict[str, Any]] = None,
    metadata_result: Optional[Dict[str, Any]] = None,
    liveness_result: Optional[Dict[str, Any]] = None,
    ocr_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for Risk Engine V2.
    """
    hard_security_flags: List[str] = []
    forensic_flags: List[str] = []
    quality_flags: List[str] = []
    unperformed_checks: List[str] = []
    all_reasons: List[str] = []

    # 1. Validation Scoring
    validation_component, val_flags = _score_validation(validation_result)
    for flag in val_flags:
        if "FAILED" in flag.upper() or "MISMATCH" in flag.upper() or "EXPIRED" in flag.upper():
            hard_security_flags.append(flag)
        else:
            all_reasons.append(flag)

    # 2. Tampering Scoring
    tampering_component, tamp_flags = _score_tampering(tampering_result)
    for flag in tamp_flags:
        if "PHOTO" in flag.upper() or "COPY_MOVE" in flag.upper() or "SEAM" in flag.upper():
            hard_security_flags.append(flag)
        else:
            forensic_flags.append(flag)

    # 3. Biometrics / Face Verification
    face_component, face_flags, face_unperformed = _score_face(face_result)
    hard_security_flags.extend(face_flags)
    if face_unperformed:
        unperformed_checks.append(face_unperformed)

    # 4. Registry / Blacklist & Multiple Identity
    registry_component, reg_flags = _score_registry(registry_result)
    hard_security_flags.extend(reg_flags)

    # 4b. Identity Cluster / Multiple Identity Detection
    cluster_component, cluster_flags = _score_identity_cluster(face_result)
    if cluster_flags:
        hard_security_flags.extend(cluster_flags)

    # 5. Quality & OCR Intake
    quality_component, q_flags = _score_quality(quality_result)
    quality_flags.extend(q_flags)

    liveness_component, live_flags, live_unperformed = _score_liveness(liveness_result)
    if live_flags:
        hard_security_flags.extend(live_flags)
    if live_unperformed:
        unperformed_checks.append(live_unperformed)

    ocr_component, ocr_flags = _score_ocr(ocr_result)
    quality_flags.extend(ocr_flags)

    # Compile combined reason list
    all_reasons.extend(hard_security_flags)
    all_reasons.extend(forensic_flags)
    all_reasons.extend(quality_flags)

    # Weighted Base Score
    base_risk_score = (
        validation_component * RISK_WEIGHT_VALIDATION
        + tampering_component * RISK_WEIGHT_TAMPERING
        + face_component * RISK_WEIGHT_FACE_MISMATCH
        + registry_component * RISK_WEIGHT_REGISTRY
    )

    # Supplemental intake contributions (including identity cluster)
    raw_risk_score = min(
        100.0,
        base_risk_score
        + quality_component * 0.08
        + liveness_component * 0.10
        + ocr_component * 0.07
        + cluster_component  # identity cluster adds directly (already scaled to points)
    )

    # Hard security overrides:
    # Blacklist, photo replacement, or verified face mismatch must trigger HIGH risk / HOLD decision
    is_blacklisted = registry_result and registry_result.get("is_blacklisted", False)
    is_photo_replaced = tampering_result and any(
        c.get("name") == "photo_region_analysis" and c.get("triggered")
        for c in tampering_result.get("checks", [])
    )
    is_face_mismatched = face_result and face_result.get("match") is False

    if is_blacklisted:
        raw_risk_score = max(raw_risk_score, 88.0)
    if is_photo_replaced:
        raw_risk_score = max(raw_risk_score, 80.0)
    if is_face_mismatched:
        raw_risk_score = max(raw_risk_score, 75.0)

    final_risk_score = round(min(100.0, max(0.0, raw_risk_score)), 2)

    risk_label, decision = _decision_for_score(final_risk_score)
    risk_category = decision  # CLEAR | REVIEW | HOLD
    breakdown = {
        "validation": round(validation_component, 2),
        "tampering": round(tampering_component, 2),
        "face": round(face_component, 2),
        "registry": round(registry_component, 2),
        "identity_cluster": round(cluster_component, 2),
        "quality": round(quality_component, 2),
        "liveness": round(liveness_component, 2),
        "ocr_confidence": round(ocr_component, 2),
    }

    evidence = {
        "validation": validation_result,
        "tampering": tampering_result,
        "face": face_result,
        "registry": registry_result,
        "quality": quality_result,
        "metadata": metadata_result,
        "liveness": liveness_result,
        "hard_security_flags": hard_security_flags,
        "forensic_signals": forensic_flags,
        "quality_warnings": quality_flags,
        "unperformed_checks": unperformed_checks,
    }

    flags_output = all_reasons if all_reasons else ["No security anomalies detected across screening signals"]

    return {
        "risk_score": final_risk_score,
        "risk_label": risk_label,
        "risk_category": risk_category,
        "decision": decision,
        "component_scores": breakdown,
        "breakdown": breakdown,
        "flags": flags_output,
        "reasons": flags_output,
        "evidence": evidence,
        "modules": {
            "validation": validation_result,
            "tampering": tampering_result,
            "face": face_result,
            "registry": registry_result,
            "quality": quality_result,
            "metadata": metadata_result,
            "liveness": liveness_result,
        },
        "explanation": _explain(risk_label, all_reasons, unperformed_checks),
    }


def _score_validation(result: Optional[Dict[str, Any]]) -> tuple[float, List[str]]:
    flags: List[str] = []
    if not result or not result.get("checks"):
        return 0.0, flags

    checks = result["checks"]
    failed = [c for c in checks if not c.get("passed")]
    total = len(checks)

    for check in failed:
        flags.append(f"Validation: {check.get('message', check.get('reason', check.get('name')))}")

    component = (len(failed) / total * 100.0) if total > 0 else 0.0
    return component, flags


def _score_tampering(result: Optional[Dict[str, Any]]) -> tuple[float, List[str]]:
    flags: List[str] = []
    if not result:
        return 0.0, flags

    if result.get("error"):
        flags.append(f"Tampering analysis error: {result['error']}")
        return 0.0, flags

    for check in result.get("checks", []):
        if check.get("triggered"):
            flags.append(f"Tampering: {check.get('detail', check.get('name'))}")

    component = float(result.get("tampering_score", 0.0))
    return component, flags


def _score_face(result: Optional[Dict[str, Any]]) -> tuple[float, List[str], Optional[str]]:
    flags: List[str] = []
    if not result:
        return FACE_NO_SELFIE_RISK_POINTS, flags, "FACE_VERIFICATION_NOT_PERFORMED (No live selfie photo uploaded)"

    if result.get("error"):
        error_msg = str(result["error"])
        flags.append(f"Face verification issue: {error_msg}")
        return FACE_NO_SELFIE_RISK_POINTS, flags, None

    if result.get("match") is True:
        return 0.0, flags, None

    if result.get("match") is False:
        flags.append(
            f"Face mismatch detected (cosine similarity: {result.get('similarity', 0.0):.2f}, threshold: {result.get('threshold', 0.40):.2f})"
        )
        return FACE_MISMATCH_RISK_POINTS, flags, None

    return 0.0, flags, "FACE_VERIFICATION_INCONCLUSIVE"


def _score_registry(result: Optional[Dict[str, Any]]) -> tuple[float, List[str]]:
    flags: List[str] = []
    if not result:
        return 0.0, flags

    flags.extend(result.get("flags", []))
    score = float(result.get("registry_score", 0.0))
    return score, flags


def _score_identity_cluster(face_result: Optional[Dict[str, Any]]) -> tuple[float, List[str]]:
    """
    Compute a risk contribution from multiple-identity detection.

    Tiered policy (configurable via config.py):
      < THRESHOLD_LOW  (0.82): no cluster risk
      0.82 - 0.90     -> RISK_CLUSTER_LOW_POINTS  (15)
      0.90 - 0.95     -> RISK_CLUSTER_MED_POINTS  (25)
      >= 0.95         -> RISK_CLUSTER_HIGH_POINTS (35)

    Wording: POTENTIAL IDENTITY CONFLICT (not 'criminal', 'terrorist', etc.)
    """
    flags: List[str] = []
    if not face_result:
        return 0.0, flags

    cluster = face_result.get("identity_cluster")
    if not cluster or not cluster.get("suspicious"):
        return 0.0, flags

    matches = cluster.get("matches", [])
    if not matches:
        return 0.0, flags

    # Use the highest similarity score among matches
    max_sim = max((float(m.get("similarity", 0.0)) for m in matches), default=0.0)

    if max_sim >= IDENTITY_CLUSTER_THRESHOLD_HIGH:   # >= 0.95
        points = RISK_CLUSTER_HIGH_POINTS
        confidence_label = "HIGH"
    elif max_sim >= IDENTITY_CLUSTER_THRESHOLD_MED:  # 0.90 - 0.95
        points = RISK_CLUSTER_MED_POINTS
        confidence_label = "MEDIUM"
    elif max_sim >= IDENTITY_CLUSTER_THRESHOLD_LOW:  # 0.82 - 0.90
        points = RISK_CLUSTER_LOW_POINTS
        confidence_label = "LOW"
    else:
        return 0.0, flags

    flags.append(
        f"POTENTIAL IDENTITY CONFLICT: face similarity {max_sim:.3f} with existing registry entry "
        f"(confidence={confidence_label}, risk_contribution={points:.0f} points)"
    )
    return points, flags


def _score_quality(result: Optional[Dict[str, Any]]) -> tuple[float, List[str]]:
    if not result:
        return 0.0, []
    score = 100.0 - float(result.get("quality_score", 100.0))
    issues = result.get("issues", [])
    return score, [f"Image quality issue: {issue}" for issue in issues]


def _score_liveness(result: Optional[Dict[str, Any]]) -> tuple[float, List[str], Optional[str]]:
    if not result:
        return 0.0, [], "LIVENESS_CHECK_NOT_PERFORMED (No selfie submitted)"
    if not result.get("passed", True):
        return 100.0 - float(result.get("liveness_score", 0.0)), [f"Liveness challenge did not pass ({result.get('challenge')})"], None
    return 100.0 - float(result.get("liveness_score", 100.0)), [], None


def _score_ocr(result: Optional[Dict[str, Any]]) -> tuple[float, List[str]]:
    if not result:
        return 0.0, []
    fields = result.get("fields", {}) or {}
    confs = [
        item.get("confidence") for item in fields.values()
        if isinstance(item, dict) and isinstance(item.get("confidence"), (int, float))
    ]
    if not confs:
        return 0.0, []
    avg = sum(confs) / len(confs)
    return (1.0 - avg) * 100.0, (["OCR confidence is below 0.60"] if avg < 0.60 else [])


def _decision_for_score(score: float) -> tuple[str, str]:
    if score <= 30.0:
        return "LOW", "CLEAR"
    if score <= 60.0:
        return "MEDIUM", "REVIEW"
    return "HIGH", "HOLD"


def _explain(label: str, flags: List[str], unperformed: List[str]) -> str:
    if not flags:
        summary = "Document screening passed with no flagged anomalies."
    else:
        summary = f"{label} risk assessment: " + "; ".join(flags[:4]) + "."
    if unperformed:
        summary += f" Notice: {', '.join(unperformed)}."
    return summary
