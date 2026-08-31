"""Unit tests for Multi-Signal Tampering Detection & Fusion (Requirements 7, 8, 9, 10, 11)."""
from pathlib import Path
import cv2
import numpy as np
import pytest
from app.services.tampering_service import (
    analyze_tampering,
    _error_level_analysis,
    _photo_region_analysis,
    _stamp_region_analysis,
    _exif_analysis,
)


def _create_sample_doc(tmp_path: Path) -> str:
    img = np.full((600, 800, 3), 235, dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (750, 550), (20, 20, 20), 2)
    path = tmp_path / "sample_doc.jpg"
    cv2.imwrite(str(path), img)
    return str(path)


def test_tampering_fusion_structure(tmp_path):
    path = _create_sample_doc(tmp_path)
    res = analyze_tampering(path)

    assert "tampering_score" in res
    assert "tampered" in res
    assert "signals" in res
    assert "detectors" in res
    assert "checks" in res
    assert "heatmap" in res

    signals = res["signals"]
    assert "ela" in signals
    assert "photo_region" in signals
    assert "copy_move" in signals
    assert "stamp" in signals
    assert "cnn" in signals
    assert "metadata" in signals


def test_ela_analysis(tmp_path):
    path = _create_sample_doc(tmp_path)
    check = _error_level_analysis(path)
    assert check["name"] == "error_level_analysis"
    assert "score" in check
    assert isinstance(check["triggered"], bool)


def test_photo_region_analysis_no_face(tmp_path):
    path = _create_sample_doc(tmp_path)
    check = _photo_region_analysis(path)
    assert check["name"] == "photo_region_analysis"
    assert check["triggered"] is False
    assert check["score"] == 0.0


def test_stamp_analysis(tmp_path):
    path = _create_sample_doc(tmp_path)
    check = _stamp_region_analysis(path)
    assert check["name"] == "stamp_forgery_analysis"
    assert "score" in check


def test_exif_analysis_no_exif(tmp_path):
    path = _create_sample_doc(tmp_path)
    check = _exif_analysis(path)
    assert check["name"] == "exif_metadata"
    # Missing EXIF alone must not flag document
    assert check["score"] == 0.0
    assert check["triggered"] is False
