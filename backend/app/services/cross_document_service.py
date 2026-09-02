"""
Identity Resolution and Cross-Document Consistency Comparison Services.

Provides:
1. Candidate Identity Resolution:
   - Resolves or instantiates canonical Person and Document records.
   - NEVER merges identities by name alone. Uses document number/hash, DOB, nationality,
     or high-confidence biometric face similarity.
2. Cross-Document Consistency Checking:
   - Retrieves historical documents for candidate person.
   - Compares current extracted fields against VERIFIED historical documents.
   - Treats UNVERIFIED historical documents strictly as informational (does not trigger high-severity flags).
   - Generates confidence-aware CrossDocumentComparison rows and risk contribution.
"""

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import (
    CROSS_DOC_DOB_MISMATCH_POINTS,
    CROSS_DOC_NAME_MISMATCH_POINTS,
    CROSS_DOC_GENERIC_MISMATCH_POINTS,
    CROSS_DOC_UNVERIFIED_MISMATCH_POINTS,
    CROSS_DOC_MIN_CONFIDENCE_THRESHOLD,
    CROSS_DOC_IDENTITY_LINK_FACE_THRESHOLD,
)
from app.models.database import Person, Document, CrossDocumentComparison, FaceEmbedding
from app.services.privacy_service import lookup_hash, encrypt_value, mask_identifier

logger = logging.getLogger(__name__)


def resolve_candidate_identity_and_document(
    db: Session,
    document_type: str,
    document_number: Optional[str],
    holder_name: Optional[str],
    date_of_birth: Optional[str],
    nationality: Optional[str] = None,
    gender: Optional[str] = None,
    image_hash: Optional[str] = None,
    evidence_path: Optional[str] = None,
    face_vector: Optional[List[float]] = None,
) -> Tuple[Person, Document, bool]:
    """
    Resolves or creates Person and Document entities.
    
    Identity Linkage Rules:
    - If document_number matches an existing Document, reuse that Document and its Person.
    - If no document match, check if a Person matches by BOTH (DOB + nationality/exact hash)
      OR by strong biometric face vector (cosine >= CROSS_DOC_IDENTITY_LINK_FACE_THRESHOLD).
    - NEVER merge identities by holder name alone.
    
    Returns:
        (person, document, is_repeat_document)
    """
    clean_doc = (document_number or "").strip().upper() if document_number else None
    doc_hash = lookup_hash(clean_doc) if clean_doc else None
    name_hash = lookup_hash(holder_name) if holder_name else None

    person: Optional[Person] = None
    document: Optional[Document] = None
    is_repeat = False

    # 1. Check if the exact document already exists in DB
    if doc_hash:
        document = db.query(Document).filter(Document.document_number_hash == doc_hash).first()
        if document:
            is_repeat = True
            if document.person_id:
                person = db.query(Person).filter(Person.id == document.person_id).first()

    # 2. Biometric-assisted person resolution if face vector is provided
    if not person and face_vector:
        norm = math.sqrt(sum(v * v for v in face_vector)) or 1.0
        best_sim = 0.0
        best_person_id = None

        for emb in db.query(FaceEmbedding).limit(300).all():
            other = emb.embedding_vector or []
            if len(other) != len(face_vector):
                continue
            other_norm = math.sqrt(sum(v * v for v in other)) or 1.0
            sim = sum(a * b for a, b in zip(face_vector, other)) / (norm * other_norm)
            if sim > best_sim:
                best_sim = sim
                best_person_id = emb.person_id

        if best_sim >= CROSS_DOC_IDENTITY_LINK_FACE_THRESHOLD and best_person_id:
            # Check if this person_id corresponds to a Person record
            candidate_p = db.query(Person).filter(Person.id == str(best_person_id)).first()
            if candidate_p:
                person = candidate_p
                logger.info("Resolved candidate person %s via biometric similarity %.3f", person.id, best_sim)

    # 3. DOB + nationality linkage if both match an existing verified person
    if not person and date_of_birth and nationality:
        candidate_p = db.query(Person).filter(
            Person.date_of_birth == date_of_birth,
            Person.nationality == nationality.upper(),
            Person.primary_name_hash == name_hash,
        ).first()
        if candidate_p:
            person = candidate_p
            logger.info("Resolved candidate person %s via DOB+Nationality+NameHash match", person.id)

    # 4. If person still not found, create an UNVERIFIED candidate Person
    if not person:
        person = Person(
            primary_name=holder_name,
            primary_name_hash=name_hash,
            date_of_birth=date_of_birth,
            nationality=nationality.upper() if nationality else None,
            gender=gender.upper() if gender else None,
            verification_status="UNVERIFIED",
        )
        db.add(person)
        db.flush()

    # 5. If document not found, create persistent Document record
    if not document:
        document = Document(
            person_id=person.id,
            document_type=document_type.lower() if document_type else "unknown",
            document_number=mask_identifier(clean_doc) if clean_doc else None,
            document_number_encrypted=encrypt_value(clean_doc) if clean_doc else None,
            document_number_hash=doc_hash,
            issuing_country=nationality.upper() if nationality else None,
            verification_status="UNVERIFIED",
            primary_image_hash=image_hash,
            evidence_file_path=evidence_path,
        )
        db.add(document)
        db.flush()
    else:
        # If document existed but didn't have person_id attached, link it
        if not document.person_id and person:
            document.person_id = person.id
            db.flush()

    return person, document, is_repeat


