"""
Reusable utilities for Region-Aware Document Forgery Analysis.

Includes:
- Loading MIDV-500 ground-truth field coordinates.
- Converting quadrilateral vertices into cropped bounding boxes with configurable margins.
- Aspect-ratio preserving crop extraction and padding to target resolution (128x128).
- Semantic field mapping across heterogeneous document types.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
MIDV_ROOT = BACKEND_ROOT / "midv500_data" / "midv500"

# Standard semantic mapping for MIDV-500 documents
# Maps standardized semantic field names to the specific field ID in ground truth JSON
MIDV_SEMANTIC_FIELD_MAP = {
    "01_alb_id": {
        "surname": "field01",
        "given_name": "field02",
        "nationality": "field03",
        "place_of_birth": "field04",
        "dob": "field05",
        "issue_date": "field06",
        "document_number": "field08",
        "expiry_date": "field10",
        "personal_number": "field11",
        "photo": "photo",
        "signature": "signature",
    },
    "02_aut_drvlic_new": {
        "surname": "field01",
        "given_name": "field02",
        "dob": "field03",
        "place_of_birth": "field04",
        "issue_date": "field05",
        "expiry_date": "field06",
        "issuing_authority": "field07",
        "document_number": "field08",
        "photo": "photo",
        "signature": "signature",
    },
    "03_aut_id_old": {
        "surname": "field01",
        "given_name": "field03",
        "dob": "field04",
        "place_of_birth": "field05",
        "issue_date": "field06",
        "document_number": "field08",
        "photo": "photo",
        "signature": "signature",
    },
    "04_aut_id": {
        "document_number": "field01",
        "surname": "field03",
        "given_name": "field04",
        "dob": "field05",
        "issue_date": "field07",
        "photo": "photo",
        "signature": "signature",
    },
    "05_aze_passport": {
        "document_number": "field03",
        "surname": "field05",
        "given_name": "field07",
        "dob": "field09",
        "personal_number": "field10",
        "issue_date": "field13",
        "expiry_date": "field14",
        "mrz_line1": "field17",
        "mrz_line2": "field18",
        "photo": "photo",
        "signature": "signature",
    },
    "06_bra_passport": {
        "document_number": "field03",
        "surname": "field04",
        "given_name": "field05",
        "dob": "field07",
        "issue_date": "field10",
        "expiry_date": "field12",
        "photo": "photo",
    },
    "07_chl_id": {
        "surname": "field01",
        "given_name": "field03",
        "dob": "field06",
        "document_number": "field07",
        "issue_date": "field08",
        "expiry_date": "field09",
        "personal_number": "field10",
        "photo": "photo",
        "signature": "signature",
    },
    "08_chn_homereturn": {
        "name": "field02",
        "dob": "field03",
        "validity_period": "field05",
        "document_number": "field07",
        "photo": "photo",
    },
}


def load_document_ground_truth(doc_key: str) -> Dict[str, dict]:
    """Loads ground-truth annotations for a specific MIDV document folder."""
    gt_file = MIDV_ROOT / doc_key / "ground_truth" / f"{doc_key}.json"
    if not gt_file.exists():
        return {}
    with open(gt_file, "r", encoding="utf-8", errors="replace") as f:
        return json.load(f)


def quad_to_bbox(
    quad: List[List[int]],
    img_width: int,
    img_height: int,
    margin_ratio: float = 0.08,
) -> Tuple[int, int, int, int]:
    """
    Converts quadrilateral 4-point coordinates into an axis-aligned bounding box (x, y, w, h)
    with a small configurable margin to preserve edge transition textures.
    """
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    raw_w = max(1, max_x - min_x)
    raw_h = max(1, max_y - min_y)

    margin_x = int(raw_w * margin_ratio)
    margin_y = int(raw_h * margin_ratio)

    x1 = max(0, min_x - margin_x)
    y1 = max(0, min_y - margin_y)
    x2 = min(img_width, max_x + margin_x)
    y2 = min(img_height, max_y + margin_y)

    return (x1, y1, max(1, x2 - x1), max(1, y2 - y1))


def extract_aspect_preserved_crop(
    img: Union[np.ndarray, Image.Image],
    bbox: Tuple[int, int, int, int],
    target_size: Tuple[int, int] = (128, 128),
    pad_mode: str = "edge",
) -> np.ndarray:
    """
    Extracts high-resolution region crop from image and resizes to target_size (128x128).
    Preserves forensic aspect ratio by padding outer boundaries rather than non-uniform squishing.
    """
    if isinstance(img, Image.Image):
        img_np = np.array(img)
    else:
        img_np = img

    h_img, w_img = img_np.shape[:2]
    x, y, w, h = bbox

    # Crop
    crop = img_np[y : y + h, x : x + w]
    if crop.size == 0:
        return np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)

    target_w, target_h = target_size
    scale = min(target_w / w, target_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))

    # Resize preserving texture
    resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Pad symmetrically to reach (target_h, target_w)
    pad_top = (target_h - new_h) // 2
    pad_bottom = target_h - new_h - pad_top
    pad_left = (target_w - new_w) // 2
    pad_right = target_w - new_w - pad_left

    if pad_mode == "edge":
        padded = cv2.copyMakeBorder(
            resized, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_REPLICATE
        )
    else:
        padded = cv2.copyMakeBorder(
            resized, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )

    return padded
