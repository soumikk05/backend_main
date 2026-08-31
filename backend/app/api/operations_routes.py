"""
Operations, Audit, Timeline, Heatmap, Metrics, and Aggregate Screening APIs.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.database import ScreeningRecord, AuditLog, ProcessingMetric
from app.services.audit_service import verify_audit_chain_with_count

router = APIRouter(tags=["operations"])


@router.get("/audit/integrity", summary="Verify full tamper-evident audit hash chain")
@router.get("/api/audit/integrity", summary="Verify full tamper-evident audit hash chain")
def audit_integrity(db: Session = Depends(get_db)):
    """
    Validates SHA-256 digital signature links across the entire audit log chain.
    """
    valid, count = verify_audit_chain_with_count(db)
    return {
        "valid": valid,
        "records_checked": count,
        "chain_intact": valid,
    }


@router.get("/audit/{screening_id}")
@router.get("/api/audit/{screening_id}")
def get_audit(screening_id: str, db: Session = Depends(get_db)):
    entry = db.query(AuditLog).filter(AuditLog.screening_id == screening_id).first()
    if not entry:
        raise HTTPException(404, "Audit entry not found")
    valid, count = verify_audit_chain_with_count(db)
    return {
        "screening_id": entry.screening_id,
        "audit_hash": entry.audit_hash,
        "previous_hash": entry.previous_hash,
        "chain_valid": valid,
        "records_checked": count,
        "risk": entry.risk_score,
        "decision": entry.decision,
        "modules": entry.modules,
        "processing_time_ms": entry.processing_time_ms,
        "timestamp": entry.timestamp,
        "officer": entry.officer,
    }


@router.get("/timeline/{screening_id}")
@router.get("/api/timeline/{screening_id}")
@router.get("/api/screening/{screening_id}/timeline")
def timeline(screening_id: str, db: Session = Depends(get_db)):
    metric = db.query(ProcessingMetric).filter(ProcessingMetric.screening_id == screening_id).first()
    if not metric:
        raise HTTPException(404, "Processing metrics not found for this screening ID")
    return {
        "screening_id": screening_id,
        "stages": metric.timings,
        "timings": metric.timings,
        "total_ms": metric.total_ms,
    }


@router.get("/metrics/{screening_id}")
@router.get("/api/metrics/{screening_id}")
def metrics(screening_id: str, db: Session = Depends(get_db)):
    return timeline(screening_id, db)


@router.get("/heatmap/{screening_id}")
@router.get("/api/heatmap/{screening_id}")
@router.get("/api/screening/{screening_id}/heatmap")
def heatmap(screening_id: str, db: Session = Depends(get_db)):
    record = db.query(ScreeningRecord).filter(ScreeningRecord.id == screening_id).first()
    if not record:
        raise HTTPException(404, "Screening record not found")
    tamp_result = record.tampering_result or {}
    return tamp_result.get("heatmap") or {
        "heatmap_available": False,
        "ela_heatmap_path": None,
        "regions": [],
        "bounding_boxes": [],
    }


@router.get("/api/dashboard/{screening_id}")
@router.get("/api/screening/{screening_id}/dashboard")
@router.get("/api/screening/{screening_id}")
def aggregate_screening_dashboard(screening_id: str, db: Session = Depends(get_db)):
    """
    Backend Aggregate Screening API returning all document, OCR, validation,
    tampering, biometric, registry, risk, timeline, and audit data in one consolidated response.
    """
    record = db.query(ScreeningRecord).filter(ScreeningRecord.id == screening_id).first()
    if not record:
        raise HTTPException(404, "Screening record not found")

    metric = db.query(ProcessingMetric).filter(ProcessingMetric.screening_id == screening_id).first()
    audit = db.query(AuditLog).filter(AuditLog.screening_id == screening_id).first()
    tamp = record.tampering_result or {}

    return {
        "screening_id": record.id,
        "document_info": {
            "document_type": record.document_type,
            "document_number": record.document_number,
            "holder_name": record.holder_name,
            "image_hash": record.image_hash,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        },
        "risk_summary": {
            "risk_score": record.risk_score,
            "risk_label": record.risk_label,
            "flags": record.flags or [],
        },
        "status_cards": {
            "risk": record.risk_label,
            "tampering": tamp.get("tampering_score", 0.0),
            "face": (record.face_result or {}).get("match"),
            "validation": (record.validation_result or {}).get("overall_valid"),
        },
        "module_outputs": {
            "ocr": record.extracted_fields,
            "validation": record.validation_result,
            "tampering": record.tampering_result,
            "face": record.face_result,
            "registry": record.registry_result,
        },
        "heatmaps": tamp.get("heatmap") or {},
        "timeline": metric.timings if metric else {},
        "audit": {
            "audit_hash": audit.audit_hash if audit else None,
            "previous_hash": audit.previous_hash if audit else None,
            "timestamp": audit.timestamp if audit else None,
            "officer": audit.officer if audit else None,
        },
    }
