"""Unit tests for OCR Routing and Field-level Confidence (Requirements 2 & 3)."""
from pathlib import Path
import pytest
from app.services.ocr_service import _add_field_metadata, extract_document_fields


def test_add_field_metadata_structure():
    raw_result = {
        "document_type": "passport",
        "fields": {
            "name": "JOHN DOE",
            "document_number": "A1234567",
            "nationality": "USA",
        },
        "confidence": {
            "document_number": 0.98,
            "ocr_average_confidence": 0.90,
        },
    }

    annotated = _add_field_metadata(raw_result, "mrz")
    fields = annotated["fields"]

    assert "document_number" in fields
    assert fields["document_number"]["value"] == "A1234567"
    assert fields["document_number"]["confidence"] == 0.98
    assert fields["document_number"]["source"] == "mrz"
    assert fields["document_number"]["validated"] is True

    assert fields["nationality"]["confidence"] == 0.90
    assert fields["nationality"]["source"] == "mrz"


def test_extract_document_fields_unreadable():
    result = extract_document_fields("non_existent_file.jpg", "passport")
    assert result["document_type"] == "passport"
    assert result["fields"] == {}


def test_ocr_extract_probable_name_title_case_and_rejection():
    from app.services.ocr_service import _extract_probable_name
    lines_with_conf = [
        ("Government of India", 0.95),
        ("Unique Identification Authority of India", 0.92),
        ("To", 0.88),
        ("Basant Raj", 0.99),
        ("C/O: Aadhar Card", 0.85),
        ("PO: Grugram", 0.90),
        ("HT HTER ,", 0.15),
    ]
    name, conf = _extract_probable_name(lines_with_conf)
    assert name == "Basant Raj"
    assert conf >= 0.90


def test_ocr_extract_document_number_negative_filters():
    from app.services.ocr_service import _extract_document_number
    sample_text = """
    Unique Identification Authority of India
    Enrolment No: 4049/30507/00690
    Basant Raj
    PIN Code: 110042
    Mobile: 9931971873
    Your Aadhaar No. : 1234 5678 9101
    VID : 9110 0445 8669 0808
    """
    lines_with_conf = [(line.strip(), 0.92) for line in sample_text.splitlines() if line.strip()]
    doc_num, conf = _extract_document_number(sample_text, lines_with_conf, "national_id")
    assert doc_num == "1234 5678 9101"
    assert conf >= 0.85


def test_ocr_find_date_near_label_glued():
    from app.services.ocr_service import _find_date_near_label, _DOB_LABELS
    lines = [
        "Basant Raj",
        "14@fDOB:01/012000",
        "MALE",
    ]
    date_val, conf = _find_date_near_label(lines, _DOB_LABELS)
    assert date_val == "01/01/2000"
    assert conf >= 0.85

