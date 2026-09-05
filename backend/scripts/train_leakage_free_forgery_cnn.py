"""
Reproducible, Leakage-Free MobileNetV2 Forgery Training Pipeline.

NVIDIA GeForce RTX 5050 Laptop GPU (sm_120, CUDA 13.0) Optimized:
- Enforces CUDA usage: fails loudly if CUDA is unavailable.
- Mixed precision training with torch.cuda.amp.autocast and GradScaler.
- Loads deterministic train and validation splits directly from dataset_split_manifest.csv.
- Strict Zero-Leakage: Group-isolated partitions guaranteed by manifest.
- Test partition remains 100% UNTOUCHED during training.
- Dynamic Class Weighting to combat genuine/tampered class imbalance.
- Saves best validation checkpoint, final checkpoint, and full training history.
"""

import os
import sys
import time
import json
import random
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

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

MANIFEST_PATH = BASE_DIR / "dataset" / "dataset_split_manifest.csv"
WEIGHTS_DIR = BASE_DIR / "app" / "models" / "weights"
WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
BEST_CHECKPOINT_PATH = WEIGHTS_DIR / "forgery_mobilenet_v2_clean.pt"
FINAL_CHECKPOINT_PATH = WEIGHTS_DIR / "forgery_mobilenet_v2_clean_final.pt"
HISTORY_PATH = WEIGHTS_DIR / "training_history.json"


def seed_everything(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class ManifestDocumentDataset(Dataset):
    def __init__(self, df: pd.DataFrame, base_dir: Path, transform=None):
        self.records = df.to_dict("records")
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
            # Fallback for transient read error: blank black image
            image = Image.new("RGB", (224, 224), color=0)

        if self.transform:
            image = self.transform(image)

        label = torch.tensor(int(row["label"]), dtype=torch.long)
        return image, label


def get_transforms():
    # Deterministic ImageNet standard normalization
    norm = T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

    train_transform = T.Compose([
        T.Resize((224, 224)),
        T.RandomHorizontalFlip(p=0.5),
        T.RandomRotation(degrees=5),
        T.ColorJitter(brightness=0.1, contrast=0.1),
        T.ToTensor(),
        norm,
    ])

    val_transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        norm,
    ])

    return train_transform, val_transform


