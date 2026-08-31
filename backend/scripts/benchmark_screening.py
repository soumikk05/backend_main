"""
Screening Latency and Pipeline Stage Benchmark Suite.

Measures latency percentiles across full `/screen` workflow:
- Mean
- Median (p50)
- 95th Percentile (p95)
- Minimum
- Maximum
- Per-stage breakdown (intake, ocr, validation, tampering, face, registry, risk)

Writes benchmark report JSON without fabricating measurements.
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run_benchmark(
    image_path: str,
    url: str,
    api_key: str,
    runs: int,
    selfie_path: str = "",
) -> Dict[str, Any]:
    durations: List[float] = []
    statuses: List[int] = []
    stage_timings: Dict[str, List[float]] = {}

    for i in range(runs):
        files = {
            "document_image": (Path(image_path).name, open(image_path, "rb"), "image/jpeg")
        }
        if selfie_path and Path(selfie_path).is_file():
            files["selfie_photo"] = (Path(selfie_path).name, open(selfie_path, "rb"), "image/jpeg")

        try:
            started = time.perf_counter()
            response = httpx.post(
                url,
                headers={"X-API-Key": api_key},
                files=files,
                timeout=120.0,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            durations.append(elapsed_ms)
            statuses.append(response.status_code)

            if response.status_code == 200:
                body = response.json()
                timeline = body.get("timeline", {})
                for stage, ms in timeline.items():
                    if isinstance(ms, (int, float)):
                        stage_timings.setdefault(stage, []).append(float(ms))
        except Exception as exc:
            statuses.append(500)
            durations.append(0.0)

    if not durations:
        return {"status": "BENCHMARK_FAILED", "runs": runs}

    valid_durations = [d for d in durations if d > 0]
    if not valid_durations:
        return {"status": "BENCHMARK_ERROR", "status_codes": statuses}

    p95 = float(np.percentile(valid_durations, 95)) if len(valid_durations) >= 2 else valid_durations[0]

    stages_summary: Dict[str, Any] = {}
    for stage, vals in stage_timings.items():
        if vals:
            stages_summary[stage] = {
                "mean_ms": round(statistics.mean(vals), 2),
                "p50_ms": round(statistics.median(vals), 2),
                "p95_ms": round(float(np.percentile(vals, 95)), 2) if len(vals) >= 2 else vals[0],
            }

    report = {
        "runs": runs,
        "successful_runs": statuses.count(200),
        "status_codes": statuses,
        "mean_ms": round(statistics.mean(valid_durations), 2),
        "median_p50_ms": round(statistics.median(valid_durations), 2),
        "p95_ms": round(p95, 2),
        "min_ms": round(min(valid_durations), 2),
        "max_ms": round(max(valid_durations), 2),
        "under_5_seconds": all(d < 5000.0 for d in valid_durations),
        "stage_breakdowns": stages_summary,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark document screening endpoint latency")
    parser.add_argument("image", help="Path to sample document image")
    parser.add_argument("--selfie", default="", help="Optional selfie image path")
    parser.add_argument("--url", default="http://127.0.0.1:8000/screen")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--api-key", default="test-api-key")
    parser.add_argument("--output", default="dataset/benchmark_report.json")
    args = parser.parse_args()

    report = run_benchmark(args.image, args.url, args.api_key, args.runs, args.selfie)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
