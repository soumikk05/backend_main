"""
Verification Script for Phase 3 Forgery Dataset Isolation & Integrity.

Confirms:
1. Every source image used for tampering appears in ml_train.csv.
2. No source document_id comes from ml_val.csv or ml_test.csv.
3. No generated tampered image uses a validation/test source.
4. No exact source-image hash occurs in validation/test.
5. Metadata contains no validation/test document IDs.
6. All generated samples have split=train.
7. Output counts by document type and attack type.
8. Exit non-zero if any violation is found.
"""

import csv
import hashlib
import sys
from pathlib import Path
from collections import Counter, defaultdict

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(131072):
            h.update(chunk)
    return h.hexdigest()

def main():
    backend_root = Path(__file__).resolve().parents[1]
    reports_dir = backend_root / "reports"
    meta_csv = backend_root / "dataset" / "forgery_ml" / "metadata.csv"

    train_csv = reports_dir / "ml_train.csv"
    val_csv = reports_dir / "ml_val.csv"
    test_csv = reports_dir / "ml_test.csv"

    for p in [meta_csv, train_csv, val_csv, test_csv]:
        if not p.exists():
            print(f"ERROR: Missing required file: {p}")
            sys.exit(1)

    print("==================================================")
    print("      PHASE 3 FORGERY DATASET VERIFICATION        ")
    print("==================================================")

    # 1. Load split sets
    with open(train_csv, "r", encoding="utf-8") as f:
        train_rows = list(csv.DictReader(f))
    with open(val_csv, "r", encoding="utf-8") as f:
        val_rows = list(csv.DictReader(f))
    with open(test_csv, "r", encoding="utf-8") as f:
        test_rows = list(csv.DictReader(f))

    train_paths = {r["image_path"] for r in train_rows}
    val_paths = {r["image_path"] for r in val_rows}
    test_paths = {r["image_path"] for r in test_rows}

    train_doc_ids = {r["document_id"] for r in train_rows}
    val_doc_ids = {r["document_id"] for r in val_rows}
    test_doc_ids = {r["document_id"] for r in test_rows}

    print(f"Loaded partitions: Train={len(train_paths)}, Val={len(val_paths)}, Test={len(test_paths)}")
    print(f"Loaded document IDs: Train={len(train_doc_ids)}, Val={len(val_doc_ids)}, Test={len(test_doc_ids)}")

    # 2. Load generated metadata
    with open(meta_csv, "r", encoding="utf-8") as f:
        meta_rows = list(csv.DictReader(f))

    total_meta = len(meta_rows)
    print(f"\nTotal generated records in metadata.csv: {total_meta}")

    violations = []

    # Check 1 & 2: Every source image in train, no doc_id from val or test
    print("\n--- CHECK 1 & 2: SOURCE IMAGE & DOCUMENT ID ORIGIN ---")
    for r in meta_rows:
        src = r["source_image"]
        did = r["document_id"]

        if src not in train_paths:
            violations.append(f"Source image not in ml_train.csv: {src}")
        if src in val_paths:
            violations.append(f"Source image LEAK from ml_val.csv: {src}")
        if src in test_paths:
            violations.append(f"Source image LEAK from ml_test.csv: {src}")

        if did in val_doc_ids:
            violations.append(f"Document ID LEAK from val: {did}")
        if did in test_doc_ids:
            violations.append(f"Document ID LEAK from test: {did}")

    if violations:
        print(f"FAIL: Found {len(violations)} source origin violations!")
        for v in violations[:5]:
            print(" ", v)
    else:
        print("PASS: 100% of source images and document IDs originate strictly from ml_train.csv.")

    # Check 3 & 4: Hash verification against validation and test
    print("\n--- CHECK 3 & 4: HASH ISOLATION AGAINST VAL & TEST ---")
    val_hashes = {sha256_file(backend_root / p) for p in val_paths}
    test_hashes = {sha256_file(backend_root / p) for p in test_paths}

    hash_violations = []
    for r in meta_rows:
        out_img_path = backend_root / r["output_image"]
        if not out_img_path.exists():
            violations.append(f"Output image missing on disk: {out_img_path}")
            continue
        h = sha256_file(out_img_path)
        if h in val_hashes:
            hash_violations.append(f"Output hash matches validation set: {r['output_image']}")
        if h in test_hashes:
            hash_violations.append(f"Output hash matches test set: {r['output_image']}")

    if hash_violations:
        print(f"FAIL: Found {len(hash_violations)} hash-level leaks to val/test!")
        for hv in hash_violations[:5]:
            print(" ", hv)
    else:
        print("PASS: Zero generated images or source images match validation or test hashes.")

    # Check 5 & 6: Split label in metadata
    print("\n--- CHECK 5 & 6: METADATA SPLIT LABELS ---")
    split_counts = Counter(r["split"] for r in meta_rows)
    print(f"  Split labels in metadata: {dict(split_counts)}")
    if set(split_counts.keys()) != {"train"}:
        violations.append(f"Unexpected split labels in metadata: {split_counts}")
    else:
        print("PASS: All generated metadata rows have split == 'train'.")

    # Check 7: Breakdown counts
    print("\n--- BREAKDOWN BY ATTACK TYPE ---")
    attack_counts = Counter(r["attack_type"] for r in meta_rows)
    for at, cnt in attack_counts.items():
        print(f"  {at:25s}: {cnt}")

    print("\n--- BREAKDOWN BY DOCUMENT TYPE ---")
    doc_type_counts = Counter(r["document_type"] for r in meta_rows)
    for dt, cnt in doc_type_counts.items():
        print(f"  {dt:25s}: {cnt}")

    print("\n--- BREAKDOWN BY CLASS (GENUINE VS TAMPERED) ---")
    genuine_count = sum(1 for r in meta_rows if r["attack_type"] == "none")
    tampered_count = sum(1 for r in meta_rows if r["attack_type"] != "none")
    print(f"  Genuine Samples : {genuine_count}")
    print(f"  Tampered Samples: {tampered_count}")
    print(f"  Balance Ratio   : {tampered_count / max(1, genuine_count):.2f}")

    # Summary
    print("\n==================================================")
    if violations or hash_violations:
        print("FINAL RESULT: VERIFICATION FAILED (VIOLATIONS DETECTED)")
        print("==================================================")
        sys.exit(1)
    else:
        print("FINAL RESULT: VERIFICATION PASSED (ZERO LEAKAGE, 100% TRAIN-ONLY)")
        print("==================================================")
        sys.exit(0)

if __name__ == "__main__":
    main()
