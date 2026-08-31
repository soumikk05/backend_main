"""
Tampering Detection & Forensic Fusion service (Module 3).

Combines 6 independent forensic signals:
  1. Error Level Analysis (ELA) — recompression variance and spatial anomaly detection.
  2. Dedicated Photo Replacement Analysis — face perimeter boundary seam, texture noise variance & ELA delta.
  3. Copy-Move Duplication Detection (ORB) — intra-document cloned region matching.
  4. Stamp Region Forgery Analysis — ink color segmentation, edge morphology & shape consistency.
  5. Hybrid CNN Patch Forgery Classification — MobileNetV2 patch inference and residual anomaly scoring.
  6. EXIF / Metadata Forensics — editing software signatures and timestamp anomalies.

Returns a calibrated composite tampering score (0-100), boolean tampered decision,
and granular forensic localization evidence.
"""

import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ExifTags

from app.config import (
    ELA_JPEG_QUALITY,
    ELA_SUSPICIOUS_MEAN_THRESHOLD,
    ELA_SUSPICIOUS_MAX_THRESHOLD,
    COPY_MOVE_MIN_MATCHES,
    COPY_MOVE_MIN_DISTANCE_PX,
    ORB_MATCH_DISTANCE_THRESHOLD,
    STAMP_MIN_RADIUS_PX,
    STAMP_MAX_RADIUS_PX,
    PHOTO_SEAM_EDGE_THRESHOLD,
    PHOTO_NOISE_RATIO_THRESHOLD,
    PHOTO_ELA_DELTA_THRESHOLD,
    EDITING_SOFTWARE_KEYWORDS,
    WEIGHT_ELA,
    WEIGHT_PHOTO_REGION,
    WEIGHT_COPY_MOVE,
    WEIGHT_CNN,
    WEIGHT_STAMP,
    WEIGHT_EXIF,
)
from app.services.cnn_forgery_service import score_image_forgery_cnn
from app.tampering.forensics import create_ela_heatmap

logger = logging.getLogger(__name__)