def train_model():
    print("==========================================================")
    print("LEAKAGE-FREE FORGERY CNN TRAINING PIPELINE (RTX 5050)")
    print("==========================================================")

    # 1. Hardware Verification Gate
    if not torch.cuda.is_available():
        raise RuntimeError("FATAL: CUDA is NOT available! This training pipeline strictly forbids silent CPU fallback.")

    device = torch.device("cuda")
    gpu_name = torch.cuda.get_device_name(0)
    gpu_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    cuda_version = torch.version.cuda
    pytorch_version = torch.__version__

    print(f"[*] PyTorch Version : {pytorch_version}")
    print(f"[*] CUDA Version    : {cuda_version}")
    print(f"[*] Selected Device : {device}")
    print(f"[*] GPU Name        : {gpu_name}")
    print(f"[*] Total GPU VRAM  : {gpu_vram_gb:.2f} GB")
    print("----------------------------------------------------------")

    seed_everything(42)

    # 2. Manifest Loading & Split Verification
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}. Run scripts/audit_and_split_dataset.py first!")

    df = pd.read_csv(MANIFEST_PATH)
    train_df = df[df["split"] == "train"].reset_index(drop=True)
    val_df = df[df["split"] == "validation"].reset_index(drop=True)
    test_df = df[df["split"] == "test"].reset_index(drop=True)

    print(f"[*] Train Samples : {len(train_df)} (Genuine: {(train_df['label']==0).sum()}, Tampered: {(train_df['label']==1).sum()})")
    print(f"[*] Val Samples   : {len(val_df)} (Genuine: {(val_df['label']==0).sum()}, Tampered: {(val_df['label']==1).sum()})")
    print(f"[*] Test Samples  : {len(test_df)} [LOCKED - STRICTLY UNTOUCHED]")

    # Check zero leakage between manifest splits
    train_groups = set(train_df["group_id"])
    val_groups = set(val_df["group_id"])
    test_groups = set(test_df["group_id"])
    assert len(train_groups & val_groups) == 0, "LEAKAGE: Train & Val group overlap!"
    assert len(train_groups & test_groups) == 0, "LEAKAGE: Train & Test group overlap!"
    assert len(val_groups & test_groups) == 0, "LEAKAGE: Val & Test group overlap!"
    print("[OK] Zero-Leakage Gate Confirmed: 0 group overlap between Train, Val, and Test.")


    # 3. Class Weighting Calculation
    n_gen = (train_df["label"] == 0).sum()
    n_tam = (train_df["label"] == 1).sum()
    total_train = n_gen + n_tam
    w0 = total_train / (2.0 * max(1, n_gen))
    w1 = total_train / (2.0 * max(1, n_tam))
    class_weights = torch.tensor([w0, w1], dtype=torch.float32, device=device)
    print(f"[*] Computed Loss Class Weights: Genuine (0)={w0:.3f}, Tampered (1)={w1:.3f}")

    # 4. Datasets and DataLoaders
    train_transform, val_transform = get_transforms()
    train_dataset = ManifestDocumentDataset(train_df, BASE_DIR, transform=train_transform)
    val_dataset = ManifestDocumentDataset(val_df, BASE_DIR, transform=val_transform)

    BATCH_SIZE = 64
    NUM_WORKERS = 4
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
        pin_memory=True,
        drop_last=False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=True,
        drop_last=False,
    )

    # 5. Model Architecture: MobileNetV2 with Dropout & 2-Class Linear Head
    model = mobilenet_v2(weights=MobileNet_V2_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(128, 2),
    )
    model = model.to(device)

    # 6. Optimization, Scheduler, and Scaler
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=2
    )
    scaler = torch.cuda.amp.GradScaler()

    # 7. Training Loop with Early Stopping
    EPOCHS = 12
    best_val_loss = float("inf")
    best_epoch = 0
    patience = 4
    patience_counter = 0

    history = {
        "train_loss": [],
        "val_loss": [],
        "val_accuracy": [],
        "val_precision": [],
        "val_recall": [],
        "val_f1": [],
        "val_roc_auc": [],
        "epoch_time_sec": [],
        "peak_vram_mb": [],
    }

    print("\n[*] Starting Fine-Tuning on NVIDIA RTX 5050...")
    total_start_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        epoch_start = time.time()
        torch.cuda.reset_peak_memory_stats(device)

        # TRAIN EPOCH
        model.train()
        running_train_loss = 0.0
        train_samples = 0

        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            optimizer.zero_grad()
            with torch.cuda.amp.autocast():
                outputs = model(images)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_train_loss += loss.item() * images.size(0)
            train_samples += images.size(0)

        epoch_train_loss = running_train_loss / max(1, train_samples)

        # VALIDATION EPOCH (Zero Gradients, Eval Mode)
        model.eval()
        running_val_loss = 0.0
        val_samples = 0
        all_preds = []
        all_probs = []
        all_targets = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)

                with torch.cuda.amp.autocast():
                    outputs = model(images)
                    loss = criterion(outputs, labels)

                running_val_loss += loss.item() * images.size(0)
                val_samples += images.size(0)

                probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()
                preds = torch.argmax(outputs, dim=1).cpu().numpy()
                targets = labels.cpu().numpy()

                all_probs.extend(probs)
                all_preds.extend(preds)
                all_targets.extend(targets)

        epoch_val_loss = running_val_loss / max(1, val_samples)
        val_acc = accuracy_score(all_targets, all_preds)
        val_prec = precision_score(all_targets, all_preds, zero_division=0)
        val_rec = recall_score(all_targets, all_preds, zero_division=0)
        val_f1 = f1_score(all_targets, all_preds, zero_division=0)
        try:
            val_auc = roc_auc_score(all_targets, all_probs)
        except Exception:
            val_auc = 0.5

        scheduler.step(epoch_val_loss)

        epoch_time = time.time() - epoch_start
        peak_vram = torch.cuda.max_memory_allocated(device) / (1024 ** 2)

        history["train_loss"].append(round(epoch_train_loss, 5))
        history["val_loss"].append(round(epoch_val_loss, 5))
        history["val_accuracy"].append(round(val_acc, 5))
        history["val_precision"].append(round(val_prec, 5))
        history["val_recall"].append(round(val_rec, 5))
        history["val_f1"].append(round(val_f1, 5))
        history["val_roc_auc"].append(round(val_auc, 5))
        history["epoch_time_sec"].append(round(epoch_time, 2))
        history["peak_vram_mb"].append(round(peak_vram, 2))

        print(
            f"Epoch {epoch:02d}/{EPOCHS:02d} | "
            f"Train Loss: {epoch_train_loss:.4f} | "
            f"Val Loss: {epoch_val_loss:.4f} | "
            f"Val Acc: {val_acc:.4f} | "
            f"Val F1: {val_f1:.4f} | "
            f"Val AUC: {val_auc:.4f} | "
            f"VRAM: {peak_vram:.1f}MB | "
            f"Time: {epoch_time:.1f}s"
        )

        # Checkpoint based on Validation Loss
        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            best_epoch = epoch
            patience_counter = 0

            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": epoch_val_loss,
                "val_acc": val_acc,
                "val_f1": val_f1,
                "val_roc_auc": val_auc,
                "architecture": "MobileNetV2",
                "weights_name": "forgery_mobilenet_v2_clean.pt",
                "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
                "input_resolution": (224, 224),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            torch.save(checkpoint, BEST_CHECKPOINT_PATH)
            print(f"  --> Saved BEST checkpoint at Epoch {epoch:02d} (Val Loss: {epoch_val_loss:.4f}, F1: {val_f1:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"  [!] Early stopping triggered: validation loss did not improve for {patience} epochs.")
                break

    # Save final checkpoint and history
    torch.save(model.state_dict(), FINAL_CHECKPOINT_PATH)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    total_time = time.time() - total_start_time
    print(f"\n[OK] Training Complete in {total_time/60:.2f} minutes!")
    print(f"    Best Checkpoint: Epoch {best_epoch} saved to {BEST_CHECKPOINT_PATH}")
    print(f"    History saved to: {HISTORY_PATH}")


if __name__ == "__main__":
    train_model()
