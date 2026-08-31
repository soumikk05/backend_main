"""
Unit tests for Tampering & Forgery Detection (Module 3).
"""

import os
import tempfile
import numpy as np
import cv2
import pytest
from PIL import Image

from app.services.tampering_service import analyze_tampering, _photo_region_analysis, _stamp_region_analysis
from app.services.cnn_forgery_service import score_image_forgery_cnn


@pytest.fixture
def sample_image():
    # Create clean synthetic test image
    img = np.ones((200, 300, 3), dtype=np.uint8) * 240
    # Add text-like lines
    cv2.putText(img, "PASSPORT SAMPLE", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        path = f.name
        cv2.imwrite(path, img)

    yield path

    if os.path.exists(path):
        os.remove(path)


def test_tampering_analysis_structure(sample_image):
    res = analyze_tampering(sample_image)
    assert "tampering_score" in res
    assert "checks" in res
    assert res["error"] is None
    assert len(res["checks"]) == 6

    # Verify all 6 check names are present
    check_names = {c["name"] for c in res["checks"]}
    assert "error_level_analysis" in check_names
    assert "photo_region_analysis" in check_names
    assert "copy_move_detection" in check_names
    assert "stamp_forgery_analysis" in check_names
    assert "cnn_forgery_classification" in check_names
    assert "exif_metadata" in check_names


def test_cnn_forgery_scoring_contract(sample_image):
    res = score_image_forgery_cnn(sample_image)
    assert "cnn_score" in res
    assert "model" in res
    assert "hybrid_mobilenet" in res["model"]
    assert 0.0 <= res["cnn_score"] <= 100.0


def test_photo_region_analysis_graceful(sample_image):
    res = _photo_region_analysis(sample_image)
    assert "name" in res
    assert res["name"] == "photo_region_analysis"
    assert "score" in res
