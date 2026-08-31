"""
History and Audit Trail Routes (Digital Trail for Investigations & Intelligence).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import require_roles
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.database import ScreeningRecord, BlacklistedDocument
from app.models.schemas import (
    ScreeningHistoryListResponse,
    ScreeningHistoryItem,
    BlacklistCreateRequest,
    BlacklistResponse,
)

router = APIRouter(tags=["history_and_registry"])


@router.get("/api/history", response_model=ScreeningHistoryListResponse)
def get_screening_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns a paginated list of past document screening records, sorted most recent first.
    """
    query = db.query(ScreeningRecord)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (ScreeningRecord.document_number.ilike(search_pattern))
            | (ScreeningRecord.holder_name.ilike(search_pattern))
            | (ScreeningRecord.risk_label.ilike(search_pattern))
        )

    total = query.count()
    records = (
        query.order_by(ScreeningRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        ScreeningHistoryItem(
            id=r.id,
            document_type=r.document_type,
            document_number=r.document_number,
            holder_name=r.holder_name,
            risk_score=r.risk_score,
            risk_label=r.risk_label,
            flags=r.flags or [],
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in records
    ]

    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/api/history/{record_id}")
def get_screening_record_detail(record_id: str, db: Session = Depends(get_db)):
    """
    Returns full details for an individual historical screening audit trail.
    """
    record = db.query(ScreeningRecord).filter(ScreeningRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Screening record not found")
    return record.to_dict()


@router.post("/api/registry/blacklist", response_model=BlacklistResponse)
def add_to_blacklist(request: BlacklistCreateRequest, db: Session = Depends(get_db)):
    """
    Adds a document number to the security watch / blacklist registry.
    """
    doc_num = request.document_number.strip().upper()
    existing = db.query(BlacklistedDocument).filter(
        BlacklistedDocument.document_number == doc_num
    ).first()

    if existing:
        existing.reason = request.reason
        existing.country = request.country
        existing.document_type = request.document_type
        existing.severity = request.severity
        existing.status = request.status
        db.commit()
        db.refresh(existing)
        return existing.to_dict()

    entry = BlacklistedDocument(
        document_number=doc_num,
        reason=request.reason,
        country=request.country,
        document_type=request.document_type,
        severity=request.severity,
        status=request.status,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry.to_dict()


@router.get("/api/registry/blacklist", response_model=List[BlacklistResponse])
def list_blacklist(db: Session = Depends(get_db)):
    """
    Lists all blacklisted / flagged identity documents.
    """
    entries = db.query(BlacklistedDocument).order_by(BlacklistedDocument.added_at.desc()).all()
    return [e.to_dict() for e in entries]


@router.delete("/api/registry/blacklist/{document_number}")
def deactivate_blacklist(document_number: str, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin"))):
    entry = db.query(BlacklistedDocument).filter(BlacklistedDocument.document_number == document_number.strip().upper()).first()
    if not entry: raise HTTPException(status_code=404, detail="Blacklist entry not found")
    entry.status = "inactive"; db.commit()
    return {"deleted": True, "document_number": entry.document_number}
