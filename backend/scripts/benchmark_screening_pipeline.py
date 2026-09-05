"""
Comprehensive Pipeline Latency Benchmarking (Requirement 42).

Runs multi-sample screening requests to measure empirical latency:
- Preprocessing & image quality
- Document classification
- Forgery detection (MobileNetV2 on RTX 5050 GPU)
- OCR extraction & field normalization
- Rule validation & MRZ checksums
- Database persistence & tamper-evident audit logging
- Total end-to-end pipeline latency

Computes and reports:
- Mean / Average
- Median / P50
- P90, P95, P99
Saves machine-readable benchmark_results.json
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import cv2
from PIL import Image

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import cv2
from PIL import Image
import torch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db import SessionLocal
from app.services.image_quality import assess_image_quality
from app.services.document_classifier import classify_document
from app.services.cnn_forgery_service import (
    score_image_forgery_cnn,
    _get_dual_stream_models,
    generate_3x3_patches,
    _TRANSFORM,
)
from app.services.tampering_service import analyze_tampering
from app.services.ocr_service import extract_document_fields
from app.services.validation_service import validate_document
from app.services.risk_engine import compute_risk_score
from app.services.audit_service import append_audit
from app.utils.image_utils import compute_image_sha256

BENCHMARK_OUTPUT = BASE_DIR / "dataset" / "pipeline_benchmark_results.json"


def run_benchmark(num_runs: int = 25):
    print("==========================================================")
    print(f"DUAL-STREAM V2 PIPELINE BENCHMARKING (N={num_runs} EXECUTIONS)")
    print("==========================================================")

    # Pick a sample specimen
    sample_img_path = BASE_DIR / "temp_benchmark_sample.jpg"
    img = np.ones((400, 600, 3), dtype=np.uint8) * 235
    cv2.putText(img, "PASSPORT REPUBLIC OF TESTING", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "SURNAME: DOE  GIVEN NAMES: JOHN", (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "PASSPORT NO: L898902C3  DOB: 12/08/1974", (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "P<UTODOE<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", (30, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "L898902C36UTO7408122F1204159ZE184226B<<<<<10", (30, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.imwrite(str(sample_img_path), img)

    timings = {
        # Micro-benchmarks for Forgery Subsystem
        "global_inference": [],
        "local_inference": [],
        "fusion": [],
        "complete_forgery_subsystem": [],
        # Stage benchmarks
        "preprocessing_quality": [],
        "document_classification": [],
        "tampering_forensic_fusion": [],
        "ocr_extraction": [],
        "validation_mrz": [],
        "risk_engine": [],
        "database_audit": [],
        # Total End-to-End
        "complete_end_to_end_pipeline": [],
    }

    db = SessionLocal()

    # Warmup runs
    gm, lm, dev, ver = _get_dual_stream_models()
    _ = classify_document(str(sample_img_path))
    _ = score_image_forgery_cnn(str(sample_img_path))
    if torch.cuda.is_available():
        torch.cuda.synchronize()

    pil_img = Image.open(sample_img_path).convert("RGB")
    g_tensor = _TRANSFORM(pil_img).unsqueeze(0).to(dev)
    patches = generate_3x3_patches(pil_img)
    p_batch = torch.stack([_TRANSFORM(p) for p in patches], dim=0).to(dev)

    for run_idx in range(1, num_runs + 1):
        # 1. Micro-benchmark: Global Inference
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_g_start = time.perf_counter()
        with torch.no_grad():
            if dev.type == "cuda":
                with torch.amp.autocast('cuda'):
                    g_out = gm(g_tensor)
            else:
                g_out = gm(g_tensor)
            p_global = float(torch.softmax(g_out, dim=1)[0, 1].item())
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_global = (time.perf_counter() - t_g_start) * 1000

        # 2. Micro-benchmark: Local 3x3 Inference
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_l_start = time.perf_counter()
        with torch.no_grad():
            if dev.type == "cuda":
                with torch.amp.autocast('cuda'):
                    l_out = lm(p_batch)
            else:
                l_out = lm(p_batch)
            l_probs = torch.softmax(l_out, dim=1)[:, 1]
            p_local_max = float(torch.max(l_probs).item())
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_local = (time.perf_counter() - t_l_start) * 1000

        # 3. Micro-benchmark: Fusion
        t_f_start = time.perf_counter()
        fused_prob = (0.60 * p_global) + (0.40 * p_local_max)
        triggered = fused_prob >= 0.40
        uncertain = 0.35 <= fused_prob <= 0.55
        cnn_score = round(fused_prob * 100.0, 2)
        t_fusion = (time.perf_counter() - t_f_start) * 1000

        # Full Pipeline Benchmark Run
        t0 = time.perf_counter()

        # Preprocessing & Quality
        t_pre_start = time.perf_counter()
        q_res = assess_image_quality(str(sample_img_path))
        img_hash = compute_image_sha256(str(sample_img_path))
        t_pre = (time.perf_counter() - t_pre_start) * 1000

        # Classification
        t_cls_start = time.perf_counter()
        cls_res = classify_document(str(sample_img_path))
        t_cls = (time.perf_counter() - t_cls_start) * 1000

        # Complete Forgery Subsystem (Dual-Stream V2)
        t_cnn_start = time.perf_counter()
        cnn_res = score_image_forgery_cnn(str(sample_img_path))
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_forgery_subsystem = (time.perf_counter() - t_cnn_start) * 1000

        # Tampering Forensic Fusion (Multi-Signal)
        t_tamp_start = time.perf_counter()
        tamp_res = analyze_tampering(str(sample_img_path))
        t_tamp = (time.perf_counter() - t_tamp_start) * 1000

        # OCR Extraction
        t_ocr_start = time.perf_counter()
        ocr_res = extract_document_fields(str(sample_img_path), cls_res.get("document_type"))
        t_ocr = (time.perf_counter() - t_ocr_start) * 1000

        # Validation & MRZ
        t_val_start = time.perf_counter()
        val_res = validate_document(ocr_res)
        t_val = (time.perf_counter() - t_val_start) * 1000

        # Risk Engine
        t_risk_start = time.perf_counter()
        risk_res = compute_risk_score(
            validation_result=val_res,
            tampering_result=tamp_res,
            face_result=None,
            ocr_result=ocr_res,
            quality_result=q_res,
        )
        t_risk = (time.perf_counter() - t_risk_start) * 1000

        # Database & Audit Log
        t_db_start = time.perf_counter()
        _ = append_audit(
            db=db,
            screening_id=f"bench_{run_idx}_{int(time.time())}",
            officer="benchmark_runner",
            document_hash=img_hash,
            risk=risk_res,
            modules={"quality": True, "classification": True, "tampering": True, "ocr": True},
            duration_ms=t_pre + t_cls + t_tamp + t_ocr + t_val + t_risk,
            document_type="passport",
        )
        db.commit()
        t_db = (time.perf_counter() - t_db_start) * 1000

        t_total = (time.perf_counter() - t0) * 1000

        timings["global_inference"].append(t_global)
        timings["local_inference"].append(t_local)
        timings["fusion"].append(t_fusion)
        timings["complete_forgery_subsystem"].append(t_forgery_subsystem)
        timings["preprocessing_quality"].append(t_pre)
        timings["document_classification"].append(t_cls)
        timings["tampering_forensic_fusion"].append(t_tamp)
        timings["ocr_extraction"].append(t_ocr)
        timings["validation_mrz"].append(t_val)
        timings["risk_engine"].append(t_risk)
        timings["database_audit"].append(t_db)
        timings["complete_end_to_end_pipeline"].append(t_total)

    db.close()
    if sample_img_path.exists():
        sample_img_path.unlink()

    # Compute percentiles
    summary = {}
    print(f"\n{'Subsystem Stage':<30} | {'Mean (ms)':<10} | {'P50 (ms)':<10} | {'P90 (ms)':<10} | {'P95 (ms)':<10} | {'P99 (ms)':<10}")
    print("-" * 86)

    for stage, vals in timings.items():
        arr = np.array(vals)
        mean_v = float(np.mean(arr))
        p50_v = float(np.percentile(arr, 50))
        p90_v = float(np.percentile(arr, 90))
        p95_v = float(np.percentile(arr, 95))
        p99_v = float(np.percentile(arr, 99))

        summary[stage] = {
            "mean_ms": round(mean_v, 2),
            "p50_ms": round(p50_v, 2),
            "p90_ms": round(p90_v, 2),
            "p95_ms": round(p95_v, 2),
            "p99_ms": round(p99_v, 2),
        }
        print(f"{stage:<30} | {mean_v:<10.2f} | {p50_v:<10.2f} | {p90_v:<10.2f} | {p95_v:<10.2f} | {p99_v:<10.2f}")

    benchmark_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runs_count": num_runs,
        "hardware": {
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
            "pytorch": torch.__version__,
        },
        "latency_percentiles": summary,
    }

    with open(BENCHMARK_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    print(f"\n[OK] Latency benchmark complete! Saved to: {BENCHMARK_OUTPUT}")


if __name__ == "__main__":
    run_benchmark(25)
