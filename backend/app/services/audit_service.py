"""Append-only, hash-chained screening audit service.

Hash versioning:
  v1 (legacy): payload = {screening_id, timestamp, officer, document_hash,
                           risk (float), decision, modules}
  v2 (current): payload = {screening_id, timestamp, officer, document_hash,
                            document_type, risk_score, risk_category, decision,
                            modules, audit_hash_version}

New records always use v2.
The integrity checker understands both versions.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.database import AuditLog, ProcessingMetric


def _v1_payload(entry: AuditLog) -> Dict[str, Any]:
    """Reconstruct the v1 hash payload from a stored AuditLog row."""
    return {
        "screening_id": entry.screening_id,
        "timestamp": entry.timestamp,
        "officer": entry.officer,
        "document_hash": entry.document_hash,
        "risk": entry.risk,
        "decision": entry.decision,
        "modules": entry.modules,
    }


def _v2_payload(entry: "AuditLog | dict") -> Dict[str, Any]:
    """
    Full v2 payload covering risk_score, risk_category, document_type.
    Accepts either an AuditLog ORM object or a plain dict (for construction before DB insert).
    """
    if isinstance(entry, dict):
        return {
            "audit_hash_version": 2,
            "screening_id": entry.get("screening_id"),
            "timestamp": entry.get("timestamp"),
            "officer": entry.get("officer"),
            "document_hash": entry.get("document_hash"),
            "document_type": entry.get("document_type"),
            "risk_score": entry.get("risk_score"),
            "risk_category": entry.get("risk_category"),
            "decision": entry.get("decision"),
            "modules": entry.get("modules"),
        }
    return {
        "audit_hash_version": 2,
        "screening_id": entry.screening_id,
        "timestamp": entry.timestamp,
        "officer": entry.officer,
        "document_hash": entry.document_hash,
        "document_type": getattr(entry, "document_type", None),
        "risk_score": entry.risk_score,
        "risk_category": entry.risk_category,
        "decision": entry.decision,
        "modules": entry.modules,
    }


def _digest(payload: Dict[str, Any], previous_hash: str) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256((previous_hash + canonical).encode()).hexdigest()


def append_audit(
    db: Session,
    screening_id: str,
    officer: Optional[str],
    document_hash: str,
    risk: Dict[str, Any],
    modules: Dict[str, Any],
    duration_ms: float,
    document_type: Optional[str] = None,
) -> AuditLog:
    previous = db.query(AuditLog).order_by(AuditLog.created_at.desc()).first()
    previous_hash = previous.audit_hash if previous else "GENESIS"

    now = datetime.utcnow().isoformat()
    risk_score_val = float(risk.get("risk_score", 0))
    risk_category_val = risk.get("risk_category") or risk.get("decision")
    decision_val = risk.get("decision")
    modules_list = sorted(modules.keys()) if isinstance(modules, dict) else []

    # Build v2 payload dict for hashing
    payload_dict = {
        "audit_hash_version": 2,
        "screening_id": screening_id,
        "timestamp": now,
        "officer": officer,
        "document_hash": document_hash,
        "document_type": document_type,
        "risk_score": risk_score_val,
        "risk_category": risk_category_val,
        "decision": decision_val,
        "modules": modules_list,
    }

    entry = AuditLog(
        screening_id=screening_id,
        timestamp=now,
        officer=officer,
        document_hash=document_hash,
        document_type=document_type,
        risk=risk_score_val,               # legacy column, kept for compat
        risk_score=risk_score_val,
        risk_category=risk_category_val,
        decision=decision_val,
        modules=modules_list,
        processing_time_ms=duration_ms,
        previous_hash=previous_hash,
        audit_hash=_digest(payload_dict, previous_hash),
        audit_hash_version=2,
    )
    db.add(entry)
    return entry


def save_metrics(db: Session, screening_id: str, timings: Dict[str, float]) -> ProcessingMetric:
    metric = ProcessingMetric(screening_id=screening_id, timings=timings, total_ms=sum(timings.values()))
    db.add(metric)
    return metric


def verify_audit_chain(db: Session) -> bool:
    valid, _ = verify_audit_chain_with_count(db)
    return valid


def verify_audit_chain_with_count(db: Session) -> Tuple[bool, int]:
    """
    Verify the full audit chain.
    Supports both v1 (legacy) and v2 (current) hash formats.
    """
    previous_hash = "GENESIS"
    records = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()
    count = 0
    for entry in records:
        count += 1
        version = getattr(entry, "audit_hash_version", None) or 1
        if version >= 2:
            payload = _v2_payload(entry)
        else:
            payload = _v1_payload(entry)

        expected_hash = _digest(payload, previous_hash)
        if entry.previous_hash != previous_hash or entry.audit_hash != expected_hash:
            return False, count
        previous_hash = entry.audit_hash
    return True, count
