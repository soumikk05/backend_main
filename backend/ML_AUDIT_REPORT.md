# MASTER ML & COMPUTER VISION AUDIT REPORT
**Project:** AI-Based Fake Identity & Document Screening System  
**Problem Statement:** SIH PS-26188  
**Repository:** `soumikk05/backend_main`  
**Date of Audit:** 2026-09-02  
**Audit Scope:** Deep-learning models, classical CV heuristics, OCR, biometrics, datasets, leakage analysis, and forensic fusion logic.  
**Ground Truth Policy:** Strictly verified against actual code and files on disk. Old reports, README claims, and filenames are treated as unverified unless validated in active implementation.

---

## 1. IDENTIFY EVERY ML / AI / CV COMPONENT

| # | Component Name | Exact File Path | Invocation Function / Class | Category | Framework / Library | Model / Algorithm Architecture | Training vs Inference | Pretrained vs From Scratch | Weights Location | Input Format | Output Format | Threshold / Operating Point | Affects Decision? | Stored in DB? | Status in Code |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Document Classifier** | `backend/app/services/document_classifier.py` | `classify_document()` -> `_load_model()` | Deep Learning | TensorFlow / Keras | 2-stage Conv2D (16->32 filters) + Dense(64) + Softmax(5) | Runtime inference (Training in `train_document_classifier.py`) | Trained from scratch on converted MIDV-500 frames | `backend/ml_artifacts/document_classifier.keras` | Preprocessed RGB image `(1, 224, 224, 3)` (Note: trained at `128x128`) | Class label string + confidence float | Confidence $\ge 0.50$ | Yes (routes OCR schema; doc type stored) | Yes (`screening_records.document_type`) | **Active** (falls back to keyword OCR if model missing or $<0.50$) |
| 2 | **Document Keyword Classifier (Fallback)** | `backend/app/services/document_classifier.py` | `classify_document()` | Rule-based logic | Python / RegExp | Keyword matching rules (`"passport"`, `"visa"`, `"driving licence"`, etc.) | Runtime inference | Heuristic rule-based | None | OCR text string from `read_document_text()` | Doc type + pseudo-confidence float ($0.50 + 0.12 \times \text{hits}$) | Score $\ge 0.50$ | Yes | Yes | **Active** (primary fallback if neural classifier $<0.50$) |
| 3 | **MobileNetV2 Forgery Patch Classifier** | `backend/app/services/cnn_forgery_service.py` | `score_image_forgery_cnn()` -> `_get_forgery_model()` | Deep Learning | PyTorch / Torchvision | MobileNetV2 backbone + Dropout(0.3) + Linear(in, 64) + ReLU + Linear(64, 1) + Sigmoid | Runtime inference (Training in `train_forgery_cnn.py`) | MobileNetV2 pretrained backbone fine-tuned | `backend/app/models/weights/forgery_mobilenet_v2.pt` | Grid cropped patches normalized ImageNet stats `(1, 3, 128, 128)` | Scalar probability per patch $[0.0, 1.0]$ | Blended CNN score $\ge 45.0$ flags triggered; score $\ge 70.0$ triggers tampering override | Yes (weighted into tampering score; $\ge 70.0$ forces `is_tampered=True`) | Yes (`tampering_result`) | **Active** |
| 4 | **Multi-Frequency Residual / Spatial Anomaly Detector** | `backend/app/services/cnn_forgery_service.py` | `score_image_forgery_cnn()` | Computer Vision Heuristic | NumPy / PIL / OpenCV | Grid patch mean diff, patch variance standard deviation, overall ELA mean diff | Runtime calculation | Statistical heuristic | None | Full RGB image + resaved JPEG at quality 90 | Statistical component score float | Blended into CNN score (40% stat + 60% neural) | Yes | Yes (embedded in `tampering_result`) | **Active** |
| 5 | **Error Level Analysis (ELA)** | `backend/app/services/tampering_service.py` | `_error_level_analysis()` | Computer Vision Heuristic | PIL / NumPy | Pixel-wise absolute difference between original and resaved JPEG (quality 90) | Runtime calculation | Classical compression forensic | None | Document file path | Continuous score $[0.0, 100.0]$ | Mean diff $>12.0$ or Max diff $>100.0$ | Yes (Weight = 0.25 in tampering fusion) | Yes (`tampering_result.signals.ela`) | **Active** |
| 6 | **Photo Replacement / Boundary Seam Detector** | `backend/app/services/tampering_service.py` | `_photo_region_analysis()` | Classical CV / Heuristic | OpenCV / Haar Cascade | Haar face detection + Canny boundary edge density + Laplacian noise variance ratio + localized ELA delta | Runtime calculation | Multi-signal CV heuristic using pretrained Haar cascade | Pretrained XML (`haarcascade_frontalface_default.xml`) | Document file path | Continuous score $[0.0, 100.0]$, bounding box, boolean `triggered` | Score $\ge 45.0$; Seam edge $>0.28$, Noise ratio outside $[0.4, 2.5]$, ELA delta $>8.0$ | Yes (Weight = 0.20; hard override: if triggered, forces `is_tampered=True` and risk score $\ge 80.0$) | Yes (`tampering_result.checks`) | **Active** |
| 7 | **ORB Copy-Move Duplication Detector** | `backend/app/services/tampering_service.py` | `_copy_move_detection()` | Classical CV / Feature Matching | OpenCV | ORB feature extraction (1500 keypoints) + BFMatcher (Hamming, $k=2$) | Runtime calculation | Classical keypoint descriptor matching | None | Grayscale image | Continuous score $[0.0, 100.0]$ | Hamming distance $<40$, spatial separation $>40\text{px}$, matched pairs $\ge 10$ | Yes (Weight = 0.20; if triggered, forces `is_tampered=True`) | Yes (`tampering_result.checks`) | **Active** |
| 8 | **Stamp Forgery & Morphological Analyzer** | `backend/app/services/tampering_service.py` | `_stamp_region_analysis()` | Classical CV / Heuristic | OpenCV | HSV ink color thresholding (red/blue/violet) + contour filtering + Canny edge density | Runtime calculation | Morphological color segmentation | None | BGR image | Score (80.0 if suspicious stamps $>0$, else 10.0 or 0.0) | Stamp radius $15-120\text{px}$, aspect ratio $0.6-1.4$, edge density $>0.35$ | Yes (Weight = 0.10) | Yes (`tampering_result.checks`) | **Active** |
| 9 | **EXIF / Metadata Forensics** | `backend/app/services/tampering_service.py` | `_exif_analysis()` | Non-ML Utility / Rule-based | PIL (`ExifTags`) | Keyword matching on Software metadata tag + DateTime discrepancy check | Runtime inspection | Rule-based metadata parser | None | JPEG/TIFF image metadata | Continuous score $[0.0, 100.0]$ | Software keyword match (Photoshop, GIMP, Canva, etc.) or DateTime mismatch | Yes (Weight = 0.10) | Yes (`tampering_result.checks`) | **Active** |
| 10 | **Forensic ELA Heatmap & Localization** | `backend/app/tampering/forensics.py` | `create_ela_heatmap()` | Classical CV / Image Processing | OpenCV / PIL / NumPy | 95th percentile thresholding on ELA diff + contour bounding boxes/polygons + Jet colormap | Runtime generation | Classical visual heuristic | None | Document image | PNG heatmap saved to disk + bounding boxes list | Contours with area $>120$ and $<80\%$ of image area | No direct score impact; visual evidence artifact only | Stored as file path in DB/response | **Active** |
| 11 | **MRZ Extraction Engine** | `backend/app/services/ocr_service.py` | `_try_passporteye()` | OCR / Computer Vision | `passporteye` (Tesseract backend) | Morphological MRZ band localization + OCR character recognition | Runtime inference | Pretrained Tesseract OCR | System Tesseract installation | Document image path | Parsed dictionary of MRZ fields + character confidence | MRZ OCR confidence threshold $\ge 30$ | Yes (populates identity fields & validates checksums) | Yes (`extracted_fields`) | **Active** (routes first for passports/visas) |
| 12 | **General Text OCR Engine** | `backend/app/services/ocr_service.py` | `_extract_via_easyocr()` | Deep Learning (OCR) | EasyOCR (PyTorch) | CRAFT (text detection) + CRNN (text recognition via ResNet + BiLSTM + CTC) | Runtime inference | Pretrained EasyOCR weights (`english_g2`) | Auto-downloaded PyTorch cache (`~/.EasyOCR`) | Document image path | List of `(bounding_box, text, confidence)` tuples | Internal EasyOCR detection thresholds | Yes (provides all text fields for non-MRZ docs or fallback) | Yes (`extracted_fields`) | **Active** |
| 13 | **Face Verification Model** | `backend/app/services/face_service.py` | `verify_faces()` -> `DeepFace.verify()` | Biometric Deep Learning | DeepFace / Keras / TensorFlow | VGG-Face (224x224 input, 26 layers, 4096-d / 512-d representations) | Runtime inference | Pretrained weights | `~/.deepface/weights/vgg_face_weights.h5` | 2 image paths (document photo crop & live selfie) | Distance float, boolean `verified`, similarity float | Cosine distance threshold $= 0.40$ (Similarity $= 1.0 - \text{distance}$) | Yes (Mismatch adds 100 risk points; forces risk score $\ge 75.0$) | Yes (`face_result`) | **Active** (when selfie is uploaded) |
| 14 | **Face Detection & Pre-Cropper** | `backend/app/services/face_service.py` | `crop_face_region()` & `_detect_faces_count()` | Pretrained Classical ML | OpenCV | Haar Feature-based Cascade Classifier (`haarcascade_frontalface_default.xml`) | Runtime inference | Pretrained Haar cascades | OpenCV data directory | Grayscale image array | Bounding box `(x, y, w, h)` of largest face, face count | `scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)` | Yes (Blocks comparison if $>1$ face detected in doc or selfie) | No | **Active** |
| 15 | **Biometric Face Embeddings** | `backend/app/services/face_service.py` | `face_embedding()` -> `DeepFace.represent()` | Biometric Deep Learning | DeepFace / TensorFlow | VGG-Face embedding representation layer | Runtime inference | Pretrained weights | `~/.deepface/weights/vgg_face_weights.h5` | Selfie image path | 512-dimensional float vector + SHA-256 hash | Vector extraction | Indirect (registers vector into database for clustering) | Yes (`face_embeddings` table) | **Active** |
| 16 | **Biometric Identity Clustering** | `backend/app/services/registry_service.py` | `detect_identity_cluster()` | Classical ML / Metric Distance | Python math / NumPy | Exact nearest-neighbor cosine similarity scan over stored embeddings (up to 500 records) | Runtime calculation | Metric comparison | None | 512-d vector from current selfie against database rows | Boolean `suspicious`, matches list with similarities | Low $\ge 0.82$ (15 pts), Med $\ge 0.90$ (25 pts), High $\ge 0.95$ (35 pts) | Yes (Adds 15 to 35 points directly to composite risk score) | Yes (`identity_clusters` table) | **Active** |
| 17 | **Software Temporal Liveness** | `backend/app/services/liveness_service.py` | `check_liveness()` | Classical CV Heuristics | OpenCV | Multi-cascade tracking (`frontalface`, `eye`, `smile`) + inter-frame Laplacian difference + specular glare | Runtime inspection | Pretrained Haar cascades + heuristic logic | OpenCV cascade XMLs | Video file or list of image frames | Liveness score $[0.0, 95.0]$, boolean `passed`, signals | Frame count $>1$, Inter-frame diff $\ge 0.8$, Glare $<0.08$, Score $\ge 50.0$ | Yes (Failure penalizes risk score via quality/liveness intake) | Yes (`face_result.liveness`) | **Active** (Interactive challenge-response) |
| 18 | **Image Quality Assessment Gate** | `backend/app/services/image_quality.py` | `assess_image_quality()` | Classical CV / Statistical Calculation | OpenCV / NumPy | Laplacian variance (blur/noise), Hough lines (skew), HSV thresholding (glare/shadow), Canny (edges) | Runtime calculation | Heuristic threshold equations | None | Input document image | Quality score $[0.0, 100.0]$, boolean `acceptable`, issues list | Minimum acceptable quality score $= 45.0$; Blur $<80$, Min dimension $<480$ | Yes (If unacceptable, **aborts pipeline immediately** with Risk=100) | Yes (`quality_result`) | **Active** |
| 19 | **Perspective Rectification** | `backend/app/services/perspective.py` | `correct_perspective()` | Computer Vision Geometric Transformation | OpenCV / NumPy | Gaussian blur + Canny edges + `findContours` + `approxPolyDP` (4-point polygon) + `warpPerspective` | Runtime calculation | Deterministic computational geometry | None | Input document image | Transformed rectified image `np.ndarray`, boolean `was_corrected` | Contour area $\ge 15\%$ of image; polygon must have exactly 4 vertices | Indirect (improves downstream OCR/tampering accuracy) | Stored as corrected image in evidence storage | **Active** |
| 20 | **Document Image Duplicate Fingerprinting** | `backend/app/utils/image_utils.py` | `compute_image_sha256()` | Cryptographic Hashing | Python `hashlib` | SHA-256 block hashing | Runtime calculation | Deterministic cryptography | None | Raw file bytes | 64-character hexadecimal hash | Exact hash match collision | Yes (Replayed image with different doc number flags 80 risk points) | Yes (`screening_records.image_hash`) | **Active** |

