# V2 Backend Integration and Regression Report
**SIH Problem Statement 26188 — AI-Based Document Screening and Identity Verification System**  
**Date:** September 4, 2026  
**System Version:** 2.0.0 (Dual-Stream High-Resolution Forgery Detection Subsystem)  
**Execution Environment:** Windows 11, Python 3.10.11, PyTorch 2.14.0+cu130, CUDA 13.0, NVIDIA GeForce RTX 5050 Laptop GPU (Blackwell `sm_120`)  

---

## 1. V2 Integration Status

The integration of the locked Dual-Stream V2 document forgery detector into the production backend has been successfully completed. 
The system operates seamlessly across all API routes, forensic fusion layers, and the composite risk decision engine.

### Strict Constraint Compliance
- **No model training performed:** All weights remained locked.
- **No weights modified:**
  - `app/models/weights/forgery_global_v1.pt` (29,053,453 bytes) remains the immutable baseline and fallback.
  - `app/models/weights/forgery_local_v2.pt` (29,044,793 bytes) loaded for localized high-resolution patch evaluation.
  - `app/models/weights/forgery_fusion_v2.pt` loaded as the calibration artifact.
- **No dataset split modified:** 37,777 train, 9,211 validation, 7,819 test samples remain untouched.
- **No hyperparameters or fusion weights tuned:** Retained exact calibration ($\alpha_{\text{global}} = 0.60, \beta_{\text{local}} = 0.40, T = 0.40$).

---

## 2. Files Changed

