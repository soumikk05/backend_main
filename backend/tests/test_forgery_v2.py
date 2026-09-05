"""
Regression Test Suite for Dual-Stream V2 Forgery Subsystem (Module 3 - V2).

Verifies all requirements:
1. V2 checkpoint loads
2. V1 checkpoint loads & preserved baseline
3. Global inference works
4. Blind 3x3 local patch inference works without ground truth coordinates
5. Calibrated fusion formula (0.60 * global + 0.40 * local_max)
6. Decision threshold (T = 0.40 / 40.0)
7. Uncertainty zone (0.35 <= P_fused <= 0.55)
8. CUDA inference works when available & CPU fallback works
9. Missing checkpoint fails safely (never silently genuine)
10. Malformed / corrupted image fails safely (explicit manual-review state)
11. Full tampering service & risk engine integration
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import cv2
from PIL import Image

import torch

from app.services.cnn_forgery_service import (
    score_image_forgery_cnn,
    generate_3x3_patches,
    _get_dual_stream_models,
    reset_models_for_testing,
    GLOBAL_WEIGHTS_PATH,
    LOCAL_WEIGHTS_PATH,
    FUSION_WEIGHTS_PATH,
    DEFAULT_ALPHA_GLOBAL,
    DEFAULT_ALPHA_LOCAL,
    DEFAULT_THRESHOLD,
    UNCERTAINTY_MIN,
    UNCERTAINTY_MAX,
)
from app.services.tampering_service import analyze_tampering
from app.services.risk_engine import compute_risk_score


@pytest.fixture
def clean_doc_image():
    """Create a temporary valid document image for testing."""
    img = np.ones((600, 800, 3), dtype=np.uint8) * 245
    cv2.rectangle(img, (50, 50), (750, 550), (30, 30, 30), 2)
    cv2.putText(img, "REPUBLIC OF INDIA - PASSPORT", (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "P<INDVERMA<<VAIBHAV<<<<<<<<<<<<<<<<<<<<<<<<<", (70, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        path = f.name
        cv2.imwrite(path, img)

    yield path

    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def corrupted_image_path():
    """Create an unreadable/corrupted file for negative testing."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"CORRUPTED_NON_IMAGE_BYTES_XYZ_12345")
        path = f.name

    yield path

    if os.path.exists(path):
        os.remove(path)


# ==============================================================================
# 1 & 2. Checkpoints Exist and Load
# ==============================================================================

def test_v1_and_v2_checkpoints_exist_and_load():
    """Verify both V1 baseline and V2 local checkpoints exist and load with state dicts."""
    assert GLOBAL_WEIGHTS_PATH.exists(), f"Global V1 weights missing: {GLOBAL_WEIGHTS_PATH}"
    assert LOCAL_WEIGHTS_PATH.exists(), f"Local V2 weights missing: {LOCAL_WEIGHTS_PATH}"
    assert FUSION_WEIGHTS_PATH.exists(), f"Fusion V2 config missing: {FUSION_WEIGHTS_PATH}"

    # Verify Global V1 checkpoint integrity
    ckpt_g = torch.load(GLOBAL_WEIGHTS_PATH, map_location="cpu", weights_only=False)
    assert isinstance(ckpt_g, dict)
    assert "model_state_dict" in ckpt_g or "classifier.1.weight" in ckpt_g or "features.0.0.weight" in ckpt_g

    # Verify Local V2 checkpoint integrity
    ckpt_l = torch.load(LOCAL_WEIGHTS_PATH, map_location="cpu", weights_only=False)
    assert isinstance(ckpt_l, dict)
    assert "model_state_dict" in ckpt_l or "classifier.1.weight" in ckpt_l or "features.0.0.weight" in ckpt_l

    # Verify Fusion config parameters
    cfg = torch.load(FUSION_WEIGHTS_PATH, map_location="cpu", weights_only=False)
    assert cfg["version"] == "2.0.0_dual_stream_fusion"
    assert cfg["alpha_global"] == 0.60
    assert cfg["alpha_local"] == 0.40
    assert cfg["decision_threshold"] == 0.40


# ==============================================================================
# 3 & 4. Dual-Stream Models & Blind 3x3 Patch Inference
# ==============================================================================

