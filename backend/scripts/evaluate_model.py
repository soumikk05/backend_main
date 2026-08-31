"""Generate accuracy, precision, recall, F1, ROC-AUC and confusion-matrix reports from prediction CSV."""
import argparse
import csv
import json
from pathlib import Path
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("predictions", help="CSV with label,score columns"); parser.add_argument("--output", default="dataset/evaluation_report.json")
    args = parser.parse_args()
    with open(args.predictions, newline="") as handle: rows = list(csv.DictReader(handle))
    labels, scores = [int(row["label"]) for row in rows], [float(row["score"]) for row in rows]
    predictions = [int(score >= .5) for score in scores]
    precision, recall, f1, _ = precision_recall_fscore_support(labels, predictions, average="binary", zero_division=0)
    report = {"samples": len(rows), "accuracy": accuracy_score(labels, predictions), "precision": precision, "recall": recall, "f1": f1, "roc_auc": roc_auc_score(labels, scores) if len(set(labels)) > 1 else None, "confusion_matrix": confusion_matrix(labels, predictions).tolist()}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True); Path(args.output).write_text(json.dumps(report, indent=2)); print(json.dumps(report, indent=2))

if __name__ == "__main__": main()
