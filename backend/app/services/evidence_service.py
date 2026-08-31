"""Local prototype evidence store for original and derived screening artifacts."""
from __future__ import annotations
from pathlib import Path
from shutil import copy2
from typing import Dict, Optional
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2] / "dataset" / "evidence"
ROOT.mkdir(parents=True, exist_ok=True)

def store_evidence(source_path: str, kind: str, screening_id: Optional[str] = None) -> str:
    evidence_id = screening_id or uuid4().hex
    target_dir = ROOT / evidence_id; target_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(source_path).suffix or ".bin"; target = target_dir / f"{kind}{suffix}"
    copy2(source_path, target)
    return f"/evidence/{evidence_id}/{target.name}"

def evidence_urls(original: str, corrected: Optional[str], heatmap: Optional[str], screening_id: str) -> Dict[str, Optional[str]]:
    return {"original_image": store_evidence(original, "original", screening_id), "corrected_image": store_evidence(corrected, "corrected", screening_id) if corrected else None, "heatmap": store_evidence(heatmap, "heatmap", screening_id) if heatmap else None}
