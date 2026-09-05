"""
Dual-Stream High-Resolution CNN & Spatial Forgery Classifier (Module 3 - V2).

Integrates the calibrated Dual-Stream V2 document forgery detection architecture:
- Global Stream: MobileNetV2 evaluated on downscaled 224x224 document context (alpha = 0.60)
  Weights: app/models/weights/forgery_global_v1.pt (immutable baseline)
- Local Stream: MobileNetV2 evaluated on blind 3x3 unannotated high-resolution grid patches (beta = 0.40)
  Weights: app/models/weights/forgery_local_v2.pt
- Calibrated Fusion: P_fused = 0.60 * P_global + 0.40 * max(P_patch_i)
  Artifact: app/models/weights/forgery_fusion_v2.pt
- Decision Threshold: T = 0.40 (score >= 40.0 triggers forgery alert)
- Uncertainty Zone: 0.35 <= P_fused <= 0.55 triggers manual review recommendation
- Hardware: Accelerated on NVIDIA GeForce RTX 5050 Laptop GPU (CUDA 13.0, sm_120) with graceful CPU fallback
- Failure Safety: If models fail to load, produces explicit manual-review state (never silently genuine)
"""

import io
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.config import ELA_JPEG_QUALITY

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WEIGHTS_DIR = BASE_DIR / "app" / "models" / "weights"

GLOBAL_WEIGHTS_PATH = WEIGHTS_DIR / "forgery_global_v1.pt"
LOCAL_WEIGHTS_PATH = WEIGHTS_DIR / "forgery_local_v2.pt"
FUSION_WEIGHTS_PATH = WEIGHTS_DIR / "forgery_fusion_v2.pt"
CLEAN_FALLBACK_WEIGHTS_PATH = WEIGHTS_DIR / "forgery_mobilenet_v2_clean.pt"

# Calibrated V2 defaults (from validation split calibration)
DEFAULT_ALPHA_GLOBAL = 0.60
DEFAULT_ALPHA_LOCAL = 0.40
DEFAULT_THRESHOLD = 0.40
UNCERTAINTY_MIN = 0.35
UNCERTAINTY_MAX = 0.55

# Load torch & torchvision
try:
    import torch
    import torch.nn as nn
    from torchvision import models, transforms
    TORCH_AVAILABLE = True
    _TRANSFORM = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
except Exception as exc:
    TORCH_AVAILABLE = False
    torch = None
    nn = None
    models = None
    transforms = None
    _TRANSFORM = None

# Singleton model holders
_GLOBAL_MODEL = None
_LOCAL_MODEL = None
_MODEL_DEVICE = None
_MODEL_VERSION = None
_FUSION_CONFIG = None


def _build_mobilenet_v2_classifier() -> Any:
    """Build the MobileNetV2 architecture with the locked classification head."""
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(128, 2),
    )
    return model


def _detect_device(preferred_device: Optional[str] = None) -> Any:
    """Detect and return torch device (CUDA if available, else CPU)."""
    if preferred_device:
        return torch.device(preferred_device)

    if torch.cuda.is_available():
        try:
            # Verify CUDA execution actually works on sm_120
            test_conv = nn.Conv2d(1, 1, 1).cuda()
            _ = test_conv(torch.randn(1, 1, 4, 4, device="cuda"))
            device_name = torch.cuda.get_device_name(0)
            logger.info("CUDA detected: %s (using cuda:0)", device_name)
            return torch.device("cuda")
        except Exception as exc:
            logger.warning("CUDA available but verification failed (%s); falling back to CPU", exc)
            return torch.device("cpu")
    return torch.device("cpu")


def _load_weights_into_model(model: Any, weights_path: Path, device: Any) -> bool:
    """Load state dict from checkpoint path safely."""
    if not weights_path.exists():
        return False
    try:
        checkpoint = torch.load(weights_path, map_location=device, weights_only=False)
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        elif isinstance(checkpoint, dict) and any(k.startswith("classifier") for k in checkpoint.keys()):
            model.load_state_dict(checkpoint)
        elif isinstance(checkpoint, dict) and "features.0.0.weight" in checkpoint:
            model.load_state_dict(checkpoint)
        else:
            model.load_state_dict(checkpoint)
        model.to(device)
        model.eval()
        return True
    except Exception as exc:
        logger.warning("Failed loading checkpoint %s on %s: %s", weights_path, device, exc)
        return False


