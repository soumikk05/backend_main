"""
Phase 4: Improved Document Forgery CNN Training Pipeline.

Architecture:
- MobileNetV2 with ImageNet pretrained weights.
- Classifier head: Dropout(0.3) -> Linear(1280, 64) -> ReLU() -> Linear(64, 1) -> Sigmoid().
- Standardized input size: 128x128 (consistent across training, validation, and inference).

Training improvements:
- Dataset: dataset/forgery_ml/ (1,250 genuine + 1,250 tampered = 2,500 images).
- Loss: Binary Cross-Entropy (nn.BCELoss).
- Optimizer: AdamW(lr=1e-4, weight_decay=1e-4).
- LR Scheduler: ReduceLROnPlateau(mode='max', factor=0.5, patience=2).
- Epochs: 10 with Early Stopping (patience=4 on validation F1).
- Batch size: 32.
- Checkpoint selection criterion: BEST VALIDATION F1 (NOT accuracy!).
- Checkpoint path: app/models/weights/best_forgery_mobilenet_v2.pt (does NOT overwrite old 92% checkpoint).

Validation tracking:
- Evaluates on dataset/forgery_ml_val/ (250 genuine + 250 tampered = 500 isolated images).
- Records: train_loss, train_acc, val_loss, val_acc, precision, recall, F1, ROC-AUC.
- Generates:
  - reports/forgery_training_history.csv
  - reports/forgery_validation_metrics.json
  - reports/forgery_validation_metrics.csv
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
    confusion_matrix,
    balanced_accuracy_score,
)
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_ROOT / "reports"
WEIGHTS_DIR = BACKEND_ROOT / "app" / "models" / "weights"
CHECKPOINT_PATH = WEIGHTS_DIR / "best_forgery_mobilenet_v2.pt"

TRAIN_META_PATH = BACKEND_ROOT / "dataset" / "forgery_ml" / "metadata.csv"
VAL_META_PATH = BACKEND_ROOT / "dataset" / "forgery_ml_val" / "metadata.csv"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 1e-4
INPUT_SIZE = (128, 128)

# Standardized normalization
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]


class ForgeryDataset(Dataset):
    def __init__(self, meta_path: Path, transform=None):
        self.samples = []
        self.transform = transform
        with open(meta_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                img_path = str(BACKEND_ROOT / r["output_image"])
                label = 0.0 if r["attack_type"] == "none" else 1.0
                attack = r["attack_type"]
                doc_type = r["document_type"]
                self.samples.append((img_path, label, attack, doc_type))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label, attack, doc_type = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, torch.tensor(label, dtype=torch.float32), attack, doc_type


def build_model() -> nn.Module:
    try:
        model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    except Exception:
        model = models.mobilenet_v2(pretrained=True)

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 64),
        nn.ReLU(),
        nn.Linear(64, 1),
        nn.Sigmoid(),
    )
    return model


def train_one_epoch(model, loader, criterion, optimizer):
    model.train()
    running_loss, correct, total = 0.0, 0, 0
    for images, labels, _, _ in loader:
        images = images.to(DEVICE)
        labels = labels.to(DEVICE).unsqueeze(1)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        preds = (outputs >= 0.5).float()
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    return running_loss / max(total, 1), (correct / max(total, 1)) * 100


def evaluate(model, loader, criterion):
    model.eval()
    running_loss, total = 0.0, 0
    all_preds, all_labels, all_probs = [], [], []
    attacks_list, doctypes_list = [], []

    with torch.no_grad():
        for images, labels, attacks, doctypes in loader:
            images = images.to(DEVICE)
            labels_tensor = labels.to(DEVICE).unsqueeze(1)

            outputs = model(images)
            loss = criterion(outputs, labels_tensor)

            running_loss += loss.item() * images.size(0)
            probs = outputs.squeeze(1).cpu().numpy().tolist()
            preds = (outputs.squeeze(1) >= 0.5).long().cpu().numpy().tolist()
            lbls = labels.long().cpu().numpy().tolist()

            all_probs.extend(probs)
            all_preds.extend(preds)
            all_labels.extend(lbls)
            attacks_list.extend(attacks)
            doctypes_list.extend(doctypes)
            total += images.size(0)

    val_loss = running_loss / max(total, 1)
    acc = float(accuracy_score(all_labels, all_preds)) * 100.0
    p, r, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average="binary", zero_division=0)
    b_acc = float(balanced_accuracy_score(all_labels, all_preds)) * 100.0

    try:
        auc = float(roc_auc_score(all_labels, all_probs))
    except Exception:
        auc = 0.0

    cm = confusion_matrix(all_labels, all_preds)
    tn, fp, fn, tp = cm.ravel()
    spec = float(tn / max(1, (tn + fp)))

    return {
        "loss": val_loss,
        "acc": acc,
        "p": float(p),
        "r": float(r),
        "f1": float(f1),
        "auc": auc,
        "spec": spec,
        "b_acc": b_acc,
        "cm": cm.tolist(),
        "labels": all_labels,
        "preds": all_preds,
        "probs": all_probs,
        "attacks": attacks_list,
        "doctypes": doctypes_list,
    }


def main():
    print("=== STARTING PHASE 4: TRAINING IMPROVED FORGERY DETECTOR ===")
    print(f"Device: {DEVICE}")
    print(f"Input Resolution: {INPUT_SIZE}")

    train_transform = transforms.Compose([
        transforms.Resize(INPUT_SIZE),
        transforms.RandomHorizontalFlip(p=0.3),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.RandomRotation(degrees=2),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])

    val_transform = transforms.Compose([
        transforms.Resize(INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])

    train_dataset = ForgeryDataset(TRAIN_META_PATH, transform=train_transform)
    val_dataset = ForgeryDataset(VAL_META_PATH, transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

    print(f"Train samples: {len(train_dataset)} | Validation samples: {len(val_dataset)}")

    model = build_model().to(DEVICE)
    criterion = nn.BCELoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)

    history = []
    best_f1 = -1.0
    best_epoch = -1
    best_eval = None
    patience = 4
    no_improve = 0

    print(f"\nTraining for up to {EPOCHS} epochs (Early stopping patience: {patience}, Selection: best val_f1)...")

    for epoch in range(1, EPOCHS + 1):
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer)
        ev = evaluate(model, val_loader, criterion)
        scheduler.step(ev["f1"])

        print(
            f"Epoch [{epoch:2d}/{EPOCHS:2d}] "
            f"Train Loss: {tr_loss:.4f} Acc: {tr_acc:.1f}% | "
            f"Val Loss: {ev['loss']:.4f} Acc: {ev['acc']:.1f}% F1: {ev['f1']:.4f} "
            f"P: {ev['p']:.4f} R: {ev['r']:.4f} AUC: {ev['auc']:.4f}"
        )

        history.append({
            "epoch": epoch,
            "train_loss": round(tr_loss, 4),
            "train_accuracy": round(tr_acc, 2),
            "val_loss": round(ev["loss"], 4),
            "val_accuracy": round(ev["acc"], 2),
            "val_precision": round(ev["p"], 4),
            "val_recall": round(ev["r"], 4),
            "val_f1": round(ev["f1"], 4),
            "val_roc_auc": round(ev["auc"], 4),
        })

        if ev["f1"] > best_f1:
            best_f1 = ev["f1"]
            best_epoch = epoch
            best_eval = ev
            no_improve = 0
            torch.save(model.state_dict(), CHECKPOINT_PATH)
            print(f"  --> Saved new best checkpoint to {CHECKPOINT_PATH.name} (Val F1: {best_f1:.4f})")
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"Early stopping triggered at epoch {epoch} (no improvement in {patience} epochs).")
                break

    print(f"\nTraining completed. Best Model Epoch: {best_epoch} with Val F1: {best_f1:.4f}")

    # Write training history CSV
    hist_path = REPORTS_DIR / "forgery_training_history.csv"
    with open(hist_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "epoch", "train_loss", "train_accuracy", "val_loss",
            "val_accuracy", "val_precision", "val_recall", "val_f1", "val_roc_auc"
        ])
        writer.writeheader()
        writer.writerows(history)
    print(f"Saved training history to: {hist_path}")

    # Load best weights for detailed validation reporting
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=DEVICE))
    final_eval = evaluate(model, val_loader, criterion)

    # Per-attack evaluation
    attack_metrics = {}
    unique_attacks = sorted(list(set(final_eval["attacks"])))
    for at in unique_attacks:
        if at == "none":
            continue
        # Compare this attack against all genuine samples (at == 'none')
        idx_attack = [i for i, a in enumerate(final_eval["attacks"]) if a == at or a == "none"]
        sub_labels = [final_eval["labels"][i] for i in idx_attack]
        sub_preds = [final_eval["preds"][i] for i in idx_attack]
        sub_probs = [final_eval["probs"][i] for i in idx_attack]

        sp, sr, sf1, _ = precision_recall_fscore_support(sub_labels, sub_preds, average="binary", zero_division=0)
        s_acc = float(accuracy_score(sub_labels, sub_preds)) * 100.0
        try:
            s_auc = float(roc_auc_score(sub_labels, sub_probs))
        except Exception:
            s_auc = 0.0

        attack_metrics[at] = {
            "samples": len([i for i in idx_attack if final_eval["labels"][i] == 1]),
            "accuracy": round(s_acc, 2),
            "precision": round(float(sp), 4),
            "recall": round(float(sr), 4),
            "f1": round(float(sf1), 4),
            "roc_auc": round(s_auc, 4),
        }

    # Consolidated JSON report
    val_report_json = {
        "status": "VALIDATION_SUCCESS",
        "checkpoint": str(CHECKPOINT_PATH.name),
        "best_epoch": best_epoch,
        "selection_criterion": "val_f1",
        "total_validation_samples": len(val_dataset),
        "genuine_samples": sum(1 for l in final_eval["labels"] if l == 0),
        "tampered_samples": sum(1 for l in final_eval["labels"] if l == 1),
        "overall_metrics": {
            "accuracy": round(final_eval["acc"], 2),
            "precision": round(final_eval["p"], 4),
            "recall": round(final_eval["r"], 4),
            "f1": round(final_eval["f1"], 4),
            "roc_auc": round(final_eval["auc"], 4),
            "specificity": round(final_eval["spec"], 4),
            "balanced_accuracy": round(final_eval["b_acc"], 2),
            "confusion_matrix": final_eval["cm"],
        },
        "per_attack_metrics": attack_metrics,
    }

    json_out = REPORTS_DIR / "forgery_validation_metrics.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(val_report_json, f, indent=2)
    print(f"Saved validation metrics JSON to: {json_out}")

    # CSV report
    csv_out = REPORTS_DIR / "forgery_validation_metrics.csv"
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Status", "VALIDATION_SUCCESS"])
        writer.writerow(["Best_Epoch", best_epoch])
        writer.writerow(["Selection_Criterion", "val_f1"])
        writer.writerow(["Total_Samples", len(val_dataset)])
        writer.writerow(["Accuracy", round(final_eval["acc"], 2)])
        writer.writerow(["Precision", round(final_eval["p"], 4)])
        writer.writerow(["Recall", round(final_eval["r"], 4)])
        writer.writerow(["F1", round(final_eval["f1"], 4)])
        writer.writerow(["ROC_AUC", round(final_eval["auc"], 4)])
        writer.writerow(["Specificity", round(final_eval["spec"], 4)])
        writer.writerow(["Balanced_Accuracy", round(final_eval["b_acc"], 2)])
        writer.writerow([])
        writer.writerow(["Attack_Type", "Tampered_Samples", "Accuracy", "Precision", "Recall", "F1", "ROC_AUC"])
        for at, m in attack_metrics.items():
            writer.writerow([at, m["samples"], m["accuracy"], m["precision"], m["recall"], m["f1"], m["roc_auc"]])
    print(f"Saved validation metrics CSV to: {csv_out}")


if __name__ == "__main__":
    main()
