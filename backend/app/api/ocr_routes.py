from fastapi import APIRouter, UploadFile, File

from app.models.schemas import OCRResponse
from app.services.ocr_service import extract_document_fields
from app.utils.image_utils import save_upload_to_temp, cleanup_temp_file

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/extract", response_model=OCRResponse)
def extract(file: UploadFile = File(..., description="Document image (passport, visa, or national ID)")):
    """
    Accepts a document image, runs OCR extraction, and returns structured fields.
    Runs synchronously in a worker threadpool to prevent blocking the event loop.
    Never raises on bad/blurry images — errors are surfaced in response body.
    """
    temp_path = save_upload_to_temp(file)
    try:
        result = extract_document_fields(temp_path)
        return result
    finally:
        cleanup_temp_file(temp_path)