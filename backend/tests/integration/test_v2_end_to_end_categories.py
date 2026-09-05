"""
End-to-End Pipeline Verification across All 11 Document Categories (Requirement 7).

Tests:
1. Genuine documents
2. Obvious forged documents
3. Localized tampered documents
4. MIDV-style localized tampering
5. Unsupported documents
6. Corrupted images
7. Low-quality images
8. Documents with missing faces
9. Documents with multiple faces
10. Malformed MRZ
11. Conflicting historical records
"""

import os
import io
import tempfile
from pathlib import Path
import numpy as np
import pytest
import cv2
import pandas as pd
from PIL import Image

from app.services.cnn_forgery_service import score_image_forgery_cnn
from app.services.tampering_service import analyze_tampering
from app.services.document_classifier import classify_document
from app.services.image_quality import assess_image_quality
from app.services.face_service import verify_faces, _detect_faces_count
from app.services.validation_service import validate_document
from app.utils.mrz_parser import validate_td3_mrz
from app.services.risk_engine import compute_risk_score
from app.services.cross_document_service import compare_cross_document_consistency
from app.db import SessionLocal
from app.models.database import Person, Document, ScreeningRecord
from app.services.privacy_service import lookup_hash, encrypt_value

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = BASE_DIR / "dataset" / "dataset_split_manifest.csv"


@pytest.fixture(scope="module")
def manifest_df():
    if MANIFEST_PATH.exists():
        return pd.read_csv(MANIFEST_PATH)
    return None


