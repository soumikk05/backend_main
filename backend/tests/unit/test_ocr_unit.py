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