def _get_dual_stream_models(preferred_device: Optional[str] = None) -> Tuple[Optional[Any], Optional[Any], Any, str]:
    """
    Lazy-load and cache the Dual-Stream V2 models (Global V1 + Local V2).
    Returns (global_model, local_model, device, version_tag).
    """
    global _GLOBAL_MODEL, _LOCAL_MODEL, _MODEL_DEVICE, _MODEL_VERSION, _FUSION_CONFIG

    if not TORCH_AVAILABLE:
        return None, None, "cpu", "unavailable"

    if _GLOBAL_MODEL is not None and _LOCAL_MODEL is not None and preferred_device is None:
        return _GLOBAL_MODEL, _LOCAL_MODEL, _MODEL_DEVICE, _MODEL_VERSION

    device = _detect_device(preferred_device)
    _MODEL_DEVICE = device

    # Read locked fusion config if present
    alpha_g = DEFAULT_ALPHA_GLOBAL
    alpha_l = DEFAULT_ALPHA_LOCAL
    threshold = DEFAULT_THRESHOLD

    if FUSION_WEIGHTS_PATH.exists():
        try:
            cfg = torch.load(FUSION_WEIGHTS_PATH, map_location="cpu", weights_only=False)
            alpha_g = float(cfg.get("alpha_global", DEFAULT_ALPHA_GLOBAL))
            alpha_l = float(cfg.get("alpha_local", DEFAULT_ALPHA_LOCAL))
            threshold = float(cfg.get("decision_threshold", DEFAULT_THRESHOLD))
            _FUSION_CONFIG = cfg
            logger.info("Loaded V2 fusion config from %s: alpha_g=%.2f, alpha_l=%.2f, T=%.2f",
                        FUSION_WEIGHTS_PATH, alpha_g, alpha_l, threshold)
        except Exception as exc:
            logger.warning("Failed loading %s: %s; using calibrated defaults", FUSION_WEIGHTS_PATH, exc)
            _FUSION_CONFIG = {
                "alpha_global": alpha_g,
                "alpha_local": alpha_l,
                "decision_threshold": threshold,
            }
    else:
        _FUSION_CONFIG = {
            "alpha_global": alpha_g,
            "alpha_local": alpha_l,
            "decision_threshold": threshold,
        }

    # 1. Load Global Model V1
    global_model = _build_mobilenet_v2_classifier()
    global_loaded = False
    if GLOBAL_WEIGHTS_PATH.exists():
        global_loaded = _load_weights_into_model(global_model, GLOBAL_WEIGHTS_PATH, device)
        if global_loaded:
            logger.info("Loaded Global Model V1 from %s on %s", GLOBAL_WEIGHTS_PATH, device)
    elif CLEAN_FALLBACK_WEIGHTS_PATH.exists():
        global_loaded = _load_weights_into_model(global_model, CLEAN_FALLBACK_WEIGHTS_PATH, device)
        if global_loaded:
            logger.info("Loaded Global Model fallback from %s on %s", CLEAN_FALLBACK_WEIGHTS_PATH, device)

    # 2. Load Local Model V2
    local_model = _build_mobilenet_v2_classifier()
    local_loaded = False
    if LOCAL_WEIGHTS_PATH.exists():
        local_loaded = _load_weights_into_model(local_model, LOCAL_WEIGHTS_PATH, device)
        if local_loaded:
            logger.info("Loaded Local Model V2 from %s on %s", LOCAL_WEIGHTS_PATH, device)

    if global_loaded and local_loaded:
        _GLOBAL_MODEL = global_model
        _LOCAL_MODEL = local_model
        _MODEL_VERSION = "2.0.0_dual_stream_fusion"
    elif global_loaded and not local_loaded:
        _GLOBAL_MODEL = global_model
        _LOCAL_MODEL = None
        _MODEL_VERSION = "1.0.0_global_v1_fallback"
        logger.warning("Local Model V2 weights missing/failed; operating in Global V1 fallback mode")
    else:
        _GLOBAL_MODEL = None
        _LOCAL_MODEL = None
        _MODEL_VERSION = "safe_failure"
        logger.error("Failed to load forgery detection models; operating in safe failure mode")

    return _GLOBAL_MODEL, _LOCAL_MODEL, _MODEL_DEVICE, _MODEL_VERSION


def reset_models_for_testing() -> None:
    """Reset cached singleton models (used for testing fallback & failure modes)."""
    global _GLOBAL_MODEL, _LOCAL_MODEL, _MODEL_DEVICE, _MODEL_VERSION, _FUSION_CONFIG
    _GLOBAL_MODEL = None
    _LOCAL_MODEL = None
    _MODEL_DEVICE = None
    _MODEL_VERSION = None
    _FUSION_CONFIG = None


