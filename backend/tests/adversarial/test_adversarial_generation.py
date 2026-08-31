"""Adversarial and Robustness Generation Tests (Requirement 31)."""
import numpy as np
import pytest
from scripts.generate_adversarial_dataset import generate_adversarial_variants


def test_adversarial_generation_all_variants():
    dummy = np.full((200, 300, 3), 180, dtype=np.uint8)
    variants = generate_adversarial_variants(dummy)

    expected_keys = [
        "blur",
        "noise",
        "screenshot",
        "print_photo",
        "darkness",
        "overexposure",
        "heavy_compression",
        "perspective_skew",
    ]

    for key in expected_keys:
        assert key in variants
        assert variants[key] is not None
        assert variants[key].shape[0] > 0