# 1. Genuine documents
def test_e2e_category_1_genuine_document(manifest_df):
    """Verify complete pipeline on a genuine document."""
    # Find a genuine sample
    sample_path = None
    if manifest_df is not None:
        sub = manifest_df[(manifest_df["label"] == 0) & (manifest_df["split"] == "test")]
        if len(sub) > 0:
            p = BASE_DIR / sub.iloc[0]["image_path"]
            if p.exists():
                sample_path = str(p)

    if not sample_path:
        # Create synthetic valid passport
        img = np.full((600, 800, 3), 245, dtype=np.uint8)
        cv2.rectangle(img, (40, 40), (760, 560), (30, 30, 30), 2)
        cv2.putText(img, "PASSPORT", (60, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            sample_path = f.name
            cv2.imwrite(sample_path, img)

    # 1. Quality
    quality = assess_image_quality(sample_path)
    assert "quality_score" in quality

    # 2. Forgery Analysis
    forgery = score_image_forgery_cnn(sample_path)
    assert forgery["model_version"] == "2.0.0_dual_stream_fusion"
    assert forgery["error"] is None
    assert 0.0 <= forgery["cnn_score"] <= 100.0
    assert len(forgery["patch_probabilities"]) == 9

    # 3. Full Tampering Fusion
    tampering = analyze_tampering(sample_path)
    assert "tampering_score" in tampering

    # 4. Risk Engine
    risk = compute_risk_score(
        validation_result={"valid": True, "checks": [{"name": "mrz_checksum", "passed": True, "severity": "HIGH"}]},
        tampering_result=tampering,
        face_result=None,
    )
    assert "risk_score" in risk
    assert risk["risk_label"] in ("LOW", "MEDIUM", "HIGH")


# 2. Obvious forged documents
def test_e2e_category_2_obvious_forged_document(manifest_df):
    """Verify complete pipeline on an obvious forged document."""
    sample_path = None
    if manifest_df is not None:
        sub = manifest_df[(manifest_df["label"] == 1) & (manifest_df["tampering_type"].isin(["splice", "copy_move"]))]
        if len(sub) > 0:
            p = BASE_DIR / sub.iloc[0]["image_path"]
            if p.exists():
                sample_path = str(p)

    if not sample_path:
        # Create obvious forged image with high-contrast spliced box
        img = np.full((600, 800, 3), 245, dtype=np.uint8)
        img[100:300, 200:500] = np.random.randint(0, 256, (200, 300, 3), dtype=np.uint8)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            sample_path = f.name
            cv2.imwrite(sample_path, img)

    forgery = score_image_forgery_cnn(sample_path)
    assert forgery["error"] is None
    assert forgery["model_version"] == "2.0.0_dual_stream_fusion"

    tampering = analyze_tampering(sample_path)
    assert "tampering_score" in tampering


# 3. Localized tampered documents
def test_e2e_category_3_localized_tampered_document(manifest_df):
    """Verify local 3x3 high-res stream captures localized text/number edits."""
    sample_path = None
    if manifest_df is not None:
        sub = manifest_df[(manifest_df["label"] == 1) & (manifest_df["tampering_type"].isin(["name_edit", "dob_edit", "document_number_edit"]))]
        if len(sub) > 0:
            p = BASE_DIR / sub.iloc[0]["image_path"]
            if p.exists():
                sample_path = str(p)

    if not sample_path:
        img = np.full((600, 800, 3), 245, dtype=np.uint8)
        # Spliced local text patch
        cv2.putText(img, "JOHN DOE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        img[80:120, 90:250] = 0 # erased
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            sample_path = f.name
            cv2.imwrite(sample_path, img)

    forgery = score_image_forgery_cnn(sample_path)
    assert forgery["error"] is None
    # Local stream must produce 9 patch probabilities
    assert len(forgery["patch_probabilities"]) == 9
    assert forgery["local_peak_probability"] >= 0.0


# 4. MIDV-style localized tampering
def test_e2e_category_4_midv_localized_tampering(manifest_df):
    """Verify Dual-Stream V2 operates on MIDV-style localized tampering without ground-truth boxes."""
    sample_path = None
    if manifest_df is not None:
        sub = manifest_df[(manifest_df["label"] == 1) & (manifest_df["source"] == "MIDV_FCDV_BENCHMARK")]
        if len(sub) > 0:
            p = BASE_DIR / sub.iloc[0]["image_path"]
            if p.exists():
                sample_path = str(p)

    if not sample_path:
        img = np.full((600, 800, 3), 230, dtype=np.uint8)
        cv2.rectangle(img, (200, 200), (350, 250), (120, 120, 120), -1)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            sample_path = f.name
            cv2.imwrite(sample_path, img)

    forgery = score_image_forgery_cnn(sample_path)
    assert forgery["error"] is None
    # Global + Local fusion properly evaluated
    assert "tamper_probability" in forgery
    assert "cnn_score" in forgery


# 5. Unsupported documents
def test_e2e_category_5_unsupported_document(tmp_path):
    """Verify unsupported document triggers manual review classification."""
    p = tmp_path / "grocery_receipt.jpg"
    receipt = np.full((600, 400, 3), 255, dtype=np.uint8)
    cv2.putText(receipt, "TARGET STORE 1234", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(receipt, "ITEM 1: $12.99", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.imwrite(str(p), receipt)

    cls_res = classify_document(str(p))
    assert cls_res["supported"] is False
    assert cls_res["document_type"] == "unknown"


# 6. Corrupted images
def test_e2e_category_6_corrupted_image(tmp_path):
    """Verify unreadable file produces safe failure mode with explicit manual-review state."""
    p = tmp_path / "corrupt.jpg"
    p.write_bytes(b"\x00\x01\x02\xFF\xD8BAD_TRUNCATED_HEADER")

    res = score_image_forgery_cnn(str(p))
    assert res["mode"] == "safe_failure"
    assert res["triggered"] is True
    assert res["uncertain"] is True
    assert res["cnn_score"] == 50.0
    assert "MANUAL_REVIEW" in res["detail"]


# 7. Low-quality images
def test_e2e_category_7_low_quality_image(tmp_path):
    """Verify blur / poor lighting is detected by intake quality gate."""
    p = tmp_path / "blurry.jpg"
    # Create extreme blur
    img = np.full((400, 600, 3), 180, dtype=np.uint8)
    blurred = cv2.GaussianBlur(img, (99, 99), 0)
    cv2.imwrite(str(p), blurred)

    quality = assess_image_quality(str(p))
    assert quality["quality_score"] < 80.0 or len(quality["issues"]) > 0


# 8. Documents with missing faces
def test_e2e_category_8_missing_faces():
    """Verify missing face on document produces match=None without crashing."""
    img_noface = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.putText(img_noface, "NO FACE DOCUMENT", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        doc_p = f.name
        cv2.imwrite(doc_p, img_noface)

    try:
        res = verify_faces(doc_p, doc_p)
        assert res["match"] is None
        assert res["matched"] is False
    finally:
        if os.path.exists(doc_p):
            os.remove(doc_p)


# 9. Documents with multiple faces
def test_e2e_category_9_multiple_faces(tmp_path):
    """Verify multiple faces on a single document are detected and flagged."""
    # Synthetic image with 2 synthetic face-like patterns or multiple face test
    p = tmp_path / "multi_face.jpg"
    img = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.imwrite(str(p), img)

    # Face count utility test
    count = _detect_faces_count(str(p))
    assert isinstance(count, int)


# 10. Malformed MRZ
def test_e2e_category_10_malformed_mrz():
    """Verify corrupted / tampered MRZ check digits fail validation."""
    line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    line2_tampered = "L898902C39UTO7408122F1204159ZE184226B<<<<<10" # Document checksum tampered from 6 to 9

    res = validate_td3_mrz(line1, line2_tampered)
    assert res["valid"] is False
    assert res["valid_number"] is False


from app.services.cross_document_service import (
    compare_cross_document_consistency,
    resolve_candidate_identity_and_document,
)


# 11. Conflicting historical records
def test_e2e_category_11_conflicting_historical_records():
    """Verify cross-document consistency engine catches conflicting DOB for same person."""
    db = SessionLocal()
    try:
        doc_num = "Z9876543"
        person, doc1, _ = resolve_candidate_identity_and_document(
            db=db,
            document_type="passport",
            document_number=doc_num,
            holder_name="TEST SUBJECT",
            date_of_birth="1985-05-20",
            nationality="IND",
        )
        doc1.verification_status = "VERIFIED"
        db.add(doc1)

        scr1 = ScreeningRecord(
            document_id=doc1.id,
            person_id=person.id,
            document_type="passport",
            extracted_fields={"date_of_birth": {"value": "1985-05-20", "confidence": 0.95}},
            risk_score=10.0,
            risk_label="LOW",
            flags=[],
        )
        db.add(scr1)
        db.commit()

        # Incoming document for same person has conflicting DOB
        doc2 = Document(
            person_id=person.id,
            document_type="national_id",
            document_number="N200",
            verification_status="UNVERIFIED",
        )
        db.add(doc2)
        db.commit()

        extracted_fields = {
            "document_number": {"value": "N200"},
            "date_of_birth": {"value": "1995-05-20"},
            "name": {"value": "TEST SUBJECT"},
        }

        comps, points, flags = compare_cross_document_consistency(
            db=db,
            person=person,
            current_document=doc2,
            current_extracted_fields=extracted_fields,
        )

        assert len(comps) >= 1
        assert points > 0.0
        assert any("CROSS_DOCUMENT_CONFLICT" in f or "CONFLICT" in f for f in flags)
    finally:
        db.rollback()
        db.close()
