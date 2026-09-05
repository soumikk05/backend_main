"""
Identity Resolution and Cross-Document Consistency Comparison Services.

Provides:
1. Candidate Identity Resolution:
   - Resolves or instantiates canonical Person and Document records.
   - Normalizes document identifiers (stripping whitespace, dashes, slashes).
   - Biometric-assisted person resolution using face embedding cosine similarity.
2. Cross-Document & Same-Document Consistency Checking:
   - Compares current extracted fields against historical records of the SAME document (detects forged DOB / altered names).
   - Compares current extracted fields against other documents for the SAME Person (e.g. Aadhaar vs Passport).
   - Generates confidence-aware CrossDocumentComparison rows and critical risk contributions.
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
from app.models.database import Person, Document, CrossDocumentComparison, FaceEmbedding, ScreeningRecord
from app.services.privacy_service import lookup_hash, encrypt_value, mask_identifier, normalize_doc_number

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
    Resolves or creates canonical Person and Document entities.
    
    Identity Linkage Rules:
    - Normalizes document number (removing spaces, dashes, slashes) to avoid format misses.
    - If document_number matches an existing Document, reuse that Document and its Person.
    - If no document match, check if a Person matches by strong biometric face vector (cosine >= 0.70).
    - Checks DOB + Name match if available.
    - NEVER merges identities by holder name alone.
    """
    clean_doc = normalize_doc_number(document_number)
    doc_hash = lookup_hash(clean_doc) if clean_doc else None
    name_hash = lookup_hash(holder_name) if holder_name else None
    norm_dob = _normalize_date_str(date_of_birth)

    person: Optional[Person] = None
    document: Optional[Document] = None
    is_repeat = False

    # 1. Check if the exact document already exists in DB by hash
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

        for emb in db.query(FaceEmbedding).limit(500).all():
            other = emb.embedding_vector or []
            if len(other) != len(face_vector):
                continue
            other_norm = math.sqrt(sum(v * v for v in other)) or 1.0
            sim = sum(a * b for a, b in zip(face_vector, other)) / (norm * other_norm)
            if sim > best_sim:
                best_sim = sim
                best_person_id = emb.person_id

        if best_sim >= CROSS_DOC_IDENTITY_LINK_FACE_THRESHOLD and best_person_id:
            candidate_p = db.query(Person).filter(Person.id == str(best_person_id)).first()
            if not candidate_p:
                # Resolve if person_id was stored as document identifier
                doc_cand = db.query(Document).filter(
                    (Document.document_number == str(best_person_id)) |
                    (Document.document_number_hash == lookup_hash(str(best_person_id)))
                ).first()
                if doc_cand and doc_cand.person_id:
                    candidate_p = db.query(Person).filter(Person.id == doc_cand.person_id).first()
            if candidate_p:
                person = candidate_p
                logger.info("Resolved candidate person %s via biometric similarity %.3f", person.id, best_sim)

    # 3. DOB + nationality + name match if verified person exists
    if not person and norm_dob and holder_name:
        candidate_p = db.query(Person).filter(
            Person.date_of_birth == norm_dob,
            Person.primary_name_hash == name_hash,
        ).first()
        if candidate_p:
            person = candidate_p
            logger.info("Resolved candidate person %s via DOB+Name match", person.id)

    # 4. If person still not found, create candidate Person
    if not person:
        person = Person(
            primary_name=holder_name,
            primary_name_hash=name_hash,
            date_of_birth=norm_dob,
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
    Compares extracted fields of the current document against:
    1. Historical screenings of the SAME document (catches re-used document with forged DOB or altered name).
    2. Historical documents of the SAME Person (e.g. Aadhaar vs Passport vs Driving License).
    
    Returns:
        (comparisons_data_list, total_risk_points, flags)
    """
    if not current_document:
        return [], 0.0, []

    comparisons: List[Dict[str, Any]] = []
    total_risk_points = 0.0
    flags: List[str] = []

    # Current extracted values
    curr_dob_info = current_extracted_fields.get("date_of_birth") or current_extracted_fields.get("dob")
    curr_dob = None
    curr_dob_conf = 1.0
    if isinstance(curr_dob_info, dict):
        curr_dob = str(curr_dob_info.get("value", "")).strip()
        curr_dob_conf = float(curr_dob_info.get("confidence", 1.0))
    elif isinstance(curr_dob_info, str):
        curr_dob = curr_dob_info.strip()

    curr_dob_norm = _normalize_date_str(curr_dob)

    curr_name_info = current_extracted_fields.get("holder_name") or current_extracted_fields.get("name")
    curr_name = None
    curr_name_conf = 1.0
    if isinstance(curr_name_info, dict):
        curr_name = str(curr_name_info.get("value", "")).strip()
        curr_name_conf = float(curr_name_info.get("confidence", 1.0))
    elif isinstance(curr_name_info, str):
        curr_name = curr_name_info.strip()

    # -----------------------------------------------------------------------
    # 1. SAME DOCUMENT NUMBER CHECK (Forged re-submission / Tampered duplicate)
    # -----------------------------------------------------------------------
    if current_document.document_number_hash:
        prior_screenings = db.query(ScreeningRecord).filter(
            ScreeningRecord.document_number_hash == current_document.document_number_hash
        ).order_by(ScreeningRecord.created_at.desc()).limit(10).all()

        for prior in prior_screenings:
            prior_fields = prior.extracted_fields or {}

            # Check DOB on same document
            prior_dob = prior.date_of_birth or prior_fields.get("date_of_birth") or prior_fields.get("dob")
            if isinstance(prior_dob, dict):
                prior_dob = prior_dob.get("value")
            prior_dob_norm = _normalize_date_str(prior_dob)

            if curr_dob_norm and prior_dob_norm:
                is_match = _compare_dates_normalized(curr_dob_norm, prior_dob_norm)
                if not is_match:
                    severity = "CRITICAL"
                    pts = 80.0
                    reason = (
                        f"CRITICAL_TAMPERING_CONFLICT: Document number previously screened with Date of Birth '{prior_dob_norm}', "
                        f"now submitted with forged Date of Birth '{curr_dob_norm}'"
                    )
                    flags.append(reason)
                    total_risk_points += pts
                    comparisons.append({
                        "person_id": person.id if person else None,
                        "current_document_id": current_document.id,
                        "trusted_document_id": prior.document_id or current_document.id,
                        "field_name": "date_of_birth",
                        "current_value": curr_dob_norm,
                        "trusted_value": prior_dob_norm,
                        "current_confidence": curr_dob_conf,
                        "trusted_confidence": 1.0,
                        "is_match": False,
                        "severity": severity,
                        "reason": reason,
                        "risk_points_assigned": pts,
                    })
                    break  # Found primary discrepancy on same document
                else:
                    comparisons.append({
                        "person_id": person.id if person else None,
                        "current_document_id": current_document.id,
                        "trusted_document_id": prior.document_id or current_document.id,
                        "field_name": "date_of_birth",
                        "current_value": curr_dob_norm,
                        "trusted_value": prior_dob_norm,
                        "current_confidence": curr_dob_conf,
                        "trusted_confidence": 1.0,
                        "is_match": True,
                        "severity": "NONE",
                        "reason": "Date of Birth matches prior screening record of this document",
                        "risk_points_assigned": 0.0,
                    })
                    break

            # Check Name on same document
            prior_name = prior.holder_name or prior_fields.get("holder_name") or prior_fields.get("name")
            if isinstance(prior_name, dict):
                prior_name = prior_name.get("value")

            if curr_name and prior_name:
                name_match, name_reason = _compare_names_fuzzy(curr_name, prior_name)
                if not name_match:
                    severity = "CRITICAL"
                    pts = 75.0
                    reason = (
                        f"CRITICAL_IDENTITY_FRAUD: Document number previously screened under name '{prior_name}', "
                        f"now presented with completely different name '{curr_name}'"
                    )
                    flags.append(reason)
                    total_risk_points += pts
                    comparisons.append({
                        "person_id": person.id if person else None,
                        "current_document_id": current_document.id,
                        "trusted_document_id": prior.document_id or current_document.id,
                        "field_name": "holder_name",
                        "current_value": curr_name,
                        "trusted_value": prior_name,
                        "current_confidence": curr_name_conf,
                        "trusted_confidence": 1.0,
                        "is_match": False,
                        "severity": severity,
                        "reason": reason,
                        "risk_points_assigned": pts,
                    })
                    break

    # -----------------------------------------------------------------------
    # 2. CROSS-DOCUMENT CHECK (Different documents belonging to the SAME Person)
    # -----------------------------------------------------------------------
    if person:
        historical_docs = db.query(Document).filter(
            Document.person_id == person.id,
            Document.id != current_document.id,
        ).all()

        for hist_doc in historical_docs:
            is_authoritative = (hist_doc.verification_status == "VERIFIED")
            prior_screening = hist_doc.screenings[-1] if hist_doc.screenings else None
            prior_fields = prior_screening.extracted_fields if prior_screening else {}

            # Compare DOB across different documents
            trusted_dob_info = prior_fields.get("date_of_birth") or prior_fields.get("dob") or person.date_of_birth
            trusted_dob = None
            trusted_dob_conf = 1.0
            if isinstance(trusted_dob_info, dict):
                trusted_dob = str(trusted_dob_info.get("value", "")).strip()
                trusted_dob_conf = float(trusted_dob_info.get("confidence", 1.0))
            elif isinstance(trusted_dob_info, str):
                trusted_dob = trusted_dob_info.strip()

            trusted_dob_norm = _normalize_date_str(trusted_dob)

            if curr_dob_norm and trusted_dob_norm:
                dob_match = _compare_dates_normalized(curr_dob_norm, trusted_dob_norm)
                is_low_conf = (curr_dob_conf < CROSS_DOC_MIN_CONFIDENCE_THRESHOLD or trusted_dob_conf < CROSS_DOC_MIN_CONFIDENCE_THRESHOLD)

                if not dob_match:
                    if is_authoritative:
                        severity = "LOW" if is_low_conf else "HIGH"
                        pts = (CROSS_DOC_DOB_MISMATCH_POINTS * 0.4) if is_low_conf else CROSS_DOC_DOB_MISMATCH_POINTS
                        reason = f"DOB '{curr_dob_norm}' contradicts verified {hist_doc.document_type.upper()} record '{trusted_dob_norm}'"
                        if is_low_conf:
                            reason += " (Low OCR confidence warning)"
                        flags.append(f"CROSS_DOCUMENT_CONFLICT: {reason}")
                    else:
                        severity = "LOW"
                        pts = CROSS_DOC_UNVERIFIED_MISMATCH_POINTS
                        reason = f"DOB '{curr_dob_norm}' differs from unverified prior {hist_doc.document_type.upper()} '{trusted_dob_norm}' (Informational)"
                        flags.append(f"CROSS_DOCUMENT_NOTE: {reason}")

                    total_risk_points += pts
                    comparisons.append({
                        "person_id": person.id,
                        "current_document_id": current_document.id,
                        "trusted_document_id": hist_doc.id,
                        "field_name": "date_of_birth",
                        "current_value": curr_dob_norm,
                        "trusted_value": trusted_dob_norm,
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
                        "current_value": curr_dob_norm,
                        "trusted_value": trusted_dob_norm,
                        "current_confidence": curr_dob_conf,
                        "trusted_confidence": trusted_dob_conf,
                        "is_match": True,
                        "severity": "NONE",
                        "reason": f"DOB matches registered {hist_doc.document_type.upper()}",
                        "risk_points_assigned": 0.0,
                    })

            # Compare Name across different documents (support initials)
            trusted_name_info = prior_fields.get("holder_name") or prior_fields.get("name") or person.primary_name
            trusted_name = None
            trusted_name_conf = 1.0
            if isinstance(trusted_name_info, dict):
                trusted_name = str(trusted_name_info.get("value", "")).strip()
                trusted_name_conf = float(trusted_name_info.get("confidence", 1.0))
            elif isinstance(trusted_name_info, str):
                trusted_name = trusted_name_info.strip()

            if curr_name and trusted_name:
                name_match, name_reason = _compare_names_fuzzy(curr_name, trusted_name)
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
                        "reason": f"Name verified ({name_reason}) with historical {hist_doc.document_type.upper()}",
                        "risk_points_assigned": 0.0,
                    })

    # Deduplicate flags
    unique_flags = list(dict.fromkeys(flags))
    return comparisons, total_risk_points, unique_flags


def _normalize_date_str(date_str: Optional[str]) -> Optional[str]:
    """Parse and normalize date into standard ISO format (YYYY-MM-DD)."""
    if not date_str:
        return None
    cleaned = str(date_str).strip().replace("/", "-").replace(".", "-").replace(",", "")
    cleaned = " ".join(cleaned.split())

    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
        "%d-%b-%Y", "%d-%B-%Y", "%d %b %Y", "%d %B %Y",
        "%Y%m%d", "%d%m%Y", "%Y-%m", "%m-%Y"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return cleaned


def _compare_dates_normalized(d1: str, d2: str) -> bool:
    """Normalize and compare two dates."""
    n1 = _normalize_date_str(d1)
    n2 = _normalize_date_str(d2)
    return bool(n1 and n2 and n1 == n2)


def _compare_names_fuzzy(n1: str, n2: str) -> Tuple[bool, str]:
    """
    Fuzzy match names supporting Indian name conventions, initials, and token permutations.
    Returns (is_match, reason).
    """
    if not n1 or not n2:
        return False, "Missing name string"

    t1 = [ch for ch in "".join(c if c.isalnum() else " " for c in n1.lower()).split() if ch]
    t2 = [ch for ch in "".join(c if c.isalnum() else " " for c in n2.lower()).split() if ch]

    if not t1 or not t2:
        return False, "Empty name tokens"

    # 1. Exact or anagram match (e.g. "Rahul Kumar" vs "Kumar Rahul")
    if sorted(t1) == sorted(t2):
        return True, "Exact name token match"

    # 2. Subset match (e.g. "Rahul Sharma" inside "Rahul Kumar Sharma")
    if set(t1).issubset(set(t2)) or set(t2).issubset(set(t1)):
        return True, "Name token subset match"

    # 3. Initials expansion check (e.g. "R. K. Sharma" vs "Rahul Kumar Sharma")
    short_tokens, long_tokens = (t1, t2) if len(t1) <= len(t2) else (t2, t1)
    if short_tokens[-1] == long_tokens[-1]:
        remaining_short = short_tokens[:-1]
        remaining_long = long_tokens[:-1]

        matches = 0
        long_idx = 0
        for s in remaining_short:
            matched_curr = False
            for j in range(long_idx, len(remaining_long)):
                l = remaining_long[j]
                if s == l or (len(s) == 1 and l.startswith(s)):
                    matched_curr = True
                    long_idx = j + 1
                    break
            if matched_curr:
                matches += 1

        if matches == len(remaining_short) and len(remaining_short) > 0:
            return True, "Name matches with initials expansion"

    return False, f"Name '{n1}' differs significantly from '{n2}'"
