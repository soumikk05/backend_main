"""
Tampering and Identity Document Dataset Preparation and Manifest Generator.

Organizes dataset hierarchy:
  dataset/
    genuine/ (passport, visa, national_id, driving_license, permit)
    tampered/ (photo_swap, text_edit, dob_edit, name_edit, number_edit, stamp_forgery, copy_move)
    adversarial/ (blur, compression, screenshot, print_photo, noise, resize)
    train/
    validation/
    test/

Outputs deterministic manifest.csv:
  image_path,label,attack_type,document_type,split
"""

import argparse
import csv
import hashlib
import os
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple

DOCUMENT_TYPES = ["passport", "visa", "national_id", "driving_license", "permit"]
ATTACK_TYPES = [
    "photo_swap",
    "text_edit",
    "dob_edit",
    "name_edit",
    "number_edit",
    "stamp_forgery",
    "copy_move",
    "none",
]


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def prepare_directories(root: Path) -> None:
    """Create standard dataset hierarchy."""
    for dtype in DOCUMENT_TYPES:
        (root / "genuine" / dtype).mkdir(parents=True, exist_ok=True)
    for atype in ATTACK_TYPES:
        if atype != "none":
            (root / "tampered" / atype).mkdir(parents=True, exist_ok=True)
    for adv in ["blur", "compression", "screenshot", "print_photo", "noise", "resize"]:
        (root / "adversarial" / adv).mkdir(parents=True, exist_ok=True)
    for split in ["train", "validation", "test"]:
        (root / split / "genuine").mkdir(parents=True, exist_ok=True)
        (root / split / "tampered").mkdir(parents=True, exist_ok=True)


def discover_and_manifest(
    root: Path,
    manifest_path: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> int:
    """
    Discover all images across dataset directories, deduplicate by SHA-256,
    assign deterministic train/val/test splits, and write CSV manifest.
    """
    prepare_directories(root)
    seen_hashes: Set[str] = set()
    manifest_records: List[Dict[str, str]] = []

    valid_extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}

    # Search for all image files under root
    for img_path in sorted(root.rglob("*")):
        if not img_path.is_file() or img_path.suffix.lower() not in valid_extensions:
            continue
        if "train" in img_path.parts or "validation" in img_path.parts or "test" in img_path.parts:
            continue

        try:
            h = file_sha256(img_path)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            parts = [p.lower() for p in img_path.parts]

            # Determine label
            is_tampered = "tampered" in parts or any(at in parts for at in ATTACK_TYPES if at != "none")
            label = "1" if is_tampered else "0"

            # Determine attack type
            attack_type = "none"
            for at in ATTACK_TYPES:
                if at != "none" and at in parts:
                    attack_type = at
                    break
            if is_tampered and attack_type == "none":
                attack_type = "generic_tampering"

            # Determine document type
            doc_type = "unknown"
            for dt in DOCUMENT_TYPES:
                if dt in parts:
                    doc_type = dt
                    break

            # Deterministic split based on hash
            hash_val = int(h[:8], 16) / 0xFFFFFFFF
            if hash_val < train_ratio:
                split = "train"
            elif hash_val < (train_ratio + val_ratio):
                split = "validation"
            else:
                split = "test"

            rel_path = str(img_path.relative_to(root.parent if root.parent else root)).replace("\\", "/")
            manifest_records.append({
                "image_path": rel_path,
                "label": label,
                "attack_type": attack_type,
                "document_type": doc_type,
                "split": split,
            })
        except Exception as exc:
            continue

    # Write manifest CSV
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image_path", "label", "attack_type", "document_type", "split"])
        writer.writeheader()
        writer.writerows(manifest_records)

    return len(manifest_records)


def main():
    parser = argparse.ArgumentParser(description="Prepare identity & tampering dataset and generate manifest.csv")
    parser.add_argument("--dataset-dir", default=str(Path(__file__).resolve().parents[1] / "dataset"))
    parser.add_argument("--manifest-file", default=str(Path(__file__).resolve().parents[1] / "dataset" / "manifest.csv"))
    args = parser.parse_args()

    root = Path(args.dataset_dir)
    manifest_path = Path(args.manifest_file)

    count = discover_and_manifest(root, manifest_path)
    print(f"Dataset preparation complete. Total indexed unique samples: {count}")
    print(f"Manifest written to: {manifest_path}")


if __name__ == "__main__":
    main()