---

## 2. DOCUMENT CLASSIFIER — COMPLETE AUDIT

### Pipeline Structure
The document classification pipeline uses a dual-engine architecture:
1. **Neural Classifier Engine:** A custom Convolutional Neural Network written in TensorFlow/Keras (`document_classifier.py`).
2. **Text Keyword Heuristic Engine:** A regex/keyword scanner executing over raw OCR output (`document_classifier.py`).

### Dataset Audit
* **Dataset Preparation Script:** `backend/scripts/prepare_document_classification_dataset.py`
* **Training Script:** `backend/scripts/train_document_classifier.py`
* **Raw Source Directory:** `midv500_data/midv500` (contains 8 subdirectories: `01_alb_id`, `02_aut_drvlic_new`, `03_aut_id_old`, `04_aut_id`, `05_aze_passport`, `06_bra_passport`, `07_chl_id`, `08_chn_homereturn`).
* **Source Images Verified in Repository:**
  * `passport`: 2 source folders (`05_aze_passport`, `06_bra_passport`)
  * `national_id`: 4 source folders (`01_alb_id`, `03_aut_id_old`, `04_aut_id`, `07_chl_id`)
  * `driving_license`: 1 source folder (`02_aut_drvlic_new`)
  * `permit`: 1 source folder (`08_chn_homereturn`)
  * `visa`: **0 source folders in MIDV-500**. Script line 41 explicitly states:  
    `"Note: 'visa' is supported by the backend but MIDV-500 lacks visa source data."`  
    **Crucial Finding:** The training script maps 5 classes (`["passport", "visa", "national_id", "driving_license", "permit"]`), but class index 1 (`visa`) has **ZERO** samples in the training manifest generated by `prepare_document_classification_dataset.py`.