def compare_cross_document_consistency(
    db: Session,
    person: Person,
    current_document: Document,
    current_extracted_fields: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], float, List[str]]:
    """
    Compares extracted fields of the current document against historical documents for the same person.
    
    Rules:
    - Only historical documents with verification_status == 'VERIFIED' generate strong security contradictions.
    - Historical documents with 'UNVERIFIED' status generate low-severity informational flags only.
    - Low-confidence OCR extractions (below CROSS_DOC_MIN_CONFIDENCE_THRESHOLD) are annotated
      and do not heavily penalize risk.
      
    Returns:
        (comparisons_data_list, total_risk_points, flags)
    """
    if not person or not current_document:
        return [], 0.0, []

    # Find historical documents for this person excluding the current document
    historical_docs = db.query(Document).filter(
        Document.person_id == person.id,
        Document.id != current_document.id,
    ).all()

    if not historical_docs:
        return [], 0.0, []

    comparisons: List[Dict[str, Any]] = []
    total_risk_points = 0.0
    flags: List[str] = []

    # Prioritize VERIFIED documents as authoritative ground truth
    verified_docs = [d for d in historical_docs if d.verification_status == "VERIFIED"]
    candidate_docs = verified_docs if verified_docs else historical_docs

    for hist_doc in candidate_docs:
        is_authoritative = (hist_doc.verification_status == "VERIFIED")
        
        # We look up prior screenings for hist_doc to get its extracted_fields
        prior_screening = hist_doc.screenings[-1] if hist_doc.screenings else None
        prior_fields = prior_screening.extracted_fields if prior_screening else {}

        # 1. Compare Date of Birth (DOB)
        curr_dob_info = current_extracted_fields.get("date_of_birth") or current_extracted_fields.get("dob")
        curr_dob = None
        curr_dob_conf = 1.0
        if isinstance(curr_dob_info, dict):
            curr_dob = str(curr_dob_info.get("value", "")).strip()
            curr_dob_conf = float(curr_dob_info.get("confidence", 1.0))
        elif isinstance(curr_dob_info, str):
            curr_dob = curr_dob_info.strip()

        trusted_dob_info = prior_fields.get("date_of_birth") or prior_fields.get("dob")
        trusted_dob = None
        trusted_dob_conf = 1.0
        if isinstance(trusted_dob_info, dict):
            trusted_dob = str(trusted_dob_info.get("value", "")).strip()
            trusted_dob_conf = float(trusted_dob_info.get("confidence", 1.0))
        elif isinstance(trusted_dob_info, str):
            trusted_dob = trusted_dob_info.strip()

        # If hist_doc has person DOB, fallback to person DOB if prior_fields had none
        if not trusted_dob and person.date_of_birth:
            trusted_dob = person.date_of_birth.strip()
            trusted_dob_conf = 1.0

        if curr_dob and trusted_dob:
            # Normalize dates (YYYY-MM-DD, DD/MM/YYYY, etc.)
            dob_match = _compare_dates_normalized(curr_dob, trusted_dob)
            is_low_conf = (curr_dob_conf < CROSS_DOC_MIN_CONFIDENCE_THRESHOLD or trusted_dob_conf < CROSS_DOC_MIN_CONFIDENCE_THRESHOLD)

            if not dob_match:
                if is_authoritative:
                    severity = "LOW" if is_low_conf else "HIGH"
                    pts = (CROSS_DOC_DOB_MISMATCH_POINTS * 0.4) if is_low_conf else CROSS_DOC_DOB_MISMATCH_POINTS
                    reason = f"DOB '{curr_dob}' contradicts verified {hist_doc.document_type.upper()} record '{trusted_dob}'"
                    if is_low_conf:
                        reason += " (Low OCR confidence warning)"
                    flags.append(f"CROSS_DOCUMENT_CONFLICT: {reason}")
                else:
                    severity = "LOW"
                    pts = CROSS_DOC_UNVERIFIED_MISMATCH_POINTS
                    reason = f"DOB '{curr_dob}' differs from unverified prior {hist_doc.document_type.upper()} '{trusted_dob}' (Informational)"
                    flags.append(f"CROSS_DOCUMENT_NOTE: {reason}")

                total_risk_points += pts
                comparisons.append({
                    "person_id": person.id,
                    "current_document_id": current_document.id,
                    "trusted_document_id": hist_doc.id,
                    "field_name": "date_of_birth",
                    "current_value": curr_dob,
                    "trusted_value": trusted_dob,
                    "current_confidence": curr_dob_conf,
                    "trusted_confidence": trusted_dob_conf,
                    "is_match": False,
                    "severity": severity,
                    "reason": reason,
                    "risk_points_assigned": pts,
                })
            else:
                comparisons.append({
                    "person_id": person.id,
                    "current_document_id": current_document.id,
                    "trusted_document_id": hist_doc.id,
                    "field_name": "date_of_birth",
                    "current_value": curr_dob,
                    "trusted_value": trusted_dob,
                    "current_confidence": curr_dob_conf,
                    "trusted_confidence": trusted_dob_conf,
                    "is_match": True,
                    "severity": "NONE",
                    "reason": f"DOB matches historical {hist_doc.document_type.upper()}",
                    "risk_points_assigned": 0.0,
                })

        # 2. Compare Holder Name
        curr_name_info = current_extracted_fields.get("holder_name") or current_extracted_fields.get("name")
        curr_name = None
        curr_name_conf = 1.0
        if isinstance(curr_name_info, dict):
            curr_name = str(curr_name_info.get("value", "")).strip()
            curr_name_conf = float(curr_name_info.get("confidence", 1.0))
        elif isinstance(curr_name_info, str):
            curr_name = curr_name_info.strip()

        trusted_name_info = prior_fields.get("holder_name") or prior_fields.get("name")
        trusted_name = None
        trusted_name_conf = 1.0
        if isinstance(trusted_name_info, dict):
            trusted_name = str(trusted_name_info.get("value", "")).strip()
            trusted_name_conf = float(trusted_name_info.get("confidence", 1.0))
        elif isinstance(trusted_name_info, str):
            trusted_name = trusted_name_info.strip()

        if not trusted_name and person.primary_name:
            trusted_name = person.primary_name.strip()
            trusted_name_conf = 1.0

        if curr_name and trusted_name:
            name_match = _compare_names_fuzzy(curr_name, trusted_name)
            if not name_match:
                if is_authoritative:
                    severity = "MEDIUM"
                    pts = CROSS_DOC_NAME_MISMATCH_POINTS
                    reason = f"Name '{curr_name}' differs from verified {hist_doc.document_type.upper()} name '{trusted_name}'"
                    flags.append(f"CROSS_DOCUMENT_CONFLICT: {reason}")
                else:
                    severity = "LOW"
                    pts = CROSS_DOC_UNVERIFIED_MISMATCH_POINTS
                    reason = f"Name '{curr_name}' differs from unverified prior {hist_doc.document_type.upper()} name '{trusted_name}' (Informational)"
                    flags.append(f"CROSS_DOCUMENT_NOTE: {reason}")

                total_risk_points += pts
                comparisons.append({
                    "person_id": person.id,
                    "current_document_id": current_document.id,
                    "trusted_document_id": hist_doc.id,
                    "field_name": "holder_name",
                    "current_value": curr_name,
                    "trusted_value": trusted_name,
                    "current_confidence": curr_name_conf,
                    "trusted_confidence": trusted_name_conf,
                    "is_match": False,
                    "severity": severity,
                    "reason": reason,
                    "risk_points_assigned": pts,
                })
            else:
                comparisons.append({
                    "person_id": person.id,
                    "current_document_id": current_document.id,
                    "trusted_document_id": hist_doc.id,
                    "field_name": "holder_name",
                    "current_value": curr_name,
                    "trusted_value": trusted_name,
                    "current_confidence": curr_name_conf,
                    "trusted_confidence": trusted_name_conf,
                    "is_match": True,
                    "severity": "NONE",
                    "reason": f"Name matches historical {hist_doc.document_type.upper()}",
                    "risk_points_assigned": 0.0,
                })

    return comparisons, total_risk_points, flags


