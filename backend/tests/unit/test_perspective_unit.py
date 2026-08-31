"""Unit tests for Perspective Correction (Requirement 5 & Section 39)."""
from pathlib import Path
import cv2
import numpy as np
import pytest
from app.services.perspective import correct_perspective


def test_perspective_straight_document(tmp_path):
    img = np.full((600, 800, 3), 240, dtype=np.uint8)
    # Draw a document card inside
    cv2.rectangle(img, (100, 100), (700, 500), (50, 50, 50), -1)
    path = tmp_path / "straight.jpg"
    cv2.imwrite(str(path), img)

    rectified, was_corrected, contour = correct_perspective(str(path))
    assert rectified is not None
    assert isinstance(was_corrected, bool)


def test_perspective_skewed_document(tmp_path):
    img = np.full((800, 800, 3), 240, dtype=np.uint8)
    pts = np.array([[150, 120], [680, 180], [620, 680], [120, 580]], np.int32)
    cv2.fillPoly(img, [pts], (30, 30, 30))
    path = tmp_path / "skewed.jpg"
    cv2.imwrite(str(path), img)

    rectified, was_corrected, contour = correct_perspective(str(path))
    assert rectified is not None
    assert rectified.shape[0] > 0 and rectified.shape[1] > 0