* **Sample Selection & Limits:** The preparation script caps selected images at 80 TIF images per category.
* **Split Strategy:** Frame-level 70% Train / 15% Validation / 15% Test.
* **Leakage in Splitting:** **CRITICAL**. Frames from the exact same physical document (e.g., video clips of `05_aze_passport` at different camera angles) are randomized and split across train, val, and test. The model evaluates on the identical document it trained on, differing only by video frame tilt/lighting.

### Preprocessing Audit
* **Input Resolution in Trainer:** Preprocessed at `(128, 128)` in `train_document_classifier.py`.
* **Input Resolution in Inference:** Preprocessed at `target_size=(224, 224)` in `document_classifier.py`.  
  **Discrepancy:** The training script fed `(128, 128)` tensors into the input layer:
  ```python
  layers.Conv2D(16, (3, 3), activation='relu', input_shape=(128, 128, 3))
  ```
  At runtime, `preprocess_image_for_classifier(image, target_size=(224, 224))` creates `(1, 224, 224, 3)`. In the saved Keras model, Keras errors out or misaligns receptive fields if the input resolution differs from the training geometry.
* **Color Space:** BGR to RGB via OpenCV.
* **Normalization:** Direct division by 255.0 to float32 $[0.0, 1.0]$.
* **Data Augmentation:** **None**. Zero rotations, shears, crops, or color jitter during training.

### Model Architecture Audit
* **Framework:** TensorFlow 2.15 / Keras.
* **Model Type:** Custom Lightweight Sequential ConvNet (Not MobileNet, despite comments and labels calling it `mobilenet_cnn` in `document_classifier.py`).
* **Layer Specification:**
  ```python
  models.Sequential([
      layers.Conv2D(16, (3, 3), activation='relu', input_shape=(128, 128, 3)),
      layers.MaxPooling2D((2, 2)),
      layers.Conv2D(32, (3, 3), activation='relu'),
      layers.MaxPooling2D((2, 2)),
      layers.Flatten(),
      layers.Dense(64, activation='relu'),
      layers.Dense(5, activation='softmax')
  ])
  ```
* **Trainable Parameters:** Trained entirely from scratch (no ImageNet backbone).
* **Loss Function:** `sparse_categorical_crossentropy`.
* **Optimizer:** Adam (default learning rate $1\times 10^{-3}$).
* **Batch Size:** 32.
* **Epochs:** **2 epochs only** (hardcoded in `train_document_classifier.py`: `print("Training model for 2 epochs...")`).
* **Regularization:** None (no Dropout, no BatchNormalization, no weight decay).

### Evaluation & Baseline Performance
* **Evaluation File:** The file `backend/reports/classifier_metrics.json` is **missing/uncommitted** in the current checkout.
* **Test Performance:** Untrustworthy because:
  1. The test set contains video frames of the exact same 8 documents present in the training set.
  2. The `visa` category has zero training instances, guaranteeing 0% recall on genuine visas for the neural branch.
  3. The model was trained for only 2 epochs on ~240 images without data augmentation.
* **Fallback Operation:** In practice, because the neural model confidence on unseen documents frequently falls below $0.50$, the system defaults to the OCR keyword heuristic scanner in `document_classifier.py`.

---

## 3. FORGERY / TAMPERING CNN — COMPLETE AUDIT

