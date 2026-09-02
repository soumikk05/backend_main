"""
Generate strictly isolated validation dataset from ml_val.csv source documents ONLY.

Guarantees:
- Never touches ml_train.csv or ml_test.csv.
- Original validation images remain untouched.
- Output goes to dataset/forgery_ml_val/
  - genuine/
  - tampered/<attack_type>/
  - metadata.csv
"""

import csv
import json
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SEED = 1337  # Independent seed from training (which used 42)
random.seed(SEED)
np.random.seed(SEED)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_ROOT / "reports"
VAL_CSV = REPORTS_DIR / "ml_val.csv"
OUTPUT_DIR = BACKEND_ROOT / "dataset" / "forgery_ml_val"
MIDV_DIR = BACKEND_ROOT / "midv500_data" / "midv500"

ATTACK_TYPES = [
    "text_edit",
    "dob_edit",
    "document_number_edit",
    "name_edit",
    "photo_replace",
    "text_erase",
    "text_insert",
    "splice",
    "copy_move",
    "stamp_edit",
    "recompression",
]

for atype in ATTACK_TYPES:
    (OUTPUT_DIR / "tampered" / atype).mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "genuine").mkdir(parents=True, exist_ok=True)


def load_val_manifest() -> List[Dict[str, str]]:
    with open(VAL_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_val_midv_annotations() -> Dict[str, dict]:
    # In validation, MIDV document is strictly MIDV_04_aut_id
    annotations = {}
    d = "04_aut_id"
    gt_path = MIDV_DIR / d / "ground_truth" / f"{d}.json"
    if gt_path.exists():
        with open(gt_path, "r", encoding="utf-8", errors="replace") as f:
            annotations[f"MIDV_{d}"] = json.load(f)
    return annotations


def erase_region(img_cv: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    h_img, w_img = img_cv.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w_img, x + w), min(h_img, y + h)
    if x2 <= x1 or y2 <= y1: return img_cv
    mask = np.zeros((h_img, w_img), dtype=np.uint8)
    mask[y1:y2, x1:x2] = 255
    inpainted = cv2.inpaint(img_cv, mask, inpaintRadius=3, flags=cv2.INPAINT_NS)
    noise = np.random.normal(0, 3.5, inpainted[y1:y2, x1:x2].shape).astype(np.float32)
    inpainted[y1:y2, x1:x2] = np.clip(inpainted[y1:y2, x1:x2].astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return inpainted


def apply_text_erase(img_cv: np.ndarray, box=None):
    h, w = img_cv.shape[:2]
    if box: x, y, bw, bh = box
    else:
        bw, bh = random.randint(int(w*0.15), int(w*0.35)), random.randint(int(h*0.03), int(h*0.06))
        x, y = random.randint(int(w*0.2), int(w*0.6)), random.randint(int(h*0.2), int(h*0.7))
    return erase_region(img_cv, x, y, bw, bh), f"x={x},y={y},w={bw},h={bh}"


def apply_text_insert(img_cv: np.ndarray, text: str = "SAMPLE", box=None):
    h, w = img_cv.shape[:2]
    if box: x, y, bw, bh = box
    else:
        bw, bh = random.randint(int(w*0.15), int(w*0.35)), random.randint(int(h*0.03), int(h*0.06))
        x, y = random.randint(int(w*0.2), int(w*0.6)), random.randint(int(h*0.2), int(h*0.7))
    erased = erase_region(img_cv, x, y, bw, bh)
    sample_bg = erased[max(0, y - 5):min(h, y + bh + 5), max(0, x - 5):min(w, x + bw + 5)]
    mean_bg = np.mean(sample_bg) if sample_bg.size > 0 else 200
    text_color = (20, 20, 20) if mean_bg > 120 else (235, 235, 235)
    img_pil = Image.fromarray(cv2.cvtColor(erased, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    try: font = ImageFont.truetype("arial.ttf", max(10, int(bh * 0.75)))
    except Exception: font = ImageFont.load_default()
    draw.text((x + 2, y + 2), text, fill=text_color, font=font)
    res = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    text_mask = np.zeros((h, w), dtype=np.uint8)
    text_mask[y:y+bh, x:x+bw] = 255
    blurred = cv2.GaussianBlur(res, (3, 3), 0.5)
    res = np.where(cv2.cvtColor(text_mask, cv2.COLOR_GRAY2BGR) > 0, cv2.addWeighted(res, 0.75, blurred, 0.25, 0), res)
    return res, f"text='{text}',box=({x},{y},{bw},{bh})"


def apply_dob_edit(img_cv: np.ndarray, box=None):
    fake_dob = f"{random.randint(1, 28):02d}.{random.randint(1, 12):02d}.{random.randint(1970, 2000)}"
    return apply_text_insert(img_cv, text=fake_dob, box=box)


def apply_doc_number_edit(img_cv: np.ndarray, box=None):
    fake_number = f"V{random.randint(1000000, 9999999)}"
    return apply_text_insert(img_cv, text=fake_number, box=box)


def apply_name_edit(img_cv: np.ndarray, box=None):
    fake_name = f"{random.choice(['BERMAN', 'SCHNEIDER', 'GARCIA', 'WANG'])}, {random.choice(['ANNA', 'FELIX', 'DAVID', 'CLARA'])}"
    return apply_text_insert(img_cv, text=fake_name, box=box)


def apply_photo_replace(img_cv: np.ndarray, donor_face_cv: np.ndarray, box=None):
    h, w = img_cv.shape[:2]
    if box: x, y, bw, bh = box
    else: bw, bh, x, y = int(w*0.22), int(h*0.40), int(w*0.06), int(h*0.22)
    x1, y1, x2, y2 = max(0, x), max(0, y), min(w, x + bw), min(h, y + bh)
    target_w, target_h = x2 - x1, y2 - y1
    if target_w <= 10 or target_h <= 10: return img_cv, "skip"
    resized_donor = cv2.resize(donor_face_cv, (target_w, target_h))
    gain = np.mean(img_cv[y1:y2, x1:x2], axis=(0, 1)) / np.maximum(np.mean(resized_donor, axis=(0, 1)), 1.0)
    resized_donor = np.clip(resized_donor.astype(np.float32) * gain, 0, 255).astype(np.uint8)
    mask = np.zeros((target_h, target_w), dtype=np.float32)
    border = max(3, min(target_w, target_h) // 12)
    mask[border:-border, border:-border] = 1.0
    mask = np.expand_dims(cv2.GaussianBlur(mask, (border*2+1, border*2+1), border/2), axis=2)
    blended = (resized_donor.astype(np.float32) * mask + img_cv[y1:y2, x1:x2].astype(np.float32) * (1.0 - mask)).astype(np.uint8)
    res = img_cv.copy()
    res[y1:y2, x1:x2] = blended
    return res, f"replaced_at=({x1},{y1},{target_w},{target_h})"


def apply_splice(img_cv: np.ndarray, donor_cv: np.ndarray):
    h, w = img_cv.shape[:2]
    dh, dw = donor_cv.shape[:2]
    pw, ph = random.randint(int(w*0.12), int(w*0.25)), random.randint(int(h*0.10), int(h*0.22))
    sx, sy = random.randint(0, max(0, dw - pw)), random.randint(0, max(0, dh - ph))
    patch = donor_cv[sy:sy+ph, sx:sx+pw]
    dx, dy = random.randint(int(w*0.1), max(int(w*0.1)+1, w-pw-int(w*0.1))), random.randint(int(h*0.1), max(int(h*0.1)+1, h-ph-int(h*0.1)))
    res = img_cv.copy()
    target_sub = res[dy:dy+ph, dx:dx+pw]
    if target_sub.shape[:2] != patch.shape[:2]: patch = cv2.resize(patch, (target_sub.shape[1], target_sub.shape[0]))
    mask = np.zeros(patch.shape[:2], dtype=np.float32)
    cv2.ellipse(mask, (patch.shape[1]//2, patch.shape[0]//2), (patch.shape[1]//2 - 3, patch.shape[0]//2 - 3), 0, 0, 360, 1.0, -1)
    mask = np.expand_dims(cv2.GaussianBlur(mask, (7, 7), 2.0), axis=2)
    blended = (patch.astype(np.float32) * mask + target_sub.astype(np.float32) * (1.0 - mask)).astype(np.uint8)
    res[dy:dy+ph, dx:dx+pw] = blended
    return res, f"spliced_at=({dx},{dy})"


def apply_copy_move(img_cv: np.ndarray):
    h, w = img_cv.shape[:2]
    pw, ph = random.randint(int(w*0.08), int(w*0.18)), random.randint(int(h*0.05), int(h*0.12))
    sx, sy = random.randint(0, max(0, w - pw)), random.randint(0, max(0, h - ph))
    patch = img_cv[sy:sy+ph, sx:sx+pw]
    dx, dy = random.randint(0, max(0, w - pw)), random.randint(0, max(0, h - ph))
    res = img_cv.copy()
    target_sub = res[dy:dy+ph, dx:dx+pw]
    if target_sub.shape[:2] != patch.shape[:2]: patch = cv2.resize(patch, (target_sub.shape[1], target_sub.shape[0]))
    mask = np.zeros(patch.shape[:2], dtype=np.float32)
    mask[2:-2, 2:-2] = 1.0
    mask = np.expand_dims(cv2.GaussianBlur(mask, (5, 5), 1.5), axis=2)
    blended = (patch.astype(np.float32) * mask + target_sub.astype(np.float32) * (1.0 - mask)).astype(np.uint8)
    res[dy:dy+ph, dx:dx+pw] = blended
    return res, f"copy_move_from=({sx},{sy})_to=({dx},{dy})"


def apply_stamp_edit(img_cv: np.ndarray):
    h, w = img_cv.shape[:2]
    radius = random.randint(int(min(w, h)*0.06), int(min(w, h)*0.12))
    cx, cy = random.randint(radius+10, w-radius-10), random.randint(radius+10, h-radius-10)
    res = img_cv.copy()
    overlay = np.zeros_like(res)
    stamp_color = random.choice([(130, 25, 25), (25, 25, 150), (25, 120, 25)])
    cv2.circle(overlay, (cx, cy), radius, stamp_color, 2)
    cv2.circle(overlay, (cx, cy), radius - 6, stamp_color, 1)
    cv2.line(overlay, (cx - radius + 8, cy), (cx + radius - 8, cy), stamp_color, 1)
    mask = (cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY) > 0).astype(np.float32)
    mask = np.expand_dims(cv2.GaussianBlur(mask, (3, 3), 0.5) * np.random.uniform(0.6, 1.0, mask.shape).astype(np.float32), axis=2)
    return (overlay.astype(np.float32) * mask + res.astype(np.float32) * (1.0 - mask)).astype(np.uint8), f"stamp_at=({cx},{cy})"


def apply_recompression(img_cv: np.ndarray):
    h, w = img_cv.shape[:2]
    bw, bh = random.randint(int(w*0.15), int(w*0.35)), random.randint(int(h*0.15), int(h*0.35))
    x, y = random.randint(0, max(0, w-bw)), random.randint(0, max(0, h-bh))
    patch = img_cv[y:y+bh, x:x+bw]
    quality = random.choice([25, 35, 45])
    _, enc = cv2.imencode(".jpg", patch, [cv2.IMWRITE_JPEG_QUALITY, quality])
    dec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    res = img_cv.copy()
    res[y:y+bh, x:x+bw] = dec
    return res, f"recompression_q={quality}_at=({x},{y})"


def main():
    print("=== PREPARING VALIDATION FORGERY DATASET (STRICTLY VAL SOURCES) ===")
    val_manifest = load_val_manifest()
    print(f"Total Validation source images: {len(val_manifest)}")

    val_doc_ids = {r["document_id"] for r in val_manifest}
    print(f"Validation document IDs: {len(val_doc_ids)}")

    # Donor face from VALIDATION MIDV doc ONLY (MIDV_04_aut_id)
    val_ann = load_val_midv_annotations()
    val_donor_faces = []
    val_flat = MIDV_DIR / "04_aut_id" / "images" / "04_aut_id.tif"
    if val_flat.exists() and "MIDV_04_aut_id" in val_ann and "photo" in val_ann["MIDV_04_aut_id"]:
        im = cv2.imread(str(val_flat))
        if im is not None:
            q = val_ann["MIDV_04_aut_id"]["photo"]["quad"]
            xs, ys = [p[0] for p in q], [p[1] for p in q]
            val_donor_faces.append(im[min(ys):max(ys), min(xs):max(xs)])

    print(f"Validation donor faces collected: {len(val_donor_faces)}")

    # We budget 250 genuine + 250 tampered for validation = 500 total evaluation images
    # Split across national_id (125) and visa (125)
    by_doctype = {
        "national_id": [r for r in val_manifest if r["document_type"] == "national_id"],
        "visa": [r for r in val_manifest if r["document_type"] == "visa"],
    }

    metadata = []
    sample_id = 0

    # 1. Genuine Validation Samples
    for dtype, items in by_doctype.items():
        n = min(len(items), 125)
        selected = random.sample(items, n)
        for r in selected:
            sample_id += 1
            src_path = BACKEND_ROOT / r["image_path"]
            img = cv2.imread(str(src_path))
            if img is None: continue
            out_filename = f"val_gen_{sample_id:05d}_{Path(src_path).stem}.jpg"
            out_rel = f"dataset/forgery_ml_val/genuine/{out_filename}"
            cv2.imwrite(str(BACKEND_ROOT / out_rel), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            metadata.append({
                "source_image": r["image_path"],
                "output_image": out_rel,
                "source_dataset": r["dataset"],
                "document_type": r["document_type"],
                "document_id": r["document_id"],
                "attack_type": "none",
                "field_name": "none",
                "severity": "none",
                "random_seed": str(SEED + sample_id),
                "split": "validation",
            })

    # 2. Tampered Validation Samples
    for dtype, items in by_doctype.items():
        n = min(len(items), 125)
        selected = random.sample(items, n)
        for r in selected:
            sample_id += 1
            src_path = BACKEND_ROOT / r["image_path"]
            img = cv2.imread(str(src_path))
            if img is None: continue
            attack = ATTACK_TYPES[sample_id % len(ATTACK_TYPES)]

            box = None
            field_name = "generic"
            doc_ann = val_ann.get(r["document_id"])
            if doc_ann:
                if attack == "dob_edit" and "field04" in doc_ann:
                    q = doc_ann["field04"]["quad"]
                    xs, ys = [p[0] for p in q], [p[1] for p in q]
                    box = (min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))
                    field_name = "field04"
                elif attack in ["document_number_edit", "text_edit"] and "field08" in doc_ann:
                    q = doc_ann["field08"]["quad"]
                    xs, ys = [p[0] for p in q], [p[1] for p in q]
                    box = (min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))
                    field_name = "field08"
                elif attack == "name_edit" and "field01" in doc_ann:
                    q = doc_ann["field01"]["quad"]
                    xs, ys = [p[0] for p in q], [p[1] for p in q]
                    box = (min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))
                    field_name = "field01"
                elif attack == "photo_replace" and "photo" in doc_ann:
                    q = doc_ann["photo"]["quad"]
                    xs, ys = [p[0] for p in q], [p[1] for p in q]
                    box = (min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))
                    field_name = "photo"

            if attack == "text_erase": tamp_img, _ = apply_text_erase(img, box)
            elif attack == "text_insert": tamp_img, _ = apply_text_insert(img, box=box)
            elif attack == "dob_edit": tamp_img, _ = apply_dob_edit(img, box=box)
            elif attack == "document_number_edit": tamp_img, _ = apply_doc_number_edit(img, box=box)
            elif attack == "name_edit": tamp_img, _ = apply_name_edit(img, box=box)
            elif attack == "photo_replace":
                donor = val_donor_faces[0] if val_donor_faces else img
                tamp_img, _ = apply_photo_replace(img, donor, box=box)
            elif attack == "splice":
                donor_row = random.choice(val_manifest)
                d_img = cv2.imread(str(BACKEND_ROOT / donor_row["image_path"]))
                tamp_img, _ = apply_splice(img, d_img if d_img is not None else img)
            elif attack == "copy_move": tamp_img, _ = apply_copy_move(img)
            elif attack == "stamp_edit": tamp_img, _ = apply_stamp_edit(img)
            elif attack == "recompression": tamp_img, _ = apply_recompression(img)
            else: tamp_img, _ = apply_copy_move(img)

            out_filename = f"val_tamp_{sample_id:05d}_{attack}.jpg"
            out_rel = f"dataset/forgery_ml_val/tampered/{attack}/{out_filename}"
            cv2.imwrite(str(BACKEND_ROOT / out_rel), tamp_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            metadata.append({
                "source_image": r["image_path"],
                "output_image": out_rel,
                "source_dataset": r["dataset"],
                "document_type": r["document_type"],
                "document_id": r["document_id"],
                "attack_type": attack,
                "field_name": field_name,
                "severity": "realistic_fine",
                "random_seed": str(SEED + sample_id),
                "split": "validation",
            })

    meta_csv = OUTPUT_DIR / "metadata.csv"
    with open(meta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_image", "output_image", "source_dataset", "document_type", "document_id",
            "attack_type", "field_name", "severity", "random_seed", "split"
        ])
        writer.writeheader()
        writer.writerows(metadata)

    print(f"Validation dataset built: {len(metadata)} images ({sum(1 for m in metadata if m['attack_type']=='none')} genuine, {sum(1 for m in metadata if m['attack_type']!='none')} tampered)")

if __name__ == "__main__":
    main()
