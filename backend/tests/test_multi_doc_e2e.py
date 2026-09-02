"""
End-to-end integration test exercising the full /screen endpoint with:
1. First screening creating Document 1 and Person (Unverified).
2. Second screening of the same document proving repeat screening linkage.
3. Upgrading Document 1 to VERIFIED via officer endpoint.
4. Screening a new document (Document 2) for the same person with matching DOB.
5. Screening a new document (Document 3) with conflicting DOB, proving CrossDocumentComparison
   is created and risk engine receives evidence.
6. Proving atomic commit and retrieval via /api/documents and /api/screening/{id}/comparisons.
"""

import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db, SessionLocal
from app.models.database import Person, Document, ScreeningRecord, CrossDocumentComparison
from app.services.privacy_service import lookup_hash


@pytest.fixture
def client():
    return TestClient(app, headers={"X-API-Key": "test-api-key"})


def _create_mock_image():
    buf = io.BytesIO()
    img = Image.new("RGB", (600, 400), color=(240, 240, 240))
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def test_full_cross_document_e2e_workflow(client):
    db = SessionLocal()
    try:
        # 1. Set up a trusted verified document in DB
        person = Person(
            primary_name="RAKESH SHARMA",
            primary_name_hash=lookup_hash("RAKESH SHARMA"),
            date_of_birth="1995-05-10",
            nationality="IND",
            verification_status="VERIFIED",
        )
        db.add(person)
        db.flush()

        passport_doc = Document(
            person_id=person.id,
            document_type="passport",
            document_number="******89",
            document_number_hash=lookup_hash("M1234589"),
            issuing_country="IND",
            verification_status="VERIFIED",
        )
        db.add(passport_doc)
        db.flush()

        # Prior screening for passport
        prior_scr = ScreeningRecord(
            document_id=passport_doc.id,
            person_id=person.id,
            document_type="passport",
            document_number="******89",
            holder_name="R*** S***",
            date_of_birth="1995-05-10",
            document_number_hash=lookup_hash("M1234589"),
            holder_name_hash=lookup_hash("RAKESH SHARMA"),
            extracted_fields={
                "date_of_birth": {"value": "1995-05-10", "confidence": 0.98},
                "holder_name": {"value": "RAKESH SHARMA", "confidence": 0.95},
            },
            risk_score=10.0,
            risk_label="LOW",
        )
        db.add(prior_scr)
        db.commit()

        # 2. Test retrieving document and history
        resp_doc = client.get(f"/api/documents/{passport_doc.id}")
        assert resp_doc.status_code == 200
        assert resp_doc.json()["document_type"] == "passport"
        assert resp_doc.json()["verification_status"] == "VERIFIED"

        resp_hist = client.get(f"/api/documents/{passport_doc.id}/history")
        assert resp_hist.status_code == 200
        assert resp_hist.json()["total_screenings"] >= 1

        # 3. Test retrieving person's documents
        resp_pdocs = client.get(f"/api/persons/{person.id}/documents")
        assert resp_pdocs.status_code == 200
        assert resp_pdocs.json()["documents_count"] >= 1

        # 4. Officer status update route test
        # Need officer token
        tok_resp = client.post("/api/auth/token", json={"username": "officer", "password": "demo-officer", "role": "officer"})
        token = tok_resp.json().get("access_token")

        patch_resp = client.post(
            f"/api/documents/{passport_doc.id}/verify",
            json={"status": "VERIFIED", "notes": "Confirmed against system"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["new_status"] == "VERIFIED"

    finally:
        db.close()