| File Path | Nature of Change | Summary of Modifications |
|---|---|---|
| [`app/services/cnn_forgery_service.py`](file:///c:/Users/soumi/OneDrive/Desktop/vaibhav/backend/app/services/cnn_forgery_service.py) | **Refactored** | Replaced legacy single-stream heuristic with Dual-Stream V2 architecture: lazy-loads Global V1 and Local V2 models on CUDA (RTX 5050) with CPU fallback; extracts blind $3 \times 3$ grid patches (row-major); computes calibrated fusion $P_{\text{fused}} = 0.60 P_g + 0.40 \max(P_l)$; evaluates threshold $T=0.40$; flags uncertainty zone $0.35 \le P_{\text{fused}} \le 0.55$; implements safe failure mode. |
| [`app/models/schemas.py`](file:///c:/Users/soumi/OneDrive/Desktop/vaibhav/backend/app/models/schemas.py) | **Updated** | Added optional V2 telemetry fields to `CNNScoreResponse` (`global_probability`, `local_peak_probability`, `local_mean_probability`, `patch_probabilities`, `uncertain`, `mode`, `device`) with `model_config = {"protected_namespaces": ()}` for Pydantic v2 compliance. |
| [`scripts/benchmark_screening_pipeline.py`](file:///c:/Users/soumi/OneDrive/Desktop/vaibhav/backend/scripts/benchmark_screening_pipeline.py) | **Updated** | Added dedicated micro-benchmarks for Global inference, Local $3 \times 3$ patch inference, Fusion, Complete Forgery subsystem, and Total End-to-End pipeline (P50, P90, P95, P99). |
| [`tests/test_forgery_v2.py`](file:///c:/Users/soumi/OneDrive/Desktop/vaibhav/backend/tests/test_forgery_v2.py) | **New** | 11 comprehensive unit tests verifying checkpoint integrity, dual-stream loading, blind $3 \times 3$ patch tiling without coordinates, fusion formula, thresholding, uncertainty zones, CUDA/CPU fallback, and safe failure on missing weights or corrupted images. |
| [`tests/integration/test_v2_end_to_end_categories.py`](file:///c:/Users/soumi/OneDrive/Desktop/vaibhav/backend/tests/integration/test_v2_end_to_end_categories.py) | **New** | 11 end-to-end integration tests verifying execution across genuine documents, obvious forged documents, localized tampered documents, MIDV-style localized tampering, unsupported documents, corrupted images, low-quality images, missing faces, multiple faces, malformed MRZ, and conflicting historical records. |

---

## 3. Model Loading Verification

Both models were independently inspected and verified:
1. **Global Model V1:**
   - Checkpoint: `app/models/weights/forgery_global_v1.pt` (29,053,453 bytes)
   - Architecture: `MobileNetV2` + `Dropout(0.3)` + `Linear(1280, 128)` + `ReLU` + `Dropout(0.2)` + `Linear(128, 2)`
   - Status: Verified active in `eval()` mode.
2. **Local Model V2:**
   - Checkpoint: `app/models/weights/forgery_local_v2.pt` (29,044,793 bytes)
   - Architecture: Identical classification head matching high-resolution patch training.
   - Status: Verified active in `eval()` mode.
3. **Calibrated Fusion Config:**
   - Checkpoint: `app/models/weights/forgery_fusion_v2.pt`
   - Parameters verified: `version = '2.0.0_dual_stream_fusion'`, `alpha_global = 0.60`, `alpha_local = 0.40`, `decision_threshold = 0.40`.

---

## 4. GPU Verification

- **Detection:** PyTorch detected `cuda:0` via `torch.cuda.is_available()`.
- **Device Identified:** `NVIDIA GeForce RTX 5050 Laptop GPU` (Blackwell architecture, compute capability `sm_120`).
- **Precision:** Accelerated with mixed-precision using `torch.amp.autocast('cuda')`.
- **CPU Fallback:** Tested via `_get_dual_stream_models(preferred_device="cpu")` and verified that CPU fallback operates reliably without runtime exceptions.
- **Device Logging:** Explicitly logged at service startup:
  ```text
  [INFO] app.services.cnn_forgery_service: CUDA detected: NVIDIA GeForce RTX 5050 Laptop GPU (using cuda:0)
  ```

---

## 5. Preprocessing Verification

Training and inference pipelines are 100% consistent:
- **Color Format:** RGB (`Image.open().convert("RGB")`).
- **Resolution:** $224 \times 224$ via `torchvision.transforms.Resize((224, 224))`.
- **Normalization:** ImageNet distribution standard (`mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]`).
- **Tensor Format:** 4D tensors `[1, 3, 224, 224]` for global and `[9, 3, 224, 224]` for batched local patches.
- **Softmax Handling:** `torch.softmax(logits, dim=1)[:, 1]` targeting Class 1 (tampered).

---

## 6. Local Patch Verification

- **Patch Strategy:** Blind $3 \times 3$ grid tiling yielding exactly 9 crops per document.
- **Zero Coordinates Required:** The local patch stream does **not** consume or require ground-truth coordinates, bounding boxes, annotations, or attack labels.
- **Ordering:** Row-major order ($r \in [0, 1, 2], c \in [0, 1, 2]$).
- **Resolution Invariance:** Grid dimensions adapt dynamically ($gw = w // 3, gh = h // 3$) accommodating any document aspect ratio or resolution.

---

## 7. Fusion Verification

- **Calibrated Formula:**  
  $$P_{\text{fused}} = 0.60 \times P_{\text{global}} + 0.40 \times \max_{i=1..9}(P_{\text{patch\_i}})$$
- **Score Scale:** $S_{\text{cnn}} = round(P_{\text{fused}} \times 100.0, 2)$
- **Decision Threshold:** $T = 0.40$ ($S_{\text{cnn}} \ge 40.0 \implies \text{triggered} = \text{True}$)
- **Uncertainty Zone:** $0.35 \le P_{\text{fused}} \le 0.55 \implies \text{uncertain} = \text{True}$
  - Explicit warning appended: `[UNCERTAIN_CLASSIFICATION: Score within decision boundary zone (0.35-0.55), manual review recommended]`

---

## 8. API Verification

FastAPI endpoints verified under authenticated and unauthenticated states:
1. **`/api/tampering/cnn-score`:**
   - Status: HTTP 200
   - Response Keys: `cnn_score`, `model`, `triggered`, `detail`, `error`, `tamper_probability`, `global_probability`, `local_peak_probability`, `local_mean_probability`, `patch_probabilities`, `uncertain`, `mode`, `model_version`, `device`
2. **`/api/tampering/analyze`:**
   - Status: HTTP 200
   - Multi-signal fusion incorporating ELA, photo region, copy-move, stamp, and CNN forgery checks.
3. **`/api/risk/assess`:**
   - Status: HTTP 200
   - Consolidates OCR, validation, tampering, biometrics, and registry checks into composite score with explanation and digital audit persistence.

---

## 9. End-to-End Tests

Verified in `tests/integration/test_v2_end_to_end_categories.py`:

| Category | Input Scenario | Observed Pipeline Behavior | Status |
|---|---|---|---|
| **1. Genuine Document** | Clean passport with consistent fields | Low forgery score (< 40.0), valid validation, LOW risk, CLEAR decision | **PASSED** |
| **2. Obvious Forged Document** | High-contrast spliced / copy-move sample | CNN and forensic fusion trigger, score elevated, HOLD decision | **PASSED** |
| **3. Localized Tampered** | Altered text / name / DOB field | High-res local patch captures localized anomaly ($\max P_l \ge 0.70$), score elevated | **PASSED** |
| **4. MIDV-Style Localized** | MIDV-FCDV localized benchmark specimen | Blind $3 \times 3$ grid tiling flags tampered zone without bounding boxes | **PASSED** |
| **5. Unsupported Document** | Non-document (receipt / ticket) | Document classifier routes to `UNSUPPORTED_DOCUMENT_MANUAL_REVIEW` | **PASSED** |
| **6. Corrupted Image** | Truncated / malformed image bytes | Safe failure mode activated: score 50.0, manual review flag, no crash | **PASSED** |
| **7. Low-Quality Image** | Heavily blurred / poor lighting image | Image quality gate flags blur issue, reduces intake quality score | **PASSED** |
| **8. Missing Face** | Document without photo / missing face | Face detector reports `match=None`, flags unperformed check safely | **PASSED** |
| **9. Multiple Faces** | Multiple faces detected on document | Face detector flags multiple face anomaly, prevents spoofing | **PASSED** |
| **10. Malformed MRZ** | Tampered MRZ check digits | MRZ validator rejects checksum, triggers validation failure flag | **PASSED** |
| **11. Conflicting Historical Records** | Contradicting DOB for existing person | Cross-document engine detects contradiction, adds +30 points, raises conflict flag | **PASSED** |

---

## 10. Regression Tests

Pytest test suite execution:
```bash
python -m pytest tests/ -v
```
**Results:**
- **Total Tests Collected:** 127
- **Total Tests Passed:** 127
- **Total Tests Failed:** 0
- **Total Warnings:** 6 (external library deprecations: `skimage.io`, `torch.ao.quantization`)
- **Execution Time:** 23.45 seconds

---

## 11. Security Tests

- **Upload Size Limits:** Verified 15 MB limit enforced in `save_upload_to_temp()`.
- **MIME & Magic-Byte Validation:** Reject non-image and executable payloads (`HTTP 415`).
- **Decompression Bomb Protection:** Configured with `Image.MAX_IMAGE_PIXELS = 100_000_000`.
- **Authentication:** Enforced via Bearer JWT and `X-API-Key` headers (`HTTP 401` on missing credentials).
- **Authorization & RBAC:** Enforced role separation (admin vs. officer, `HTTP 403` on restricted endpoints).
- **Audit Logging:** Tamper-evident SHA-256 hash chaining committed to database upon each screening.

---

## 12. Latency Benchmarks

Measured over 25 consecutive end-to-end executions on the NVIDIA GeForce RTX 5050 GPU:

| Subsystem Component | Mean Latency | P50 (Median) | P90 | P95 | P99 |
|---|---|---|---|---|---|
| **Global Inference** ($1 \times 3 \times 224 \times 224$) | 12.44 ms | 13.41 ms | 14.97 ms | 15.35 ms | 15.63 ms |
| **Local Inference** ($9 \times 3 \times 224 \times 224$) | 25.21 ms | 29.29 ms | 29.85 ms | 30.19 ms | 30.67 ms |
| **Dual-Stream Fusion & Thresholding** | 0.01 ms | 0.01 ms | 0.01 ms | 0.01 ms | 0.01 ms |
| **Complete Forgery Subsystem (V2)** | 59.49 ms | 61.00 ms | 65.20 ms | 69.22 ms | 76.24 ms |
| **Preprocessing & Image Quality** | 13.48 ms | 13.56 ms | 14.81 ms | 14.97 ms | 16.62 ms |
| **Document Classification** | 857.55 ms | 865.47 ms | 895.49 ms | 896.20 ms | 900.27 ms |
| **Tampering Multi-Signal Fusion** | 143.54 ms | 138.66 ms | 150.99 ms | 157.92 ms | 290.59 ms |
| **OCR & MRZ Extraction** | 1254.72 ms | 1182.73 ms | 1243.07 ms | 1261.93 ms | 2588.49 ms |
| **Rule Validation** | 0.13 ms | 0.11 ms | 0.16 ms | 0.19 ms | 0.45 ms |
| **Consolidated Risk Engine** | 0.05 ms | 0.04 ms | 0.06 ms | 0.06 ms | 0.09 ms |
| **Database & Cryptographic Audit** | 17.33 ms | 11.37 ms | 39.98 ms | 54.35 ms | 64.89 ms |
| **Total End-to-End Pipeline** | **2346.30 ms** | **2279.42 ms** | **2350.30 ms** | **2364.81 ms** | **3851.04 ms** |

*Note: Forgery detection executes in ~61 ms on RTX 5050 GPU, representing only ~2.6% of the end-to-end screening latency.*

---

## 13. Failures Discovered During Integration

1. **PyTorch 2.6 Weights Loading Policy:**
   - *Discovery:* Default PyTorch 2.6+ `torch.load` defaults to `weights_only=True`, rejecting state dicts with numpy scalar metadata.
   - *Resolution:* Added explicit `weights_only=False` across all model and fusion loading calls.
2. **Pydantic v2 Namespace Conflict:**
   - *Discovery:* Adding `model_version` to `CNNScoreResponse` emitted a Pydantic namespace warning (`protected namespace "model_"`).
   - *Resolution:* Added `model_config = {"protected_namespaces": ()}` to `CNNScoreResponse`.
3. **Deprecated Autocast API:**
   - *Discovery:* `torch.cuda.amp.autocast()` emitted deprecation warnings in PyTorch 2.14.
   - *Resolution:* Updated to modern standard `torch.amp.autocast('cuda')`.
4. **ORM Column Mismatch in Test:**
   - *Discovery:* `Person` model uses `primary_name`, not `full_name`.
   - *Resolution:* Aligned integration test harness with schema definition.

---

## 14. Fixes Applied

All discoveries were systematically fixed, tested, and validated:
1. `cnn_forgery_service.py`: Refactored to complete Dual-Stream V2 architecture with GPU acceleration, CPU fallback, and safe failure behavior.
2. `schemas.py`: Synchronized API models with V2 telemetry fields.
3. `test_forgery_v2.py`: Added 11 regression tests covering all edge and failure cases.
4. `test_v2_end_to_end_categories.py`: Added 11 end-to-end integration tests.
5. `benchmark_screening_pipeline.py`: Added isolated latency benchmarking.

---

## 15. Final Status

```
INTEGRATION PASSED
```

The Dual-Stream V2 document forgery detector is integrated into the production backend, rigorously tested, fully functional on the RTX 5050 GPU, safe against missing weights and corrupted input, and ready for deployment.
