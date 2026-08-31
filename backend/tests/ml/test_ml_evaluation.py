"""ML Model and Forensic Detector Evaluation Tests (Requirement 30)."""
import pytest
from scripts.evaluate_models import evaluate_predictions


def test_evaluate_predictions_valid():
    labels = [0, 0, 1, 1, 1, 0]
    scores = [0.1, 0.2, 0.85, 0.90, 0.75, 0.3]
    attacks = ["none", "none", "photo_swap", "copy_move", "stamp_forgery", "none"]

    res = evaluate_predictions(labels, scores, attacks, threshold=0.50)
    assert res["status"] == "EVALUATION_SUCCESS"
    assert res["accuracy"] == 1.0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0
    assert "photo_swap" in res["per_attack_breakdown"]


def test_evaluate_predictions_insufficient_data():
    res = evaluate_predictions([1], [0.9])
    assert res["status"] == "INSUFFICIENT_DATA"
    assert res["accuracy"] is None
