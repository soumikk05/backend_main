"""
Evaluate the forgery CNN on the held-out test split only.

This script uses the same model architecture, dataset split, transforms, and
synthetic-tampering logic as train_forgery_cnn.py. It never uses train or
validation images.
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader
from torchvision import models, transforms

# Make backend/app importable when run from the backend folder.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.tampering.dataset_loader import load_tampering_dataset
from train_forgery_cnn import RealDocumentTamperingDataset

WEIGHTS_PATH = BASE_DIR / "app" / "models" / "weights" / "forgery_mobilenet_v2.pt"
REPORTS_DIR = BASE_DIR / "reports"
JSON_OUT = REPORTS_DIR / "tampering_metrics.json"
CSV_OUT = REPORTS_DIR / "tampering_metrics.csv"


def build_evaluation_model():
    """Build the exact MobileNetV2 classifier architecture used during training."""
    model = models.mobilenet_v2(weights=None)

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 64),
        nn.ReLU(),
        nn.Linear(64, 1),
        nn.Sigmoid(),
    )
    return model


def main(data_root: str, batch_size: int, seed: int):
    print("=== EVALUATING FORGERY CNN ON HELD-OUT TEST DATA ===")

    if not WEIGHTS_PATH.exists():
        print(f"ERROR: Model weights were not found:\n{WEIGHTS_PATH}")
        print("Train the model first with train_forgery_cnn.py.")
        return 1

    # Makes the generated synthetic test samples reproducible.
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    splits = load_tampering_dataset(root=data_root)
    genuine_test = [path for path, label in splits["test"] if label == 0]
    real_tampered_test = [path for path, label in splits["test"] if label == 1]

    if not genuine_test and not real_tampered_test:
        print(f"ERROR: No test images were found under '{data_root}'.")
        return 1

    # Mirrors the trainer: real tampered samples are included if available;
    # otherwise, tampered samples are generated from held-out genuine images.
    synthetic_target = max(0, len(genuine_test) - len(real_tampered_test))

    test_transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])

    test_dataset = RealDocumentTamperingDataset(
        genuine_paths=genuine_test,
        real_tampered_paths=real_tampered_test,
        target_synthetic_tampered=synthetic_target,
        transform=test_transform,
    )

    if len(test_dataset) == 0:
        print("ERROR: The held-out test dataset is empty.")
        return 1

    print(f"Held-out genuine images: {len(genuine_test)}")
    print(f"Held-out real tampered images: {len(real_tampered_test)}")
    print(f"Generated synthetic-tampered test images: {synthetic_target}")
    print(f"Total test samples: {len(test_dataset)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_evaluation_model().to(device)

    try:
        state_dict = torch.load(WEIGHTS_PATH, map_location=device, weights_only=True)
    except TypeError:
        # Supports older PyTorch versions.
        state_dict = torch.load(WEIGHTS_PATH, map_location=device)

    model.load_state_dict(state_dict)
    model.eval()

    dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    all_predictions = []
    all_targets = []
    all_probabilities = []

    print(f"Running evaluation on {device}...")

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            probabilities = model(images).squeeze(1).cpu()

            predictions = (probabilities >= 0.5).long().tolist()
            targets = labels.long().tolist()

            all_predictions.extend(predictions)
            all_targets.extend(targets)
            all_probabilities.extend(probabilities.tolist())

    report = classification_report(
        all_targets,
        all_predictions,
        labels=[0, 1],
        target_names=["genuine", "tampered"],
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(all_targets, all_predictions, labels=[0, 1]).tolist()

    accuracy = float(report["accuracy"])
    genuine_metrics = report["genuine"]
    tampered_metrics = report["tampered"]

    print("\n=== HELD-OUT TEST RESULTS ===")
    print(f"Accuracy:          {accuracy:.2%}")
    print(f"Genuine precision: {genuine_metrics['precision']:.2%}")
    print(f"Genuine recall:    {genuine_metrics['recall']:.2%}")
    print(f"Tampered precision:{tampered_metrics['precision']:.2%}")
    print(f"Tampered recall:   {tampered_metrics['recall']:.2%}")
    print(f"Tampered F1 score: {tampered_metrics['f1-score']:.4f}")
    print("\nConfusion matrix: [[genuine->genuine, genuine->tampered],")
    print("                   [tampered->genuine, tampered->tampered]]")
    print(matrix)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    metrics = {
        "status": "evaluated",
        "dataset_split": "held_out_test",
        "test_seed": seed,
        "num_samples": len(test_dataset),
        "held_out_genuine_images": len(genuine_test),
        "held_out_real_tampered_images": len(real_tampered_test),
        "generated_synthetic_tampered_images": synthetic_target,
        "test_accuracy": accuracy,
        "classification_report": report,
        "confusion_matrix": matrix,
        "decision_threshold": 0.5,
        "framework": "pytorch/torchvision",
        "weights_path": str(WEIGHTS_PATH),
    }

    with open(JSON_OUT, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["metric", "value"])
        writer.writerow(["accuracy", accuracy])
        writer.writerow(["genuine_precision", genuine_metrics["precision"]])
        writer.writerow(["genuine_recall", genuine_metrics["recall"]])
        writer.writerow(["genuine_f1", genuine_metrics["f1-score"]])
        writer.writerow(["tampered_precision", tampered_metrics["precision"]])
        writer.writerow(["tampered_recall", tampered_metrics["recall"]])
        writer.writerow(["tampered_f1", tampered_metrics["f1-score"]])
        writer.writerow(["true_genuine", matrix[0][0]])
        writer.writerow(["false_tampered_alert", matrix[0][1]])
        writer.writerow(["missed_tampered", matrix[1][0]])
        writer.writerow(["true_tampered", matrix[1][1]])

    print(f"\nJSON report saved to: {JSON_OUT}")
    print(f"CSV report saved to:  {CSV_OUT}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate the forgery CNN on the held-out test split."
    )
    parser.add_argument(
        "--data_root",
        default="dataset",
        help="Dataset folder containing genuine/ and tampered/ subfolders.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=16,
        help="Number of images evaluated together.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed used to reproduce synthetic test samples.",
    )
    args = parser.parse_args()

    raise SystemExit(main(args.data_root, args.batch_size, args.seed))