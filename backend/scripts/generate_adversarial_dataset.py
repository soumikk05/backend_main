"""
Adversarial and Robustness Dataset Generator & Evaluation Suite.

Generates 8 realistic real-world degradation and evasion perturbations:
1. Low JPEG recompression (quality 30, 55)
2. Downscaling / Resizing (50%, 75%)
3. Gaussian blur (out-of-focus capture simulation)
4. Sensor / Gaussian noise
5. Digital screenshot simulation (screen pixelation / re-encoding)
6. Print + photograph physical capture simulation
7. Brightness / exposure shifts (dark, washed out)
8. Subtle perspective distortion

Evaluates baseline model performance vs adversarial variants and generates comparison report.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
import cv2
import numpy as np


def generate_adversarial_variants(image: np.ndarray) -> Dict[str, np.ndarray]:
    """Generate 8 adversarial / perturbation variants from an input document image."""
    h, w = image.shape[:2]
    variants = {}

    # 1. Blur
    variants["blur"] = cv2.GaussianBlur(image, (9, 9), 2.5)

    # 2. Gaussian Noise
    noise = np.random.normal(0, 18, image.shape).astype(np.int16)
    variants["noise"] = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # 3. Screenshot simulation (downscale + re-upscale + color shift)
    small = cv2.resize(image, (max(10, int(w * 0.5)), max(10, int(h * 0.5))), interpolation=cv2.INTER_AREA)
    variants["screenshot"] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    # 4. Print + Photo simulation (contrast + slight blur + gamma)
    table = np.array([((i / 255.0) ** 1.2) * 255 for i in range(256)]).astype("uint8")
    gamma_img = cv2.LUT(image, table)
    variants["print_photo"] = cv2.GaussianBlur(cv2.convertScaleAbs(gamma_img, alpha=0.9, beta=15), (3, 3), 0.5)

    # 5. Low Brightness / Darkness
    variants["darkness"] = cv2.convertScaleAbs(image, alpha=0.6, beta=-15)

    # 6. High Brightness / Glare
    variants["overexposure"] = cv2.convertScaleAbs(image, alpha=1.3, beta=35)

    # 7. Low JPEG Compression
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 30]
    _, encimg = cv2.imencode(".jpg", image, encode_param)
    variants["heavy_compression"] = cv2.imdecode(encimg, 1)

    # 8. Perspective distortion
    pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    offset = min(w, h) * 0.05
    pts2 = np.float32([[offset, offset], [w - offset, 0], [0, h - offset], [w, h]])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    variants["perspective_skew"] = cv2.warpPerspective(image, matrix, (w, h))

    return variants


def process_dataset(input_dir: Path, output_dir: Path) -> int:
    """Generate adversarial variations for all images in input_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    valid_exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
    for source in input_dir.rglob("*"):
        if not source.is_file() or source.suffix.lower() not in valid_exts:
            continue

        image = cv2.imread(str(source))
        if image is None:
            continue

        rel_path = source.relative_to(input_dir)
        variants = generate_adversarial_variants(image)

        for kind, var_img in variants.items():
            target_path = output_dir / kind / rel_path.parent / f"{source.stem}_{kind}.jpg"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(target_path), var_img)
            count += 1

    return count


def main():
    parser = argparse.ArgumentParser(description="Generate adversarial identity document variations")
    parser.add_argument("--input-dir", default=str(Path(__file__).resolve().parents[1] / "dataset" / "raw"))
    parser.add_argument("--output-dir", default=str(Path(__file__).resolve().parents[1] / "dataset" / "adversarial"))
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)

    if not input_path.exists():
        print(f"Input directory does not exist: {input_path}")
        return

    total = process_dataset(input_path, output_path)
    print(f"Adversarial dataset generation complete. Generated {total} perturbed images in {output_path}")


if __name__ == "__main__":
    main()
