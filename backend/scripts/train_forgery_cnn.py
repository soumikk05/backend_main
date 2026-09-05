"""
Training and Fine-Tuning Script for Document Forgery CNN (MobileNetV2).

Loads REAL genuine/tampered document images via app.tampering.dataset_loader
(the existing dataset infrastructure, previously unused by this script).

If dataset/tampered/** is empty or sparse, automatically generates additional
synthetic tampering examples FROM the real genuine images (splice, copy-move,
localized blur, localized noise, recompression ghosting) — never from
synthetic random noise arrays. This means the model always learns from real
document texture/structure, even before you've built a large tampered set.

Expected folder layout under --data_root (default: dataset/), matching
app/tampering/dataset_loader.py's CLASS_FOLDERS exactly:
    dataset/genuine/passport/*.jpg
    dataset/genuine/visa/*.jpg
    dataset/genuine/id/*.jpg
    dataset/genuine/license/*.jpg
    dataset/tampered/photo_swap/*.jpg      (optional — real tampered examples if you have them)
    dataset/tampered/text_edit/*.jpg
    dataset/tampered/dob_edit/*.jpg
    dataset/tampered/number_edit/*.jpg
    dataset/tampered/stamp/*.jpg
    dataset/tampered/copy_move/*.jpg

Usage:
    python scripts/train_forgery_cnn.py --epochs 15 --batch_size 16 --data_root dataset
"""

import os
import sys
import argparse
import random
from pathlib import Path
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image, ImageFilter

# Make app/ importable when run as `python scripts/train_forgery_cnn.py` from backend/
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.tampering.dataset_loader import load_tampering_dataset  # noqa: E402

WEIGHTS_DIR = BASE_DIR / "app" / "models" / "weights"
MODEL_SAVE_PATH = WEIGHTS_DIR / "forgery_mobilenet_v2.pt"

MIN_GENUINE_IMAGES = 10  # below this, synthetic tampering has too little real variety to learn from


# ---------------------------------------------------------------------------
# Synthetic tampering operations applied to REAL images (not random noise)
# ---------------------------------------------------------------------------

