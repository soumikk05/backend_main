"""Cached document classifier supporting 5 standard travel & identity document categories."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional
import cv2
import numpy as np

SUPPORTED_TYPES = {"passport", "visa", "national_id", "driving_license", "permit"}

LABELS = ["passport", "visa", "national_id", "driving_license", "permit"]


@lru_cache(maxsize=1)
def _load_model():
    """Load a locally provisioned TensorFlow classifier only; never downloads at runtime."""
    path = Path(__file__).resolve().parents[2] / "ml_artifacts" / "document_classifier.keras"
    if not path.exists():
        return None
    try:
        from tensorflow import keras
        return keras.models.load_model(str(path))
    except Exception:
        return None


def preprocess_image_for_classifier(image: np.ndarray, target_size=(224, 224)) -> np.ndarray:
    """Standardize input image dimensions and RGB normalization."""
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, target_size)
    normalized = resized.astype(np.float32) / 255.0
    return np.expand_dims(normalized, axis=0)


def classify_document(image_path: str) -> Dict[str, Any]:
    """
    Classify a document image into one of 5 supported classes:
    1. passport
    2. visa
    3. national_id
    4. driving_license
    5. permit

    Returns:
    {
        "document_type": str,
        "confidence": float,
        "supported": bool,
        "source": str,
        "error": str | None
    }
    """
    image = cv2.imread(image_path)
    if image is None:
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "supported": False,
            "source": "unreadable",
            "error": "Could not decode input image",
        }

    # 1. Neural Classifier (MobileNet / CNN)
    model = _load_model()
    if model is not None:
        try:
            batch = preprocess_image_for_classifier(image)
            probabilities = model.predict(batch, verbose=0)[0]
            index = int(np.argmax(probabilities))
            confidence = float(probabilities[index])
            doc_type = LABELS[index] if index < len(LABELS) else "unknown"

            if confidence >= 0.50 and doc_type in SUPPORTED_TYPES:
                return {
                    "document_type": doc_type,
                    "confidence": round(confidence, 4),
                    "supported": True,
                    "source": "mobilenet_cnn",
                    "classifier_mode": "ml",
                    "model_version": "1.0.0",
                    "error": None,
                }
        except Exception:
            pass

    # 2. Text Keyword Heuristic Classifier
    try:
        from app.services.ocr_service import read_document_text
        text = read_document_text(image_path).lower()
    except Exception:
        text = ""

    rules = [
        ("passport", ("passport", "republic", "nationality", "surname", "given name", "p<")),
        ("visa", ("visa", "entry permit", "entries", "valid until", "type/type")),
        ("driving_license", ("driving licence", "driver license", "driving license", "dl no", "vehicle class")),
        ("national_id", ("national id", "identity card", "aadhaar", "unique identification", "resident")),
        ("permit", ("permit", "work permit", "residence permit", "issued to", "permit no")),
    ]

    best_match: Optional[str] = None
    best_score = 0.0

    for label, keywords in rules:
        hits = sum(1 for kw in keywords if kw in text)
        if hits > 0:
            score = 0.50 + 0.12 * hits
            if score > best_score:
                best_score = score
                best_match = label

    if best_match and best_score >= 0.50:
        return {
            "document_type": best_match,
            "confidence": round(min(0.98, best_score), 4),
            "supported": True,
            "source": "heuristic_ocr",
            "classifier_mode": "heuristic_fallback",
            "model_version": None,
            "error": None,
        }

    return {
        "document_type": "unknown",
        "confidence": 0.0,
        "supported": False,
        "source": "fallback",
        "classifier_mode": "heuristic_fallback",
        "model_version": None,
        "error": "Unsupported or unrecognized document type",
    }

