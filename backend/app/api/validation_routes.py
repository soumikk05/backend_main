from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models.schemas import ValidationResponse
from app.services.validation_service import validate_document

router = APIRouter(prefix="/api/validation", tags=["validation"])


class ExtractionInput(BaseModel):
    document_type: str = Field(..., examples=["PASSPORT"])
    fields: Dict[str, Any] = Field(default_factory=dict)
    confidence: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


@router.post("/check", response_model=ValidationResponse)
def check(extraction: ExtractionInput):
    """
    Accepts an OCR extraction result and runs rule-based validation checks
    against it (MRZ checksums, document number format, date logic).
    Runs synchronously in a worker threadpool. Never raises 500s on malformed input.
    """
    result = validate_document(extraction.dict())
    return result