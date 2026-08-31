import os
import csv
import random
import cv2

# Root path for raw MIDV500 TIF files
MIDV_DIR = 'd:/backend-scaffold (2)/backend/midv500_data/midv500'
OUT_DIR = 'dataset/document_classification'

# Class mapping: map folder names to our 4 target document classes
CLASS_MAP = {
    '01_alb_id': 'national_id',
    '03_aut_id_old': 'national_id',
    '04_aut_id': 'national_id',
    '07_chl_id': 'national_id',
    '02_aut_drvlic_new': 'driving_license',
    '05_aze_passport': 'passport',
    '06_bra_passport': 'passport',
    '08_chn_homereturn': 'permit',
}

def main():
    print("=== PREPARING DOCUMENT CLASSIFICATION DATASET ===")
    if not os.path.exists(MIDV_DIR):
        print("Error: midv500_data directory not found!")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    for c in ['passport', 'national_id', 'driving_license', 'permit', 'visa']:
        os.makedirs(os.path.join(OUT_DIR, c), exist_ok=True)

    # Collect images
    all_records = []
    
    # Random seed for reproducibility
    random.seed(42)

    for folder, doc_type in CLASS_MAP.items():
        folder_path = os.path.join(MIDV_DIR, folder)
        if not os.path.exists(folder_path):
            continue
        
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
                relative_dest_path = os.path.relpath(dest_path, 'd:/backend-scaffold (2)/backend')
                all_records.append({
                    'image_path': relative_dest_path.replace('\\', '/'),
                    'document_type': doc_type,
                    'split': split
                })

    # Write manifest CSV
    manifest_path = os.path.join(OUT_DIR, 'manifest.csv')
    with open(manifest_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['image_path', 'document_type', 'split'])
        writer.writeheader()
        writer.writerows(all_records)

    print(f"Dataset prepared. Total images copied: {len(all_records)}")
    print(f"Manifest saved to: {manifest_path}")

if __name__ == '__main__':
    main()
