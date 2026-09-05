import os
import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np
from PIL import Image

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import torch
import torch.nn as nn
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "dataset" / "dataset_split_manifest.csv"
WEIGHTS_PATH = BASE_DIR / "app" / "models" / "weights" / "forgery_mobilenet_v2_clean.pt"

class EvalDataset(Dataset):
    def __init__(self, records, base_dir, transform):
        self.records = records
        self.base_dir = base_dir
        self.transform = transform
    def __len__(self):
        return len(self.records)
    def __getitem__(self, idx):
        r = self.records[idx]
        img_path = self.base_dir / r['image_path']
        try:
            with Image.open(img_path) as img:
                image = img.convert('RGB')
        except Exception:
            image = Image.new('RGB', (224, 224), color=0)
        return self.transform(image), int(r['label']), str(r.get('source', '')), str(r.get('document_type', '')), str(r.get('tampering_type', ''))

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[*] Running on device: {device}", flush=True)

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    model = models.mobilenet_v2(weights=None)
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(1280, 128),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.2),
        nn.Linear(128, 2)
    )
    ckpt = torch.load(WEIGHTS_PATH, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model.to(device)
    model.eval()

    df = pd.read_csv(MANIFEST_PATH)

    for split_name in ['validation', 'test']:
        sub_df = df[df['split'] == split_name].reset_index(drop=True)
        records = sub_df.to_dict('records')
        loader = DataLoader(EvalDataset(records, BASE_DIR, transform), batch_size=128, shuffle=False, num_workers=0)
        
        all_preds, all_labels, all_sources, all_docs, all_tampers = [], [], [], [], []
        t0 = time.time()
        with torch.no_grad():
            for i, (imgs, labels, sources, doc_types, tampers) in enumerate(loader):
                imgs = imgs.to(device, non_blocking=True)
                with torch.cuda.amp.autocast():
                    outputs = model(imgs)
                preds = torch.argmax(outputs, dim=1).cpu().numpy()
                all_preds.extend(preds)
                all_labels.extend(labels.numpy())
                all_sources.extend(sources)
                all_docs.extend(doc_types)
                all_tampers.extend(tampers)
                if (i + 1) % 20 == 0 or (i + 1) == len(loader):
                    print(f"[{split_name.upper()}] Processed {len(all_preds)} / {len(records)} samples...", flush=True)
        
        duration = time.time() - t0
        y_pred = np.array(all_preds)
        y_true = np.array(all_labels)
        acc = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        print(f"\n==================================================", flush=True)
        print(f"SPLIT: {split_name.upper()} (N={len(y_true)}, Time: {duration:.1f}s)", flush=True)
        print(f"Overall Accuracy: {acc*100:.2f}% | F1: {f1:.4f}", flush=True)
        print(f"==================================================", flush=True)
        
        res = pd.DataFrame({
            'true': y_true, 'pred': y_pred, 'source': all_sources, 'doc': all_docs, 'tamper': all_tampers,
            'correct': (y_true == y_pred)
        })
        
        print("Breakdown by Source:", flush=True)
        for src, g in res.groupby('source'):
            src_acc = g['correct'].mean() * 100
            n_gen = (g['true'] == 0).sum()
            n_tam = (g['true'] == 1).sum()
            gen_acc = (g[g['true'] == 0]['correct'].mean() * 100) if n_gen > 0 else float('nan')
            tam_acc = (g[g['true'] == 1]['correct'].mean() * 100) if n_tam > 0 else float('nan')
            print(f"  {src:36s} | Total: {len(g):5d} | Acc: {src_acc:6.2f}% | Gen({n_gen:4d}): {gen_acc:6.2f}% | Tam({n_tam:4d}): {tam_acc:6.2f}%", flush=True)

        print("\nBreakdown by Document Type:", flush=True)
        for dt, g in res.groupby('doc'):
            dt_acc = g['correct'].mean() * 100
            n_gen = (g['true'] == 0).sum()
            n_tam = (g['true'] == 1).sum()
            print(f"  {dt:25s} | Total: {len(g):5d} | Acc: {dt_acc:6.2f}% | Gen: {n_gen:5d} | Tam: {n_tam:5d}", flush=True)

if __name__ == '__main__':
    main()
