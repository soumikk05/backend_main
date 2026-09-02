"""
Tests for Multi-Document Identity Resolution, Cross-Document Consistency,
Verification Trust Tiers, and Atomic Commit Behaviors.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

from app.db import Base
from app.models.database import (
    Person,
    Document,
    ScreeningRecord,
    CrossDocumentComparison,
    AuditLog,
    ProcessingMetric,
)
from app.services.cross_document_service import (
    resolve_candidate_identity_and_document,
    compare_cross_document_consistency,
)
from app.services.risk_engine import compute_risk_score


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_document_creation_and_person_linkage(test_db):
    """Verify initial document and person creation when none exist."""
    person, doc, is_repeat = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="passport",
        document_number="Z1234567",
        holder_name="Alice Smith",
        date_of_birth="1995-04-12",
        nationality="USA",
        gender="F",
        image_hash="hash123",
        evidence_path="/evidence/test.jpg",
    )
    test_db.commit()

    assert person.id is not None
    assert doc.id is not None
    assert doc.person_id == person.id
    assert is_repeat is False
    assert person.verification_status == "UNVERIFIED"
    assert doc.verification_status == "UNVERIFIED"
    assert doc.document_number == "******67"


def test_repeat_screening_of_same_document(test_db):
    """Verify that screening the exact same document number reuses the persistent Document entity."""
    person1, doc1, is_repeat1 = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="passport",
        document_number="Z1234567",
        holder_name="Alice Smith",
        date_of_birth="1995-04-12",
        nationality="USA",
    )
    test_db.commit()

    person2, doc2, is_repeat2 = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="passport",
        document_number="Z1234567",
        holder_name="Alice Smith",
        date_of_birth="1995-04-12",
        nationality="USA",
    )

    assert is_repeat2 is True
    assert doc2.id == doc1.id
    assert person2.id == person1.id


def test_no_automatic_identity_merge_by_name_alone(test_db):
    """Verify that two people sharing the same name but different doc numbers and details are NOT merged."""
    person1, doc1, _ = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="passport",
        document_number="A1111111",
        holder_name="John Doe",
        date_of_birth="1980-01-01",
        nationality="GBR",
    )
    test_db.commit()

    person2, doc2, _ = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="national_id",
        document_number="B2222222",
        holder_name="John Doe",
        date_of_birth="1992-05-20",  # Different DOB & nationality
        nationality="CAN",
    )
    test_db.commit()

    assert person1.id != person2.id
    assert doc1.person_id != doc2.person_id


def test_unverified_document_not_treated_as_trusted_ground_truth(test_db):
    """
    Verify that if a historical document is UNVERIFIED, a DOB mismatch produces only
    low-severity informational notes (+5.0 pts), NOT a high-severity contradiction.
    """
    # Create Document 1 (UNVERIFIED)
    person, doc1, _ = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="passport",
        document_number="Z100",
        holder_name="Bob Jones",
        date_of_birth="1990-01-01",
        nationality="IND",
    )
    doc1.verification_status = "UNVERIFIED"

    # Create prior screening record for doc1
    scr1 = ScreeningRecord(
        document_id=doc1.id,
        person_id=person.id,
        document_type="passport",
        extracted_fields={"date_of_birth": {"value": "1990-01-01", "confidence": 0.95}},
    )
    test_db.add(scr1)
    test_db.commit()

    # Create Document 2 for same person with conflicting DOB
    doc2 = Document(
        person_id=person.id,
        document_type="national_id",
        document_number="N200",
        verification_status="UNVERIFIED",
    )
    test_db.add(doc2)
    test_db.commit()

    comparisons, risk_pts, flags = compare_cross_document_consistency(
        db=test_db,
        person=person,
        current_document=doc2,
        current_extracted_fields={"date_of_birth": {"value": "1993-07-15", "confidence": 0.95}},
    )

    assert len(comparisons) == 1
    assert comparisons[0]["is_match"] is False
    assert comparisons[0]["severity"] == "LOW"
    assert risk_pts == 5.0
    assert any("CROSS_DOCUMENT_NOTE" in f for f in flags)
    assert not any("CROSS_DOCUMENT_CONFLICT" in f for f in flags)


def test_verified_document_used_as_baseline_dob_mismatch(test_db):
    """
    Verify that when historical document is VERIFIED, a DOB mismatch generates a
    HIGH severity contradiction and adds full configured risk points (+30.0 pts).
    """
    person, doc1, _ = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="passport",
        document_number="Z999",
        holder_name="Charlie Brown",
        date_of_birth="1998-06-15",
        nationality="IND",
    )
    doc1.verification_status = "VERIFIED"
    person.verification_status = "VERIFIED"

    scr1 = ScreeningRecord(
        document_id=doc1.id,
        person_id=person.id,
        document_type="passport",
        extracted_fields={"date_of_birth": {"value": "1998-06-15", "confidence": 0.99}},
    )
    test_db.add(scr1)
    test_db.commit()

    doc2 = Document(
        person_id=person.id,
        document_type="national_id",
        document_number="AADHAAR-555",
        verification_status="UNVERIFIED",
    )
    test_db.add(doc2)
    test_db.commit()

    comparisons, risk_pts, flags = compare_cross_document_consistency(
        db=test_db,
        person=person,
        current_document=doc2,
        current_extracted_fields={"date_of_birth": {"value": "2000-01-01", "confidence": 0.94}},
    )

    assert len(comparisons) == 1
    assert comparisons[0]["is_match"] is False
    assert comparisons[0]["severity"] == "HIGH"
    assert risk_pts == 30.0
    assert any("CROSS_DOCUMENT_CONFLICT" in f for f in flags)


def test_matching_dob_against_verified_document(test_db):
    """Verify that when DOB matches trusted baseline, comparison is recorded with is_match=True and 0 points."""
    person, doc1, _ = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="passport",
        document_number="Z888",
        holder_name="Diana Prince",
        date_of_birth="1990-10-25",
        nationality="IND",
    )
    doc1.verification_status = "VERIFIED"

    scr1 = ScreeningRecord(
        document_id=doc1.id,
        person_id=person.id,
        document_type="passport",
        extracted_fields={"date_of_birth": {"value": "25-10-1990", "confidence": 0.98}},
    )
    test_db.add(scr1)
    test_db.commit()

    doc2 = Document(
        person_id=person.id,
        document_type="national_id",
        document_number="AADHAAR-888",
    )
    test_db.add(doc2)
    test_db.commit()

    comparisons, risk_pts, flags = compare_cross_document_consistency(
        db=test_db,
        person=person,
        current_document=doc2,
        current_extracted_fields={"date_of_birth": {"value": "1990/10/25", "confidence": 0.95}},
    )

    assert len(comparisons) == 1
    assert comparisons[0]["is_match"] is True
    assert comparisons[0]["severity"] == "NONE"
    assert risk_pts == 0.0


def test_low_confidence_mismatch_handling(test_db):
    """Verify that when OCR confidence is low (< 0.55), risk points are scaled down to avoid false penalties."""
    person, doc1, _ = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="passport",
        document_number="Z777",
        holder_name="Edward Norton",
        date_of_birth="1985-03-01",
        nationality="IND",
    )
    doc1.verification_status = "VERIFIED"

    scr1 = ScreeningRecord(
        document_id=doc1.id,
        person_id=person.id,
        document_type="passport",
        extracted_fields={"date_of_birth": {"value": "1985-03-01", "confidence": 0.99}},
    )
    test_db.add(scr1)
    test_db.commit()

    doc2 = Document(person_id=person.id, document_type="driving_license", document_number="DL-123")
    test_db.add(doc2)
    test_db.commit()

    comparisons, risk_pts, flags = compare_cross_document_consistency(
        db=test_db,
        person=person,
        current_document=doc2,
        current_extracted_fields={"date_of_birth": {"value": "1987-03-01", "confidence": 0.40}},  # Low confidence!
    )

    assert len(comparisons) == 1
    assert comparisons[0]["is_match"] is False
    assert comparisons[0]["severity"] == "LOW"
    assert risk_pts == 30.0 * 0.4  # Scaled down from 30 to 12


def test_foreign_key_integrity_and_atomic_rollback(test_db):
    """Verify foreign key enforcement on SQLite and atomic rollback on error."""
    # Attempting to insert a document with nonexistent person_id should fail PRAGMA foreign_keys
    bad_doc = Document(person_id="nonexistent-uuid-1234", document_type="passport")
    test_db.add(bad_doc)

    with pytest.raises(Exception):
        test_db.commit()
    test_db.rollback()

    # Verify rollback kept session clean
    assert test_db.query(Document).count() == 0


def test_risk_engine_integration_with_cross_document_evidence():
    """Verify risk engine consumes cross_document_result and incorporates points into breakdown and final score."""
    val_res = {"pass_count": 5, "fail_count": 0, "rules": []}
    cross_res = {
        "risk_points": 30.0,
        "flags": ["CROSS_DOCUMENT_CONFLICT: DOB contradicts verified Passport"],
    }
    risk_output = compute_risk_score(
        validation_result=val_res,
        tampering_result=None,
        face_result=None,
        cross_document_result=cross_res,
    )

    assert "cross_document_consistency" in risk_output["breakdown"]
    assert risk_output["breakdown"]["cross_document_consistency"] == 30.0
    assert any("CROSS_DOCUMENT_CONFLICT" in r for r in risk_output["reasons"])
