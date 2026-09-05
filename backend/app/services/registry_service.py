"""
Registry and Intelligence Analysis Service (Module 6 Enhancement).
"""

import logging
import math
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.config import REGISTRY_BLACKLIST_HIT_POINTS, REGISTRY_DUPLICATE_HIT_POINTS
from app.models.database import BlacklistedDocument, ScreeningRecord, FaceEmbedding, IdentityCluster
from app.services.privacy_service import lookup_hash, normalize_doc_number
from app.services.cross_document_service import _normalize_date_str, _compare_dates_normalized, _compare_names_fuzzy

logger = logging.getLogger(__name__)


def check_blacklist(
    document_number: Optional[str],
    db: Optional[Session] = None,
    document_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Checks if a document identifier is present on the simulated security blacklist registry.
    Handles db passed positionally as second parameter or kwargs.
    """
    if isinstance(document_type, Session) and db is None:
        db = document_type
        document_type = None

    if not document_number or db is None:
        return {"is_blacklisted": False, "reason": None, "country": None, "flags": [], "severity": "none"}

    try:
        clean_doc = document_number.strip().upper()
        query = db.query(BlacklistedDocument).filter(
            BlacklistedDocument.document_number == clean_doc,
            BlacklistedDocument.status == "active"
        )
        if document_type:
            type_match = query.filter(BlacklistedDocument.document_type == document_type.lower()).first()
            match = type_match or query.first()
        else:
            match = query.first()

        if match:
            flag = f"BLACKLIST HIT: Document identifier {clean_doc} is flagged on watchlist ({match.reason}, severity: {match.severity})"
            return {
                "is_blacklisted": True,
                "reason": match.reason,
                "country": match.country,
                "document_type": match.document_type,
                "severity": match.severity,
                "flags": [flag],
            }

        return {"is_blacklisted": False, "reason": None, "country": None, "flags": [], "severity": "none"}
    except Exception as exc:
        logger.warning("Blacklist check query failed: %s", exc)
        return {"is_blacklisted": False, "reason": None, "country": None, "flags": [f"Blacklist check skipped: {exc}"], "severity": "none"}


def check_duplicate_identity(
    document_number: Optional[str],
    holder_name: Optional[str],
    image_hash: Optional[str],
    db: Optional[Session] = None,
    date_of_birth: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Screens historical records to detect duplicate identity and replay fraud patterns:
      - Same document number previously screened under a different holder name.
      - Same document number or holder name previously screened with a conflicting date of birth.
      - Same person name previously associated with a different document number.
      - Exact document image re-used under a different document number (Replay Attack).
    """
    if db is None:
        return {"is_duplicate": False, "matched_record_ids": [], "flags": []}

    flags: List[str] = []
    matched_ids: List[str] = []
    is_duplicate = False

    try:
        clean_doc = normalize_doc_number(document_number)
        clean_name = holder_name.strip() if holder_name else None
        clean_dob = _normalize_date_str(date_of_birth)

        # Pattern 1: Same document number with different holder name or altered DOB
        if clean_doc:
            doc_h = lookup_hash(clean_doc)
            prior_records = db.query(ScreeningRecord).filter(
                (ScreeningRecord.document_number == clean_doc) | 
                (ScreeningRecord.document_number_hash == doc_h)
            ).limit(10).all()

            for rec in prior_records:
                prior_name = rec.holder_name
                if clean_name and prior_name:
                    name_match, _ = _compare_names_fuzzy(clean_name, prior_name)
                    if not name_match:
                        is_duplicate = True
                        matched_ids.append(rec.id)
                        flags.append(
                            f"DUPLICATE IDENTITY CONFLICT: Document number {clean_doc} previously screened under name '{rec.holder_name}'"
                        )

                # Pattern 1b: Same document number with conflicting date of birth
                prior_dob = _normalize_date_str(rec.date_of_birth)
                if clean_dob and prior_dob and not _compare_dates_normalized(clean_dob, prior_dob):
                    is_duplicate = True
                    matched_ids.append(rec.id)
                    flags.append(
                        f"CRITICAL_TAMPERING_CONFLICT: Document number {clean_doc} previously screened with date of birth '{prior_dob}', now presented with forged date of birth '{clean_dob}'"
                    )

        # Pattern 2: Same person name with different document number
        if clean_name and len(clean_name) > 3:
            name_h = lookup_hash(clean_name)
            prior_name_records = db.query(ScreeningRecord).filter(
                (ScreeningRecord.holder_name == clean_name) | 
                (ScreeningRecord.holder_name_hash == name_h)
            ).limit(10).all()

            for rec in prior_name_records:
                prior_doc = normalize_doc_number(rec.document_number)
                if clean_doc and prior_doc and prior_doc != clean_doc:
                    is_duplicate = True
                    matched_ids.append(rec.id)
                    flags.append(
                        f"POTENTIAL MULTIPLE IDENTITIES: Person '{holder_name}' was previously screened with different document number '{rec.document_number}'"
                    )

                # Pattern 2b: Same name, but conflicting date of birth (possible impersonation)
                prior_dob = _normalize_date_str(rec.date_of_birth)
                if clean_dob and prior_dob and not _compare_dates_normalized(clean_dob, prior_dob):
                    is_duplicate = True
                    matched_ids.append(rec.id)
                    flags.append(
                        f"IDENTITY DOB MISMATCH: Person '{holder_name}' previously screened with date of birth '{prior_dob}', now presented as '{clean_dob}'"
                    )

        # Pattern 3: Image replay hash collision with different document number
        if image_hash:
            prior_hash_records = db.query(ScreeningRecord).filter(
                ScreeningRecord.image_hash == image_hash
            ).limit(10).all()

            for rec in prior_hash_records:
                prior_doc = (rec.document_number or "").strip().upper()
                if clean_doc and prior_doc and prior_doc != clean_doc:
                    is_duplicate = True
                    matched_ids.append(rec.id)
                    flags.append(
                        f"IMAGE REPLAY DETECTED: Identical document image previously screened as document '{rec.document_number}'"
                    )

        return {
            "is_duplicate": is_duplicate,
            "matched_record_ids": list(set(matched_ids)),
            "flags": list(dict.fromkeys(flags)),
        }
    except Exception as exc:
        logger.warning("Duplicate identity check query failed: %s", exc)
        return {"is_duplicate": False, "matched_record_ids": [], "flags": [f"Duplicate check skipped: {exc}"]}


def screen_registry(
    document_number: Optional[str],
    holder_name: Optional[str],
    image_hash: Optional[str],
    db: Optional[Session] = None,
    document_type: Optional[str] = None,
    date_of_birth: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Consolidated registry check combining blacklist and duplicate detection.
    """
    blacklist_res = check_blacklist(document_number, db=db, document_type=document_type)
    duplicate_res = check_duplicate_identity(document_number, holder_name, image_hash, db=db, date_of_birth=date_of_birth)

    flags = blacklist_res.get("flags", []) + duplicate_res.get("flags", [])
    is_blacklisted = blacklist_res.get("is_blacklisted", False)
    is_duplicate = duplicate_res.get("is_duplicate", False)

    registry_score = 0.0
    if is_blacklisted:
        severity = blacklist_res.get("severity", "medium")
        registry_score = 100.0 if severity == "high" else REGISTRY_BLACKLIST_HIT_POINTS
    elif is_duplicate:
        registry_score = REGISTRY_DUPLICATE_HIT_POINTS

    return {
        "registry_score": registry_score,
        "is_blacklisted": is_blacklisted,
        "is_duplicate": is_duplicate,
        "blacklist_detail": blacklist_res,
        "duplicate_detail": duplicate_res,
        "flags": flags,
    }


def register_face_embedding(person_id: str, vector: List[float], embedding_hash: str, db: Session) -> Optional[str]:
    """Store biometric embedding in the identity registry."""
    if not vector or not embedding_hash:
        return None
    existing = db.query(FaceEmbedding).filter(FaceEmbedding.embedding_hash == embedding_hash).first()
    if existing:
        return existing.embedding_id
    record = FaceEmbedding(person_id=person_id, embedding_vector=vector, embedding_hash=embedding_hash)
    db.add(record)
    db.flush()
    return record.embedding_id


def detect_identity_cluster(
    person_id: str,
    document_number: Optional[str],
    holder_name: Optional[str],
    vector: List[float],
    db: Optional[Session],
    threshold: float = 0.82,
) -> Dict[str, Any]:
    """
    Nearest-neighbor biometric scan: flags if the same face embedding was previously associated
    with conflicting identities (Potential Identity Conflict).
    """
    if db is None or not vector:
        return {"suspicious": False, "potential_multiple_identity": False, "matches": [], "flags": []}

    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    matches: List[Dict[str, Any]] = []
    flags: List[str] = []

    for record in db.query(FaceEmbedding).limit(500).all():
        other = record.embedding_vector or []
        if len(other) != len(vector):
            continue
        other_norm = math.sqrt(sum(v * v for v in other)) or 1.0
        similarity = sum(a * b for a, b in zip(vector, other)) / (norm * other_norm)

        if similarity >= threshold and str(record.person_id) != str(person_id):
            matches.append({
                "person_id": record.person_id,
                "similarity": round(similarity, 4),
                "confidence": round(similarity, 4),
            })
            flags.append(
                f"POTENTIAL_MULTIPLE_IDENTITY: Face similarity {similarity:.2f} with previously registered identity '{record.person_id}'"
            )

    has_conflict = len(flags) > 0
    if has_conflict:
        db.add(IdentityCluster(
            person_id=person_id,
            document_number=document_number,
            holder_name=holder_name,
            evidence={"matches": matches, "flags": flags},
        ))

    return {
        "suspicious": has_conflict,
        "potential_multiple_identity": has_conflict,
        "matches": matches,
        "flags": flags,
    }