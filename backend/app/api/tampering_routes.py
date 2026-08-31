"""
Tampering detection routes (Module 3).
"""

from fastapi import APIRouter, UploadFile, File

from app.models.schemas import TamperingResponse, CNNScoreResponse
from app.services.tampering_service import analyze_tampering
from app.services.cnn_forgery_service import score_image_forgery_cnn
from app.utils.image_utils import save_upload_to_temp, cleanup_temp_file

router = APIRouter(prefix="/api/tampering", tags=["tampering"])


@router.post("/analyze", response_model=TamperingResponse)
def analyze(file: UploadFile = File(..., description="Document image to screen for tampering")):
    """
    Runs rule-based and deep tampering analysis (ELA + EXIF + copy-move + stamp + CNN patch analysis).
    Runs synchronously in a worker threadpool. Never raises on unreadable images.
    """
    temp_path = save_upload_to_temp(file)
    try:
        result = analyze_tampering(temp_path)
        return result
    finally:
        cleanup_temp_file(temp_path)


@router.post("/cnn-score", response_model=CNNScoreResponse)
def cnn_score(file: UploadFile = File(..., description="Document image for deep CNN forgery analysis")):
    """
    Direct endpoint for convolutional spatial anomaly and ELA patch forgery classification.
    """
    temp_path = save_upload_to_temp(file)
    try:
        result = score_image_forgery_cnn(temp_path)
        return result
    finally:
        cleanup_temp_file(temp_path)