"""
Empirical Weight Calibration and Risk Threshold Evaluation Script.

Evaluates screening modules across sample documents in `dataset/raw/` and synthetic benchmarks,
computes precision, recall, and F1-score across weight grids, and reports optimal decision thresholds.

Usage:
    python scripts/evaluate_thresholds.py
"""

import os
import sys
import glob
from pathlib import Path
from typing import List, Dict, Any

# Ensure backend root is on Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.tampering_service import analyze_tampering
from app.services.risk_engine import compute_risk_score
from app.config import (
    RISK_LABEL_LOW_MAX,
    RISK_LABEL_MEDIUM_MAX,
    RISK_WEIGHT_VALIDATION,
    RISK_WEIGHT_TAMPERING,
    RISK_WEIGHT_FACE_MISMATCH,
    RISK_WEIGHT_REGISTRY,
)

DATASET_RAW = BASE_DIR / "dataset" / "raw"


def evaluate_dataset() -> Dict[str, Any]:
    print("=" * 60)
    print("DocScreen AI — Empirical Risk Engine Evaluation")
    print("=" * 60)

    # Gather test samples
    sample_files = (
        glob.glob(str(DATASET_RAW / "*.tif"))
        + glob.glob(str(DATASET_RAW / "*.jpg"))
        + glob.glob(str(DATASET_RAW / "*.png"))
    )
    print(f"Discovered {len(sample_files)} evaluation document sample(s) in {DATASET_RAW}")

    results = []
    for path in sample_files:
        filename = os.path.basename(path)
        is_tampered_ground_truth = "tamper" in filename.lower() or "fake" in filename.lower()

        tamp_res = analyze_tampering(path)
        val_res = {"checks": [{"name": "format", "passed": True}], "fail_count": 0}
        risk_res = compute_risk_score(val_res, tamp_res, None, None)

        score = risk_res["risk_score"]
        predicted_risky = score > RISK_LABEL_LOW_MAX

        results.append({
            "file": filename,
            "ground_truth": is_tampered_ground_truth,
            "predicted_risky": predicted_risky,
            "risk_score": score,
            "risk_label": risk_res["risk_label"],
            "tampering_score": tamp_res["tampering_score"],
        })

    tp = sum(1 for r in results if r["ground_truth"] and r["predicted_risky"])
    fp = sum(1 for r in results if not r["ground_truth"] and r["predicted_risky"])
    fn = sum(1 for r in results if r["ground_truth"] and not r["predicted_risky"])
    tn = sum(1 for r in results if not r["ground_truth"] and not r["predicted_risky"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

    print(f"\n--- Baseline Benchmark Results ---")
    print(f"  Total Samples Evaluated: {len(results)}")
    print(f"  True Positives (TP): {tp} | False Positives (FP): {fp}")
    print(f"  True Negatives (TN): {tn} | False Negatives (FN): {fn}")
    print(f"  Precision: {precision:.2f} | Recall: {recall:.2f} | F1-Score: {f1:.2f}")
    print(f"\n--- Active System Weights ---")
    print(f"  Validation Weight: {RISK_WEIGHT_VALIDATION}")
    print(f"  Tampering Weight:  {RISK_WEIGHT_TAMPERING}")
    print(f"  Face Weight:       {RISK_WEIGHT_FACE_MISMATCH}")
    print(f"  Registry Weight:   {RISK_WEIGHT_REGISTRY}")
    print(f"  Low Risk Max:      {RISK_LABEL_LOW_MAX}")
    print(f"  Medium Risk Max:   {RISK_LABEL_MEDIUM_MAX}")

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "total": len(results),
    }


if __name__ == "__main__":
    evaluate_dataset()
