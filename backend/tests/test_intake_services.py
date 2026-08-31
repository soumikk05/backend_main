import cv2
import numpy as np

from app.services.image_quality import assess_image_quality
from app.services.perspective import correct_perspective


def test_quality_rejects_unreadable_image(tmp_path):
    result = assess_image_quality(str(tmp_path / "missing.jpg"))
    assert result["acceptable"] is False
    assert "unreadable_image" in result["issues"]


def test_quality_accepts_clear_image(tmp_path):
    path = tmp_path / "clear.png"
    image = np.full((700, 1000, 3), 180, dtype=np.uint8)
    cv2.putText(image, "PASSPORT A1234567", (70, 350), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 20, 20), 3)
    cv2.imwrite(str(path), image)
    assert assess_image_quality(str(path))["acceptable"] is True


def test_perspective_keeps_image_when_no_contour(tmp_path):
    path = tmp_path / "flat.png"
    cv2.imwrite(str(path), np.full((200, 300, 3), 128, dtype=np.uint8))
    image, corrected, contour = correct_perspective(str(path))
    assert image.shape[:2] == (200, 300)
    assert corrected is False
    assert contour is None
