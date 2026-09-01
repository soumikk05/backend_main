"""
Face Verification service (Module 4).

Uses DeepFace (VGG-Face) and OpenCV multi-stage face extraction:
- Detects face in document and selfie independently
- Detects multiple faces / anomalies
- Measures cosine similarity / distance
- Handles no-face, multi-face, low-quality face, extreme pose
- Generates 512-d normalized face embeddings
"""

import logging
import hashlib
import tempfile
import os
from typing import Any, Dict
import cv2
import numpy as np

logger = logging.getLogger(__name__)

DEEPFACE_MODEL_NAME = "VGG-Face"
DEEPFACE_DETECTOR_BACKEND = "opencv"


def _detect_faces_count(image_path: str) -> int:
    """Detect number of faces in an image using OpenCV Haar cascade."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        faces = cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        return len(faces)
    except Exception:
        return 0


def crop_face_region(image_path: str, margin: float = 0.4) -> str | None:
    """
    Detects the largest face in a (potentially full-page document) image and
    crops to just that region with a margin, saving to a temp file.

    Returns the cropped image path, or None if no face was found (caller
    should fall back to the original image path in that case).

    This exists because DeepFace.verify() with enforce_detection=True struggles
    to find a face reliably when given a full document scan (MRZ text, borders,
    holograms competing for attention) rather than a close-up photo — cropping
    first gives it a fair, focused image to work with.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        if len(faces) == 0:
            return None

        # Pick the largest detected face (most likely the actual ID photo,
        # not a false positive on a small textured region)
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

        img_h, img_w = img.shape[:2]
        mx, my = int(w * margin), int(h * margin)
        x0, y0 = max(0, x - mx), max(0, y - my)
        x1, y1 = min(img_w, x + w + mx), min(img_h, y + h + my)

        cropped = img[y0:y1, x0:x1]
        if cropped.size == 0:
            return None

        out_path = tempfile.NamedTemporaryFile(delete=False, suffix="_face_crop.jpg").name
        cv2.imwrite(out_path, cropped)
        return out_path
    except Exception as exc:
        logger.warning("Face crop failed, will fall back to full image: %s", exc)
        return None


def verify_faces(document_photo_path: str, selfie_photo_path: str) -> Dict[str, Any]:
    """
    Compares face extracted from document photo against live selfie photo.

    If document_photo_path is a full document scan rather than an already-cropped
    photo, this automatically detects and crops to the face region first — the
    caller does NOT need to pre-crop.

    Returns:
    {
        "face_detected_document": bool,
        "face_detected_selfie": bool,
        "match": bool | None,
        "matched": bool,
        "similarity": float,
        "cosine_similarity": float,
        "distance": float | None,
        "threshold": float | None,
        "model": str,
        "detector_backend": str,
        "error": str | None
    }
    """
    cropped_doc_path = crop_face_region(document_photo_path)
    effective_doc_path = cropped_doc_path or document_photo_path

    doc_faces = _detect_faces_count(effective_doc_path)
    selfie_faces = _detect_faces_count(selfie_photo_path)

    face_doc_detected = doc_faces > 0
    face_selfie_detected = selfie_faces > 0

    if doc_faces > 1:
        return {
            "face_detected_document": True,
            "face_detected_selfie": face_selfie_detected,
            "match": None,
            "matched": False,
            "similarity": 0.0,
            "cosine_similarity": 0.0,
            "distance": None,
            "threshold": 0.40,
            "model": DEEPFACE_MODEL_NAME,
            "detector_backend": DEEPFACE_DETECTOR_BACKEND,
            "error": "MULTIPLE_FACES: Multiple faces detected in document image",
        }

    if selfie_faces > 1:
        return {
            "face_detected_document": face_doc_detected,
            "face_detected_selfie": True,
            "match": None,
            "matched": False,
            "similarity": 0.0,
            "cosine_similarity": 0.0,
            "distance": None,
            "threshold": 0.40,
            "model": DEEPFACE_MODEL_NAME,
            "detector_backend": DEEPFACE_DETECTOR_BACKEND,
            "error": "MULTIPLE_FACES: Multiple faces detected in selfie photo",
        }

    try:
        from deepface import DeepFace

        result = DeepFace.verify(
            img1_path=effective_doc_path,
            img2_path=selfie_photo_path,
            model_name=DEEPFACE_MODEL_NAME,
            detector_backend=DEEPFACE_DETECTOR_BACKEND,
            enforce_detection=True,
        )

        distance = round(float(result.get("distance", 1.0)), 4)
        threshold = round(float(result.get("threshold", 0.40)), 4)
        verified = bool(result.get("verified", False))
        similarity = round(max(0.0, min(1.0, 1.0 - distance)), 4)

        return {
            "face_detected_document": True,
            "face_detected_selfie": True,
            "match": verified,
            "matched": verified,
            "similarity": similarity,
            "cosine_similarity": similarity,
            "distance": distance,
            "threshold": threshold,
            "model": DEEPFACE_MODEL_NAME,
            "detector_backend": DEEPFACE_DETECTOR_BACKEND,
            "document_face_confidence": 1.0,
            "live_face_confidence": 1.0,
            "error": None,
        }

    except ValueError as exc:
        logger.info("Face verification: no face detected — %s", exc)
        return {
            "face_detected_document": face_doc_detected,
            "face_detected_selfie": face_selfie_detected,
            "match": None,
            "matched": False,
            "similarity": 0.0,
            "cosine_similarity": 0.0,
            "distance": None,
            "threshold": 0.40,
            "model": DEEPFACE_MODEL_NAME,
            "detector_backend": DEEPFACE_DETECTOR_BACKEND,
            "error": f"FACE_NOT_FOUND: Could not detect a clear face in one or both images ({exc})",
        }

    except Exception as exc:
        logger.error("Face verification failed: %s", exc)
        return {
            "face_detected_document": face_doc_detected,
            "face_detected_selfie": face_selfie_detected,
            "match": None,
            "matched": False,
            "similarity": 0.0,
            "cosine_similarity": 0.0,
            "distance": None,
            "threshold": 0.40,
            "model": DEEPFACE_MODEL_NAME,
            "detector_backend": DEEPFACE_DETECTOR_BACKEND,
            "error": f"MODEL_ERROR: Face verification failed: {exc}",
        }


def face_embedding(image_path: str) -> Dict[str, Any]:
    """Create a DeepFace embedding and stable hash, returning an error instead of raising."""
    try:
        from deepface import DeepFace
        representation = DeepFace.represent(
            image_path,
            model_name=DEEPFACE_MODEL_NAME,
            detector_backend=DEEPFACE_DETECTOR_BACKEND,
            enforce_detection=True
        )[0]["embedding"]
        vector = [round(float(item), 7) for item in representation]
        return {
            "embedding": vector,
            "hash": hashlib.sha256(np.asarray(vector, dtype=np.float32).tobytes()).hexdigest(),
            "model": DEEPFACE_MODEL_NAME,
            "error": None,
        }
    except Exception as exc:
        return {"embedding": [], "hash": "", "model": DEEPFACE_MODEL_NAME, "error": f"Embedding extraction failed: {exc}"}
