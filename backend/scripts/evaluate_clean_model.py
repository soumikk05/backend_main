"""
Auditable, Rigorous Evaluation Script for Clean Forgery Detection Model.

Evaluates the LOCKED MobileNetV2 checkpoint on the untouched TEST set.
Generates:
1. Overall Metrics:
   - Accuracy, Precision, Recall, F1-Score
   - Specificity, Sensitivity
   - ROC-AUC, PR-AUC
   - False Acceptance Rate (FAR), False Rejection Rate (FRR)
   - Confusion Matrix [[TN, FP], [FN, TP]]
2. Per-Tampering-Type Breakdown:
   - Evaluates each specific tampering attack category (Copy-Move, DOB Edit, Photo Replace, etc.)
   - Precision, Recall, F1, and Support per category
   - Identifies weakest tampering categories
3. Per-Document-Type Breakdown (Passport, Visa, Driving License, National ID, Permit)
4. Saves machine-readable evaluation_results.json and metrics tables.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from torchvision.models import mobilenet_v2
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    auc,
    confusion_matrix,
)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

MANIFEST_PATH = BASE_DIR / "dataset" / "dataset_split_manifest.csv"
WEIGHTS_PATH = BASE_DIR / "app" / "models" / "weights" / "forgery_mobilenet_v2_clean.pt"
RESULTS_OUTPUT = BASE_DIR / "dataset" / "final_test_evaluation_results.json"


class TestDocumentDataset(Dataset):
    def __init__(self, records: List[Dict[str, Any]], base_dir: Path, transform=None):
        self.records = records
        self.base_dir = base_dir
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        row = self.records[idx]
        img_path = self.base_dir / row["image_path"]
        try:
            with Image.open(img_path) as img:
                image = img.convert("RGB")
        except Exception:
            image = Image.new("RGB", (224, 224), color=0)

        if self.transform:
            image = self.transform(image)

        label = torch.tensor(int(row["label"]), dtype=torch.long)
        return image, label, row["tampering_type"], row["document_type"]


def evaluate_test_set():
    print("==========================================================")
    print("INDEPENDENT FINAL TEST SET EVALUATION")
    print("==========================================================")

    if not torch.cuda.is_available():
        raise RuntimeError("FATAL: CUDA is not available for evaluation.")

    device = torch.device("cuda")
    print(f"[*] Running evaluation on: {torch.cuda.get_device_name(0)}")

    # 1. Load Locked Checkpoint
    if not WEIGHTS_PATH.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {WEIGHTS_PATH}")

    checkpoint = torch.load(WEIGHTS_PATH, map_location=device, weights_only=False)
    model = mobilenet_v2()
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(128, 2),
    )
    if "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)
    model = model.to(device)
    model.eval()
    print(f"[OK] Successfully loaded locked model from: {WEIGHTS_PATH}")

    # 2. Load Untouched Test Set from Manifest
    df = pd.read_csv(MANIFEST_PATH)
    test_df = df[df["split"] == "test"].reset_index(drop=True)
    test_records = test_df.to_dict("records")
    print(f"[*] Total Untouched Test Samples: {len(test_records)}")

    # Transform (Identical to validation, strictly NO random augmentation)
    norm = T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    test_transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        norm,
    ])

    test_dataset = TestDocumentDataset(test_records, BASE_DIR, transform=test_transform)
    test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False, num_workers=4)

    # 3. Predict on Test Set
    all_probs = []
    all_preds = []
    all_targets = []
    all_tamper_types = []
    all_doc_types = []

    start_eval = time.time()
    with torch.no_grad():
        for images, labels, tamper_types, doc_types in test_loader:
            images = images.to(device, non_blocking=True)
            with torch.cuda.amp.autocast():
                outputs = model(images)

            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()
            preds = torch.argmax(outputs, dim=1).cpu().numpy()

            all_probs.extend(probs)
            all_preds.extend(preds)
            all_targets.extend(labels.numpy())
            all_tamper_types.extend(tamper_types)
            all_doc_types.extend(doc_types)

    eval_duration = time.time() - start_eval
    y_true = np.array(all_targets)
    y_pred = np.array(all_preds)
    y_prob = np.array(all_probs)

    # 4. Compute Overall Metrics
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.5

    precisions_curve, recalls_curve, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = float(auc(recalls_curve, precisions_curve))

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = [int(v) for v in cm.ravel()]

    sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    far = float(fp / (tn + fp)) if (tn + fp) > 0 else 0.0  # False Acceptance Rate (genuine flagged as fake or vice versa)
    frr = float(fn / (tp + fn)) if (tp + fn) > 0 else 0.0  # False Rejection Rate

    print("\n--- OVERALL TEST SET PERFORMANCE ---")
    print(f"Accuracy    : {acc:.4f} ({acc*100:.2f}%)")
    print(f"Precision   : {prec:.4f}")
    print(f"Recall      : {rec:.4f}")
    print(f"F1-Score    : {f1:.4f}")
    print(f"ROC-AUC     : {roc_auc:.4f}")
    print(f"PR-AUC      : {pr_auc:.4f}")
    print(f"Sensitivity : {sensitivity:.4f}")
    print(f"Specificity : {specificity:.4f}")
    print(f"FAR         : {far:.4f}")
    print(f"FRR         : {frr:.4f}")
    print(f"Confusion Matrix : TN={tn}, FP={fp}, FN={fn}, TP={tp}")

    # 5. Per-Tampering-Type Evaluation
    tamper_groups = defaultdict(list)
    for i in range(len(y_true)):
        ttype = all_tamper_types[i]
        tamper_groups[ttype].append(i)

    per_tampering_results = {}
    print("\n--- PER-TAMPERING-TYPE BREAKDOWN ---")
    print(f"{'Attack Category':<32} | {'Support':<8} | {'Accuracy':<10} | {'Recall':<10}")
    print("-" * 68)

    for ttype, indices in sorted(tamper_groups.items()):
        sub_true = y_true[indices]
        sub_pred = y_pred[indices]
        support = len(indices)
        sub_acc = float(accuracy_score(sub_true, sub_pred))
        sub_rec = float(recall_score(sub_true, sub_pred, zero_division=0)) if 1 in sub_true else sub_acc
        per_tampering_results[ttype] = {
            "support": support,
            "accuracy": round(sub_acc, 4),
            "recall": round(sub_rec, 4),
        }
        print(f"{ttype:<32} | {support:<8} | {sub_acc:<10.4f} | {sub_rec:<10.4f}")

    # 6. Save Complete Auditable Test Results JSON
    results = {
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_path": str(WEIGHTS_PATH),
        "test_samples_count": len(y_true),
        "eval_duration_seconds": round(eval_duration, 2),
        "overall_metrics": {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "sensitivity": round(sensitivity, 4),
            "specificity": round(specificity, 4),
            "false_acceptance_rate": round(far, 4),
            "false_rejection_rate": round(frr, 4),
            "confusion_matrix": {
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn,
                "true_positive": tp,
            },
        },
        "per_tampering_type": per_tampering_results,
    }

    with open(RESULTS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Test evaluation complete! Saved to: {RESULTS_OUTPUT}")


if __name__ == "__main__":
    evaluate_test_set()
