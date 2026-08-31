"""United States (USA) Document Validator."""
import re
from typing import Any, Dict
from app.validation.validators.base import BaseCountryValidator

# US Passport: 6 to 9 alphanumeric characters (e.g. 9 digits or Book/Card identifiers)
US_PASSPORT_REGEX = re.compile(r"^[A-Z0-9]{6,9}$")
US_VISA_REGEX = re.compile(r"^[A-Z0-9]{8,12}$")
US_SSN_MASKED_REGEX = re.compile(r"^(\d{3}-\d{2}-\d{4}|\*{5}\d{4}|\d{9})$")


class USAValidator(BaseCountryValidator):
    country_code = "USA"
    country_name = "United States"

    def validate_document_number(self, number: str, document_type: str) -> Dict[str, Any]:
        clean = (number or "").strip().upper()
        if not clean:
            return {
                "valid": None,
                "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
                "rule": "usa_document_number_present",
                "message": "Missing document number for USA validation",
            }

        doc_type = document_type.lower()
        if doc_type == "passport":
            valid = bool(US_PASSPORT_REGEX.fullmatch(clean))
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "usa_passport_format",
                "message": "Valid US Passport format" if valid else f"Invalid US Passport format: '{clean}'",
            }
        elif doc_type == "visa":
            valid = bool(US_VISA_REGEX.fullmatch(clean))
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "usa_visa_format",
                "message": "Valid US Visa format" if valid else f"Invalid US Visa format: '{clean}'",
            }
        elif doc_type == "national_id":
            valid = bool(US_SSN_MASKED_REGEX.fullmatch(clean)) or len(clean) >= 6
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "usa_id_format",
                "message": "Valid US ID format" if valid else f"Invalid US ID format: '{clean}'",
            }

        return {
            "valid": None,
            "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
            "rule": "usa_unsupported_document_type",
            "message": f"No public format rule for USA {document_type}",
        }
