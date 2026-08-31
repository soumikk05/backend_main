"""Fast, deterministic image quality gates for document intake."""
from __future__ import annotations

from typing import Any, Dict, List
import cv2
import numpy as np


def _detect_skew_angle(gray: np.ndarray) -> float:
    """Estimate image skew angle in degrees using Hough lines or thresholded edges."""
    try:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
        if lines is None or len(lines) == 0:
            return 0.0
        angles = []
        for line in lines[:20]:
            rho, theta = line[0]
            deg = np.degrees(theta) - 90.0
            if abs(deg) <= 45.0:
                angles.append(deg)
        if angles:
            return float(np.median(angles))
        return 0.0
    except Exception:
        return 0.0


def assess_image_quality(image_path: str, minimum_score: float = 45.0) -> Dict[str, Any]:
    """
    Assess document image quality across 10 distinct physical and optical metrics:
    - Blur (Laplacian variance)
    - Low resolution
    - Darkness / underexposure
    - Excessive brightness / overexposure
    - Contrast
    - Glare / specular hotspots
    - Shadows
    - Noise
    - Border occlusion / cropping
    - Skew angle

    Returns:
    {
        "quality_score": float (0-100),
        "acceptable": bool,
        "issues": list[str],
        "error_code": str | None,
        "metrics": dict
    }
    """
    image = cv2.imread(image_path)
    if image is None:
        return {
            "quality_score": 0.0,
            "acceptable": False,
            "issues": ["unreadable_image"],
            "error_code": "IMAGE_QUALITY_INSUFFICIENT",
            "metrics": {},
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    brightness = float(gray.mean())
    contrast = float(gray.std())
    blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    noise = float(cv2.Laplacian(cv2.GaussianBlur(gray, (3, 3), 0), cv2.CV_64F).var())

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    glare_ratio = float(np.mean((hsv[:, :, 2] > 245) & (hsv[:, :, 1] < 45)))
    shadow_ratio = float(np.mean(hsv[:, :, 2] < 35))

    # Border occlusion
    border = np.concatenate((
        gray[: max(1, height // 20), :].ravel(),
        gray[-max(1, height // 20):, :].ravel(),
        gray[:, : max(1, width // 20)].ravel(),
        gray[:, -max(1, width // 20):].ravel(),
    ))
    occlusion_ratio = float(np.mean((border < 12) | (border > 248)))

    # Skew detection
    skew_angle = _detect_skew_angle(gray)

    issues: List[str] = []
    penalties = 0.0

    if min(width, height) < 480:
        issues.append("low_resolution")
        penalties += 25.0
    if blur_variance < 80:
        issues.append("blur")
        penalties += 25.0
    if brightness < 45:
        issues.append("darkness")
        penalties += 20.0
    elif brightness > 215:
        issues.append("excessive_brightness")
        penalties += 20.0
    elif brightness < 55 or brightness > 200:
        issues.append("poor_brightness")
        penalties += 10.0
    if contrast < 25:
        issues.append("low_contrast")
        penalties += 12.0
    if glare_ratio > 0.025:
        issues.append("glare")
        penalties += min(20.0, glare_ratio * 300.0)
    if shadow_ratio > 0.20:
        issues.append("shadows")
        penalties += min(15.0, shadow_ratio * 70.0)
    if occlusion_ratio > 0.65:
        issues.append("occlusion")
        penalties += 10.0
    if noise > 350:
        issues.append("high_noise")
        penalties += 8.0
    if abs(skew_angle) > 15.0:
        issues.append("excessive_skew")
        penalties += 15.0

    quality_score = round(max(0.0, 100.0 - penalties), 2)
    acceptable = quality_score >= minimum_score

    return {
        "quality_score": quality_score,
        "acceptable": acceptable,
        "issues": issues,
        "error_code": None if acceptable else "IMAGE_QUALITY_INSUFFICIENT",
        "metrics": {
            "width": width,
            "height": height,
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "blur_variance": round(blur_variance, 2),
            "glare_ratio": round(glare_ratio, 4),
            "shadow_ratio": round(shadow_ratio, 4),
            "noise_level": round(noise, 2),
            "occlusion_ratio": round(occlusion_ratio, 4),
            "skew_angle_deg": round(skew_angle, 2),
        },
    }
