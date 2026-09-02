"""
Build Region-Aware Forgery Dataset Manifest & Crops.

STRICT SPLIT RULES:
- TRAIN crops are extracted ONLY from train documents in ml_train.csv.
- VALIDATION crops are extracted ONLY from validation documents in ml_val.csv.
- TEST documents (ml_test.csv) MUST NOT be generated, accessed, or touched!

Outputs:
- dataset/forgery_regions/train/<field_name>/
- dataset/forgery_regions/val/<field_name>/
- reports/forgery_region_inventory.csv
"""

import csv
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.region_utils import (
    MIDV_SEMANTIC_FIELD_MAP,
    extract_aspect_preserved_crop,
    load_document_ground_truth,
    quad_to_bbox,
)

REPORTS_DIR = BACKEND_ROOT / "reports"
OUTPUT_DIR = BACKEND_ROOT / "dataset" / "forgery_regions"
INVENTORY_CSV = REPORTS_DIR / "forgery_region_inventory.csv"

TRAIN_CSV = REPORTS_DIR / "ml_train.csv"
VAL_CSV = REPORTS_DIR / "ml_val.csv"
TEST_CSV = REPORTS_DIR / "ml_test.csv"


def get_field_quads(doc_key: str) -> dict:
    """Returns mapping of semantic field names -> quad for given document key."""
    gt_data = load_document_ground_truth(doc_key)
    if not gt_data:
        return {}
    mapping = MIDV_SEMANTIC_FIELD_MAP.get(doc_key, {})
    result = {}
    for sem_name, fkey in mapping.items():
        if fkey in gt_data and "quad" in gt_data[fkey]:
            result[sem_name] = gt_data[fkey]["quad"]
    return result


def main():
    print("=== STARTING BUILD FORGERY REGION DATASET (TRAIN & VAL ONLY) ===")

    # Load splits
    with open(TRAIN_CSV, "r", encoding="utf-8") as f:
        train_rows = list(csv.DictReader(f))
    with open(VAL_CSV, "r", encoding="utf-8") as f:
        val_rows = list(csv.DictReader(f))

    # Note: test_rows is loaded ONLY to ensure set exclusion, never to open images!
    with open(TEST_CSV, "r", encoding="utf-8") as f:
        test_rows = list(csv.DictReader(f))

    test_doc_ids = {r["document_id"] for r in test_rows}
    test_paths = {r["image_path"] for r in test_rows}

    # Filter to MIDV documents which have field-level coordinate ground-truth
    # In Train: 5 MIDV documents ('01_alb_id', '02_aut_drvlic_new', '03_aut_id_old', '05_aze_passport', '08_chn_homereturn')
    # In Val: 1 MIDV document ('04_aut_id')
    train_midv = [r for r in train_rows if r["dataset"] == "MIDV-500" and not r["image_path"].startswith("dataset/genuine/")]
    val_midv = [r for r in val_rows if r["dataset"] == "MIDV-500"]

    print(f"Train MIDV candidate images: {len(train_midv)}")
    print(f"Validation MIDV candidate images: {len(val_midv)}")

    # Pre-load ground-truth quads per doc
    doc_quads = {}
    for r in train_midv + val_midv:
        dkey = r["document_id"].replace("MIDV_", "")
        if dkey not in doc_quads:
            doc_quads[dkey] = get_field_quads(dkey)

    inventory_records = []
    crop_counter = 0

    # Process partitions
    partitions = [
        ("train", train_midv),
        ("validation", val_midv),
    ]

    # Subsample frames to construct a diverse, balanced crop repository
    # (Select flat scans + representative frame samples per document)
    for split_name, rows in partitions:
        print(f"\nProcessing {split_name} partition...")
        # Group by document_id
        by_doc = {}
        for r in rows:
            by_doc.setdefault(r["document_id"], []).append(r)

        for did, items in by_doc.items():
            # Security verification: ensure DID not in test set
            if did in test_doc_ids:
                raise RuntimeError(f"SECURITY VIOLATION: Test document {did} found in {split_name} processing!")

            dkey = did.replace("MIDV_", "")
            quads = doc_quads.get(dkey, {})
            if not quads:
                continue

            # Pick flat scan image if present, plus 15 representative video frames per document
            flat_items = [i for i in items if i["image_path"].endswith(f"{dkey}.tif")]
            frame_items = [i for i in items if not i["image_path"].endswith(f"{dkey}.tif")][:15]
            selected = flat_items + frame_items

            for sel in selected:
                img_path = BACKEND_ROOT / sel["image_path"]
                if sel["image_path"] in test_paths:
                    raise RuntimeError(f"SECURITY VIOLATION: Test image path accessed: {sel['image_path']}")

                im_cv = cv2.imread(str(img_path))
                if im_cv is None:
                    continue

                h_orig, w_orig = im_cv.shape[:2]

                for sem_name, quad in quads.items():
                    bbox = quad_to_bbox(quad, w_orig, h_orig, margin_ratio=0.08)
                    x, y, w, h = bbox

                    crop_128 = extract_aspect_preserved_crop(im_cv, bbox, target_size=(128, 128))

                    crop_dir = OUTPUT_DIR / split_name / sem_name
                    crop_dir.mkdir(parents=True, exist_ok=True)

                    crop_filename = f"{dkey}_{Path(sel['image_path']).stem}_{sem_name}.jpg"
                    rel_crop_path = f"dataset/forgery_regions/{split_name}/{sem_name}/{crop_filename}"
                    abs_crop_path = BACKEND_ROOT / rel_crop_path

                    cv2.imwrite(str(abs_crop_path), crop_128, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    crop_counter += 1

                    inventory_records.append({
                        "source_image": sel["image_path"],
                        "document_id": sel["document_id"],
                        "document_type": sel["document_type"],
                        "field_name": sem_name,
                        "crop_path": rel_crop_path,
                        "original_bbox": f"({x},{y},{w},{h})",
                        "crop_width": 128,
                        "crop_height": 128,
                        "split": split_name,
                    })

    # Save inventory CSV
    with open(INVENTORY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_image", "document_id", "document_type", "field_name",
            "crop_path", "original_bbox", "crop_width", "crop_height", "split"
        ])
        writer.writeheader()
        writer.writerows(inventory_records)

    print(f"\nRegion inventory successfully saved to: {INVENTORY_CSV}")
    print(f"Total region crops generated: {len(inventory_records)}")
    print(f"  Train crops     : {sum(1 for r in inventory_records if r['split'] == 'train')}")
    print(f"  Validation crops: {sum(1 for r in inventory_records if r['split'] == 'validation')}")


if __name__ == "__main__":
    main()
