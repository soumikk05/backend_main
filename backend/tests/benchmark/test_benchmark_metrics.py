"""Benchmark Metrics & Stage Latency Tests (Requirement 29)."""
import numpy as np
import pytest


def test_percentile_calculation():
    latencies = [120.0, 150.0, 180.0, 210.0, 450.0]
    p95 = float(np.percentile(latencies, 95))
    assert p95 >= 210.0
    assert p95 <= 450.0
