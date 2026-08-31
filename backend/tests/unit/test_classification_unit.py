"""Unit tests for Document Classification (Requirement 1 & Section 39)."""
from pathlib import Path
import cv2
import numpy as np
import pytest
from app.services.document_classifier import classify_document, SUPPORTED_TYPES


def _make_dummy_image(tmp_path: Path, text: str = "") -> str:
    img = np.full((300, 400, 3), 240, dtype=np.uint8)
    if text:
        cv2.putText(img, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    path = tmp_path / "doc.jpg"
    cv2.imwrite(str(path), img)
    return str(path)


def test_classify_passport_text(tmp_path):
    path = _make_dummy_image(tmp_path, "REPUBLIC PASSPORT SURNAME NATIONALITY")
    res = classify_document(path)
    assert res["document_type"] == "passport"
    assert res["supported"] is True
    assert res["confidence"] >= 0.50


def test_classify_visa_text(tmp_path):
    path = _make_dummy_image(tmp_path, "VISA ENTRIES VALID UNTIL")
    res = classify_document(path)
    assert res["document_type"] == "visa"
    assert res["supported"] is True


def test_classify_national_id_text(tmp_path):
    path = _make_dummy_image(tmp_path, "IDENTITY CARD NATIONAL ID")
    res = classify_document(path)
    assert res["document_type"] == "national_id"
    assert res["supported"] is True


def test_classify_driving_license_text(tmp_path):
    path = _make_dummy_image(tmp_path, "DRIVING LICENSE VEHICLE CLASS")
    res = classify_document(path)
    assert res["document_type"] == "driving_license"
    assert res["supported"] is True


def test_classify_permit_text(tmp_path):
    path = _make_dummy_image(tmp_path, "WORK PERMIT ISSUED TO")
    res = classify_document(path)
    assert res["document_type"] == "permit"
    assert res["supported"] is True


def test_classify_unsupported_document(tmp_path):
    path = _make_dummy_image(tmp_path, "GROCERY STORE RECEIPT TOTAL $45.00")
    res = classify_document(path)
    assert res["document_type"] == "unknown"
    assert res["supported"] is False
