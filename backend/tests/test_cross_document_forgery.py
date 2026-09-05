"""
Automated Verification Tests for Cross-Document & Same-Document Tampering Detection.
Tests:
1. Re-submitting the same document number with forged Date of Birth (DOB).
2. Cross-document consistency checking between Aadhaar and Passport for the same person.
3. Indian name initials matching (e.g., 'R. K. Sharma' vs 'Rahul Kumar Sharma').
4. Document number identity reuse with completely different names.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.database import Person, Document, ScreeningRecord
from app.services.privacy_service import lookup_hash, normalize_doc_number
from app.services.cross_document_service import (
    resolve_candidate_identity_and_document,
    compare_cross_document_consistency,
    _compare_dates_normalized,
    _compare_names_fuzzy,
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_date_normalization_and_comparison():
    """Verify robust date parsing across DD/MM/YYYY, YYYY-MM-DD, and textual formats."""
    assert _compare_dates_normalized("15/08/1990", "1990-08-15") is True
    assert _compare_dates_normalized("15-08-1990", "15/08/1990") is True
    assert _compare_dates_normalized("15 Aug 1990", "1990-08-15") is True
    # Forged date must not match
    assert _compare_dates_normalized("15/08/1990", "15/08/2000") is False
    assert _compare_dates_normalized("01/01/1995", "01/01/1996") is False


def test_name_and_initials_matching():
    """Verify name fuzzy matching and initials expansion for government identities."""
    match, reason = _compare_names_fuzzy("R. K. Sharma", "Rahul Kumar Sharma")
    assert match is True
    assert "initials" in reason.lower()

    match, reason = _compare_names_fuzzy("A. Verma", "Ajay Verma")
    assert match is True

    match, reason = _compare_names_fuzzy("Rahul Sharma", "Rahul Sharma")
    assert match is True

    match, reason = _compare_names_fuzzy("Rahul Sharma", "Sunita Devi")
    assert match is False


def test_same_id_with_forged_dob_tampering(test_db):
    """
    Core User Case:
    1. An ID (e.g. Aadhaar '1234 5678 9012') is screened and stored with DOB '1990-08-15'.
    2. A tampered ID with the exact same Aadhaar number is uploaded with forged DOB '2000-08-15'.
    3. System must flag CRITICAL_TAMPERING_CONFLICT and assign 80 risk points.
    """
    aadhar_num = "1234 5678 9012"
    doc_hash = lookup_hash(normalize_doc_number(aadhar_num))

    # Step 1: Simulate the genuine record already existing in the database
    person = Person(
        primary_name="Rahul Sharma",
        primary_name_hash=lookup_hash("Rahul Sharma"),
        date_of_birth="1990-08-15",
        verification_status="VERIFIED",
    )
    test_db.add(person)
    test_db.flush()

    doc = Document(
        person_id=person.id,
        document_type="aadhaar",
        document_number="********9012",
        document_number_hash=doc_hash,
        verification_status="VERIFIED",
    )
    test_db.add(doc)
    test_db.flush()

    prior_screening = ScreeningRecord(
        document_id=doc.id,
        person_id=person.id,
        document_type="aadhaar",
        document_number="********9012",
        document_number_hash=doc_hash,
        holder_name="Rahul Sharma",
        date_of_birth="1990-08-15",
        extracted_fields={"date_of_birth": "1990-08-15", "holder_name": "Rahul Sharma"},
        risk_score=5.0,
        risk_label="LOW",
    )
    test_db.add(prior_screening)
    test_db.commit()

    # Step 2: Now re-screen with forged DOB '2000-08-15' (same aadhar number, same name)
    resolved_person, resolved_doc, is_repeat = resolve_candidate_identity_and_document(
        db=test_db,
        document_type="aadhaar",
        document_number=aadhar_num,
        holder_name="Rahul Sharma",
        date_of_birth="15/08/2000",  # Forged 10-year discrepancy!
    )
    assert is_repeat is True

    # Step 3: Run cross-document / same-document consistency check
    current_extracted = {
        "date_of_birth": "15/08/2000",
        "holder_name": "Rahul Sharma",
    }
    comparisons, risk_pts, flags = compare_cross_document_consistency(
        db=test_db,
        person=resolved_person,
        current_document=resolved_doc,
        current_extracted_fields=current_extracted,
    )

    # Verification
    assert risk_pts >= 80.0
    assert any("CRITICAL_TAMPERING_CONFLICT" in f for f in flags)
    dob_comp = next((c for c in comparisons if c["field_name"] == "date_of_birth"), None)
    assert dob_comp is not None
    assert dob_comp["is_match"] is False
    assert dob_comp["current_value"] == "2000-08-15"
    assert dob_comp["trusted_value"] == "1990-08-15"
    assert dob_comp["severity"] == "CRITICAL"
    print("\n[OK] Successfully caught same-document forged DOB tampering! Assigned risk points:", risk_pts)


def test_cross_document_aadhaar_to_passport_consistency(test_db):
    """
    Test Person having both Aadhaar and Passport:
    - Same DOB and compatible names ('R. K. Sharma' vs 'Rahul Kumar Sharma') should pass cleanly.
    - If Passport has conflicting DOB, it must flag CROSS_DOCUMENT_CONFLICT.
    """
    # 1. Existing person with Aadhaar
    person = Person(
        primary_name="Rahul Kumar Sharma",
        primary_name_hash=lookup_hash("Rahul Kumar Sharma"),
        date_of_birth="1992-05-20",
        verification_status="VERIFIED",
    )
    test_db.add(person)
    test_db.flush()

    aadhar_doc = Document(
        person_id=person.id,
        document_type="aadhaar",
        document_number="********4321",
        document_number_hash=lookup_hash("999988884321"),
        verification_status="VERIFIED",
    )
    test_db.add(aadhar_doc)
    test_db.flush()

    prior_screening = ScreeningRecord(
        document_id=aadhar_doc.id,
        person_id=person.id,
        document_type="aadhaar",
        document_number="********4321",
        document_number_hash=aadhar_doc.document_number_hash,
        holder_name="Rahul Kumar Sharma",
        date_of_birth="1992-05-20",
        extracted_fields={"date_of_birth": "1992-05-20", "holder_name": "Rahul Kumar Sharma"},
        risk_score=2.0,
    )
    test_db.add(prior_screening)
    test_db.commit()

    # 2. Person now submits Passport with matching DOB and initials 'R. K. Sharma'
    passport_doc = Document(
        person_id=person.id,
        document_type="passport",
        document_number="Z1234567",
        document_number_hash=lookup_hash("Z1234567"),
        verification_status="UNVERIFIED",
    )
    test_db.add(passport_doc)
    test_db.flush()

    comparisons, risk_pts, flags = compare_cross_document_consistency(
        db=test_db,
        person=person,
        current_document=passport_doc,
        current_extracted_fields={"date_of_birth": "20/05/1992", "holder_name": "R. K. Sharma"},
    )
    assert risk_pts == 0.0
    assert len(flags) == 0
    print("[OK] Passport with matching DOB and initials passed cleanly with 0 penalty points.")

    # 3. Person now submits Passport with conflicting DOB '1998-05-20'
    comparisons_bad, risk_pts_bad, flags_bad = compare_cross_document_consistency(
        db=test_db,
        person=person,
        current_document=passport_doc,
        current_extracted_fields={"date_of_birth": "20/05/1998", "holder_name": "Rahul Kumar Sharma"},
    )
    assert risk_pts_bad >= 30.0
    assert any("CROSS_DOCUMENT_CONFLICT" in f for f in flags_bad)
    print("[OK] Passport with conflicting DOB caught with risk points:", risk_pts_bad)
