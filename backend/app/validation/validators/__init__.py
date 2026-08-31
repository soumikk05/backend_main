"""Country validators package."""
from typing import Dict, Optional, Any
from app.validation.validators.base import BaseCountryValidator
from app.validation.validators.india import IndiaValidator
from app.validation.validators.usa import USAValidator
from app.validation.validators.uk import UKValidator
from app.validation.validators.canada import CanadaValidator

_VALIDATORS: Dict[str, BaseCountryValidator] = {
    "IND": IndiaValidator(),
    "INDIA": IndiaValidator(),
    "USA": USAValidator(),
    "US": USAValidator(),
    "GBR": UKValidator(),
    "UK": UKValidator(),
    "CAN": CanadaValidator(),
    "CANADA": CanadaValidator(),
}


def get_country_validator(country_code: Optional[str]) -> Optional[BaseCountryValidator]:
    if not country_code:
        return None
    return _VALIDATORS.get(country_code.strip().upper())


def validate_country_document(number: str, country: Optional[str], document_type: str) -> Dict[str, Any]:
    validator = get_country_validator(country)
    if not validator:
        return {
            "valid": None,
            "status": "NOT_VERIFIABLE_WITH_AVAILABLE_DATA",
            "rule": "unsupported_country_code",
            "message": f"Country '{country}' not in public validation database",
        }
    return validator.validate_document_number(number, document_type)
