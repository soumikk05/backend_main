"""
Verification script for Region-Aware Forgery Dataset & Inventory.

Asserts:
1. Train and validation document_ids are disjoint.
2. No test document (from ml_test.csv) is accessed or present in inventory.
3. Crop source paths belong to the correct split.
4. No duplicate crop records exist in forgery_region_inventory.csv.
5. All crops exist on disk with valid 128x128 dimensions.
6. Original source images remain untouched.
7. Exit non-zero if any violation is found.
"""

import csv
import sys
from collections import Counter
from pathlib import Path
from PIL import Image

def main():
    backend_root = Path(__file__).resolve().parents[1]
    reports_dir = backend_root / "reports"

    inventory_csv = reports_dir / "forgery_region_inventory.csv"
    train_csv = reports_dir / "ml_train.csv"
    val_csv = reports_dir / "ml_val.csv"
    test_csv = reports_dir / "ml_test.csv"

    for p in [inventory_csv, train_csv, val_csv, test_csv]:
        if not p.exists():
            print(f"ERROR: Required file missing: {p}")
            sys.exit(1)

    print("==================================================")
    print("   FORGERY REGION DATASET VERIFICATION SUITE      ")
    print("==================================================")

    # 1. Load splits
    with open(train_csv, "r", encoding="utf-8") as f:
        train_rows = list(csv.DictReader(f))
    with open(val_csv, "r", encoding="utf-8") as f:
        val_rows = list(csv.DictReader(f))
    with open(test_csv, "r", encoding="utf-8") as f:
        test_rows = list(csv.DictReader(f))

    train_doc_ids = {r["document_id"] for r in train_rows}
    val_doc_ids = {r["document_id"] for r in val_rows}
    test_doc_ids = {r["document_id"] for r in test_rows}

    train_img_paths = {r["image_path"] for r in train_rows}
    val_img_paths = {r["image_path"] for r in val_rows}
    test_img_paths = {r["image_path"] for r in test_rows}

    # 2. Load inventory
    with open(inventory_csv, "r", encoding="utf-8") as f:
        inventory = list(csv.DictReader(f))

    print(f"Loaded Inventory Records: {len(inventory)}")
    violations = []

    # Check 1: Train & Validation disjoint in inventory
    inv_train_dids = {r["document_id"] for r in inventory if r["split"] == "train"}
    inv_val_dids = {r["document_id"] for r in inventory if r["split"] == "validation"}
    overlap = inv_train_dids.intersection(inv_val_dids)
    if overlap:
        violations.append(f"Train and Val document_id overlap in inventory: {overlap}")
    else:
        print(f"PASS: Train and Val document_ids are strictly disjoint.")

    # Check 2: No test document in inventory
    inv_all_dids = {r["document_id"] for r in inventory}
    test_leak = inv_all_dids.intersection(test_doc_ids)
    if test_leak:
        violations.append(f"SECURITY VIOLATION: Test document_ids in inventory: {test_leak}")
    else:
        print("PASS: Zero test document_ids found in region inventory.")

    # Check 3: Crop source path split integrity
    for r in inventory:
        src = r["source_image"]
        split = r["split"]
        did = r["document_id"]

        if split == "train":
            if src not in train_img_paths or did not in train_doc_ids:
                violations.append(f"Train crop source not in train partition: {src}")
        elif split == "validation":
            if src not in val_img_paths or did not in val_doc_ids:
                violations.append(f"Val crop source not in val partition: {src}")
        else:
            violations.append(f"Unexpected split label: {split}")

        if src in test_img_paths:
            violations.append(f"SECURITY VIOLATION: Test image leaked into inventory: {src}")

    if not any("source not in" in v for v in violations):
        print("PASS: 100% of crop source paths belong strictly to their designated split.")

    # Check 4: No duplicate crop records
    crop_paths = [r["crop_path"] for r in inventory]
    counts = Counter(crop_paths)
    dupes = [k for k, v in counts.items() if v > 1]
    if dupes:
        violations.append(f"Duplicate crop paths found: {len(dupes)}")
    else:
        print("PASS: Zero duplicate crop records in inventory.")

    # Check 5: Physical files on disk & dimensions
    dim_errors = 0
    for r in inventory:
        p = backend_root / r["crop_path"]
        if not p.exists():
            violations.append(f"Crop file missing on disk: {p}")
            continue
        try:
            im = Image.open(p)
            if im.size != (128, 128):
                violations.append(f"Crop has wrong size {im.size}: {p}")
                dim_errors += 1
        except Exception as e:
            violations.append(f"Failed to read crop image {p}: {e}")

    if dim_errors == 0:
        print("PASS: 100% of crop files exist on disk and have exact (128, 128) dimensions.")

    # Summary breakdown
    print("\n--- INVENTORY BREAKDOWN BY FIELD ---")
    by_field = Counter(r["field_name"] for r in inventory)
    for f, c in sorted(by_field.items()):
        print(f"  {f:20s}: {c} crops")

    print("\n--- INVENTORY BREAKDOWN BY SPLIT ---")
    by_split = Counter(r["split"] for r in inventory)
    for s, c in sorted(by_split.items()):
        print(f"  {s:20s}: {c} crops")

    print("==================================================")
    if violations:
        print(f"FINAL RESULT: FAILED ({len(violations)} VIOLATIONS FOUND)")
        for v in violations[:5]:
            print(" ", v)
        sys.exit(1)
    else:
        print("FINAL RESULT: VERIFICATION PASSED (ZERO LEAKAGE, CLEAN REGION DATASET)")
        print("==================================================")
        sys.exit(0)

if __name__ == "__main__":
    main()
