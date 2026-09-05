"""
Controlled Training Script for High-Resolution Localized Forgery Detection Stream (V2).

STRICT SPLIT RULES:
- Trains ONLY on patches from dataset/train_patches_manifest.csv (derived strictly from train split).
- Never accesses or modifies the test set.
- Validates on validation split documents using blind unannotated candidate patch extraction.
- Saves locked local checkpoint to app/models/weights/forgery_local_v2.pt.
- Exports training history to app/models/weights/training_history_v2.json.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

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
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

BASE_DIR = Path(__file__).resolve().parent.parent
PATCH_MANIFEST = BASE_DIR / "dataset" / "train_patches_manifest.csv"
SPLIT_MANIFEST = BASE_DIR / "dataset" / "dataset_split_manifest.csv"
WEIGHTS_DIR = BASE_DIR / "app" / "models" / "weights"
LOCAL_WEIGHTS_PATH = WEIGHTS_DIR / "forgery_local_v2.pt"
HISTORY_PATH = WEIGHTS_DIR / "training_history_v2.json"

WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# Hardware setup
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class PatchDataset(Dataset):
    def __init__(self, records: List[Dict], base_dir: Path, transform=None):
        self.records = records
        self.base_dir = base_dir
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        row = self.records[idx]
        img_path = self.base_dir / row["patch_path"]
        try:
            with Image.open(img_path) as img:
                image = img.convert("RGB")
        except Exception:
            image = Image.new("RGB", (224, 224), color=0)

        if self.transform:
            image = self.transform(image)

        label = torch.tensor(int(row["label"]), dtype=torch.long)
        return image, label


class BlindDocValidationDataset(Dataset):
    """
    Extracts a 3x3 multi-scale high-resolution grid of patches from any document
    WITHOUT knowing where the forgery is located.
    """
    def __init__(self, records: List[Dict], base_dir: Path, transform=None):
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
                w, h = img.size
                # Multi-scale grid patches (3x3 grid)
                patches = []
                gw, gh = w // 3, h // 3
                for r in range(3):
                    for c in range(3):
                        box = (c * gw, r * gh, min(w, (c + 1) * gw), min(h, (r + 1) * gh))
                        p_img = img.crop(box)
                        if self.transform:
                            p_img = self.transform(p_img)
                        patches.append(p_img)
                # Stack to tensor [9, 3, 224, 224]
                patch_tensor = torch.stack(patches, dim=0)
        except Exception:
            # Fallback black patches
            patch_tensor = torch.zeros((9, 3, 224, 224), dtype=torch.float32)

        label = torch.tensor(int(row["label"]), dtype=torch.long)
        return patch_tensor, label, row["source"], row["tampering_type"]


def build_local_model() -> nn.Module:
    model = mobilenet_v2(weights=MobileNet_V2_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 128),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.2),
        nn.Linear(128, 2),
    )
    return model


def main():
    print("==========================================================")
    print("STARTING CONTROLLED LOCALIZED FORGERY MODEL TRAINING (V2)")
    print("==========================================================")
    print(f"[*] Training Device: {DEVICE} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    torch.manual_seed(42)
    np.random.seed(42)

    # 1. Load Patch Training Manifest
    patch_df = pd.read_csv(PATCH_MANIFEST)
    train_records = patch_df.to_dict("records")
    print(f"[*] Total training patches: {len(train_records)}")
    n_gen = (patch_df['label'] == 0).sum()
    n_tam = (patch_df['label'] == 1).sum()
    print(f"    Genuine: {n_gen}, Tampered: {n_tam}")

    # Calculate class weighting
    weight_gen = len(patch_df) / (2.0 * n_gen)
    weight_tam = len(patch_df) / (2.0 * n_tam)
    class_weights = torch.tensor([weight_gen, weight_tam], dtype=torch.float32).to(DEVICE)
    print(f"[*] Loss class weights: [Genuine: {weight_gen:.3f}, Tampered: {weight_tam:.3f}]")

    # Transforms
    norm = T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    train_transform = T.Compose([
        T.Resize((224, 224)),
        T.RandomRotation(degrees=(-5, 5)),
        T.ColorJitter(brightness=0.1, contrast=0.1),
        T.ToTensor(),
        norm,
    ])
    val_transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        norm,
    ])

    train_dataset = PatchDataset(train_records, BASE_DIR, transform=train_transform)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=0)

    # 2. Load Validation Set for Monitoring (Validation Split ONLY)
    split_df = pd.read_csv(SPLIT_MANIFEST)
    val_df = split_df[split_df['split'] == 'validation'].reset_index(drop=True)
    # Focus on MIDV + sample of other validation docs for fast epoch monitoring
    midv_val = val_df[val_df['source'] == 'MIDV_FCDV_BENCHMARK']
    other_val = val_df[val_df['source'] != 'MIDV_FCDV_BENCHMARK'].sample(n=300, random_state=42)
    eval_val_df = pd.concat([midv_val, other_val]).reset_index(drop=True)
    val_records = eval_val_df.to_dict("records")

    print(f"[*] Validation monitoring subset: {len(val_records)} documents (MIDV: {len(midv_val)}, Non-MIDV: {len(other_val)})")
    val_dataset = BlindDocValidationDataset(val_records, BASE_DIR, transform=val_transform)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False, num_workers=0)

    # 3. Model, Optimizer, Loss
    model = build_local_model().to(DEVICE)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1.5e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=2)
    scaler = torch.amp.GradScaler('cuda')

    best_val_score = -1.0
    best_epoch = -1
    history = []
    patience = 4
    epochs_no_improve = 0

    max_epochs = 8
    print(f"\n[*] Starting training loop for up to {max_epochs} epochs...")

    for epoch in range(1, max_epochs + 1):
        model.train()
        total_loss = 0.0
        correct_train = 0
        total_train = 0
        start_time = time.time()

        for imgs, labels in train_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()

            with torch.amp.autocast('cuda'):
                outputs = model(imgs)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item() * imgs.size(0)
            preds = torch.argmax(outputs, dim=1)
            correct_train += (preds == labels).sum().item()
            total_train += labels.size(0)

        epoch_train_loss = total_loss / total_train
        epoch_train_acc = correct_train / total_train

        # Validation Phase (Blind Grid Patch Evaluation)
        model.eval()
        all_preds = []
        all_targets = []
        all_sources = []
        all_tampers = []

        with torch.no_grad():
            for patch_tensors, labels, sources, tampers in val_loader:
                # patch_tensors: [B, 9, 3, 224, 224]
                B, N, C, H, W = patch_tensors.shape
                flat_patches = patch_tensors.view(B * N, C, H, W).to(DEVICE)

                with torch.amp.autocast('cuda'):
                    out = model(flat_patches)
                probs = torch.softmax(out, dim=1)[:, 1].view(B, N)
                # Document prediction = max patch probability
                doc_probs = torch.max(probs, dim=1).values.cpu().numpy()
                doc_preds = (doc_probs >= 0.50).astype(int)

                all_preds.extend(doc_preds)
                all_targets.extend(labels.numpy())
                all_sources.extend(sources)
                all_tampers.extend(tampers)

        y_true = np.array(all_targets)
        y_pred = np.array(all_preds)

        val_acc = float(accuracy_score(y_true, y_pred))
        val_f1 = float(f1_score(y_true, y_pred, zero_division=0))

        # Check MIDV tampered recall
        midv_mask = np.array([s == "MIDV_FCDV_BENCHMARK" for s in all_sources])
        midv_tam_mask = midv_mask & (y_true == 1)
        midv_tam_recall = float(recall_score(y_true[midv_tam_mask], y_pred[midv_tam_mask], zero_division=0)) if midv_tam_mask.sum() > 0 else 0.0

        # Check genuine accuracy (to ensure low false alarms)
        gen_mask = (y_true == 0)
        gen_acc = float(accuracy_score(y_true[gen_mask], y_pred[gen_mask])) if gen_mask.sum() > 0 else 0.0

        epoch_time = time.time() - start_time
        # Optimization metric: balanced combination of MIDV recall and Genuine accuracy
        selection_score = (0.60 * midv_tam_recall) + (0.40 * gen_acc)

        print(f"Epoch {epoch:2d}/{max_epochs} ({epoch_time:.1f}s) | Train Loss: {epoch_train_loss:.4f} Acc: {epoch_train_acc*100:.2f}% | "
              f"Val Acc: {val_acc*100:.2f}% F1: {val_f1:.4f} | "
              f"MIDV Tam Recall: {midv_tam_recall*100:.2f}% | Gen Acc: {gen_acc*100:.2f}% | Score: {selection_score:.4f}", flush=True)

        history.append({
            "epoch": epoch,
            "train_loss": round(epoch_train_loss, 4),
            "train_acc": round(epoch_train_acc, 4),
            "val_acc": round(val_acc, 4),
            "val_f1": round(val_f1, 4),
            "midv_tam_recall": round(midv_tam_recall, 4),
            "genuine_acc": round(gen_acc, 4),
            "selection_score": round(selection_score, 4),
            "epoch_time_seconds": round(epoch_time, 1),
        })

        scheduler.step(selection_score)

        if selection_score > best_val_score:
            best_val_score = selection_score
            best_epoch = epoch
            epochs_no_improve = 0
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_score": best_val_score,
                "midv_tam_recall": midv_tam_recall,
                "genuine_acc": gen_acc,
                "arch": "mobilenet_v2_local_patch",
            }, LOCAL_WEIGHTS_PATH)
            print(f"  --> [SAVED] Best checkpoint at epoch {epoch} (Score: {best_val_score:.4f}, MIDV Recall: {midv_tam_recall*100:.2f}%) to {LOCAL_WEIGHTS_PATH}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"[*] Early stopping triggered after {epoch} epochs.")
                break

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    print(f"\n[OK] Local patch training completed. Best Epoch: {best_epoch} (Score: {best_val_score:.4f})")
    print(f"Weights saved to: {LOCAL_WEIGHTS_PATH}")
    print(f"History saved to: {HISTORY_PATH}")


if __name__ == '__main__':
    main()
