"""India (IND) Document Validator."""
import re
from typing import Any, Dict
from app.validation.validators.base import BaseCountryValidator

# Official Indian Passport: 1 uppercase letter followed by 7 digits (e.g. Z1234567)
# Aadhaar (masked/unmasked): 12 digits or 4 masked digits + 4 visible
# PAN: 5 uppercase letters, 4 digits, 1 uppercase letter
PASSPORT_REGEX = re.compile(r"^[A-Z][0-9]{7}$")
VISA_REGEX = re.compile(r"^[A-Z0-9]{6,12}$")
AADHAAR_REGEX = re.compile(r"^(\d{12}|\d{4}\s\d{4}\s\d{4}|\*{8}\d{4}|[Xx*]{4}\s[Xx*]{4}\s\d{4})$")
DRIVING_LICENSE_REGEX = re.compile(r"^[A-Z]{2}[0-9]{2}[0-9]{11}$")


class IndiaValidator(BaseCountryValidator):
    country_code = "IND"
    country_name = "India"

    def validate_document_number(self, number: str, document_type: str) -> Dict[str, Any]:
        clean = (number or "").strip().upper()
        if not clean:
            return {
                "valid": None,
                "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
                "rule": "ind_document_number_present",
                "message": "Missing document number for India validation",
            }

        doc_type = document_type.lower()
        if doc_type == "passport":
            valid = bool(PASSPORT_REGEX.fullmatch(clean))
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "ind_passport_format_1letter_7digits",
                "message": "Valid Indian Passport format (1 letter + 7 digits)" if valid else f"Invalid Indian Passport format: '{clean}'",
            }
        elif doc_type == "visa":
            valid = bool(VISA_REGEX.fullmatch(clean))
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "ind_visa_format",
                "message": "Valid Indian Visa format" if valid else f"Invalid Indian Visa format: '{clean}'",
            }
        elif doc_type == "national_id":
            clean_no_space = clean.replace(" ", "")
            valid = bool(AADHAAR_REGEX.fullmatch(clean)) or bool(AADHAAR_REGEX.fullmatch(clean_no_space)) or len(clean_no_space) >= 8
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "ind_aadhaar_or_national_id_format",
                "message": "Valid Indian National ID format" if valid else f"Invalid Indian National ID format: '{clean}'",
            }
        elif doc_type == "driving_license":
            # State code (2 letters) + RTO (2 digits) + Year/Serial
            valid = bool(DRIVING_LICENSE_REGEX.fullmatch(clean)) or (len(clean) >= 10 and clean[:2].isalpha())
            return {
                "valid": valid,
                "status": "VALID" if valid else "INVALID",
                "rule": "ind_driving_license_format",
                "message": "Valid Indian Driving License format" if valid else f"Invalid Indian DL format: '{clean}'",
            }

        return {
            "valid": None,
            "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
            "rule": "ind_unsupported_document_type",
            "message": f"No public format rule for India {document_type}",
        }
