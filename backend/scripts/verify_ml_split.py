"""
Split Verification Script for Machine Learning Dataset Splits.

Verifies:
1. No document_id occurs in multiple splits.
2. No exact image path occurs in multiple splits.
3. No exact SHA-256 image hash occurs in multiple splits.
4. Prints counts by:
   - dataset
   - document_type
   - document_id
   - split
5. Reports any violations and exits with non-zero status if leakage is found.
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

    train_csv = reports_dir / "ml_train.csv"
    val_csv = reports_dir / "ml_val.csv"
    test_csv = reports_dir / "ml_test.csv"

    for p in [train_csv, val_csv, test_csv]:
        if not p.exists():
            print(f"ERROR: Missing split file: {p}")
            sys.exit(1)

    splits_data = {}
    for name, p in [("train", train_csv), ("val", val_csv), ("test", test_csv)]:
        with open(p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            splits_data[name] = list(reader)

    print("==================================================")
    print("      ML DATASET SPLIT VERIFICATION SUITE         ")
    print("==================================================")

    # 1. Total counts
    total_images = sum(len(rows) for rows in splits_data.values())
    print(f"\nTotal Split Counts (Total: {total_images}):")
    for name, rows in splits_data.items():
        print(f"  {name:5s}: {len(rows):6d} images ({len(rows)/total_images*100:5.2f}%)")

    # 2. Check Image Path Leakage
    print("\n--- CHECK 1: IMAGE PATH LEAKAGE ---")
    paths_by_split = defaultdict(set)
    all_paths = {}
    path_violations = []

    for name, rows in splits_data.items():
        for r in rows:
            p = r["image_path"]
            if p in all_paths:
                path_violations.append((p, all_paths[p], name))
            all_paths[p] = name
            paths_by_split[name].add(p)

    if path_violations:
        print(f"FAIL: Found {len(path_violations)} image path cross-split leakages!")
        for v in path_violations[:5]:
            print(f"  Path: {v[0]} in {v[1]} AND {v[2]}")
    else:
        print("PASS: Zero image paths cross splits.")

    # 3. Check Document ID Leakage
    print("\n--- CHECK 2: DOCUMENT ID (PHYSICAL IDENTITY) LEAKAGE ---")
    doc_ids_by_split = defaultdict(set)
    all_doc_ids = {}
    doc_id_violations = []

    for name, rows in splits_data.items():
        for r in rows:
            did = r["document_id"]
            if did in all_doc_ids and all_doc_ids[did] != name:
                doc_id_violations.append((did, all_doc_ids[did], name))
            all_doc_ids[did] = name
            doc_ids_by_split[name].add(did)

    if doc_id_violations:
        print(f"FAIL: Found {len(doc_id_violations)} document_id cross-split leakages!")
        for v in doc_id_violations[:5]:
            print(f"  Document ID: {v[0]} in {v[1]} AND {v[2]}")
    else:
        print("PASS: Zero document_ids cross splits.")
        for name, dids in doc_ids_by_split.items():
            print(f"  Unique physical documents/groups in {name}: {len(dids)}")

    # 4. Check Exact SHA-256 Hash Leakage
    print("\n--- CHECK 3: SHA-256 IMAGE HASH LEAKAGE ---")
    hashes_by_split = defaultdict(set)
    all_hashes = {}
    hash_violations = []

    for name, rows in splits_data.items():
        print(f"  Computing hashes for {name} ({len(rows)} images)...")
        for idx, r in enumerate(rows):
            img_file = backend_root / r["image_path"]
            if not img_file.exists():
                print(f"ERROR: Image file not found on disk: {img_file}")
                sys.exit(1)
            h = sha256_file(img_file)
            if h in all_hashes and all_hashes[h] != name:
                hash_violations.append((r["image_path"], all_hashes[h], name, h))
            all_hashes[h] = name
            hashes_by_split[name].add(h)

    if hash_violations:
        print(f"FAIL: Found {len(hash_violations)} hash-level duplicate cross-split leakages!")
        for v in hash_violations[:5]:
            print(f"  Hash {v[3][:8]} in {v[1]} AND {v[2]} (path: {v[0]})")
    else:
        print("PASS: Zero identical image hashes cross splits.")

    # 5. Breakdown by Document Type & Dataset
    print("\n--- BREAKDOWN BY DOCUMENT TYPE ---")
    for name, rows in splits_data.items():
        dt_counts = Counter(r["document_type"] for r in rows)
        print(f"  {name.upper()}: {dict(dt_counts)}")

    print("\n--- BREAKDOWN BY DATASET ---")
    for name, rows in splits_data.items():
        ds_counts = Counter(r["dataset"] for r in rows)
        print(f"  {name.upper()}: {dict(ds_counts)}")

    # 6. Specific MIDV Physical Document Allocation
    print("\n--- MIDV PHYSICAL DOCUMENT ALLOCATION ---")
    for name, rows in splits_data.items():
        midv_docs = sorted(list(set(r["document_id"] for r in rows if "MIDV" in r["dataset"])))
        print(f"  {name.upper()} ({len(midv_docs)} documents): {midv_docs}")

    # 7. Final Verdict
    print("\n==================================================")
    if path_violations or doc_id_violations or hash_violations:
        print("FINAL RESULT: VERIFICATION FAILED (LEAKAGE DETECTED)")
        print("==================================================")
        sys.exit(1)
    else:
        print("FINAL RESULT: VERIFICATION PASSED (ZERO LEAKAGE)")
        print("==================================================")
        sys.exit(0)

if __name__ == "__main__":
    main()
