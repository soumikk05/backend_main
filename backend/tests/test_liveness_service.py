import cv2
import numpy as np
from app.services.liveness_service import check_liveness


def test_liveness_rejects_bad_image(tmp_path):
    result = check_liveness(str(tmp_path / "missing.jpg"), "blink")
    assert result["passed"] is False
    assert result["challenge"] == "blink"


def test_liveness_returns_requested_challenge(tmp_path):
    path = tmp_path / "image.jpg"
    cv2.imwrite(str(path), np.full((200, 200, 3), 128, dtype=np.uint8))
    assert check_liveness(str(path), "smile")["challenge"] == "smile"