def test_dual_stream_models_initialization():
    """Verify dual-stream model loader initializes both models in eval mode."""
    reset_models_for_testing()
    gm, lm, dev, ver = _get_dual_stream_models()
    assert gm is not None, "Global model failed to load"
    assert lm is not None, "Local model failed to load"
    assert ver == "2.0.0_dual_stream_fusion"
    assert not gm.training
    assert not lm.training


def test_blind_3x3_patch_generation():
    """
    Verify blind 3x3 patch generation produces exactly 9 crops without needing
    ground-truth coordinates or attack annotations.
    """
    # Test across multiple arbitrary dimensions
    for w, h in [(600, 800), (317, 489), (1024, 768), (224, 224)]:
        pil_img = Image.new("RGB", (w, h), color=(200, 200, 200))
        patches = generate_3x3_patches(pil_img)
        assert len(patches) == 9
        for p in patches:
            assert isinstance(p, Image.Image)
            pw, ph = p.size
            assert pw > 0 and ph > 0


def test_dual_stream_inference_pipeline(clean_doc_image):
    """
    Verify end-to-end scoring produces complete V2 contract:
    global_probability, local_peak_probability, local_mean_probability,
    patch_probabilities (length 9), cnn_score, and fused tamper_probability.
    """
    res = score_image_forgery_cnn(clean_doc_image)
    assert res["error"] is None
    assert res["model"] == "hybrid_mobilenet_v2_dual_stream"
    assert res["model_version"] == "2.0.0_dual_stream_fusion"
    assert 0.0 <= res["cnn_score"] <= 100.0
    assert 0.0 <= res["tamper_probability"] <= 1.0
    assert 0.0 <= res["global_probability"] <= 1.0
    assert 0.0 <= res["local_peak_probability"] <= 1.0
    assert 0.0 <= res["local_mean_probability"] <= 1.0
    assert len(res["patch_probabilities"]) == 9
    assert res["local_peak_probability"] == pytest.approx(max(res["patch_probabilities"]), abs=1e-4)


# ==============================================================================
# 5. Fusion Math Verification
# ==============================================================================

def test_calibrated_fusion_formula(clean_doc_image):
    """Verify P_fused = 0.60 * P_global + 0.40 * P_local_peak exactly."""
    res = score_image_forgery_cnn(clean_doc_image)
    expected_fused = (DEFAULT_ALPHA_GLOBAL * res["global_probability"]) + (DEFAULT_ALPHA_LOCAL * res["local_peak_probability"])
    assert res["tamper_probability"] == pytest.approx(round(expected_fused, 4), abs=1e-3)
    assert res["cnn_score"] == pytest.approx(round(expected_fused * 100.0, 2), abs=1e-1)


# ==============================================================================
# 6 & 7. Decision Threshold & Uncertainty Zone
# ==============================================================================

def test_threshold_and_uncertainty_logic():
    """Verify decision boundary trigger at 0.40 and uncertainty band 0.35-0.55."""
    # Score 0.20: Below threshold, outside uncertainty -> clean
    p_fused_clean = 0.20
    triggered_clean = bool(p_fused_clean >= DEFAULT_THRESHOLD)
    uncertain_clean = bool(UNCERTAINTY_MIN <= p_fused_clean <= UNCERTAINTY_MAX)
    assert not triggered_clean
    assert not uncertain_clean

    # Score 0.38: Below threshold, but inside uncertainty (0.35-0.55) -> uncertain review
    p_fused_border = 0.38
    triggered_border = bool(p_fused_border >= DEFAULT_THRESHOLD)
    uncertain_border = bool(UNCERTAINTY_MIN <= p_fused_border <= UNCERTAINTY_MAX)
    assert not triggered_border
    assert uncertain_border

    # Score 0.45: Above threshold, inside uncertainty -> triggered and uncertain
    p_fused_tampered_border = 0.45
    triggered_tampered_border = bool(p_fused_tampered_border >= DEFAULT_THRESHOLD)
    uncertain_tampered_border = bool(UNCERTAINTY_MIN <= p_fused_tampered_border <= UNCERTAINTY_MAX)
    assert triggered_tampered_border
    assert uncertain_tampered_border

    # Score 0.85: Above threshold, outside uncertainty -> clear tamper alert
    p_fused_obvious = 0.85
    triggered_obvious = bool(p_fused_obvious >= DEFAULT_THRESHOLD)
    uncertain_obvious = bool(UNCERTAINTY_MIN <= p_fused_obvious <= UNCERTAINTY_MAX)
    assert triggered_obvious
    assert not uncertain_obvious


