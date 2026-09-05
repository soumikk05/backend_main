"""
Prepare High-Resolution Patch Training Dataset (TRAIN SPLIT ONLY).

Strict Zero-Leakage Rules:
1. ONLY processes documents where split == 'train' in dataset/dataset_split_manifest.csv.
2. NEVER touches or reads images from 'validation' or 'test' splits!
3. Cross-checks EVERY patch candidate against dataset_split_manifest.csv.
4. Saves patch metadata to dataset/train_patches_manifest.csv and patch images to dataset/patches_train/
"""

import os
import sys
import csv
from pathlib import Path
from typing import Dict, List, Tuple
import cv2
import numpy as np
import pandas as pd
from PIL import Image

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "dataset" / "dataset_split_manifest.csv"
OUTPUT_DIR = BASE_DIR / "dataset" / "patches_train"
PATCH_MANIFEST = BASE_DIR / "dataset" / "train_patches_manifest.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "genuine").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "tampered").mkdir(parents=True, exist_ok=True)

def main():
    print("==========================================================")
    print("PREPARING HIGH-RESOLUTION PATCH DATASET (TRAIN SPLIT ONLY)")
    print("==========================================================")

    df = pd.read_csv(MANIFEST_PATH)
    path_to_split = dict(zip(df['image_path'], df['split']))
    path_to_label = dict(zip(df['image_path'], df['label']))
    
    train_paths = set(df[df['split'] == 'train']['image_path'])
    val_paths = set(df[df['split'] == 'validation']['image_path'])
    test_paths = set(df[df['split'] == 'test']['image_path'])

    print(f"[*] Train images in manifest: {len(train_paths)}")
    print(f"[*] Validation images: {len(val_paths)}")
    print(f"[*] Test images: {len(test_paths)}")

    patch_records = []
    patch_id = 0

    # 1. Existing crops in manifest that are strictly in TRAIN split
    train_crop_rows = df[(df['split'] == 'train') & (df['source'] == 'FORGERY_REGIONS_CROPS')]
    print(f"[*] Found {len(train_crop_rows)} crops in manifest marked split == 'train'...")

    for idx, r in train_crop_rows.iterrows():
        p = BASE_DIR / r['image_path']
        if not p.exists():
            continue
        rel = str(p.relative_to(BASE_DIR)).replace("\\", "/")
        if rel in test_paths or rel in val_paths:
            raise RuntimeError(f"SECURITY VIOLATION: {rel} is in test/val!")
        
        patch_records.append({
            "patch_path": rel,
            "label": int(r['label']),
            "source_type": "manifest_crop_train",
            "attack_type": r['tampering_type'],
            "split": "train"
        })
        patch_id += 1

    print(f"[*] Added {len(patch_records)} verified train crops from manifest.")

    # 2. Extract tampered diff crops from dataset/forgery_ml/ (TRAIN ONLY)
    fml_meta = BASE_DIR / "dataset" / "forgery_ml" / "metadata.csv"
    if fml_meta.exists():
        fml_df = pd.read_csv(fml_meta)
        
        # Security: ONLY keep rows whose output_image is in train_paths!
        fml_train = fml_df[fml_df['output_image'].isin(train_paths)]
        print(f"[*] Verified {len(fml_train)} forgery_ml rows belonging to TRAIN split...")

        for idx, row in fml_train.iterrows():
            if row['attack_type'] == 'none':
                continue
            
            out_p = BASE_DIR / row['output_image']
            src_p = BASE_DIR / row['source_image']

            if not out_p.exists() or not src_p.exists():
                continue

            rel_out = str(out_p.relative_to(BASE_DIR)).replace("\\", "/")
            if rel_out not in train_paths or rel_out in test_paths or rel_out in val_paths:
                continue

            try:
                im_tam = cv2.imread(str(out_p))
                im_gen = cv2.imread(str(src_p))
                if im_tam is None or im_gen is None:
                    continue

                if im_tam.shape != im_gen.shape:
                    im_gen = cv2.resize(im_gen, (im_tam.shape[1], im_tam.shape[0]))

                h_orig, w_orig = im_tam.shape[:2]
                diff = np.max(np.abs(im_tam.astype(int) - im_gen.astype(int)), axis=2)
                mask = (diff > 15).astype(np.uint8)
                pts = cv2.findNonZero(mask)

                if pts is not None:
                    x, y, w, h = cv2.boundingRect(pts)
                    # Add 25% margin around tampered area
                    mx = max(20, int(w * 0.25))
                    my = max(20, int(h * 0.25))
                    x1 = max(0, x - mx)
                    y1 = max(0, y - my)
                    x2 = min(w_orig, x + w + mx)
                    y2 = min(h_orig, y + h + my)

                    crop_tam = im_tam[y1:y2, x1:x2]
                    crop_gen = im_gen[y1:y2, x1:x2]

                    if crop_tam.size > 0 and crop_gen.size > 0:
                        crop_tam_224 = cv2.resize(crop_tam, (224, 224), interpolation=cv2.INTER_AREA)
                        crop_gen_224 = cv2.resize(crop_gen, (224, 224), interpolation=cv2.INTER_AREA)

                        tam_name = f"tam_{patch_id:06d}_{row['attack_type']}.jpg"
                        gen_name = f"gen_{patch_id:06d}_{row['attack_type']}.jpg"

                        tam_dest = OUTPUT_DIR / "tampered" / tam_name
                        gen_dest = OUTPUT_DIR / "genuine" / gen_name

                        cv2.imwrite(str(tam_dest), crop_tam_224, [cv2.IMWRITE_JPEG_QUALITY, 95])
                        cv2.imwrite(str(gen_dest), crop_gen_224, [cv2.IMWRITE_JPEG_QUALITY, 95])

                        patch_records.append({
                            "patch_path": str(tam_dest.relative_to(BASE_DIR)).replace("\\", "/"),
                            "label": 1,
                            "source_type": "midv_diff_crop_tampered",
                            "attack_type": row['attack_type'],
                            "split": "train"
                        })
                        patch_records.append({
                            "patch_path": str(gen_dest.relative_to(BASE_DIR)).replace("\\", "/"),
                            "label": 0,
                            "source_type": "midv_diff_crop_genuine",
                            "attack_type": "none",
                            "split": "train"
                        })
                        patch_id += 1
            except Exception:
                continue

    print(f"[*] Patches after diff extraction: {len(patch_records)}")

    # 3. Extract high-resolution grid patches from genuine documents in TRAIN split
    gen_train_rows = df[(df['split'] == 'train') & (df['label'] == 0)].sample(n=1200, random_state=42)
    print(f"[*] Sampling {len(gen_train_rows)} genuine train documents for multi-scale grid patches...")

    for idx, row in gen_train_rows.iterrows():
        p = BASE_DIR / row['image_path']
        if not p.exists():
            continue

        rel_p = str(p.relative_to(BASE_DIR)).replace("\\", "/")
        if rel_p not in train_paths or rel_p in test_paths or rel_p in val_paths:
            continue

        try:
            im = cv2.imread(str(p))
            if im is None:
                continue
            h, w = im.shape[:2]
            if h < 200 or w < 200:
                continue

            # Patch 1: Center
            cw1, ch1 = int(w * 0.25), int(h * 0.25)
            cw2, ch2 = int(w * 0.75), int(h * 0.75)
            p1 = cv2.resize(im[ch1:ch2, cw1:cw2], (224, 224), interpolation=cv2.INTER_AREA)

            # Patch 2: Top-Right
            rx1, ry1 = int(w * 0.5), 0
            rx2, ry2 = w, int(h * 0.5)
            p2 = cv2.resize(im[ry1:ry2, rx1:rx2], (224, 224), interpolation=cv2.INTER_AREA)

            p1_name = f"gen_grid_{patch_id:06d}_center.jpg"
            p2_name = f"gen_grid_{patch_id+1:06d}_topright.jpg"

            cv2.imwrite(str(OUTPUT_DIR / "genuine" / p1_name), p1, [cv2.IMWRITE_JPEG_QUALITY, 95])
            cv2.imwrite(str(OUTPUT_DIR / "genuine" / p2_name), p2, [cv2.IMWRITE_JPEG_QUALITY, 95])

            patch_records.append({
                "patch_path": str((OUTPUT_DIR / "genuine" / p1_name).relative_to(BASE_DIR)).replace("\\", "/"),
                "label": 0,
                "source_type": "grid_patch_genuine",
                "attack_type": "none",
                "split": "train"
            })
            patch_records.append({
                "patch_path": str((OUTPUT_DIR / "genuine" / p2_name).relative_to(BASE_DIR)).replace("\\", "/"),
                "label": 0,
                "source_type": "grid_patch_genuine",
                "attack_type": "none",
                "split": "train"
            })
            patch_id += 2
        except Exception:
            continue

    # Save manifest
    patch_df = pd.DataFrame(patch_records)
    patch_df.to_csv(PATCH_MANIFEST, index=False)

    print(f"\n[OK] High-resolution patch training manifest saved to: {PATCH_MANIFEST}")
    print(f"Total train patches: {len(patch_df)}")
    print(f"  Genuine patches (0) : {(patch_df['label'] == 0).sum()}")
    print(f"  Tampered patches (1): {(patch_df['label'] == 1).sum()}")
    print(f"  Class balance: {(patch_df['label'] == 1).sum() / len(patch_df) * 100:.2f}% tampered")

if __name__ == '__main__':
    main()
