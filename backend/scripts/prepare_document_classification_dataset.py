import os
import csv
import random
import cv2
import argparse
from pathlib import Path

# Root path for raw MIDV500 TIF files (default)
DEFAULT_MIDV_DIR = 'midv500_data/midv500'
OUT_DIR = 'dataset/document_classification'

def classify_folder(folder_name: str) -> str | None:
    name = folder_name.lower()
    if "passport" in name:
        return "passport"
    if "drvlic" in name or "license" in name or "licence" in name:
        return "driving_license"
    if "homereturn" in name or "bordercrossing" in name:
        return "permit"
    if "id" in name:
        return "national_id"
    return None  # unmapped, skip

def main():
    parser = argparse.ArgumentParser(description="Prepare document classification dataset")
    parser.add_argument("--midv_dir", default=DEFAULT_MIDV_DIR, help="Path to MIDV-500 extracted images")
    args = parser.parse_args()

    # Resolve midv_dir relative to the backend root (parent of scripts/)
    backend_root = Path(__file__).resolve().parent.parent
    midv_dir_path = backend_root / args.midv_dir

    print("=== PREPARING DOCUMENT CLASSIFICATION DATASET ===")
    if not midv_dir_path.exists():
        print(f"Error: midv500_data directory not found at {midv_dir_path}!")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    for c in ['passport', 'national_id', 'driving_license', 'permit']:
        os.makedirs(os.path.join(OUT_DIR, c), exist_ok=True)
    print("Note: 'visa' is supported by the backend but MIDV-500 lacks visa source data.")

    # Collect images
    all_records = []
    
    # Random seed for reproducibility
    random.seed(42)

    class_counts = {'passport': 0, 'national_id': 0, 'driving_license': 0, 'permit': 0}
    source_folder_counts = {'passport': 0, 'national_id': 0, 'driving_license': 0, 'permit': 0}

    for folder in os.listdir(midv_dir_path):
        folder_path = os.path.join(midv_dir_path, folder)
        if not os.path.isdir(folder_path):
            continue
        
        doc_type = classify_folder(folder)
        if not doc_type:
            continue
        
        source_folder_counts[doc_type] += 1
        
        tif_files = []
        for r, dirs, files in os.walk(folder_path):
            for f in files:
                if f.lower().endswith('.tif'):
                    tif_files.append(os.path.join(r, f))
        
        # Sort files to ensure deterministic split before shuffle
        tif_files.sort()
        random.shuffle(tif_files)

        # For fast training, we can copy up to 80 images per category to prevent slow training
        selected_files = tif_files[:80]
        
        # Split (70/15/15)
        n = len(selected_files)
        n_train = int(n * 0.70)
        n_val = int(n * 0.15)
        
        for idx, src_path in enumerate(selected_files):
            if idx < n_train:
                split = 'train'
            elif idx < n_train + n_val:
                split = 'val'
            else:
                split = 'test'
            
            # Destination path
            filename = f"{folder}_{os.path.basename(src_path)}".replace('.tif', '.jpg')
            dest_dir = os.path.join(OUT_DIR, doc_type)
            dest_path = os.path.join(dest_dir, filename)
            
            # Copy file (converting TIF to JPEG using cv2 to save space/time)
            img = cv2.imread(src_path)
            if img is not None:
                cv2.imwrite(dest_path, img)
                relative_dest_path = os.path.relpath(dest_path, str(backend_root))
                all_records.append({
                    'image_path': relative_dest_path.replace('\\', '/'),
                    'document_type': doc_type,
                    'split': split
                })
                class_counts[doc_type] += 1

    # Write manifest CSV
    manifest_path = os.path.join(OUT_DIR, 'manifest.csv')
    with open(manifest_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['image_path', 'document_type', 'split'])
        writer.writeheader()
        writer.writerows(all_records)

    print(f"Dataset prepared. Total images copied: {len(all_records)}")
    print(f"Manifest saved to: {manifest_path}")
    
    print("\n=== Category Summary ===")
    for c in ['passport', 'national_id', 'driving_license', 'permit']:
        print(f"  {c.ljust(15)}: {source_folder_counts.get(c, 0)} source folders, {class_counts.get(c, 0)} images")

if __name__ == '__main__':
    main()