# ==============================================================================
# 8. CUDA and CPU Behavior
# ==============================================================================

def test_cuda_and_cpu_fallback(clean_doc_image):
    """
    Verify inference runs on CUDA when available (detects RTX 5050)
    and CPU fallback works safely when preferred_device is CPU.
    """
    if torch.cuda.is_available():
        reset_models_for_testing()
        gm, lm, dev, ver = _get_dual_stream_models(preferred_device="cuda")
        assert dev.type == "cuda"
        res_gpu = score_image_forgery_cnn(clean_doc_image)
        assert res_gpu["device"] == "cuda"
        assert res_gpu["error"] is None

    # Force CPU execution
    reset_models_for_testing()
    gm_cpu, lm_cpu, dev_cpu, ver_cpu = _get_dual_stream_models(preferred_device="cpu")
    assert dev_cpu.type == "cpu"
    res_cpu = score_image_forgery_cnn(clean_doc_image)
    assert res_cpu["device"] == "cpu"
    assert res_cpu["error"] is None
    assert 0.0 <= res_cpu["cnn_score"] <= 100.0

    # Reset back to default
    reset_models_for_testing()


# ==============================================================================
# 9. Failure Safety: Missing Checkpoint
# ==============================================================================

def test_missing_checkpoints_fails_safely(clean_doc_image):
    """
    CRITICAL SAFETY REQUIREMENT:
    If forgery models fail to load, DO NOT silently classify document as genuine (0 score).
    Must produce an explicit error and flag for manual review.
    """
    reset_models_for_testing()
    with patch("app.services.cnn_forgery_service._load_weights_into_model", return_value=False):
        res = score_image_forgery_cnn(clean_doc_image)
        assert res["mode"] == "safe_failure"
        assert res["triggered"] is True
        assert res["uncertain"] is True
        assert res["cnn_score"] == 50.0  # Lands in MANUAL_REVIEW bracket
        assert res["error"] is not None
        assert "MANUAL_REVIEW" in res["detail"]

    reset_models_for_testing()


# ==============================================================================
# 10. Failure Safety: Corrupted or Malformed Image
# ==============================================================================

def test_corrupted_image_fails_safely(corrupted_image_path):
    """Verify corrupted images do not crash and produce safe manual-review flag."""
    res = score_image_forgery_cnn(corrupted_image_path)
    assert res["mode"] == "safe_failure"
    assert res["triggered"] is True
    assert res["uncertain"] is True
    assert res["cnn_score"] == 50.0
    assert res["error"] is not None
    assert "MANUAL_REVIEW" in res["detail"]


def test_tiny_image_dimensions():
    """Verify images smaller than 32x32 return unavailable mode gracefully."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
        img = np.ones((20, 20, 3), dtype=np.uint8) * 200
        cv2.imwrite(path, img)

    try:
        res = score_image_forgery_cnn(path)
        assert res["mode"] == "unavailable"
        assert res["triggered"] is False
    finally:
        if os.path.exists(path):
            os.remove(path)


# ==============================================================================
# 11. Multi-Signal Fusion & Risk Engine Integration
# ==============================================================================

def test_tampering_service_and_risk_engine_integration(clean_doc_image):
    """
    Verify V2 output flows through tampering service and into the risk engine
    without allowing CNN alone to automatically authorize or bypass other signals.
    """
    tamp_result = analyze_tampering(clean_doc_image)
    assert "tampering_score" in tamp_result
    cnn_check = next((c for c in tamp_result["checks"] if c["name"] == "cnn_forgery_classification"), None)
    assert cnn_check is not None
    assert "Dual-Stream V2" in cnn_check["detail"]

    # Verify risk engine consumes tampering result
    risk = compute_risk_score(
        validation_result={"checks": [{"name": "mrz_checksum", "passed": True, "severity": "HIGH"}]},
        tampering_result=tamp_result,
        face_result=None,
    )
    assert "risk_score" in risk
    assert risk["risk_label"] in ("LOW", "MEDIUM", "HIGH")
    assert "tampering" in risk["component_scores"]
