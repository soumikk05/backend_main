"""Base Country Validator interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseCountryValidator(ABC):
    """Abstract base validator for jurisdiction-specific travel and identity document rules."""

    country_code: str = "UNKNOWN"
    country_name: str = "Unknown"

    @abstractmethod
    def validate_document_number(self, number: str, document_type: str) -> Dict[str, Any]:
        """
        Validate document format against public specification.
        Returns:
        {
            "valid": bool | None,
            "status": "VALID" | "INVALID" | "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
            "rule": str,
            "message": str
        }
        """
        pass