def _compare_dates_normalized(d1: str, d2: str) -> bool:
    """Normalize and compare two date strings across common formats."""
    d1_clean = d1.replace("/", "-").replace(".", "-").strip()
    d2_clean = d2.replace("/", "-").replace(".", "-").strip()

    if d1_clean == d2_clean:
        return True

    formats = ["%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%Y%m%d", "%d%m%Y"]
    dt1 = None
    dt2 = None

    for fmt in formats:
        if not dt1:
            try:
                dt1 = datetime.strptime(d1_clean, fmt)
            except ValueError:
                pass
        if not dt2:
            try:
                dt2 = datetime.strptime(d2_clean, fmt)
            except ValueError:
                pass

    if dt1 and dt2:
        return dt1.date() == dt2.date()

    return False


def _compare_names_fuzzy(n1: str, n2: str) -> bool:
    """Check if two names match either exactly or token-wise."""
    c1 = "".join(ch for ch in n1.lower() if ch.isalnum() or ch.isspace()).split()
    c2 = "".join(ch for ch in n2.lower() if ch.isalnum() or ch.isspace()).split()
    if not c1 or not c2:
        return False
    # Exact match or set equality
    if sorted(c1) == sorted(c2):
        return True
    # Substring / initials token match
    common = set(c1).intersection(set(c2))
    if len(common) >= min(len(c1), len(c2)):
        return True
    return False
