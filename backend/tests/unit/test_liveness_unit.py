"""Unit tests for Prototype Software Liveness (Requirement 13 & Section 39)."""
from pathlib import Path
import cv2
import numpy as np
import pytest
from app.services.liveness_service import check_liveness, CHALLENGES


def test_liveness_unreadable_image():
    res = check_liveness("non_existent_file.jpg")
    assert res["passed"] is False
    assert res["liveness_score"] == 0.0
    assert "error" in res
    assert "not hardware-grade" in res["note"]


def test_liveness_challenge_types():
    assert "blink" in CHALLENGES
    assert "smile" in CHALLENGES
    assert "turn_left" in CHALLENGES
    assert "turn_right" in CHALLENGES