### Component Overview
* **Inference Service:** `backend/app/services/cnn_forgery_service.py`
* **Training Script:** `backend/scripts/train_forgery_cnn.py`
* **Dataset Loader:** `backend/app/tampering/dataset_loader.py`
* **Evaluation Script:** `backend/scripts/evaluate_forgery_cnn.py`
* **Saved Weights File:** `backend/app/models/weights/forgery_mobilenet_v2.pt` (Size: 9,468,833 bytes / ~9.5 MB).

### Dataset Origin & Manipulation Synthesis
In `train_forgery_cnn.py`, the dataset pipeline does not train on real-world forged documents. Instead, it expects genuine images under `dataset/genuine/{passport, visa, national_id, driving_license}` and real tampered examples under `dataset/tampered/`.

**Physical File Inventory on Disk:**
* `dataset/tampered/`: **Does not exist** on disk (`Test-Path dataset/tampered` returns `False`).
* `dataset/genuine/passport`: 10 images (all from `05_aze_passport`).
* `dataset/genuine/id`: 10 images (all from `01_alb_id`).
* `dataset/genuine/license`: 10 images (all from `02_aut_drvlic_new`).
* `dataset/genuine/visa`: Contains `archive/visa dataset/` with subfolders for `canada`, `china`, `japan`, `korea`, `usa`.
* **Synthetic Attack Generators (Applied On-the-Fly):**
  1. `_splice(img, donor)`: Pastes a scaled rectangular patch ($w/4, h/4$) from a donor image.
  2. `_copy_move(img)`: Crops patch ($w/5, h/5$) from $(sx, sy)$ and pastes to $(tx, ty)$ within the same image.
  3. `_localized_blur(img)`: Crops patch ($w/3, h/3$) and applies `ImageFilter.GaussianBlur(radius=3)`.
  4. `_localized_noise(img)`: Adds Gaussian noise $\mathcal{N}(0, 20)$ to a $(w/3, h/3)$ rectangular region.
  5. `_recompression_ghost(img)`: Recompresses a $(w/3, h/3)$ region to JPEG at quality 30, 40, or 95.

**Synthetic vs. Real-World Breakdown:**
* **Real-World Forgeries:** **0**. No genuine fraudulent documents from casework or law enforcement exist in the training set.
* **Synthetic Forgeries:** **100%**. All tampered samples are generated by the five PIL functions above.
* **Fine-Grained Attacks (DOB edit, Name edit, Number edit, Stamp forgery):** The comments list these classes, but no code generates realistic text replacement or font manipulation during CNN training. The operations are purely crude block pastes, blurs, and noise.

### Split Quality & Patch Generation
* **Dataset Loader Logic:** In `dataset_loader.py`, files are collected by folder name and shuffled with a fixed random seed `seed:folder`. The 70/15/15 split is performed at the **image level**.
* **Data Leakage:** **CRITICAL**. Because the genuine images in `dataset/genuine/passport`, `id`, and `license` are different camera angles of the exact same physical ID cards (`05_aze_passport`, `01_alb_id`, `02_aut_drvlic_new`), frames from the same identity appear in both train and validation/test splits. Furthermore, synthetic tampering applies on-the-fly splices using donor images from the same shared pool.
* **Patch Sampling During Runtime Inference:**
  * In `cnn_forgery_service.py`, runtime inference divides the incoming image into a dynamic grid:
    ```python
    grid_rows, grid_cols = max(2, min(6, h // 80)), max(2, min(6, w // 80))
    ```
  * It crops each grid cell, resizes it to `(128, 128)`, and feeds it to MobileNetV2.
  * It computes:
    ```python
    neural_component = (max_neural_prob * 65.0) + (avg_neural_prob * 35.0)
    ```
  * Then it blends the neural score with spatial ELA statistics:
    ```python
    raw_score = (neural_component * 0.60) + (stat_component * 0.40)
    ```

### Model Architecture
* **Backbone:** PyTorch `torchvision.models.mobilenet_v2(weights=MobileNet_V2_Weights.DEFAULT)`.
* **Classifier Head:**
  ```python
  nn.Sequential(
      nn.Dropout(p=0.3),
      nn.Linear(1280, 64),
      nn.ReLU(),
      nn.Linear(64, 1),
      nn.Sigmoid()
  )
  ```
* **Loss Function:** Binary Cross Entropy (`nn.BCELoss()`).
* **Optimizer:** Adam, learning rate $1\times 10^{-4}$.
* **Epochs:** 15 epochs, batch size 16.
* **Decision Threshold:** $0.50$ on probability; continuous score scaled to $0-100$. Triggered flag set at $\ge 45.0$.

### Evaluation Metrics
In `backend/reports/tampering_metrics.json` and `backend/reports/tampering_metrics.csv`:
```json
{
  "status": "INSUFFICIENT_DATA",
  "samples": 0,
  "accuracy": null,
  "precision": null,
  "recall": null,
  "f1": null,
  "roc_auc": null,
  "confusion_matrix": null,
  "per_attack_breakdown": {}
}
```
**Finding:** The reported evaluation state in the repository is officially `INSUFFICIENT_DATA` with 0 samples evaluated.

---

## 4. TAMPERING FUSION AUDIT

### Mathematical & Logical Implementation
The fusion logic in `backend/app/services/tampering_service.py` computes a unified composite tampering score from 6 forensic signals.

#### Signal Scores
1. **$S_{\text{ELA}}$ (Error Level Analysis):**
   $$\text{diff} = |\text{Image}_{\text{orig}} - \text{Image}_{\text{JPEG90}}|$$
   $$S_{\text{mean}} = \min\left(100.0, \frac{\mu(\text{diff})}{12.0} \times 60.0\right), \quad S_{\text{max}} = \min\left(100.0, \frac{\max(\text{diff})}{100.0} \times 40.0\right)$$
   $$S_{\text{ELA}} = \min(100.0, S_{\text{mean}} + S_{\text{max}})$$
   *Triggered if:* $\mu(\text{diff}) > 12.0$ or $\max(\text{diff}) > 100.0$.

