"""Dataset discovery and reproducible 70/15/15 splits for forgery training."""
from __future__ import annotations
from pathlib import Path
from random import Random
from typing import Dict, List, Tuple

CLASS_FOLDERS = ("genuine/passport", "genuine/visa", "genuine/national_id", "genuine/driving_license", "tampered/photo_swap", "tampered/text_edit", "tampered/dob_edit", "tampered/name_edit", "tampered/number_edit", "tampered/stamp_forgery", "tampered/copy_move", "tampered/external_passport", "tampered/external_license")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

def load_tampering_dataset(root: str, seed: int = 42) -> Dict[str, List[Tuple[str, int]]]:
    """Return stratified train/validation/test file paths labelled 0 genuine / 1 tampered."""
    splits: Dict[str, List[Tuple[str, int]]] = {"train": [], "validation": [], "test": []}
    base = Path(root)
    for folder in CLASS_FOLDERS:
        samples = [(str(path), int(folder.startswith("tampered"))) for path in (base / folder).glob("**/*") if path.suffix.lower() in IMAGE_EXTENSIONS]
        Random(f"{seed}:{folder}").shuffle(samples)
        train_end, valid_end = round(len(samples) * .70), round(len(samples) * .85)
        splits["train"].extend(samples[:train_end]); splits["validation"].extend(samples[train_end:valid_end]); splits["test"].extend(samples[valid_end:])
    return splits
