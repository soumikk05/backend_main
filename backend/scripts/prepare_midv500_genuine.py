"""
Converts MIDV-500 TIF frames into dataset/genuine/{passport,visa,id,license}/*.jpg,
matching the folder structure app/tampering/dataset_loader.py expects.

MIDV-500 has NO visa documents — only passports, national IDs, and driving licenses.
This script never populates genuine/visa/ (see note at the end of the run).

Picks images from DIFFERENT clip subfolders per category (not many frames from the
same clip) so you get variety in angle/lighting/background, since near-duplicate
frames from one video add little training value.

Usage:
    python scripts/prepare_midv500_genuine.py --midv_root midv500_data/midv500 --per_category 10
"""

import argparse
import os
import zipfile
from pathlib import Path

from PIL import Image

# Category detection heuristic based on MIDV-500 folder naming conventions
# (e.g. 01_alb_id, 05_aze_passport, aut_drvlic, 03_aut_id_old)
def detect_category(folder_name: str) -> str:
    name = folder_name.lower()
    if "passport" in name:
        return "passport"
    if "drvlic" in name or "license" in name or "licence" in name:
        return "license"
    if "id" in name:  # check after passport/drvlic so e.g. "id" inside other words doesn't misfire
        return "id"
    return "unknown"


def find_tif_frames(category_folder: Path):
    """
    Returns list of (clip_subfolder_name, tif_path), preferring one representative
    frame per clip subfolder for diversity rather than every frame.
    """
    images_dir = category_folder / "images"
    if not images_dir.exists():
        return []

    results = []
    # Each clip is usually a numbered subfolder (01, 02, ... 10) inside images/
    clip_dirs = sorted([d for d in images_dir.iterdir() if d.is_dir()]) or [images_dir]
    for clip_dir in clip_dirs:
        tifs = sorted(clip_dir.glob("*.tif")) + sorted(clip_dir.glob("*.tiff")) + sorted(clip_dir.glob("*.TIF"))
        if tifs:
            mid_frame = tifs[len(tifs) // 2]  # middle frame tends to be more stable than first/last
            results.append((clip_dir.name, mid_frame))
    return results


def convert_and_save(tif_path: Path, out_path: Path) -> bool:
    try:
        img = Image.open(tif_path).convert("RGB")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "JPEG", quality=92)
        return True
    except Exception as exc:
        print(f"  WARNING: could not convert {tif_path}: {exc}")
        return False


def main(midv_root: str, out_root: str, per_category: int):
    midv_root_path = Path(midv_root)
    out_root_path = Path(out_root)

    if not midv_root_path.exists():
        print(f"ERROR: MIDV-500 root not found at '{midv_root}'. Check the path and try again.")
        return

    zipped = list(midv_root_path.glob("*.zip"))
    if zipped:
        print(f"Found {len(zipped)} unextracted .zip folder(s) — skipping these until unzipped:")
        for z in zipped:
            print(f"  {z.name}  (unzip with: unzip \"{z}\" -d \"{z.with_suffix('')}\"  or right-click > Extract All on Windows)")
        print()

    category_counts = {"passport": 0, "id": 0, "license": 0}
    skipped_unknown = []

    for folder in sorted(midv_root_path.iterdir()):
        if not folder.is_dir():
            continue
        category = detect_category(folder.name)
        if category == "unknown":
            skipped_unknown.append(folder.name)
            continue
        if category_counts[category] >= per_category:
            continue

        frames = find_tif_frames(folder)
        for clip_name, tif_path in frames:
            if category_counts[category] >= per_category:
                break
            out_name = f"{folder.name}_{clip_name}.jpg"
            out_path = out_root_path / category / out_name
            if convert_and_save(tif_path, out_path):
                category_counts[category] += 1
                print(f"  [{category}] {tif_path.name} -> {out_path}")

    print("\n=== Summary ===")
    for cat, count in category_counts.items():
        print(f"  genuine/{cat}: {count} images")
    print(f"  genuine/visa: 0 images  (MIDV-500 has no visa documents — needs a separate source)")

    if skipped_unknown:
        print(f"\nSkipped {len(skipped_unknown)} folder(s) that didn't match passport/id/license naming "
              f"(e.g. permits, home-return documents): {', '.join(skipped_unknown[:5])}"
              + (" ..." if len(skipped_unknown) > 5 else ""))
        print("These aren't lost — they're just not auto-categorized. Review manually if you want to use them.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert MIDV-500 TIFs into dataset/genuine/ JPGs")
    parser.add_argument("--midv_root", type=str, default="midv500_data/midv500", help="Path to extracted MIDV-500 folders")
    parser.add_argument("--out_root", type=str, default="dataset/genuine", help="Output root (matches dataset_loader.py)")
    parser.add_argument("--per_category", type=int, default=10, help="Max images to pull per category")
    args = parser.parse_args()
    main(args.midv_root, args.out_root, args.per_category)