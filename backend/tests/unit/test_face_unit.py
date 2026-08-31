"""Unit tests for Face Verification (Requirement 12 & Section 39)."""
from pathlib import Path
import cv2
import numpy as np
import pytest
from app.services.face_service import verify_faces, face_embedding


def test_verify_faces_missing_images():
    res = verify_faces("missing_doc.jpg", "missing_selfie.jpg")
    assert res["match"] is None
    assert res["matched"] is False
    assert res["error"] is not None


def test_face_embedding_empty_on_missing():
    res = face_embedding("missing.jpg")
    assert res["embedding"] == []
    assert res["error"] is not None
