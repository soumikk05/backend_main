import time
import uuid
import random
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.schemas import FaceVerifyResponse
from app.services.face_service import verify_faces
from app.services.liveness_service import check_liveness, CHALLENGES
from app.utils.image_utils import save_upload_to_temp, cleanup_temp_file

router = APIRouter(prefix="/api/face", tags=["face"])

# In-memory challenge session storage with TTL
_LIVENESS_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_TTL_SECONDS = 120


def _cleanup_expired_sessions():
    now = time.time()
    expired = [k for k, v in _LIVENESS_SESSIONS.items() if now - v.get("created_at", 0) > SESSION_TTL_SECONDS]
    for k in expired:
        _LIVENESS_SESSIONS.pop(k, None)


@router.post("/liveness-challenge")
def get_liveness_challenge() -> Dict[str, Any]:
    """
    Issues a randomized liveness challenge (blink, smile, turn_left, turn_right)
    and creates a timed session token.
    """
    _cleanup_expired_sessions()
    session_token = str(uuid.uuid4())
    challenge = random.choice(CHALLENGES)
    _LIVENESS_SESSIONS[session_token] = {
        "challenge": challenge,
        "created_at": time.time(),
        "verified": False,
    }
    return {
        "challenge": challenge,
        "session_token": session_token,
        "expires_in_seconds": SESSION_TTL_SECONDS,
    }


@router.post("/liveness-verify")
def verify_liveness_burst(
    session_token: str = Form(...),
    frames: List[UploadFile] = File(...),
) -> Dict[str, Any]:
    """
    Evaluates a burst sequence of captured camera frames against the challenge issued for session_token.
    """
    _cleanup_expired_sessions()
    session = _LIVENESS_SESSIONS.get(session_token)
    if not session:
        return {
            "liveness_passed": False,
            "score": 0.0,
            "challenge": "unknown",
            "reason": "Session token expired or invalid. Please request a new challenge.",
            "detail": "Session expired or not found",
        }

    challenge = session["challenge"]
    temp_paths = []
    try:
        for f in frames:
            temp_paths.append(save_upload_to_temp(f))

        result = check_liveness(temp_paths, challenge=challenge)
        passed = result.get("passed", False)
        score = result.get("liveness_score", 0.0)
        error = result.get("error")

        if passed:
            session["verified"] = True

        reason = error
        if not passed and not reason:
            reason = f"The requested motion ({challenge}) was not clearly detected."

        return {
            "liveness_passed": passed,
            "score": score,
            "challenge": challenge,
            "reason": reason,
            "faces_detected": result.get("faces_detected", 1),
            "status": result.get("status", "SUCCESS" if passed else "FAILED"),
            "signals": result.get("signals", {}),
            "detail": "Active challenge-response verification succeeded" if passed else "Active challenge verification failed",
        }
    finally:
        for p in temp_paths:
            cleanup_temp_file(p)


@router.post("/verify", response_model=FaceVerifyResponse)
def verify(
    document_photo: UploadFile = File(..., description="Photo extracted/cropped from the ID document"),
    selfie_photo: UploadFile = File(..., description="Live selfie photo to compare against"),
):
    """
    Compares a document photo against a live selfie using DeepFace (VGG-Face).
    Runs synchronously in a worker threadpool to avoid blocking event loops during neural inference.
    Returns match=None with an error message (not a 500) if faces cannot be detected.
    """
    doc_temp_path = save_upload_to_temp(document_photo)
    selfie_temp_path = save_upload_to_temp(selfie_photo)
    try:
        result = verify_faces(doc_temp_path, selfie_temp_path)
        return result
    finally:
        cleanup_temp_file(doc_temp_path)
        cleanup_temp_file(selfie_temp_path)


@router.post("/liveness")
def liveness(selfie_photo: UploadFile = File(...), challenge: str | None = None):
    path = save_upload_to_temp(selfie_photo)
    try: return check_liveness(path, challenge)
    finally: cleanup_temp_file(path)

