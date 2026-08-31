"""
Downloads the MIDV-500 identity document dataset and copies a handful
of sample images into your project's dataset/raw/ folder for testing.

Run this from inside your `backend` folder, with your venv activated:
    pip install midv500
    python get_sample_images.py
"""

import os
import shutil
import glob
import midv500

DOWNLOAD_DIR = "midv500_data"
DEST_DIR = os.path.join("dataset", "raw")
NUM_SAMPLES = 10  # how many sample images to copy over

os.makedirs(DEST_DIR, exist_ok=True)

print("Downloading MIDV-500 dataset (this may take a few minutes)...")
midv500.download_dataset(DOWNLOAD_DIR)

# Find all extracted document images (they're .tif files under */images/)
image_paths = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "images", "**", "*.tif"), recursive=True)

if not image_paths:
    print("No images found — check that the dataset downloaded correctly.")
else:
    print(f"Found {len(image_paths)} images. Copying {NUM_SAMPLES} samples to {DEST_DIR}...")
    for i, path in enumerate(image_paths[:NUM_SAMPLES]):
        dest_name = f"sample_{i+1}.tif"
        shutil.copy(path, os.path.join(DEST_DIR, dest_name))
        print(f"  copied {dest_name}")

    print("\nDone! Sample identity document images are now in dataset/raw/")
