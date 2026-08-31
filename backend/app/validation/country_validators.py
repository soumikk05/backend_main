"""Country document number validation router (backwards-compatible wrapper)."""
from typing import Optional
from app.validation.validators import validate_country_document


def validate_document_number(number: str, country: Optional[str], document_type: str) -> Optional[bool]:
    """
    Returns True/False if verifiable, or None if NOT_VERIFIABLE_WITH_AVAILABLE_DATA.
    """
    result = validate_country_document(number, country, document_type)
    return result.get("valid")