def analyze_tampering(image_path: str) -> Dict[str, Any]:
    """
    Main entry point for Module 3 forensic fusion.

    Returns:
    {
        "tampering_score": float (0-100),
        "tampered": bool,
        "signals": {
            "ela": float,
            "cnn": float,
            "copy_move": float,
            "photo_region": float,
            "stamp": float,
            "metadata": float
        },
        "detectors": dict,
        "checks": list[dict],
        "heatmap": dict,
        "error": str | None
    }
    """
    try:
        checks: List[Dict[str, Any]] = []

        # 1. Error Level Analysis
        ela_check = _error_level_analysis(image_path)
        checks.append(ela_check)

        # 2. Dedicated Photo Replacement Analysis
        photo_check = _photo_region_analysis(image_path)
        checks.append(photo_check)

        # 3. Copy-Move Duplication Detection
        copy_move_check = _copy_move_detection(image_path)
        checks.append(copy_move_check)

        # 4. Stamp Region Analysis
        stamp_check = _stamp_region_analysis(image_path)
        checks.append(stamp_check)

        # 5. Hybrid CNN Patch Forgery Classification
        cnn_result = score_image_forgery_cnn(image_path)
        cnn_score = float(cnn_result.get("cnn_score", 0.0))
        cnn_check = {
            "name": "cnn_forgery_classification",
            "triggered": cnn_result.get("triggered", False),
            "score": cnn_score,
            "detail": cnn_result.get("detail", "CNN forgery analysis completed"),
        }
        checks.append(cnn_check)

        # 6. EXIF Metadata Forensics
        exif_check = _exif_analysis(image_path)
        checks.append(exif_check)

        # Dynamic weight renormalization handles missing CNN signals safely
        all_signals = {
            "ela": (ela_check, WEIGHT_ELA),
            "photo_region": (photo_check, WEIGHT_PHOTO_REGION),
            "copy_move": (copy_move_check, WEIGHT_COPY_MOVE),
            "cnn": (cnn_check, WEIGHT_CNN),
            "stamp": (stamp_check, WEIGHT_STAMP),
            "exif": (exif_check, WEIGHT_EXIF),
        }

        signals_available = []
        signals_unavailable = []
        cnn_mode = cnn_result.get("mode", "unavailable")

        for name, (chk, weight) in all_signals.items():
            if name == "cnn" and cnn_mode == "unavailable":
                signals_unavailable.append(name)
            else:
                signals_available.append(name)

        sum_weights = sum(all_signals[name][1] for name in signals_available)
        effective_weights = {}
        weighted_sum = 0.0

        for name in signals_available:
            chk, w = all_signals[name]
            eff_w = w / sum_weights
            effective_weights[name] = round(eff_w, 4)
            weighted_sum += chk["score"] * eff_w

        final_score = round(min(100.0, max(0.0, weighted_sum)), 2)
        # Only check CNN override if CNN is genuinely available
        is_tampered = bool(
            final_score >= 45.0
            or photo_check["triggered"]
            or copy_move_check["triggered"]
            or (cnn_mode == "trained_model" and cnn_score >= 70.0)
        )

        signals = {
            "ela": ela_check["score"],
            "photo_region": photo_check["score"],
            "copy_move": copy_move_check["score"],
            "stamp": stamp_check["score"],
            "cnn": cnn_check["score"] if cnn_mode == "trained_model" else None,
            "metadata": exif_check["score"],
        }
        detectors = {
            "ela": ela_check["score"],
            "photo_replacement": photo_check["score"],
            "copy_move": copy_move_check["score"],
            "stamp": stamp_check["score"],
            "cnn": cnn_check["score"] if cnn_mode == "trained_model" else None,
            "metadata": exif_check["score"],
        }

        # Generate localization heatmap and bounding boxes
        heatmaps_dir = str(Path(__file__).resolve().parents[2] / "dataset" / "heatmaps")
        heatmap_artifacts = create_ela_heatmap(image_path, heatmaps_dir)

        return {
            "tampering_score": final_score,
            "tampered": is_tampered,
            "signals": signals,
            "detectors": detectors,
            "checks": checks,
            "heatmap": heatmap_artifacts,
            "signals_available": signals_available,
            "signals_unavailable": signals_unavailable,
            "effective_weights": effective_weights,
            "error": None,
        }
    except Exception as exc:
        logger.error("Tampering analysis failed: %s", exc)
        return {
            "tampering_score": 0.0,
            "tampered": False,
            "signals": {"ela": 0.0, "photo_region": 0.0, "copy_move": 0.0, "stamp": 0.0, "cnn": None, "metadata": 0.0},
            "detectors": {},
            "checks": [],
            "heatmap": None,
            "signals_available": [],
            "signals_unavailable": ["ela", "photo_region", "copy_move", "stamp", "cnn", "exif"],
            "effective_weights": {},
            "error": f"Tampering analysis failed on this image: {exc}",
        }



# --- 1. Error Level Analysis ---------------------------------------------

def _error_level_analysis(image_path: str) -> Dict[str, Any]:
    name = "error_level_analysis"
    try:
        original = Image.open(image_path).convert("RGB")

        buffer = io.BytesIO()
        original.save(buffer, "JPEG", quality=ELA_JPEG_QUALITY)
        buffer.seek(0)
        resaved = Image.open(buffer)

        original_arr = np.asarray(original).astype(np.int16)
        resaved_arr = np.asarray(resaved).astype(np.int16)

        diff = np.abs(original_arr - resaved_arr)
        mean_diff = float(diff.mean())
        max_diff = float(diff.max())

        mean_component = min(100.0, (mean_diff / ELA_SUSPICIOUS_MEAN_THRESHOLD) * 60)
        max_component = min(100.0, (max_diff / ELA_SUSPICIOUS_MAX_THRESHOLD) * 40)
        score = round(min(100.0, mean_component + max_component), 2)

        triggered = mean_diff > ELA_SUSPICIOUS_MEAN_THRESHOLD or max_diff > ELA_SUSPICIOUS_MAX_THRESHOLD

        return {
            "name": name,
            "triggered": triggered,
            "score": score,
            "detail": (
                f"ELA mean diff={mean_diff:.2f}, max diff={max_diff:.2f} "
                f"(thresholds: mean>{ELA_SUSPICIOUS_MEAN_THRESHOLD}, max>{ELA_SUSPICIOUS_MAX_THRESHOLD})"
            ),
        }
    except Exception as exc:
        logger.warning("ELA check failed: %s", exc)
        return {"name": name, "triggered": False, "score": 0.0, "detail": f"ELA check skipped: {exc}"}


