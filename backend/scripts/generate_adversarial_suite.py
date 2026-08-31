"""Create non-destructive robustness variants for blur, noise, compression, screenshot and print-photo simulations."""
import argparse
from pathlib import Path
import cv2
import numpy as np

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("input_dir"); parser.add_argument("output_dir"); args = parser.parse_args()
    output = Path(args.output_dir)
    for source in Path(args.input_dir).glob("**/*"):
        if source.suffix.lower() not in {".jpg", ".jpeg", ".png"}: continue
        image = cv2.imread(str(source)); relative = source.relative_to(args.input_dir); stem = relative.stem
        variants = {"blur": cv2.GaussianBlur(image, (9, 9), 2), "noise": np.clip(image.astype(np.int16) + np.random.normal(0, 18, image.shape), 0, 255).astype(np.uint8), "screenshot": cv2.resize(cv2.resize(image, None, fx=.55, fy=.55), (image.shape[1], image.shape[0])), "print_photo": cv2.GaussianBlur(cv2.convertScaleAbs(image, alpha=.8, beta=20), (3, 3), 0)}
        for kind, variant in variants.items():
            target = output / kind / relative.parent / f"{stem}.jpg"; target.parent.mkdir(parents=True, exist_ok=True); cv2.imwrite(str(target), variant, [cv2.IMWRITE_JPEG_QUALITY, 55 if kind == "screenshot" else 90])

if __name__ == "__main__": main()
