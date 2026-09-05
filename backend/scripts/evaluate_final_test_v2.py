"""
Final Locked Evaluation of Dual-Stream Forgery Pipeline (V2) on the UNTOUCHED TEST SET.

STRICT RULES:
- Evaluates the LOCKED V2 pipeline: Global V1 (0.60) + Local V2 (0.40) at threshold 0.40.
- Operates on the 7,819 untouched test samples from dataset_split_manifest.csv.
- NO hyperparameter tuning or threshold adjustment allowed.
- Outputs dataset/final_test_evaluation_v2.json.
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
from torchvision.models import mobilenet_v2
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "dataset" / "dataset_split_manifest.csv"
GLOBAL_WEIGHTS_PATH = BASE_DIR / "app" / "models" / "weights" / "forgery_global_v1.pt"
LOCAL_WEIGHTS_PATH = BASE_DIR / "app" / "models" / "weights" / "forgery_local_v2.pt"
FUSION_WEIGHTS_PATH = BASE_DIR / "app" / "models" / "weights" / "forgery_fusion_v2.pt"
TEST_RESULTS_OUTPUT = BASE_DIR / "dataset" / "final_test_evaluation_v2.json"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class DualStreamTestDataset(Dataset):
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
                img_rgb = img.convert("RGB")
                w, h = img_rgb.size

                global_img = self.transform(img_rgb) if self.transform else T.ToTensor()(img_rgb)

                # Blind 3x3 high-resolution grid patches
                patches = []
                gw, gh = w // 3, h // 3
                for r in range(3):
                    for c in range(3):
                        box = (c * gw, r * gh, min(w, (c + 1) * gw), min(h, (r + 1) * gh))
                        p_crop = img_rgb.crop(box)
                        if self.transform:
                            p_crop = self.transform(p_crop)
                        patches.append(p_crop)

                patch_tensor = torch.stack(patches, dim=0) # [9, 3, 224, 224]
        except Exception:
            global_img = torch.zeros((3, 224, 224), dtype=torch.float32)
            patch_tensor = torch.zeros((9, 3, 224, 224), dtype=torch.float32)

        label = int(row["label"])
        return global_img, patch_tensor, label, row["source"], row["tampering_type"], row["document_type"]


def load_model(weights_path: Path) -> nn.Module:
    model = mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(128, 2),
    )
    checkpoint = torch.load(weights_path, map_location=DEVICE, weights_only=False)
    if "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)
    model.to(DEVICE)
    model.eval()
    return model


def main():
    print("==========================================================")
    print("LOCKED FINAL EVALUATION ON UNTOUCHED TEST SET (V2)")
    print("==========================================================")
    print(f"[*] Device: {DEVICE}")

    # Load Fusion Artifact
    fusion_cfg = torch.load(FUSION_WEIGHTS_PATH, map_location="cpu")
    alpha_global = fusion_cfg["alpha_global"]
    alpha_local = fusion_cfg["alpha_local"]
    threshold = fusion_cfg["decision_threshold"]

    print(f"[*] Locked Fusion Config: Global={alpha_global:.2f}, Local={alpha_local:.2f}, Threshold={threshold:.2f}")

    global_model = load_model(GLOBAL_WEIGHTS_PATH)
    local_model = load_model(LOCAL_WEIGHTS_PATH)

    df = pd.read_csv(MANIFEST_PATH)
    test_df = df[df['split'] == 'test'].reset_index(drop=True)
    test_records = test_df.to_dict("records")
    print(f"[*] Untouched Test Samples: {len(test_records)}")

    norm = T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        norm,
    ])

    loader = DataLoader(
        DualStreamTestDataset(test_records, BASE_DIR, transform=transform),
        batch_size=16,
        shuffle=False,
        num_workers=0,
    )

    all_fused_probs = []
    all_preds = []
    all_targets = []
    all_sources = []
    all_tampers = []
    all_docs = []

    start_time = time.time()
    with torch.no_grad():
        for i, (global_imgs, patch_tensors, labels, sources, tampers, docs) in enumerate(loader):
            B = global_imgs.size(0)
            global_imgs = global_imgs.to(DEVICE)

            with torch.amp.autocast('cuda'):
                g_out = global_model(global_imgs)
                g_probs = torch.softmax(g_out, dim=1)[:, 1].cpu().numpy()

                N = patch_tensors.size(1)
                flat_patches = patch_tensors.view(B * N, 3, 224, 224).to(DEVICE)
                l_out = local_model(flat_patches)
                l_probs = torch.softmax(l_out, dim=1)[:, 1].view(B, N)
                l_max = torch.max(l_probs, dim=1).values.cpu().numpy()

            fused_batch = (alpha_global * g_probs) + (alpha_local * l_max)
            preds_batch = (fused_batch >= threshold).astype(int)

            all_fused_probs.extend(fused_batch)
            all_preds.extend(preds_batch)
            all_targets.extend(labels.numpy())
            all_sources.extend(sources)
            all_tampers.extend(tampers)
            all_docs.extend(docs)

            if (i + 1) % 50 == 0 or (i + 1) == len(loader):
                print(f"    Processed {len(all_preds)} / {len(test_records)} test samples...", flush=True)

    elapsed = time.time() - start_time
    print(f"[OK] Test inference complete in {elapsed:.1f}s.")

    y_true = np.array(all_targets)
    y_pred = np.array(all_preds)
    y_prob = np.array(all_fused_probs)

    # Compute Final Test Metrics
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.5

    gen_mask = (y_true == 0)
    tam_mask = (y_true == 1)
    far = float((y_pred[gen_mask] == 1).sum() / gen_mask.sum())
    frr = float((y_pred[tam_mask] == 0).sum() / tam_mask.sum())
    cm = confusion_matrix(y_true, y_pred).tolist()

    print("\n==========================================================")
    print("FINAL TEST SET METRICS (DUAL-STREAM V2)")
    print("==========================================================")
    print(f"Accuracy               : {acc*100:.2f}% ({sum(y_true == y_pred)} / {len(y_true)})")
    print(f"Precision              : {prec:.4f}")
    print(f"Recall (Sensitivity)   : {rec:.4f}")
    print(f"Specificity            : {1.0 - far:.4f}")
    print(f"F1-Score               : {f1:.4f}")
    print(f"ROC-AUC                : {roc_auc:.4f}")
    print(f"False Acceptance Rate  : {far*100:.2f}% ({(y_pred[gen_mask] == 1).sum()} / {gen_mask.sum()})")
    print(f"False Rejection Rate   : {frr*100:.2f}% ({(y_pred[tam_mask] == 0).sum()} / {tam_mask.sum()})")
    print(f"Confusion Matrix       : {cm}")

    # Breakdown by Source
    source_results = {}
    print("\nBreakdown by Source on Test Set:")
    for src in sorted(set(all_sources)):
        m = np.array(all_sources) == src
        s_acc = float(accuracy_score(y_true[m], y_pred[m]))
        n_gen = int((gen_mask & m).sum())
        n_tam = int((tam_mask & m).sum())
        gen_acc = float(accuracy_score(y_true[gen_mask & m], y_pred[gen_mask & m])) if n_gen > 0 else None
        tam_rec = float(recall_score(y_true[tam_mask & m], y_pred[tam_mask & m], zero_division=0)) if n_tam > 0 else None
        source_results[src] = {
            "total": int(m.sum()),
            "genuine_count": n_gen,
            "tampered_count": n_tam,
            "accuracy": s_acc,
            "genuine_acc": gen_acc,
            "tampered_recall": tam_rec,
        }
        print(f"  {src:36s} | N={m.sum():5d} | Acc={s_acc*100:6.2f}% | Gen({n_gen}): {gen_acc*100 if gen_acc is not None else 0:6.2f}% | Tam({n_tam}): {tam_rec*100 if tam_rec is not None else 0:6.2f}%")

    # Breakdown by Tampering Attack Category
    attack_results = {}
    print("\nBreakdown by Tampering Type on Test Set:")
    for atype in sorted(set(all_tampers)):
        m = (np.array(all_tampers) == atype) & tam_mask
        n_samples = int(m.sum())
        if n_samples > 0:
            a_rec = float(recall_score(y_true[m], y_pred[m], zero_division=0))
            attack_results[atype] = {
                "support": n_samples,
                "recall": a_rec,
                "status": "Statistically Robust" if n_samples >= 30 else "INSUFFICIENT TEST SUPPORT",
            }
            print(f"  {atype:32s} (N={n_samples:4d}) | Recall: {a_rec*100:6.2f}% | {attack_results[atype]['status']}")

    test_evaluation = {
        "model_version": "2.0.0_dual_stream_fusion",
        "evaluation_split": "untouched_test",
        "sample_count": len(y_true),
        "overall_metrics": {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "specificity": 1.0 - far,
            "f1_score": f1,
            "roc_auc": roc_auc,
            "far": far,
            "frr": frr,
            "confusion_matrix": cm,
        },
        "source_breakdown": source_results,
        "attack_breakdown": attack_results,
    }

    with open(TEST_RESULTS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(test_evaluation, f, indent=2)

    print(f"\n[OK] Final test evaluation results exported to: {TEST_RESULTS_OUTPUT}")


if __name__ == '__main__':
    main()