2. **$S_{\text{Photo}}$ (Photo Replacement Analysis):**
   * Seam edge density along perimeter border mask: $D_{\text{border}} = \frac{\text{Canny edges in border}}{\text{Total border pixels}}$. Flagged if $D_{\text{border}} > 0.28$ (+45 pts).
   * Noise ratio: $R_{\text{noise}} = \frac{\text{Var}(\text{Laplacian}(\text{photo}))}{\text{Var}(\text{Laplacian}(\text{doc background}))}$. Flagged if $R_{\text{noise}} > 2.5$ or $R_{\text{noise}} < 0.4$ (+30 pts).
   * Localized ELA delta: $|\mu(\text{diff}_{\text{photo}}) - \mu(\text{diff}_{\text{doc}})|$. Flagged if delta $> 8.0$ (+25 pts).
   $$S_{\text{Photo}} = \min(100.0, \text{Points}_{\text{seam}} + \text{Points}_{\text{noise}} + \text{Points}_{\text{ELA}})$$
   *Triggered if:* $S_{\text{Photo}} \ge 45.0$.

3. **$S_{\text{CopyMove}}$ (ORB Keypoint Matching):**
   * $N_{\text{pairs}} =$ number of matched keypoints with Hamming distance $< 40$ and spatial distance $> 40\text{px}$.
   $$S_{\text{CopyMove}} = \min\left(100.0, \frac{N_{\text{pairs}}}{10} \times 100.0\right)$$
   *Triggered if:* $N_{\text{pairs}} \ge 10$.

4. **$S_{\text{Stamp}}$ (Stamp Forgery Analysis):**
   * Segment HSV ink (blue, red, violet). Find contours with area $\pi(15)^2 \le A \le \pi(120)^2$ and aspect ratio $0.6 \le w/h \le 1.4$.
   * Measure edge density $D_{\text{edge}} = \frac{\text{Canny edges}}{w \times h}$. Suspicious if $D_{\text{edge}} > 0.35$.
   $$S_{\text{Stamp}} = 80.0 \text{ if any suspicious stamps, else } 10.0 \text{ (if normal stamps found) or } 0.0$$
   *Triggered if:* Suspicious stamp count $> 0$.

5. **$S_{\text{CNN}}$ (MobileNetV2 + Spatial Anomaly):**
   * $\text{Stat} = 1.6 \cdot \max(\mu_{\text{patch}}) + 0.12 \cdot \sigma(\sigma^2_{\text{patch}}) + 1.1 \cdot \mu(\text{diff})$.
   * $\text{Neural} = 65.0 \cdot \max(P_{\text{patch}}) + 35.0 \cdot \text{mean}(P_{\text{patch}})$.
   $$S_{\text{CNN}} = \min(100.0, \max(0.0, 0.60 \cdot \text{Neural} + 0.40 \cdot \text{Stat}))$$
   *Triggered if:* $S_{\text{CNN}} \ge 45.0$.

6. **$S_{\text{EXIF}}$ (Metadata Forensics):**
   * $+70.0$ if software matches editing keywords (`photoshop`, `gimp`, `canva`, etc.).
   * $+15.0$ if no datetime tags present.
   * $+25.0$ if `DateTime` and `DateTimeOriginal` disagree.
   $$S_{\text{EXIF}} = \min(100.0, \text{Points})$$
   *Triggered if:* Any flags present.

#### Configuration Weights
Defined in `backend/app/config.py`:
* $W_{\text{ELA}} = 0.25$
* $W_{\text{Photo}} = 0.20$
* $W_{\text{CopyMove}} = 0.20$
* $W_{\text{CNN}} = 0.15$
* $W_{\text{Stamp}} = 0.10$
* $W_{\text{EXIF}} = 0.10$
$$\sum W = 1.00$$

#### Missing Signal Handling & Normalization
If the CNN model is missing or unavailable (`mode == "unavailable"`), the CNN signal is removed from the active set:
$$W_{\text{eff}, i} = \frac{W_i}{\sum_{j \in \text{Available}} W_j}$$
$$S_{\text{Final}} = \sum_{i \in \text{Available}} S_i \cdot W_{\text{eff}, i}$$

#### Final Decision & Overrides
In `tampering_service.py`:
```python
is_tampered = bool(
    final_score >= 45.0
    or photo_check["triggered"]
    or copy_move_check["triggered"]
    or (cnn_mode == "trained_model" and cnn_score >= 70.0)
)
```

#### Calibration Status
* **Weight Provenance:** Manually engineered heuristics.
* **Evaluation/Optimization Status:** The script `backend/scripts/evaluate_thresholds.py` prints static weights and evaluates against `dataset/raw/`, but does not optimize weights.

---

## 5. OCR / DOCUMENT CLASSIFICATION INTERACTION

### Complete Sequence & Coupling Analysis
1. **Intake Order:** `classify_document(doc_temp_path)` is executed first. If the neural classifier fails or outputs confidence $<0.50$, it calls `read_document_text()` on the fly, which spins up EasyOCR to extract words for keyword matching.
2. **Field Extraction Routing:** `extract_document_fields()` routes passports/visas to `_try_passporteye()` (Tesseract MRZ parser). If MRZ is unreadable or fails checksums, it falls back to EasyOCR.
3. **Impact on Validation & Risk Engine:** In `risk_engine.py`, OCR field confidences are averaged. The OCR component contributes 7% to the final risk score. In `validation_service.py`, if average field confidence $<0.55$, a `MEDIUM` severity failure check (`ocr_confidence`) is generated.
4. **False Tampering Potential from OCR Errors:** An OCR error does not alter physical image pixels. However, in `registry_service.py`, if OCR misreads a character in `holder_name` or `document_number`, it can trigger a false duplicate identity alert (`DUPLICATE IDENTITY CONFLICT` or `IDENTITY DOB MISMATCH`), adding up to **80 risk points**.

---

## 6. FACE VERIFICATION MODEL AUDIT

### Exact Runtime Implementation
* **File:** `backend/app/services/face_service.py`
* **Backbone Architecture:** VGG-Face deep convolutional neural network (DeepFace / TensorFlow / Keras).
* **Detector Backend:** `opencv` (`haarcascade_frontalface_default.xml`).
* **Distance Metric:** Cosine distance.
* **Pre-Cropping Logic:** To prevent DeepFace from failing on full A4 document scans, `crop_face_region()` uses Haar cascades to detect the largest face bounding box in the document, expands it by a 40% margin (`margin=0.4`), crops it, and saves a temporary JPEG file for verification.
* **Number of Faces Allowed:** Exactly 1 in document photo, exactly 1 in selfie. If $>1$ face is detected, comparison is aborted with `"MULTIPLE_FACES"`.
* **Distance & Verification Threshold:** Hardcoded in DeepFace VGG-Face cosine configuration: $\text{Threshold} = 0.40$. If $\text{Distance} \le 0.40 \implies \text{verified} = \text{True}$.
* **Missing Face Behavior:** Caught via `ValueError`, returning `match=None`, `matched=False`, and error code `"FACE_NOT_FOUND"`.
* **Embedding Vector & Storage:** Extracted via `DeepFace.represent(model_name="VGG-Face")`, generating a 512-dimensional vector saved in SQLite table `face_embeddings`. Used by `detect_identity_cluster()` in `registry_service.py` for cross-screening nearest-neighbor lookups.