# --- 2. Photo Region / Replacement Analysis -------------------------------

def _photo_region_analysis(image_path: str) -> Dict[str, Any]:
    """
    Targets Photo Replacement / Splicing:
      - Face & portrait boundary detection.
      - Seam/boundary Canny edge density at photo border.
      - Noise variance ratio between photo crop and surrounding document.
      - Recompression ELA differential inside vs outside portrait region.
    """
    name = "photo_region_analysis"
    try:
        bgr = cv2.imread(image_path)
        if bgr is None:
            return {"name": name, "triggered": False, "score": 0.0, "detail": "Could not load image for photo analysis"}

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))

        if len(faces) == 0:
            return {
                "name": name,
                "triggered": False,
                "score": 0.0,
                "detail": "No isolated face photo region detected for targeted boundary analysis",
                "bounding_box": None,
                "suspicious": False,
                "evidence": {"face_detected": False},
            }

        fx, fy, fw, fh = faces[0]
        pad = int(min(fw, fh) * 0.15)
        bx1, by1 = max(0, fx - pad), max(0, fy - pad)
        bx2, by2 = min(w, fx + fw + pad), min(h, fy + fh + pad)

        photo_roi = gray[by1:by2, bx1:bx2]

        # 1. Seam / Boundary Edge Detection
        edges = cv2.Canny(photo_roi, 80, 180)
        border_mask = np.zeros_like(edges)
        border_thickness = max(2, int(pad * 0.8))
        border_mask[:border_thickness, :] = 1
        border_mask[-border_thickness:, :] = 1
        border_mask[:, :border_thickness] = 1
        border_mask[:, -border_thickness:] = 1

        border_edges = cv2.bitwise_and(edges, edges, mask=border_mask)
        border_density = float(np.count_nonzero(border_edges)) / float(np.count_nonzero(border_mask) + 1e-5)
        seam_flagged = border_density > PHOTO_SEAM_EDGE_THRESHOLD

        # 2. Texture & Noise Variance Consistency
        photo_noise_var = float(cv2.Laplacian(photo_roi, cv2.CV_64F).var())
        bg_sample = gray[0 : min(h, 100), 0 : min(w, 100)]
        bg_noise_var = float(cv2.Laplacian(bg_sample, cv2.CV_64F).var()) + 1e-5
        noise_ratio = photo_noise_var / bg_noise_var
        noise_flagged = noise_ratio > PHOTO_NOISE_RATIO_THRESHOLD or noise_ratio < (1.0 / PHOTO_NOISE_RATIO_THRESHOLD)

        # 3. ELA Delta
        pil_img = Image.open(image_path).convert("RGB")
        buf = io.BytesIO()
        pil_img.save(buf, "JPEG", quality=ELA_JPEG_QUALITY)
        buf.seek(0)
        ela_diff = np.abs(np.array(pil_img).astype(np.float32) - np.array(Image.open(buf)).astype(np.float32))
        photo_ela_mean = float(np.mean(ela_diff[by1:by2, bx1:bx2]))
        doc_ela_mean = float(np.mean(ela_diff))
        ela_delta = abs(photo_ela_mean - doc_ela_mean)
        ela_flagged = ela_delta > PHOTO_ELA_DELTA_THRESHOLD

        score = 0.0
        flags = []
        if seam_flagged:
            score += 45.0
            flags.append(f"Sharp rectangular seam detected around photo perimeter (density={border_density:.2f})")
        if noise_flagged:
            score += 30.0
            flags.append(f"Noise/resolution discrepancy between photo and doc background (ratio={noise_ratio:.2f})")
        if ela_flagged:
            score += 25.0
            flags.append(f"Photo region ELA compression mismatch (delta={ela_delta:.1f})")

        score = min(100.0, score)
        triggered = score >= 45.0

        return {
            "name": name,
            "triggered": triggered,
            "score": round(score, 2),
            "suspicious": triggered,
            "detail": "; ".join(flags) if flags else f"Photo region verified intact (seam_density={border_density:.2f}, noise_ratio={noise_ratio:.2f})",
            "region": {"x": int(bx1), "y": int(by1), "width": int(bx2 - bx1), "height": int(by2 - by1)},
            "bounding_box": {"x": int(bx1), "y": int(by1), "width": int(bx2 - bx1), "height": int(by2 - by1)},
            "evidence": {
                "face_detected": True,
                "seam_density": round(border_density, 4),
                "noise_ratio": round(noise_ratio, 4),
                "ela_delta": round(ela_delta, 4),
                "flags": flags,
            },
        }
    except Exception as exc:
        logger.warning("Photo region analysis failed: %s", exc)
        return {"name": name, "triggered": False, "score": 0.0, "detail": f"Photo analysis skipped: {exc}"}


