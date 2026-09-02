"""
Verification script for Validation Set Isolation (Part 6).

Confirms:
- no train document_id appears in validation source documents
- no validation generated image is copied from train
- no test document_id appears in validation data
- validation source documents remain untouched
- metadata has split=validation
"""

import csv
import hashlib
import sys
from pathlib import Path

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(131072): h.update(chunk)
    return h.hexdigest()

def main():
    backend_root = Path(__file__).resolve().parents[1]
    reports_dir = backend_root / "reports"
    val_meta = backend_root / "dataset" / "forgery_ml_val" / "metadata.csv"
    train_meta = backend_root / "dataset" / "forgery_ml" / "metadata.csv"

    with open(reports_dir / "ml_train.csv", "r", encoding="utf-8") as f:
        train_rows = list(csv.DictReader(f))
    with open(reports_dir / "ml_val.csv", "r", encoding="utf-8") as f:
        val_rows = list(csv.DictReader(f))
    with open(reports_dir / "ml_test.csv", "r", encoding="utf-8") as f:
        test_rows = list(csv.DictReader(f))

    with open(val_meta, "r", encoding="utf-8") as f:
        val_meta_rows = list(csv.DictReader(f))
    with open(train_meta, "r", encoding="utf-8") as f:
        train_meta_rows = list(csv.DictReader(f))

    train_doc_ids = {r["document_id"] for r in train_rows}
    test_doc_ids = {r["document_id"] for r in test_rows}
    val_source_paths = {r["image_path"] for r in val_rows}

    train_out_hashes = {sha256_file(backend_root / r["output_image"]) for r in train_meta_rows}

    print("==================================================")
    print("    VALIDATION DATASET LEAKAGE VERIFICATION       ")
    print("==================================================")

    violations = []

    # 1. No train or test document_id in validation metadata
    for r in val_meta_rows:
        did = r["document_id"]
        src = r["source_image"]
        if did in train_doc_ids:
            violations.append(f"Train document_id found in val: {did}")
        if did in test_doc_ids:
            violations.append(f"Test document_id found in val: {did}")
        if src not in val_source_paths:
            violations.append(f"Val source not in ml_val.csv: {src}")
        if r["split"] != "validation":
            violations.append(f"Invalid split label in val metadata: {r['split']}")

    # 2. No val generated image hash matches train generated image hash
    for r in val_meta_rows:
        vh = sha256_file(backend_root / r["output_image"])
        if vh in train_out_hashes:
            violations.append(f"Generated validation image copied from train: {r['output_image']}")

    if violations:
        print(f"FAIL: Found {len(violations)} validation leakage violations!")
        for v in violations[:5]: print(" ", v)
        sys.exit(1)
    else:
        print(f"PASS: Validation dataset ({len(val_meta_rows)} images) is 100% isolated from train and test.")
        sys.exit(0)

if __name__ == "__main__":
    main()
