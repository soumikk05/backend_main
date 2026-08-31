from fastapi import APIRouter, File, UploadFile
from app.services.document_classifier import classify_document
from app.services.image_quality import assess_image_quality
from app.utils.image_utils import cleanup_temp_file, save_upload_to_temp

router = APIRouter(tags=["document intake"])

@router.post("/classify-document")
@router.post("/api/classify-document")
def classify(file: UploadFile = File(..., description="Document image")):
    path = save_upload_to_temp(file)
    try: return classify_document(path)
    finally: cleanup_temp_file(path)

@router.post("/api/image-quality")
def quality(file: UploadFile = File(..., description="Document image")):
    path = save_upload_to_temp(file)
    try: return assess_image_quality(path)
    finally: cleanup_temp_file(path)