---

## 7. LIVENESS MODEL / LOGIC AUDIT

### Technical Classification
**The liveness subsystem is classical computer-vision heuristics and state-machine logic over OpenCV Haar cascades.**  
It is **NOT** a deep-learning anti-spoofing neural network.

### Verification Logic & Triggers
Implemented in `backend/app/services/liveness_service.py`:
1. **Input Handling:** Accepts a video file or list of image paths.
2. **Static Image Replay Guard:** Resizes face ROIs across consecutive frames to equal dimensions. If mean diff $<0.8$ or std diff $<0.1$, flags `"STATIC_IMAGE_DETECTED"`.
3. **Texture Sharpness:** Evaluates Laplacian variance across frames.
4. **Specular Glare Penalty:** Flags specular glare if HSV Value $>250$ in $>8\%$ of pixels (-20 pts).
5. **Interactive Challenge-Response Evaluation:** Evaluates `blink` (eye cascade), `smile` (mouth cascade), or `turn_left`/`turn_right` (horizontal centroid offset).
6. **Prototype Fallback Risk:** In lines 197, 214, and 245 of `liveness_service.py`, prototype fallback overrides are present:
   ```python
   # Fallback: Haar cascades are brittle. If the sequence is captured, assume intent to pass for prototype.
   challenge_detected = True
   ```
   If Haar cascade detections fail to register a movement, the code sets `challenge_detected = True` regardless.

---

## 8. DATASET AUDIT — ALL DATA SOURCES

| Dataset Name | Purpose | Exact Path on Disk | Training Use | Validation / Test Use | Evaluation Only? | Active? | Sample Count | Document Types Present | Known Limitations |
|---|---|---|---|---|---|---|---|---|---|
| **MIDV-500 (Raw Extraction)** | Source raw document video frames | `backend/midv500_data/midv500` | Extracted into training folders | Extracted into test folders | No | Yes | 8 document folders (TIF video frame sequences) | Passports (Azerbaijan, Brazil), National IDs (Albania, Austria, Chile), Driving License (Austria), Border Permit (China) | Only 8 unique identities; no real visas; all clean scans/recordings; high cross-frame correlation |
| **MIDV-500 Genuine Subsets** | Staged clean genuine documents | `backend/dataset/genuine/` | Yes (`train_forgery_cnn.py`, `dataset_loader.py`) | Yes (`evaluate_forgery_cnn.py`) | No | Yes | `passport`: 10<br>`id`: 10<br>`license`: 10<br>`visa`: 5 country subfolders | Passports, National IDs, Driving Licenses, Visas | Extremely small genuine baseline for passport, id, license (10 files each, derived from 1 document each) |
| **Visa Dataset Archive** | Raw genuine visa scans | `backend/dataset/genuine/visa/archive/visa dataset/` | None currently linked in loader | Unused by default loaders | No | Dormant | Thousands of JPEG files in `canada`, `china`, `japan`, `korea`, `usa` | Visas only | Unstructured directory hierarchy (`archive/visa dataset/canada/doc.X.jpg`); ignored by `dataset_loader.py` |
| **Synthetic Tampered Dataset** | Forgery training and testing | Supposed to be `backend/dataset/tampered/` | Generated on-the-fly | Generated on-the-fly | No | Stored folder missing; code creates dynamically | **0 files on disk**; dynamically generated in RAM | Synthetically modified versions of genuine images | Block pastes, synthetic noise, and blurs only. No realistic font glyph alteration or high-end photoshop tampering |
| **Adversarial Perturbation Suite** | Robustness benchmarking | Generated via `generate_adversarial_dataset.py` into `dataset/adversarial/` | None | Benchmark script `evaluate_adversarial.py` | Yes | Dormant (folder not committed) | 8 perturbation classes (`blur`, `noise`, `screenshot`, `print_photo`, etc.) | Variations of images in `dataset/raw/` | Depends on images in `dataset/raw/`, which currently contains only `.gitkeep` |
| **Raw Staging Folder** | Raw staging input | `backend/dataset/raw/` | None | Staging only | Yes | Dormant | Only `.gitkeep` (0 images) | None | Empty |

---

## 9. DATA LEAKAGE AUDIT

### Overall Leakage Risk Rating: **CRITICAL**

### Concrete Evidence from Codebase:
1. **Video Frame Identity Leakage:** In `dataset/genuine/passport/`, all 10 images are frames extracted from video clips of the **same single physical Azerbaijani passport**. In `dataset_loader.py`, splitting is done at the frame level. 7 frames go to train, 1-2 to validation, 1-2 to test. The model evaluates on the identical document it trained on.
2. **Synthetic Donor Leakage:** In `train_forgery_cnn.py`, splicing donors are sampled from the same small pool. In `evaluate_forgery_cnn.py`, synthetic test samples are created using the same function on `genuine_test`.
3. **Document Classifier Preparation Leakage:** In `prepare_document_classification_dataset.py`, up to 80 TIF frames are taken per category folder, shuffled, and split 70/15/15 into `train`, `val`, and `test`. Frames from the same video clip appear in both train and test splits.

---

## 10. CURRENT PERFORMANCE BASELINE

