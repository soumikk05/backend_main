"""Forensic heatmap and spatial anomaly localization generator."""
from __future__ import annotations
import io
from pathlib import Path
from uuid import uuid4
from typing import Any, Dict, List
import cv2
import numpy as np
from PIL import Image


def create_ela_heatmap(image_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Generate Error Level Analysis (ELA) and residual heatmap artifacts with spatial bounding boxes.
    """
    try:
        original = Image.open(image_path).convert("RGB")
        buffer = io.BytesIO()
        original.save(buffer, "JPEG", quality=90)
        buffer.seek(0)
        resaved = Image.open(buffer).convert("RGB")

        diff = np.abs(np.asarray(original, dtype=np.int16) - np.asarray(resaved, dtype=np.int16)).mean(axis=2).astype(np.uint8)
        norm_diff = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        heatmap = cv2.applyColorMap(norm_diff, cv2.COLORMAP_JET)

        # Threshold top anomalies
        thresh_val = max(15, int(np.percentile(diff, 95)))
        _, mask = cv2.threshold(diff, thresh_val, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes: List[List[int]] = []
        regions: List[Dict[str, Any]] = []
        polygons: List[List[List[int]]] = []

        h, w = diff.shape
        total_area = float(h * w)

        for c in contours:
            area = cv2.contourArea(c)
            if area > 120 and (area / total_area) < 0.80:
                bx, by, bw, bh = cv2.boundingRect(c)
                roi_diff = diff[by : by + bh, bx : bx + bw]
                region_score = round(float(np.mean(roi_diff) / 25.0), 4) if roi_diff.size > 0 else 0.5
                region_score = min(1.0, max(0.1, region_score))

                boxes.append([int(bx), int(by), int(bw), int(bh)])
                regions.append({
                    "x": int(bx),
                    "y": int(by),
                    "width": int(bw),
                    "height": int(bh),
                    "score": region_score,
                })

                poly = [[int(pt[0][0]), int(pt[0][1])] for pt in cv2.approxPolyDP(c, 0.03 * cv2.arcLength(c, True), True)]
                if len(poly) >= 3:
                    polygons.append(poly)

        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        heatmap_filename = f"ela_{uuid4().hex}.png"
        heatmap_path = directory / heatmap_filename
        cv2.imwrite(str(heatmap_path), heatmap)

        return {
            "heatmap_available": True,
            "ela_heatmap_path": str(heatmap_path),
            "cnn_heatmap_path": None,
            "regions": regions,
            "bounding_boxes": boxes,
            "suspicious_polygons": polygons,
        }
    except Exception:
        return {
            "heatmap_available": False,
            "ela_heatmap_path": None,
            "cnn_heatmap_path": None,
            "regions": [],
            "bounding_boxes": [],
            "suspicious_polygons": [],
        }