def generate_3x3_patches(img_rgb: Image.Image) -> List[Image.Image]:
    """
    Generate 9 blind unannotated high-resolution patches using a 3x3 grid tiling.
    Does NOT require ground-truth coordinates, annotations, or attack labels.
    Patches are ordered row-major (0..8).
    """
    w, h = img_rgb.size
    gw, gh = w // 3, h // 3
    patches: List[Image.Image] = []
    for r in range(3):
        for c in range(3):
            box = (c * gw, r * gh, min(w, (c + 1) * gw), min(h, (r + 1) * gh))
            p_crop = img_rgb.crop(box)
            patches.append(p_crop)
    return patches


def score_image_forgery_cnn(image_path: str) -> Dict[str, Any]:
    """
    Computes document forgery suspicion score (0-100) using the locked Dual-Stream V2 pipeline:
      1. Global forgery inference on downscaled 224x224 document (weight = 0.60)
      2. Blind 3x3 high-resolution local patch inference (weight = 0.40 on peak patch)
      3. Calibrated fusion: P_fused = 0.60 * P_global + 0.40 * max(P_patch_i)
      4. Decision threshold: 0.40 (score >= 40.0 triggers forgery alert)
      5. Uncertainty handling: 0.35 <= P_fused <= 0.55 flags human review recommendation
      6. Safe failure: missing models or malformed images produce explicit manual-review state

    Returns:
      dict matching CNNScoreResponse schema and tampering_service integration.
    """
    # 1. Image loading & validation
    if not os.path.exists(image_path):
        return {
            "cnn_score": 50.0,
            "tamper_probability": 0.50,
            "global_probability": 0.50,
            "local_peak_probability": 0.50,
            "local_mean_probability": 0.50,
            "patch_probabilities": [],
            "model": "hybrid_mobilenet_v2_dual_stream",
            "triggered": True,
            "uncertain": True,
            "mode": "safe_failure",
            "model_version": "safe_failure",
            "device": "cpu",
            "detail": f"Document image file does not exist: {image_path} [MANUAL_REVIEW_REQUIRED]",
            "error": "File not found",
        }

    try:
        img = Image.open(image_path)
        img.verify()
        # Re-open after verify() closes/invalidates the file handle
        img = Image.open(image_path).convert("RGB")
    except Exception as exc:
        logger.warning("Invalid or corrupted image in CNN forgery scoring: %s", exc)
        return {
            "cnn_score": 50.0,
            "tamper_probability": 0.50,
            "global_probability": 0.50,
            "local_peak_probability": 0.50,
            "local_mean_probability": 0.50,
            "patch_probabilities": [],
            "model": "hybrid_mobilenet_v2_dual_stream",
            "triggered": True,
            "uncertain": True,
            "mode": "safe_failure",
            "model_version": "safe_failure",
            "device": "cpu",
            "detail": f"Corrupted or undecodable image: {exc} [MANUAL_REVIEW_REQUIRED]",
            "error": str(exc),
        }

    w, h = img.size
    if h < 32 or w < 32:
        return {
            "cnn_score": 0.0,
            "tamper_probability": 0.0,
            "global_probability": 0.0,
            "local_peak_probability": 0.0,
            "local_mean_probability": 0.0,
            "patch_probabilities": [],
            "model": "hybrid_mobilenet_v2_dual_stream",
            "triggered": False,
            "uncertain": False,
            "mode": "unavailable",
            "model_version": None,
            "device": "cpu",
            "detail": "Image dimensions too small for deep patch analysis (<32px)",
            "error": None,
        }

    # 2. Multi-frequency ELA & spatial statistics (computed for forensic explainability)
    overall_mean = 0.0
    try:
        img_np = np.array(img)
        buffer = io.BytesIO()
        img.save(buffer, "JPEG", quality=ELA_JPEG_QUALITY)
        buffer.seek(0)
        resaved = Image.open(buffer)
        diff = np.abs(img_np.astype(np.float32) - np.array(resaved).astype(np.float32))
        overall_mean = float(np.mean(diff))
    except Exception:
        diff = None

    # 3. Model Retrieval & Failure Safety
    global_model, local_model, device, version_tag = _get_dual_stream_models()

    alpha_g = DEFAULT_ALPHA_GLOBAL
    alpha_l = DEFAULT_ALPHA_LOCAL
    threshold = DEFAULT_THRESHOLD
    if _FUSION_CONFIG:
        alpha_g = float(_FUSION_CONFIG.get("alpha_global", DEFAULT_ALPHA_GLOBAL))
        alpha_l = float(_FUSION_CONFIG.get("alpha_local", DEFAULT_ALPHA_LOCAL))
        threshold = float(_FUSION_CONFIG.get("decision_threshold", DEFAULT_THRESHOLD))

    # Safe Failure Mode: If both models failed to load, DO NOT silently classify as genuine
    if global_model is None and local_model is None:
        logger.error("Safe failure triggered: no forgery models loaded.")
        return {
            "cnn_score": 50.0,
            "tamper_probability": 0.50,
            "global_probability": 0.50,
            "local_peak_probability": 0.50,
            "local_mean_probability": 0.50,
            "patch_probabilities": [],
            "model": "hybrid_mobilenet_v2_dual_stream",
            "triggered": True,
            "uncertain": True,
            "mode": "safe_failure",
            "model_version": version_tag,
            "device": str(device),
            "detail": "CNN forgery detection models unavailable; document flagged for manual review [MANUAL_REVIEW]",
            "error": "Models unavailable",
        }

    # 4. Global Forgery Inference
    full_tamper_prob = 0.0
    if global_model is not None and _TRANSFORM is not None:
        try:
            global_tensor = _TRANSFORM(img).unsqueeze(0).to(device)
            with torch.no_grad():
                if device.type == "cuda":
                    with torch.amp.autocast('cuda'):
                        g_out = global_model(global_tensor)
                else:
                    g_out = global_model(global_tensor)
                g_probs = torch.softmax(g_out, dim=1)[0]
                full_tamper_prob = float(g_probs[1].item())
        except Exception as exc:
            logger.warning("Global model inference exception: %s", exc)
            full_tamper_prob = 0.50

    # 5. Local 3x3 High-Resolution Patch Inference (Blind unannotated)
    patch_probs: List[float] = []
    patch_crops = generate_3x3_patches(img)
    target_local_model = local_model if local_model is not None else global_model

    if target_local_model is not None and _TRANSFORM is not None:
        try:
            transformed_patches = [_TRANSFORM(p) for p in patch_crops]
            patch_batch = torch.stack(transformed_patches, dim=0).to(device) # [9, 3, 224, 224]

            with torch.no_grad():
                if device.type == "cuda":
                    with torch.amp.autocast('cuda'):
                        l_out = target_local_model(patch_batch)
                else:
                    l_out = target_local_model(patch_batch)
                l_probs = torch.softmax(l_out, dim=1)[:, 1] # [9]
                patch_probs = [float(p.item()) for p in l_probs]
        except Exception as exc:
            logger.warning("Local patch inference exception: %s", exc)
            patch_probs = [full_tamper_prob] * 9

    peak_patch_prob = max(patch_probs) if patch_probs else full_tamper_prob
    mean_patch_prob = (sum(patch_probs) / len(patch_probs)) if patch_probs else full_tamper_prob

    # 6. Calibrated Dual-Stream Fusion
    if local_model is not None:
        # Full Dual-Stream V2 Fusion
        fused_prob = (alpha_g * full_tamper_prob) + (alpha_l * peak_patch_prob)
        mode = "trained_model"
    else:
        # Graceful Global V1 Fallback (V2 local weights unavailable)
        fused_prob = full_tamper_prob
        mode = "fallback_v1"

    raw_score = fused_prob * 100.0
    cnn_score = round(min(100.0, max(0.0, raw_score)), 2)

    # 7. Decision Threshold & Uncertainty Zone
    triggered = bool(fused_prob >= threshold)
    uncertain = bool(UNCERTAINTY_MIN <= fused_prob <= UNCERTAINTY_MAX) or (mode == "fallback_v1")

    detail_msg = (
        f"Dual-Stream V2 Forgery Score: {cnn_score:.1f}/100 "
        f"(global={full_tamper_prob:.3f} [@{alpha_g:.2f}], peak_patch={peak_patch_prob:.3f} [@{alpha_l:.2f}], "
        f"mean_patch={mean_patch_prob:.3f}, fused_prob={fused_prob:.3f}, T={threshold:.2f}, "
        f"device={device}, mode={mode})"
    )
    if uncertain:
        detail_msg += " [UNCERTAIN_CLASSIFICATION: Score within decision boundary zone (0.35-0.55), manual review recommended]"
    if mode == "fallback_v1":
        detail_msg += " [NOTICE: Running in Global V1 fallback mode; officer review advised]"

    return {
        "cnn_score": cnn_score,
        "tamper_probability": round(fused_prob, 4),
        "global_probability": round(full_tamper_prob, 4),
        "local_peak_probability": round(peak_patch_prob, 4),
        "local_mean_probability": round(mean_patch_prob, 4),
        "patch_probabilities": [round(p, 4) for p in patch_probs],
        "model": "hybrid_mobilenet_v2_dual_stream",
        "triggered": triggered,
        "uncertain": uncertain,
        "mode": mode,
        "model_version": version_tag,
        "device": str(device),
        "detail": detail_msg,
        "error": None,
    }

