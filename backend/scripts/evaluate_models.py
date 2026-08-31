"""
Comprehensive ML Model and Forensic Detector Evaluation Suite.

Evaluates tampering detection across attack types:
- Photo replacement / swap
- Text modification
- DOB modification
- Name modification
- Number modification
- Stamp forgery
- Copy-move duplication

Generates:
  reports/tampering_metrics.json
  reports/tampering_metrics.csv
  reports/confusion_matrix.png (when matplotlib available)
  reports/roc_curve.png (when matplotlib available)

Safely handles INSUFFICIENT_DATA without crashing or fabricating results.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from sklearn.metrics import (
        accuracy_score,
        precision_recall_fscore_support,
        roc_auc_score,
        confusion_matrix,
        roc_curve,
    )
except ImportError:
    accuracy_score = None


def evaluate_predictions(
    labels: List[int],
    scores: List[float],
    attack_types: Optional[List[str]] = None,
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Calculate standard evaluation metrics and per-attack breakdown."""
    if not labels or len(labels) < 2 or accuracy_score is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "samples": len(labels),
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "roc_auc": None,
            "confusion_matrix": None,
            "per_attack_breakdown": {},
        }

    preds = [1 if s >= threshold else 0 for s in scores]

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary", zero_division=0
    )
    acc = float(accuracy_score(labels, preds))
    cm = confusion_matrix(labels, preds).tolist()

    try:
        auc = float(roc_auc_score(labels, scores)) if len(set(labels)) > 1 else None
    except Exception:
        auc = None

    per_attack: Dict[str, Any] = {}
    if attack_types and len(attack_types) == len(labels):
        attacks_set = set(attack_types)
        for atype in attacks_set:
            if atype == "none":
                continue
            indices = [i for i, at in enumerate(attack_types) if at == atype or labels[i] == 0]
            if len(indices) >= 2:
                sub_labels = [labels[i] for i in indices]
                sub_preds = [preds[i] for i in indices]
                sub_p, sub_r, sub_f1, _ = precision_recall_fscore_support(
                    sub_labels, sub_preds, average="binary", zero_division=0
                )
                per_attack[atype] = {
                    "samples": len(indices),
                    "accuracy": round(float(accuracy_score(sub_labels, sub_preds)), 4),
                    "precision": round(float(sub_p), 4),
                    "recall": round(float(sub_r), 4),
                    "f1": round(float(sub_f1), 4),
                }

    return {
        "status": "EVALUATION_SUCCESS",
        "samples": len(labels),
        "threshold": threshold,
        "accuracy": round(acc, 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(auc, 4) if auc is not None else None,
        "confusion_matrix": cm,
        "per_attack_breakdown": per_attack,
    }


def save_reports(
    results: Dict[str, Any],
    labels: List[int],
    scores: List[float],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. JSON Report
    json_path = output_dir / "tampering_metrics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # 2. CSV Report
    csv_path = output_dir / "tampering_metrics.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Status", results.get("status")])
        writer.writerow(["Samples", results.get("samples")])
        writer.writerow(["Accuracy", results.get("accuracy")])
        writer.writerow(["Precision", results.get("precision")])
        writer.writerow(["Recall", results.get("recall")])
        writer.writerow(["F1", results.get("f1")])
        writer.writerow(["ROC_AUC", results.get("roc_auc")])
        writer.writerow([])
        writer.writerow(["Attack Type", "Samples", "Accuracy", "Precision", "Recall", "F1"])
        for atype, metrics in results.get("per_attack_breakdown", {}).items():
            writer.writerow([
                atype,
                metrics.get("samples"),
                metrics.get("accuracy"),
                metrics.get("precision"),
                metrics.get("recall"),
                metrics.get("f1"),
            ])

    # 3. Optional plot generation if matplotlib is available
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cm = results.get("confusion_matrix")
        if cm:
            plt.figure(figsize=(4, 4))
            plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
            plt.title("Confusion Matrix")
            plt.colorbar()
            plt.xticks([0, 1], ["Genuine", "Tampered"])
            plt.yticks([0, 1], ["Genuine", "Tampered"])
            for i in range(2):
                for j in range(2):
                    plt.text(j, i, str(cm[i][j]), ha="center", va="center", color="red")
            plt.tight_layout()
            plt.savefig(str(output_dir / "confusion_matrix.png"))
            plt.close()

        if len(set(labels)) > 1:
            fpr, tpr, _ = roc_curve(labels, scores)
            plt.figure(figsize=(5, 4))
            plt.plot(fpr, tpr, label=f"ROC (AUC = {results.get('roc_auc')})")
            plt.plot([0, 1], [0, 1], "k--")
            plt.xlabel("False Positive Rate")
            plt.ylabel("True Positive Rate")
            plt.title("Tampering ROC Curve")
            plt.legend(loc="lower right")
            plt.tight_layout()
            plt.savefig(str(output_dir / "roc_curve.png"))
            plt.close()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Evaluate tampering detection models and forensic pipeline")
    parser.add_argument("--predictions", default="", help="CSV containing label,score,attack_type")
    parser.add_argument("--manifest", default="", help="Manifest CSV to run online evaluation")
    parser.add_argument("--output-dir", default=str(Path(__file__).resolve().parents[1] / "reports"))
    parser.add_argument("--threshold", type=float, default=0.50)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    labels: List[int] = []
    scores: List[float] = []
    attack_types: List[str] = []

    if args.predictions and Path(args.predictions).is_file():
        with open(args.predictions, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                labels.append(int(row["label"]))
                scores.append(float(row.get("score", row.get("tampering_score", 0.0))))
                attack_types.append(row.get("attack_type", "unknown"))
    elif args.manifest and Path(args.manifest).is_file():
        from app.services.tampering_service import analyze_tampering
        with open(args.manifest, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                img_path = Path(__file__).resolve().parents[1] / row["image_path"]
                if img_path.is_file():
                    res = analyze_tampering(str(img_path))
                    labels.append(int(row["label"]))
                    scores.append(float(res.get("tampering_score", 0.0)) / 100.0)
                    attack_types.append(row.get("attack_type", "none"))

    results = evaluate_predictions(labels, scores, attack_types, threshold=args.threshold)
    save_reports(results, labels, scores, output_dir)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
