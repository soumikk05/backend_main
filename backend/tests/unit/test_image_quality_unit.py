"""Unit tests for Image Quality Assessment (Requirement 4 & Section 39)."""
from pathlib import Path
import cv2
import numpy as np
import pytest
from app.services.image_quality import assess_image_quality


def test_quality_good_image(tmp_path):
    img = np.full((600, 800, 3), 180, dtype=np.uint8)
    # Add high contrast edges to simulate clear text
    cv2.putText(img, "PASSPORT NUMBER 123456", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (10, 10, 10), 2)
    path = tmp_path / "good.jpg"
    cv2.imwrite(str(path), img)

    res = assess_image_quality(str(path))
    assert res["quality_score"] >= 60.0
    assert res["acceptable"] is True
    assert res["error_code"] is None


def test_quality_dark_image(tmp_path):
    img = np.full((500, 500, 3), 20, dtype=np.uint8)
    path = tmp_path / "dark.jpg"
    cv2.imwrite(str(path), img)

    res = assess_image_quality(str(path))
    assert "darkness" in res["issues"] or "poor_brightness" in res["issues"]


def test_quality_glare_image(tmp_path):
    img = np.full((500, 500, 3), 150, dtype=np.uint8)
    # Create specular glare hotspot
    img[100:300, 100:300] = [255, 255, 255]
    path = tmp_path / "glare.jpg"
    cv2.imwrite(str(path), img)

    res = assess_image_quality(str(path))
    assert "glare" in res["issues"]


def test_quality_blurry_image(tmp_path):
    img = np.full((500, 500, 3), 150, dtype=np.uint8)
    blurred = cv2.GaussianBlur(img, (25, 25), 10)
    path = tmp_path / "blurry.jpg"
    cv2.imwrite(str(path), blurred)

    res = assess_image_quality(str(path))
    assert "blur" in res["issues"]


def test_quality_unreadable_file():
    res = assess_image_quality("non_existent_file_path.jpg")
    assert res["acceptable"] is False
    assert res["error_code"] == "IMAGE_QUALITY_INSUFFICIENT"
