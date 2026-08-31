from app.services.validation_service import validate_document


def test_validation_understands_confidence_wrapped_fields():
    result = validate_document({
        "document_type": "passport",
        "fields": {"document_number": {"value": "A1234567", "confidence": .9}, "nationality": {"value": "IND", "confidence": .9}, "date_of_birth": {"value": "1990-01-01", "confidence": .9}, "expiration_date": {"value": "2030-01-01", "confidence": .9}},
        "confidence": {"overall_composite": True, "document_number": True, "date_of_birth": True, "expiration_date": True},
    })
    assert result["confidence"] == .9
    assert result["passed_rules"]
    assert "warnings" in result


def test_low_ocr_confidence_requires_review_warning():
    result = validate_document({"document_type": "national_id", "fields": {"document_number": {"value": "ABC123456", "confidence": .2}}})
    assert any(check["name"] == "ocr_confidence" for check in result["failed_rules"])