# --- 3. Copy-move forgery detection (ORB) ---------------------------------

def _copy_move_detection(image_path: str) -> Dict[str, Any]:
    name = "copy_move_detection"
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {"name": name, "triggered": False, "score": 0.0, "detail": "Could not read image for copy-move check"}

        orb = cv2.ORB_create(nfeatures=1500)
        keypoints, descriptors = orb.detectAndCompute(img, None)

        if descriptors is None or len(keypoints) < 20:
            return {
                "name": name,
                "triggered": False,
                "score": 0.0,
                "detail": "Too few keypoints detected — image likely too small/blurry for copy-move analysis",
            }

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(descriptors, descriptors, k=2)

        genuine_pairs: List[Tuple[int, int]] = []
        for match_pair in matches:
            if len(match_pair) < 2:
                continue
            best, second = match_pair
            if best.queryIdx == best.trainIdx:
                best = second
            if best.queryIdx == best.trainIdx:
                continue

            pt1 = keypoints[best.queryIdx].pt
            pt2 = keypoints[best.trainIdx].pt
            spatial_dist = float(np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1]))

            if best.distance < ORB_MATCH_DISTANCE_THRESHOLD and spatial_dist > COPY_MOVE_MIN_DISTANCE_PX:
                pair_key = tuple(sorted((best.queryIdx, best.trainIdx)))
                genuine_pairs.append(pair_key)

        unique_pairs = set(genuine_pairs)
        match_count = len(unique_pairs)

        score = min(100.0, (match_count / COPY_MOVE_MIN_MATCHES) * 100)
        triggered = match_count >= COPY_MOVE_MIN_MATCHES

        return {
            "name": name,
            "triggered": triggered,
            "score": round(score, 2),
            "detail": (
                f"{match_count} candidate duplicated-region keypoint pairs found "
                f"(flag threshold: {COPY_MOVE_MIN_MATCHES})"
            ),
        }
    except Exception as exc:
        logger.warning("Copy-move check failed: %s", exc)
        return {"name": name, "triggered": False, "score": 0.0, "detail": f"Copy-move check skipped: {exc}"}


# --- 4. Stamp Region Analysis --------------------------------------------

