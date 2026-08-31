"""Canada (CAN) Document Validator."""
import re
from typing import Any, Dict
from app.validation.validators.base import BaseCountryValidator

# Canadian Passport: 2 letters followed by 6 digits (e.g. AA123456)
CAN_PASSPORT_REGEX = re.compile(r"^[A-Z]{2}[0-9]{6}$")
CAN_VISA_REGEX = re.compile(r"^[A-Z0-9]{8,12}$")


class CanadaValidator(BaseCountryValidator):
    country_code = "CAN"
    country_name = "Canada"

    def validate_document_number(self, number: str, document_type: str) -> Dict[str, Any]:
        clean = (number or "").strip().upper()
        if not clean:
            return {
                "valid": None,
                "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
                "rule": "can_document_number_present",
                "message": "Missing document number for Canada validation",
            }

        doc_type = document_type.lower()
        if doc_type == "passport":
            valid = bool(CAN_PASSPORT_REGEX.fullmatch(clean))
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "can_passport_format_2letters_6digits",
                "message": "Valid Canadian Passport format (2 letters + 6 digits)" if valid else f"Invalid Canadian Passport format: '{clean}'",
            }
        elif doc_type == "visa":
            valid = bool(CAN_VISA_REGEX.fullmatch(clean))
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "can_visa_format",
                "message": "Valid Canadian Visa format" if valid else f"Invalid Canadian Visa format: '{clean}'",
            }

        return {
            "valid": None,
            "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
            "rule": "can_unsupported_document_type",
            "message": f"No public format rule for Canada {document_type}",
        }