| Component | Architecture | Dataset | Train Size | Val Size | Test Size | Accuracy | Precision | Recall | F1 Score | ROC-AUC | Decision Threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Document Classifier** | 2-stage Conv2D + Dense(64) | MIDV-500 subset | ~168 frames | ~36 frames | ~36 frames | **NOT AVAILABLE** (Metrics uncommitted) | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | Softmax argmax $\ge 0.50$ |
| **Forgery CNN** | MobileNetV2 | Synthetic + Clean genuine | 0 real tampered | 0 real tampered | 0 real tampered | **NOT AVAILABLE** (`status: INSUFFICIENT_DATA` in `tampering_metrics.json`) | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | Probability $\ge 0.50$; Score $\ge 45.0$ |
| **Face Verification** | DeepFace (VGG-Face) | Standard VGG-Face benchmark | N/A (Pretrained) | N/A | N/A | Benchmark claimed ~98% on LFW | NOT AVAILABLE in repo | NOT AVAILABLE in repo | NOT AVAILABLE in repo | NOT AVAILABLE in repo | Cosine distance $\le 0.40$ |
| **Tampering Fusion** | 6-signal hybrid heuristic | Evaluated on `dataset/raw` | N/A | N/A | 0 samples in `dataset/raw` | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | Composite score $\ge 45.0$ |
| **Software Liveness** | Cascade State Machine | Interactive Video | N/A | N/A | N/A | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | Score $\ge 50.0$ |

---

## 11. MODEL WEAKNESSES

### Weakness Ranking

#### 1. CRITICAL: Extreme Synthetic-to-Real Domain Gap in Forgery CNN
The model is trained exclusively on crude rectangular block pastes, Gaussian noise squares, and local Gaussian blurs applied to 30 genuine document images. Real forgeries feature digital font replacement, fine boundary inpainting, vector graphic modifications, and high-resolution photo swaps with feathering.

#### 2. CRITICAL: Document Identity Data Leakage
The training and testing splits are performed at the video frame level rather than at the document identity level. The model memorizes the background textures, colors, and layout of the specific 8 MIDV-500 documents.

#### 3. HIGH: Complete Absence of Visa Data in Neural Document Classifier
The neural document classifier has an output neuron for `visa`, but the training dataset script explicitly skipped visas because MIDV-500 lacks them. Any genuine visa presented to the neural classifier will be misclassified into one of the other 4 classes with arbitrary probabilities.

#### 4. HIGH: Dimension Discrepancy Between Classifier Training and Inference
`train_document_classifier.py` resized images to `(128, 128)` before compiling `input_shape=(128, 128, 3)`. At runtime, `document_classifier.py` resizes images to `(224, 224)`.

#### 5. HIGH: Brittle Haar Cascades and Hardcoded Liveness Bypass
Facial boundary inspection and interactive liveness rely on classical OpenCV Haar cascades. Because they fail under uneven lighting or dark skin tones, lines 197, 214, and 245 of `liveness_service.py` hardcode `challenge_detected = True`, rendering the liveness check completely spoofable.

#### 6. MEDIUM: Uncalibrated Static Fusion Weights
The 6 forensic weights ($0.25, 0.20, 0.20, 0.15, 0.10, 0.10$) were manually selected without mathematical calibration or cross-validation on an annotated forensic benchmark.

---

## 12. MODEL IMPROVEMENT OPPORTUNITIES (RECOMMENDATIONS FOR NEXT STAGE)

1. **Document-Level Group Splitting (GroupKFold):** Redesign dataset splitting scripts to enforce strict document-identity isolation.
2. **Transition to Standard Forensic Datasets:** Ingest established document forgery datasets such as **DocTamper** (60,000+ real and synthetic document tampering instances) or **CASIA v2.0**.
3. **Advanced Synthetic Text Manipulation:** Upgrade synthetic generation from basic block pasting to realistic text glyph inpainting using tools like `SynthText` or text-erasure diffusion models.
4. **Integrate Real Visa Data into Classification:** Incorporate the dormant images in `backend/dataset/genuine/visa/archive/visa dataset/` into `prepare_document_classification_dataset.py`.
5. **Standardize Input Tensor Geometry:** Enforce consistent resolution (e.g., $224 \times 224$) across training, validation, and production inference.
6. **Replace Haar Cascades with Modern Lightweight Deep Learning:** Replace OpenCV Haar cascades with MediaPipe Face Mesh or RetinaFace-MobileNet, and MiniVision Silent-Face-Anti-Spoofing.
7. **Empirical Forensic Weight Optimization:** Run logistic regression or Platt scaling over the 6 forensic detector outputs against an annotated validation set.

---

## 13. PRODUCTION / PROTOTYPE REALISM

| Component | Realism Classification | Justification |
|---|---|---|
| **Document Classification (Neural)** | **Needs Improvement** | Only trained for 2 epochs on 4 classes with severe video frame leakage; missing visa training data. |
| **Document Classification (Heuristic)**| **Prototype-Suitable** | Regex/keyword rules reliably identify standard passports, licenses, and IDs if OCR is clean. |
| **Forgery Detection (MobileNetV2)** | **Not Reliable Enough for Real Deployment** | Trained only on crude synthetic block splices on 30 images; will not generalize to real-world forgery. |
| **Tampering Fusion Pipeline** | **Prototype-Suitable** | ELA, ORB copy-move, photo boundary edge density, and EXIF checks provide strong demo heuristics. |
| **Face Verification (VGG-Face)** | **Prototype-Suitable** | DeepFace VGG-Face with 0.40 cosine threshold is solid for demos; production requires ArcFace/InsightFace. |
| **Software Liveness** | **Not Reliable Enough for Real Deployment** | Haar cascades are brittle, and challenge detection is hardcoded to bypass failures with `True`. |
| **Image Quality & Perspective** | **Prototype-Suitable** | 10-point quality check (Laplacian blur, skew, glare) and 4-point contour warp work reliably. |

---

## 14. EXACT FILE MAP

### Document Classification
* **Training Script:** `backend/scripts/train_document_classifier.py`
* **Dataset Preparation:** `backend/scripts/prepare_document_classification_dataset.py`
* **Dataset Loader:** Custom manifest reader in `train_document_classifier.py`
* **Model Definition:** Sequential Conv2D in `train_document_classifier.py`
* **Inference Service:** `backend/app/services/document_classifier.py`
* **Weights File:** `backend/ml_artifacts/document_classifier.keras`
* **Evaluation Script:** Embedded evaluation at end of `train_document_classifier.py`

