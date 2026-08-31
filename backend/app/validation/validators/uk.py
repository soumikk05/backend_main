"""United Kingdom (GBR / UK) Document Validator."""
import re
from typing import Any, Dict
from app.validation.validators.base import BaseCountryValidator

# UK Passport: 9 digits
UK_PASSPORT_REGEX = re.compile(r"^[0-9]{9}$")
UK_VISA_REGEX = re.compile(r"^[A-Z0-9]{7,12}$")
UK_DRIVING_LICENSE_REGEX = re.compile(r"^[A-Z9]{5}\d{6}[A-Z9]{2}\d[A-Z]{2}$")


class UKValidator(BaseCountryValidator):
    country_code = "GBR"
    country_name = "United Kingdom"

    def validate_document_number(self, number: str, document_type: str) -> Dict[str, Any]:
        clean = (number or "").strip().upper()
        if not clean:
            return {
                "valid": None,
                "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
                "rule": "uk_document_number_present",
                "message": "Missing document number for UK validation",
            }

        doc_type = document_type.lower()
        if doc_type == "passport":
            valid = bool(UK_PASSPORT_REGEX.fullmatch(clean))
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "uk_passport_format_9digits",
                "message": "Valid UK Passport format (9 digits)" if valid else f"Invalid UK Passport format: '{clean}'",
            }
        elif doc_type == "visa":
            valid = bool(UK_VISA_REGEX.fullmatch(clean))
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "uk_visa_format",
                "message": "Valid UK Visa format" if valid else f"Invalid UK Visa format: '{clean}'",
            }
        elif doc_type == "driving_license":
            valid = bool(UK_DRIVING_LICENSE_REGEX.fullmatch(clean)) or len(clean) == 16
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "uk_driving_license_format",
                "message": "Valid UK Driving License format" if valid else f"Invalid UK Driving License format: '{clean}'",
            }

        return {
            "valid": None,
            "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
            "rule": "uk_unsupported_document_type",
            "message": f"No public format rule for UK {document_type}",
        }
