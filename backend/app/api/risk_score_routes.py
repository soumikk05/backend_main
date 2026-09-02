"""
Risk assessment routes (Module 5).

/api/risk/assess is the main pipeline endpoint:
  1. Computes SHA-256 image fingerprint.
  2. OCR field extraction (Module 1).
  3. Rule-based validation (Module 2).
  4. Multi-signal tampering analysis (Module 3).
  5. 1:1 Face verification if selfie is provided (Module 4).
  6. Intelligence registry screening for duplicate IDs and blacklists (Module 6).
  7. Blended weighted risk calculation (Module 5).
  8. Persistent audit trail creation in database (Digital Trail).
"""

import json
import logging
import tempfile
import cv2
from time import perf_counter
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.database import ScreeningRecord
from app.models.schemas import ErrorResponse, RiskAssessResponse
from app.services.ocr_service import extract_document_fields
from app.services.document_classifier import classify_document
from app.services.image_quality import assess_image_quality
from app.services.perspective import correct_perspective
from app.services.validation_service import validate_document
from app.services.tampering_service import analyze_tampering
from app.services.face_service import verify_faces, face_embedding
from app.services.liveness_service import check_liveness
from app.services.registry_service import screen_registry, register_face_embedding, detect_identity_cluster
from app.services.risk_engine import compute_risk_score
from app.services.audit_service import append_audit, save_metrics
from app.services.cross_document_service import (
    resolve_candidate_identity_and_document,
    compare_cross_document_consistency,
)
from app.services.evidence_service import evidence_urls
from app.services.privacy_service import encrypt_value, lookup_hash, mask_identifier, mask_name
from app.utils.image_utils import compute_image_sha256, save_upload_to_temp, cleanup_temp_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/assess", response_model=RiskAssessResponse, summary="Run complete document screening", responses={401: {"model": ErrorResponse, "description": "Missing or invalid API key/JWT."}, 413: {"model": ErrorResponse, "description": "Upload exceeds configured size limit."}})
@router.post("/screen", response_model=RiskAssessResponse, include_in_schema=False)
def assess(
    document_image: UploadFile = File(..., description="Full document image (passport/visa/ID)"),
    selfie_photo: Optional[UploadFile] = File(
        None, description="Optional live selfie — if omitted, face verification is skipped"
    ),
    db: Session = Depends(get_db),
):
    """
    Runs the full end-to-end identity screening pipeline.
    Runs synchronously in a worker threadpool. Never raises 500s on degraded input.
    """
    doc_temp_path = save_upload_to_temp(document_image)
    selfie_temp_path = save_upload_to_temp(selfie_photo) if selfie_photo is not None else None

    try:
        started = perf_counter(); timings = {}
        # 1. Image Fingerprinting
        image_hash = compute_image_sha256(doc_temp_path)

        quality_result = assess_image_quality(doc_temp_path)
        classification = classify_document(doc_temp_path)
        timings["intake"] = round((perf_counter() - started) * 1000, 2)
        if not quality_result["acceptable"]:
            return {"risk_score": 100.0, "risk_label": "HIGH", "component_scores": {"quality": 100.0}, "flags": ["Image quality gate rejected upload: " + ", ".join(quality_result["issues"])], "ocr": {"document_type": classification["document_type"], "fields": {}}, "modules": {"quality": quality_result, "classification": classification}}
        corrected_path = None
        try:
            corrected, was_corrected, _ = correct_perspective(doc_temp_path)
            if was_corrected:
                handle = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg"); corrected_path = handle.name; handle.close(); cv2.imwrite(corrected_path, corrected)
        except Exception:
            corrected_path = None
        processing_path = corrected_path or doc_temp_path

        # 2. OCR Extraction
        ocr_result = extract_document_fields(processing_path, classification.get("document_type"))
        timings["ocr"] = round((perf_counter() - started) * 1000 - timings["intake"], 2)

        # Extract potential identity keys for registry lookup
        doc_fields = ocr_result.get("fields", {}) if isinstance(ocr_result, dict) else {}
        doc_type = ocr_result.get("document_type", "UNKNOWN")
        values = {key: value.get("value") if isinstance(value, dict) else value for key, value in doc_fields.items()}
        doc_number = values.get("passport_number") or values.get("document_number") or values.get("id_number") or values.get("license_number") or values.get("visa_number")
        holder_name = f"{values.get('given_names', '')} {values.get('surname', '')}".strip() or values.get("name")
        date_of_birth = values.get("date_of_birth") or values.get("dob")

        # 3. Rule-based Validation
        validation_result = validate_document(ocr_result)
        timings["validation"] = round((perf_counter() - started) * 1000 - sum(timings.values()), 2)

        # 4. Tampering Analysis
        tampering_result = analyze_tampering(processing_path)
        timings["tampering"] = round((perf_counter() - started) * 1000 - sum(timings.values()), 2)

        # 5. Face Verification (optional)
        face_result = None
        face_vec = None
        if selfie_temp_path is not None:
            face_result = verify_faces(processing_path, selfie_temp_path)
            face_result["liveness"] = check_liveness(selfie_temp_path)
            embedding = face_embedding(selfie_temp_path)
            if not embedding["error"]:
                face_vec = embedding["embedding"]
                person_id_key = str(doc_number or holder_name or image_hash)
                register_face_embedding(person_id_key, embedding["embedding"], embedding["hash"], db)
                face_result["identity_cluster"] = detect_identity_cluster(person_id_key, doc_number, holder_name, embedding["embedding"], db)
        timings["face"] = round((perf_counter() - started) * 1000 - sum(timings.values()), 2)

        # 6. Candidate Identity & Document Resolution (Persistence Preparation)
        classified_type = classification.get("document_type", doc_type)
        person, persistent_doc, is_repeat = resolve_candidate_identity_and_document(
            db=db,
            document_type=classified_type,
            document_number=doc_number,
            holder_name=holder_name,
            date_of_birth=date_of_birth,
            nationality=doc_fields.get("nationality", {}).get("value") if isinstance(doc_fields.get("nationality"), dict) else doc_fields.get("nationality"),
            gender=doc_fields.get("sex", {}).get("value") or doc_fields.get("gender", {}).get("value") if isinstance(doc_fields.get("sex") or doc_fields.get("gender"), dict) else (doc_fields.get("sex") or doc_fields.get("gender")),
            image_hash=image_hash,
            evidence_path=None,
            face_vector=face_vec,
        )

        # 7. Cross-Document Consistency Checking (against trusted/verified records)
        comparisons_data, cross_doc_points, cross_doc_flags = compare_cross_document_consistency(
            db=db,
            person=person,
            current_document=persistent_doc,
            current_extracted_fields=doc_fields,
        )
        cross_doc_summary = {
            "comparisons": comparisons_data,
            "risk_points": cross_doc_points,
            "flags": cross_doc_flags,
            "compared_records_count": len(comparisons_data),
        }

        # 8. Duplicate Identity & Blacklist Registry Check
        registry_result = screen_registry(
            document_number=doc_number,
            holder_name=holder_name,
            image_hash=image_hash,
            db=db,
            date_of_birth=date_of_birth,
        )
        timings["registry"] = round((perf_counter() - started) * 1000 - sum(timings.values()), 2)

        # 9. Consolidated Risk Calculation (incorporating cross-document evidence)
        risk_result = compute_risk_score(
            validation_result=validation_result,
            tampering_result=tampering_result,
            face_result=face_result,
            registry_result=registry_result,
            quality_result=quality_result,
            metadata_result=next((check for check in tampering_result.get("checks", []) if check.get("name") == "exif_metadata"), None),
            liveness_result=face_result.get("liveness") if face_result else None,
            ocr_result=ocr_result,
            cross_document_result=cross_doc_summary,
        )
        timings["risk"] = round((perf_counter() - started) * 1000 - sum(timings.values()), 2)

        # 10. Digital Audit Trail Persistence & Atomic Commit
        record_id = None
        try:
            record = ScreeningRecord(
                document_id=persistent_doc.id,
                person_id=person.id,
                document_type=classified_type,
                document_number=mask_identifier(doc_number),
                holder_name=mask_name(holder_name),
                date_of_birth=date_of_birth,
                document_number_encrypted=encrypt_value(doc_number),
                holder_name_encrypted=encrypt_value(holder_name),
                document_number_hash=lookup_hash(doc_number),
                holder_name_hash=lookup_hash(holder_name),
                image_hash=image_hash,
                extracted_fields=doc_fields,
                validation_result=validation_result,
                tampering_result=tampering_result,
                face_result=face_result,
                registry_result=registry_result,
                risk_score=risk_result["risk_score"],
                risk_label=risk_result["risk_label"],
                flags=risk_result["flags"],
            )
            db.add(record)
            db.flush()

            # Store evidence artifacts on disk and record relative path
            heatmap_path = (tampering_result.get("heatmap") or {}).get("ela_heatmap_path")
            ev_urls = evidence_urls(doc_temp_path, corrected_path, heatmap_path, record.id)
            record.evidence_file_path = ev_urls.get("original_image")
            if not persistent_doc.evidence_file_path:
                persistent_doc.evidence_file_path = ev_urls.get("original_image")
            risk_result["evidence_artifacts"] = ev_urls

            # Stage CrossDocumentComparison records
            for comp in comparisons_data:
                db.add(CrossDocumentComparison(
                    screening_id=record.id,
                    person_id=comp.get("person_id"),
                    current_document_id=comp["current_document_id"],
                    trusted_document_id=comp["trusted_document_id"],
                    field_name=comp["field_name"],
                    current_value=comp.get("current_value"),
                    trusted_value=comp.get("trusted_value"),
                    current_confidence=comp.get("current_confidence"),
                    trusted_confidence=comp.get("trusted_confidence"),
                    is_match=comp["is_match"],
                    severity=comp["severity"],
                    reason=comp.get("reason"),
                    risk_points_assigned=comp["risk_points_assigned"],
                ))

            timings["total"] = round((perf_counter() - started) * 1000, 2)
            append_audit(
                db, record.id, None, image_hash, risk_result,
                risk_result.get("modules", {}), timings["total"],
                document_type=classified_type,
            )
            save_metrics(db, record.id, timings)

            # Atomic commit of all staged changes
            db.commit()
            db.refresh(record)
            record_id = record.id

            # Structured JSON audit logging — PII fields are masked
            logger.info(
                json.dumps({
                    "event": "SCREENING_COMPLETED",
                    "record_id": record_id,
                    "document_id": persistent_doc.id,
                    "person_id": person.id,
                    "document_type": classified_type,
                    "document_number_masked": mask_identifier(doc_number),
                    "risk_score": risk_result["risk_score"],
                    "risk_label": risk_result["risk_label"],
                    "decision": risk_result.get("decision"),
                    "flags_count": len(risk_result["flags"]),
                })
            )
        except Exception as exc:
            logger.error("Audit trail persistence failed: %s", exc)
            db.rollback()

        return {
            "ocr": ocr_result,
            "record_id": record_id,
            **risk_result,
            "modules": {**risk_result.get("modules", {}), "quality": quality_result, "classification": classification, "perspective_corrected": bool(corrected_path)},
            "evidence": risk_result.get("evidence_artifacts", risk_result.get("evidence", {})),
            "timeline": timings,
        }
    finally:
        cleanup_temp_file(doc_temp_path)
        if selfie_temp_path is not None:
            cleanup_temp_file(selfie_temp_path)
        if 'corrected_path' in locals() and corrected_path:
            cleanup_temp_file(corrected_path)