### Forgery CNN
* **Training Script:** `backend/scripts/train_forgery_cnn.py`
* **Dataset Preparation:** Dynamic generation in `train_forgery_cnn.py` and `prepare_dataset.py`
* **Dataset Loader:** `backend/app/tampering/dataset_loader.py`
* **Model Definition:** `build_model()` in `train_forgery_cnn.py`
* **Inference Service:** `backend/app/services/cnn_forgery_service.py`
* **Weights File:** `backend/app/models/weights/forgery_mobilenet_v2.pt`
* **Evaluation Script:** `backend/scripts/evaluate_forgery_cnn.py` and `evaluate_models.py`

### OCR
* **Runtime Orchestrator:** `backend/app/services/ocr_service.py`
* **MRZ Engine:** `PassportEye` (Tesseract) in `ocr_service.py`
* **Text Engine:** `EasyOCR` (CRAFT + CRNN) in `ocr_service.py`
* **MRZ Parsing Utility:** `backend/app/utils/mrz_parser.py`
* **Configuration:** `EASYOCR_LANGS = ["en"]` in `backend/app/config.py`

### Face Verification & Biometrics
* **Runtime Orchestrator:** `backend/app/services/face_service.py`
* **Deep Biometric Model:** DeepFace VGG-Face (`model_name="VGG-Face"`)
* **Face Detector Backend:** OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`)
* **Identity Clustering Engine:** `backend/app/services/registry_service.py`
* **API Endpoints:** `backend/app/api/face_routes.py`

### Liveness Detection
* **Runtime Service:** `backend/app/services/liveness_service.py`
* **Cascades Used:** `haarcascade_frontalface_default.xml`, `haarcascade_eye.xml`, `haarcascade_smile.xml`
* **Session Storage & Challenge Router:** `backend/app/api/face_routes.py`

### Tampering Fusion & Forensics
* **Fusion Service:** `backend/app/services/tampering_service.py`
* **Heatmap & Localization:** `backend/app/tampering/forensics.py`
* **Weights & Thresholds Config:** `backend/app/config.py`
* **Evaluation Script:** `backend/scripts/evaluate_thresholds.py`

---

## 15. FINAL SUMMARY FOR ANOTHER AI

```markdown
## WHAT I CURRENTLY HAVE
A fully functional, end-to-end FastAPI backend pipeline that successfully integrates image intake,
perspective rectification, quality gates, OCR, 6-signal forensic fusion, face verification,
and risk calculation. It has comprehensive unit/integration test suites (72 passing tests)
and solid API contract definitions.

## WHAT IS ACTUALLY WORKING
- Preprocessing and image quality gates (Laplacian blur, skew, overexposure).
- Document perspective rectification via 4-point contour geometry.
- PassportEye MRZ extraction and ICAO Doc 9303 checksum validation.
- EasyOCR extraction with document-type heuristic keyword parsing.
- Classical forensic checks: ELA, ORB copy-move detection, Photo region boundary seam detection,
  and EXIF editing software detection.
- DeepFace VGG-Face 1:1 facial comparison between document crop and selfie.
- SHA-256 image duplicate detection and face embedding nearest-neighbor clustering in SQLite.

## WHAT IS ACTUALLY TRAINED
1. `document_classifier.keras`: A 2-stage custom Conv2D trained for only 2 epochs from scratch
   on ~240 MIDV-500 frames. (Visa class was never trained).
2. `forgery_mobilenet_v2.pt`: A MobileNetV2 classifier head fine-tuned for 15 epochs on 30 genuine
   document images with on-the-fly synthetic block pastes and Gaussian noise.

## WHAT DATA IS ACTUALLY USED
- Genuine training data: 30 images total (10 frames each from 3 unique documents: Azerbaijan passport,
  Albanian ID, Austrian driving license) taken from MIDV-500.
- Tampered training data: 0 real-world forgeries. 100% synthetic PIL transformations.
- A large collection of thousands of real visa documents exists in
  `dataset/genuine/visa/archive/visa dataset/` but is completely unindexed and unused by the training scripts.

## CURRENT PERFORMANCE
- Production benchmark metrics in `reports/tampering_metrics.json` are officially `INSUFFICIENT_DATA` (0 samples).
- Test accuracy numbers in documentation (e.g. 100%) were derived from a 2-sample test manifest.
- True generalization accuracy on unseen real-world identity documents is currently low and unvalidated.

## BIGGEST PROBLEMS
1. CRITICAL DATA LEAKAGE: Training and test splits split video frames of the exact same physical documents.
2. SYNTHETIC-REAL DOMAIN GAP: The forgery model has never seen a real forged document, realistic font manipulation,
   or professional digital tampering.
3. MISSING VISA CLASS: The document classifier output includes 'visa' but has zero training samples for it.
4. RESOLUTION MISMATCH: Document classifier was trained on 128x128 images but infers on 224x224 images.
5. BRITTLE LIVENESS: Relies on Haar cascades with hardcoded bypass fallbacks (`challenge_detected = True`).

## BIGGEST DATA PROBLEMS
- Dataset volume is severely deficient (only 3 unique physical documents actively fed to training loaders).
- 0 real-world forged document images exist in the training pipeline.
- No document-level grouping (GroupKFold) is implemented in dataset splitting.

## BIGGEST MODEL PROBLEMS
- The MobileNetV2 patch model classifies arbitrary grid patches rather than learning semantic document structure.
- The document classifier ConvNet lacks depth, regularization, and data augmentation.
- Forensic fusion weights are hardcoded heuristics rather than statistically calibrated parameters.

## MOST IMPORTANT THINGS TO FIX FIRST
1. Rewrite `prepare_document_classification_dataset.py` and `dataset_loader.py` to implement strict
   Document-Level Grouping so no frames from the same physical document ever cross train/val/test splits.
2. Ingest the thousands of dormant visa images from `dataset/genuine/visa/archive/visa dataset/`
   into the document classifier training manifest.
3. Fix the resolution mismatch in `document_classifier.py` to ensure training and inference resolutions match.
4. Replace crude rectangular splice generation in `train_forgery_cnn.py` with realistic font/text glyph
   modifications or train on an established open document forensics dataset (e.g., DocTamper or CASIA).
5. Replace OpenCV Haar cascades with MediaPipe Face Mesh for robust facial landmark and blink tracking.

## INFORMATION STILL MISSING
- Annotated ground-truth datasets for authentic vs. forged identity documents with pixel-level ground-truth masks.
- Empirical test benchmark results on unperturbed, unseen real-world document samples.
```