def _splice(img: Image.Image, donor: Image.Image) -> Image.Image:
    """Paste a patch from a different real genuine image — mimics photo/region replacement."""
    img = img.copy()
    w, h = img.size
    patch_w, patch_h = max(16, w // 4), max(16, h // 4)
    donor_resized = donor.resize((patch_w, patch_h))
    x = random.randint(0, max(0, w - patch_w))
    y = random.randint(0, max(0, h - patch_h))
    img.paste(donor_resized, (x, y))
    return img


def _copy_move(img: Image.Image) -> Image.Image:
    """Copy a real patch from elsewhere in the SAME image and paste it — classic copy-move forgery."""
    img = img.copy()
    w, h = img.size
    patch_w, patch_h = max(12, w // 5), max(12, h // 5)
    sx, sy = random.randint(0, max(0, w - patch_w)), random.randint(0, max(0, h - patch_h))
    patch = img.crop((sx, sy, sx + patch_w, sy + patch_h))
    tx, ty = random.randint(0, max(0, w - patch_w)), random.randint(0, max(0, h - patch_h))
    img.paste(patch, (tx, ty))
    return img


def _localized_blur(img: Image.Image) -> Image.Image:
    """Blur a region — mimics covering up an edited area."""
    img = img.copy()
    w, h = img.size
    bw, bh = max(16, w // 3), max(16, h // 3)
    x, y = random.randint(0, max(0, w - bw)), random.randint(0, max(0, h - bh))
    region = img.crop((x, y, x + bw, y + bh)).filter(ImageFilter.GaussianBlur(radius=3))
    img.paste(region, (x, y))
    return img


def _localized_noise(img: Image.Image) -> Image.Image:
    """Inject noise into one region only — full-image noise is unrealistic for real tampering."""
    arr = np.array(img).astype(np.int16)
    h, w = arr.shape[:2]
    bw, bh = max(16, w // 3), max(16, h // 3)
    x, y = random.randint(0, max(0, w - bw)), random.randint(0, max(0, h - bh))
    noise = np.random.normal(0, 20, (bh, bw, 3)).astype(np.int16)
    arr[y:y + bh, x:x + bw] = np.clip(arr[y:y + bh, x:x + bw] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def _recompression_ghost(img: Image.Image) -> Image.Image:
    """Double-JPEG-compress a region at a different quality — classic recompression forgery signature."""
    import io
    img = img.copy()
    w, h = img.size
    bw, bh = max(16, w // 3), max(16, h // 3)
    x, y = random.randint(0, max(0, w - bw)), random.randint(0, max(0, h - bh))
    region = img.crop((x, y, x + bw, y + bh))
    buf = io.BytesIO()
    region.save(buf, "JPEG", quality=random.choice([30, 40, 95]))
    buf.seek(0)
    img.paste(Image.open(buf), (x, y))
    return img


TAMPER_OPS = [_copy_move, _localized_blur, _localized_noise, _recompression_ghost]  # ops needing only 1 image
TAMPER_OPS_NEEDS_DONOR = [_splice]  # ops needing a second real image


class RealDocumentTamperingDataset(Dataset):
    """
    Wraps real genuine + real tampered image paths.
    - Real tampered paths are loaded as-is (label 1).
    - Genuine paths are split: some loaded as-is (label 0), some have a synthetic
      tampering op applied on-the-fly (label 1) using REAL image content as source.
    Synthetic ops are re-randomized every epoch (acts as data augmentation).
    """

    def __init__(self, genuine_paths: List[str], real_tampered_paths: List[str],
                 target_synthetic_tampered: int, transform=None):
        self.genuine_paths = genuine_paths
        self.real_tampered_paths = real_tampered_paths
        self.transform = transform

        n_genuine_clean = max(len(genuine_paths) - target_synthetic_tampered, len(genuine_paths) // 2)
        self.clean_indices = list(range(min(n_genuine_clean, len(genuine_paths))))

        self.samples: List[Tuple[str, int, bool]] = []
        for i in self.clean_indices:
            self.samples.append((genuine_paths[i], 0, False))
        for p in real_tampered_paths:
            self.samples.append((p, 1, False))
        for _ in range(target_synthetic_tampered):
            src = random.choice(genuine_paths)
            self.samples.append((src, 1, True))  # True = apply synthetic op at load time

        random.shuffle(self.samples)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label, needs_synthetic = self.samples[idx]
        img = Image.open(path).convert("RGB")

        if needs_synthetic:
            op = random.choice(TAMPER_OPS + TAMPER_OPS_NEEDS_DONOR)
            if op in TAMPER_OPS_NEEDS_DONOR:
                donor_path = random.choice(self.genuine_paths)
                donor = Image.open(donor_path).convert("RGB")
                img = op(img, donor)
            else:
                img = op(img)

        if self.transform:
            img = self.transform(img)

        return img, torch.tensor(float(label), dtype=torch.float32)


def build_model() -> nn.Module:
    """Same architecture as before — required for compatibility with cnn_forgery_service.py."""
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


def run_epoch(model, dataloader, device, optimizer=None, criterion=None) -> Tuple[float, float]:
    """Runs one epoch. Trains if optimizer is provided, otherwise evaluates only."""
    is_train = optimizer is not None
    model.train() if is_train else model.eval()

    running_loss, correct, total = 0.0, 0, 0
    context = torch.enable_grad() if is_train else torch.no_grad()

    with context:
        for images, labels in dataloader:
            images = images.to(device)
            labels = labels.to(device).unsqueeze(1)

            if is_train:
                optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            if is_train:
                loss.backward()
                optimizer.step()

            running_loss += loss.item() * images.size(0)
            preds = (outputs >= 0.5).float()
            correct += (preds == labels).sum().item()
            total += labels.size(0)

    return running_loss / max(total, 1), (correct / max(total, 1)) * 100


def train_forgery_model(data_root: str = "dataset", epochs: int = 15, batch_size: int = 16, lr: float = 1e-4, max_samples: int = 0, device_str: str = "auto"):
    print("Initializing MobileNetV2 for document forgery classification...")
    os.makedirs(WEIGHTS_DIR, exist_ok=True)

    splits = load_tampering_dataset(root=data_root)
    genuine_train = [p for p, lbl in splits["train"] if lbl == 0]
    tampered_train = [p for p, lbl in splits["train"] if lbl == 1]
    genuine_val = [p for p, lbl in splits["validation"] if lbl == 0]
    tampered_val = [p for p, lbl in splits["validation"] if lbl == 1]

    if max_samples > 0:
        genuine_train = genuine_train[:max_samples]
        tampered_train = tampered_train[:max_samples]
        genuine_val = genuine_val[:max(1, max_samples // 4)]
        tampered_val = tampered_val[:max(1, max_samples // 4)]

    total_genuine = len(genuine_train) + len(genuine_val)
    if total_genuine < MIN_GENUINE_IMAGES:
        print(
            f"\nERROR: Found only {total_genuine} genuine document image(s) under "
            f"'{data_root}/genuine/'. Need at least {MIN_GENUINE_IMAGES} to train anything meaningful.\n"
            f"Populate these folders with real document images before training "
            f"(e.g. your MIDV-500 extraction):\n"
            f"  {data_root}/genuine/passport/\n"
            f"  {data_root}/genuine/visa/\n"
            f"  {data_root}/genuine/id/\n"
            f"  {data_root}/genuine/license/\n"
            f"Real tampered examples in {data_root}/tampered/... are optional — "
            f"this script generates synthetic tampering from your real genuine images automatically.\n"
        )
        sys.exit(1)

    print(f"Found {len(genuine_train)} genuine (train) / {len(genuine_val)} genuine (val)")
    print(f"Found {len(tampered_train)} real tampered (train) / {len(tampered_val)} real tampered (val)")

    train_synth_target = max(0, len(genuine_train) - len(tampered_train))
    val_synth_target = max(0, len(genuine_val) - len(tampered_val))
    print(f"Generating {train_synth_target} synthetic-tampered (train) / {val_synth_target} synthetic-tampered (val) from real images")

    train_transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.RandomRotation(3),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_dataset = RealDocumentTamperingDataset(genuine_train, tampered_train, train_synth_target, transform=train_transform)
    val_dataset = RealDocumentTamperingDataset(genuine_val, tampered_val, val_synth_target, transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False) if len(val_dataset) > 0 else None

    model = build_model()
    device = torch.device("cpu")
    if device_str == "cuda":
        device = torch.device("cuda")
    elif device_str == "auto" and torch.cuda.is_available():
        try:
            test_conv = nn.Conv2d(1, 1, 1).cuda()
            _ = test_conv(torch.randn(1, 1, 4, 4, device="cuda"))
            device = torch.device("cuda")
        except Exception:
            device = torch.device("cpu")
    model.to(device)

    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    print(f"Training on {device} for {epochs} epoch(s)... ({len(train_dataset)} train samples, {len(val_dataset)} val samples)")
    best_val_acc = -1.0
    for epoch in range(epochs):
        train_loss, train_acc = run_epoch(model, train_loader, device, optimizer=optimizer, criterion=criterion)

        if val_loader is not None:
            val_loss, val_acc = run_epoch(model, val_loader, device, optimizer=None, criterion=criterion)
            print(f"  Epoch [{epoch+1}/{epochs}] — Train Loss: {train_loss:.4f} Acc: {train_acc:.1f}% | Val Loss: {val_loss:.4f} Acc: {val_acc:.1f}%")
            if val_acc >= best_val_acc:
                best_val_acc = val_acc
                torch.save(model.state_dict(), MODEL_SAVE_PATH)
        else:
            print(f"  Epoch [{epoch+1}/{epochs}] — Train Loss: {train_loss:.4f} Acc: {train_acc:.1f}% | (no validation set)")
            torch.save(model.state_dict(), MODEL_SAVE_PATH)

    print(f"Successfully saved best model weights to: {MODEL_SAVE_PATH}" + (f" (best val acc: {best_val_acc:.1f}%)" if val_loader is not None else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train MobileNetV2 Document Forgery Classifier on real document images")
    parser.add_argument("--data_root", type=str, default="dataset", help="Root folder containing genuine/ and tampered/ subfolders")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--max_samples", type=int, default=0, help="Max train samples per class (0 for all)")
    parser.add_argument("--device", type=str, default="auto", help="Device ('cpu', 'cuda', 'auto')")
    args = parser.parse_args()
    train_forgery_model(data_root=args.data_root, epochs=args.epochs, batch_size=args.batch_size, max_samples=args.max_samples, device_str=args.device)