def _stamp_region_analysis(image_path: str) -> Dict[str, Any]:
    """
    Stamp analysis with color segmentation (blue/red ink), edge morphology,
    and aspect-ratio bounding inspection.
    """
    name = "stamp_forgery_analysis"
    try:
        bgr = cv2.imread(image_path)
        if bgr is None:
            return {"name": name, "triggered": False, "score": 0.0, "detail": "Could not read image for stamp inspection"}

        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        blue_mask = cv2.inRange(hsv, np.array([90, 50, 50]), np.array([140, 255, 255]))
        red_mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
        red_mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        violet_mask = cv2.inRange(hsv, np.array([130, 40, 40]), np.array([165, 255, 255]))
        ink_mask = blue_mask | red_mask1 | red_mask2 | violet_mask

        contours, _ = cv2.findContours(ink_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidate_stamps = 0
        suspicious_stamps = 0
        stamp_regions = []

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        for c in contours:
            area = cv2.contourArea(c)
            if area < (np.pi * (STAMP_MIN_RADIUS_PX ** 2)) or area > (np.pi * (STAMP_MAX_RADIUS_PX ** 2)):
                continue

            x, y, w, h = cv2.boundingRect(c)
            aspect_ratio = float(w) / h if h > 0 else 0
            if 0.6 <= aspect_ratio <= 1.4:
                candidate_stamps += 1
                roi = gray[y : y + h, x : x + w]
                edges = cv2.Canny(roi, 100, 200)
                edge_density = float(np.count_nonzero(edges)) / (w * h)
                is_suspicious = edge_density > 0.35
                if is_suspicious:
                    suspicious_stamps += 1
                stamp_regions.append({"x": x, "y": y, "width": w, "height": h, "edge_density": round(edge_density, 3), "suspicious": is_suspicious})

        if candidate_stamps == 0:
            return {
                "name": name,
                "triggered": False,
                "score": 0.0,
                "stamp_detected": False,
                "suspicious_score": 0.0,
                "confidence": 0.85,
                "detail": "No distinct official stamp regions detected on document",
                "evidence": {"candidate_stamps": 0, "regions": []},
            }

        score = 80.0 if suspicious_stamps > 0 else 10.0
        triggered = suspicious_stamps > 0

        return {
            "name": name,
            "triggered": triggered,
            "score": score,
            "stamp_detected": True,
            "suspicious_score": score,
            "confidence": 0.90,
            "detail": (
                f"{candidate_stamps} candidate stamp region(s) analyzed; "
                f"{suspicious_stamps} showed anomalous boundary edge densities"
            ),
            "evidence": {"candidate_stamps": candidate_stamps, "suspicious_stamps": suspicious_stamps, "regions": stamp_regions},
        }
    except Exception as exc:
        logger.warning("Stamp region analysis failed: %s", exc)
        return {"name": name, "triggered": False, "score": 0.0, "detail": f"Stamp check skipped: {exc}"}


# --- 5. EXIF metadata analysis --------------------------------------------

def _exif_analysis(image_path: str) -> Dict[str, Any]:
    name = "exif_metadata"
    try:
        image = Image.open(image_path)
        raw_exif = image._getexif() if hasattr(image, "_getexif") else None

        if not raw_exif:
            return {
                "name": name,
                "triggered": False,
                "score": 0.0,
                "detail": "No EXIF metadata present (common for scans/screenshots — not inherently suspicious)",
                "metadata_present": False,
            }

        tags = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}
        software = str(tags.get("Software", "")).lower()
        editing_flagged = any(kw in software for kw in EDITING_SOFTWARE_KEYWORDS)

        has_datetime = bool(tags.get("DateTime") or tags.get("DateTimeOriginal"))
        datetime_mismatch = (
            "DateTime" in tags and "DateTimeOriginal" in tags
            and tags["DateTime"] != tags["DateTimeOriginal"]
        )

        flags = []
        score = 0.0
        if editing_flagged:
            flags.append(f"Software tag indicates an image editor: '{tags.get('Software')}'")
            score += 70.0
        if not has_datetime:
            flags.append("No timestamp fields present in EXIF")
            score += 15.0
        if datetime_mismatch:
            flags.append("DateTime and DateTimeOriginal disagree")
            score += 25.0

        score = min(score, 100.0)
        triggered = bool(flags)

        return {
            "name": name,
            "triggered": triggered,
            "score": round(score, 2),
            "detail": "; ".join(flags) if flags else "EXIF present, no editing signatures or timestamp issues found",
            "metadata_present": True,
        }
    except Exception as exc:
        logger.warning("EXIF check failed: %s", exc)
        return {"name": name, "triggered": False, "score": 0.0, "detail": f"EXIF check skipped: {exc}"}
