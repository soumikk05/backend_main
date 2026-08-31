import os
import csv
import cv2
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
from keras import layers, models

MANIFEST_PATH = 'dataset/document_classification/manifest.csv'
MODEL_SAVE_PATH = 'models/document_classifier.keras'
REPORTS_DIR = 'reports'
METRICS_SAVE_PATH = os.path.join(REPORTS_DIR, 'classifier_metrics.json')

LABELS = ["passport", "visa", "national_id", "driving_license", "permit"]
LABEL_MAP = {lbl: idx for idx, lbl in enumerate(LABELS)}

def load_data_from_manifest():
    train_x, train_y = [], []
    val_x, val_y = [], []
    test_x, test_y = [], []

    with open(MANIFEST_PATH, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_path = row['image_path']
            doc_type = row['document_type']
            split = row['split']

            img = cv2.imread(img_path)
            if img is None:
                continue
            
            # Preprocess image
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_resized = cv2.resize(img_rgb, (128, 128))
            normalized = img_resized.astype(np.float32) / 255.0

            label_idx = LABEL_MAP[doc_type]

            if split == 'train':
                train_x.append(normalized)
                train_y.append(label_idx)
            elif split == 'val':
                val_x.append(normalized)
                val_y.append(label_idx)
            else:
                test_x.append(normalized)
                test_y.append(label_idx)

    return (
        np.array(train_x), np.array(train_y),
        np.array(val_x), np.array(val_y),
        np.array(test_x), np.array(test_y)
    )

def main():
    print("=== TRAINING DOCUMENT CLASSIFIER ===")
    os.makedirs('models', exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if not os.path.exists(MANIFEST_PATH):
        print("Error: manifest.csv not found!")
        return

    # Load dataset
    print("Loading images...")
    tx, ty, vx, vy, sx, sy = load_data_from_manifest()
    print(f"Loaded: Train={len(tx)}, Val={len(vx)}, Test={len(sx)}")

    if len(tx) == 0:
        print("Error: No training data found!")
        return

    # Build model (Lightweight ConvNet)
    model = models.Sequential([
        layers.Conv2D(16, (3, 3), activation='relu', input_shape=(128, 128, 3)),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(32, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dense(5, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    print("Training model for 2 epochs...")
    model.fit(
        tx, ty,
        epochs=2,
        validation_data=(vx, vy),
        batch_size=32,
        verbose=1
    )

    # Save trained model
    model.save(MODEL_SAVE_PATH)
    print("Model saved to:", MODEL_SAVE_PATH)

    # Evaluate on test set
    print("Evaluating on test set...")
    loss, accuracy = model.evaluate(sx, sy, verbose=0)
    print(f"Test Accuracy: {accuracy:.4f}")

    # Compute detailed metrics
    predictions = model.predict(sx, verbose=0)
    pred_classes = np.argmax(predictions, axis=1)

    # Calculate per-class metrics
    from sklearn.metrics import classification_report, confusion_matrix
    report = classification_report(
        sy, pred_classes,
        target_names=[LABELS[i] for i in sorted(list(set(sy) | set(pred_classes)))],
        output_dict=True
    )
    conf_matrix = confusion_matrix(sy, pred_classes).tolist()

    # Save metrics report JSON
    metrics = {
        "status": "trained",
        "dataset_version": "midv500_v1",
        "num_samples": len(tx) + len(vx) + len(sx),
        "test_loss": float(loss),
        "test_accuracy": float(accuracy),
        "classification_report": report,
        "confusion_matrix": conf_matrix,
        "framework": "tensorflow/keras",
        "model_version": "1.0.0"
    }

    with open(METRICS_SAVE_PATH, 'w') as f:
        json.dump(metrics, f, indent=2)
    print("Metrics saved to:", METRICS_SAVE_PATH)

if __name__ == '__main__':
    main()
