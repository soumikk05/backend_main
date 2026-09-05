"""
Shared image helpers used across services (OCR, tampering, face, hashing).

Security policy (SIH PS-26188):
- Strict MIME type allowlist: unknown or disallowed MIME → HTTP 415
- Magic byte validation: file content must match a supported image format
- Upload size cap: configurable MAX_UPLOAD_SIZE_MB → HTTP 413
- Temp file isolation: NamedTemporaryFile, no user-controlled path components
"""

import hashlib
import io
import os
import struct
import tempfile
import logging
from typing import Tuple

import cv2
from fastapi import UploadFile, HTTPException

from app.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    IMAGE_MAGIC_BYTES,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
)

logger = logging.getLogger(__name__)

# Minimum bytes to read for magic signature detection
_MAGIC_READ_BYTES = 12


def _detect_image_type_from_bytes(header: bytes) -> str:
    """
    Detect image or video format from the first 12 bytes of a file.
    Returns a MIME type string or raises HTTPException 415 for unknown/unsupported formats.
    """
    if header[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if header[:4] == b"RIFF":
        if header[8:12] == b"WEBP":
            return "image/webp"
        if header[8:12] == b"AVI ":
            return "video/x-msvideo"
    if header[4:8] == b"ftyp":
        # Could be video/mp4 or video/quicktime
        return "video/mp4"
    if header[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    if header[:2] == b"BM":
        return "image/bmp"
    raise HTTPException(
        status_code=415,
        detail=(
            "Unsupported file format. File signature does not match any allowed image or video format "
            "(JPEG, PNG, WEBP, TIFF, BMP, MP4, MOV, AVI). Ensure the file is valid and uncorrupted."
        ),
    )


def _validate_image_readable(file_path: str) -> None:
    """
    Verify the saved temp file is actually a decodable image or video via OpenCV.
    Raises HTTPException 415 if OpenCV cannot decode it.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".mp4", ".mov", ".avi"):
        cap = cv2.VideoCapture(file_path)
        readable = cap.isOpened()
        if readable:
            ret, frame = cap.read()
            readable = ret and frame is not None
        cap.release()
        if not readable:
            raise HTTPException(
                status_code=415,
                detail="The uploaded file could not be decoded as a valid video.",
            )
    else:
        img = cv2.imread(file_path)
        if img is None:
            raise HTTPException(
                status_code=415,
                detail=(
                    "The uploaded file could not be decoded as a valid image. "
                    "The file may be corrupt, truncated, or in an unsupported sub-format."
                ),
            )
        h, w = img.shape[:2]
        if h > 10000 or w > 10000 or (h * w) > 50_000_000:
            raise HTTPException(
                status_code=415,
                detail=f"Image dimensions ({w}x{h}) exceed maximum allowable limits (decompression bomb protection).",
            )
        if h < 20 or w < 20:
            raise HTTPException(
                status_code=415,
                detail=f"Image dimensions ({w}x{h}) are too small to be a valid document.",
            )


def compute_image_sha256(file_path: str) -> str:
    """Computes SHA-256 hash of a local image file for duplicate replay detection."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as exc:
        logger.warning("Could not compute image sha256: %s", exc)
        return ""


def save_upload_to_temp(upload_file: UploadFile) -> str:
    """
    Persists an incoming FastAPI UploadFile to a temp file on disk.

    Security checks (in order):
    1. Declared MIME type allowlist (HTTP 415 if not in allowed set)
    2. Upload size cap (HTTP 413)
    3. Magic byte signature verification (HTTP 415 if content doesn't match an image)
    4. OpenCV decode verification (HTTP 415 if file is corrupt/unreadable)

    Returns the local file path of the validated temp file.
    """
    filename = upload_file.filename or "upload.bin"
    suffix = os.path.splitext(filename)[1].lower()

    # Validate declared extension
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"File extension '{suffix}' is not allowed. Permitted: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}",
        )

    # Validate declared MIME type (strict — application/octet-stream no longer accepted)
    declared_mime = (upload_file.content_type or "").split(";")[0].strip().lower()
    if declared_mime and declared_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"MIME type '{declared_mime}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )

    # Stream to temp file with size guard
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
    try:
        size = 0
        header_buf = b""
        while True:
            chunk = upload_file.file.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE_BYTES:
                tmp.close()
                cleanup_temp_file(tmp.name)
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded file exceeds maximum allowed size of {MAX_UPLOAD_SIZE_MB} MB",
                )
            tmp.write(chunk)
            # Accumulate enough bytes for magic detection (only first pass)
            if len(header_buf) < _MAGIC_READ_BYTES:
                header_buf += chunk
    finally:
        tmp.close()

    # Magic byte validation — detect actual content type regardless of extension/MIME claim
    detected_mime = _detect_image_type_from_bytes(header_buf[:_MAGIC_READ_BYTES])

    # Rename with correct extension for downstream tools
    correct_suffix = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/tiff": ".tif",
        "image/bmp": ".bmp",
        "video/mp4": ".mp4",
        "video/x-msvideo": ".avi",
    }.get(detected_mime, ".img")

    final_path = tmp.name.replace(".tmp", correct_suffix)
    try:
        os.rename(tmp.name, final_path)
    except OSError:
        final_path = tmp.name  # Keep .tmp name if rename fails (different drive, etc.)

    # Structural decode validation via OpenCV
    _validate_image_readable(final_path)

    return final_path


def cleanup_temp_file(path: str) -> None:
    """Best-effort delete of a temp file created by save_upload_to_temp."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass