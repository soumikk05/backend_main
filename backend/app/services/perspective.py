"""Document contour detection and four-point perspective rectification."""
from __future__ import annotations
from typing import Optional, Tuple
import cv2
import numpy as np

def _order(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    sums, diffs = points.sum(axis=1), np.diff(points, axis=1).ravel()
    rect[0], rect[2] = points[np.argmin(sums)], points[np.argmax(sums)]
    rect[1], rect[3] = points[np.argmin(diffs)], points[np.argmax(diffs)]
    return rect

def correct_perspective(image_path: str) -> Tuple[np.ndarray, bool, Optional[np.ndarray]]:
    """Return (image, corrected, contour). Original image is returned if no document is found."""
    image = cv2.imread(image_path)
    if image is None: raise ValueError("Unreadable image")
    ratio = image.shape[0] / 900.0
    resized = cv2.resize(image, (int(image.shape[1] / ratio), 900)) if image.shape[0] > 900 else image.copy()
    gray = cv2.GaussianBlur(cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    contours, _ = cv2.findContours(cv2.Canny(gray, 50, 150), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:12]:
        approx = cv2.approxPolyDP(contour, .02 * cv2.arcLength(contour, True), True)
        if len(approx) != 4 or cv2.contourArea(approx) < resized.shape[0] * resized.shape[1] * .15: continue
        pts = _order(approx.reshape(4, 2).astype("float32") * ratio)
        (tl, tr, br, bl) = pts
        width = int(max(np.linalg.norm(br-bl), np.linalg.norm(tr-tl)))
        height = int(max(np.linalg.norm(tr-br), np.linalg.norm(tl-bl)))
        if min(width, height) < 100: break
        dest = np.array([[0,0],[width-1,0],[width-1,height-1],[0,height-1]], dtype="float32")
        return cv2.warpPerspective(image, cv2.getPerspectiveTransform(pts, dest), (width, height)), True, pts
    return image, False, None
