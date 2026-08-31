import os
import csv
import json
import numpy as np
from pathlib import Path
from app.services.document_classifier import classify_document
from app.services.tampering_service import analyze_tampering

ADV_DIR = 'dataset/adversarial'
REPORTS_DIR = 'reports'
JSON_OUT = os.path.join(REPORTS_DIR, 'adversarial_results.json')
CSV_OUT = os.path.join(REPORTS_DIR, 'adversarial_results.csv')

PERTURBATIONS = [
    "blur", "noise", "screenshot", "print_photo", 
    "darkness", "overexposure", "heavy_compression", "perspective_skew"
]

def main():
    print("=== RUNNING ADVERSARIAL EVALUATION ===")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if not os.path.exists(ADV_DIR):
        print("Error: dataset/adversarial directory not found!")
        return

    results = {}
    
    # We sample 5 files per perturbation to keep it reasonably fast
    # and perform strict evaluation.
    for p in PERTURBATIONS:
        p_dir = os.path.join(ADV_DIR, p)
        if not os.path.exists(p_dir):
            continue
        
        all_files = []
        for r, dirs, files in os.walk(p_dir):
            for f in files:
                if f.lower().endswith('.jpg'):
                    all_files.append(os.path.join(r, f))
        
        if not all_files:
            continue
        
        # Sample 5 files deterministically
        all_files.sort()
        sampled = all_files[:5]
        
        p_res = []
        for fpath in sampled:
            # 1. Classification check
            cls = classify_document(fpath)
            # 2. Tampering check
            tamp = analyze_tampering(fpath)
            
            p_res.append({
                "file": os.path.basename(fpath),
                "classification": cls["document_type"],
                "classifier_confidence": cls["confidence"],
                "classifier_mode": cls.get("classifier_mode", "heuristic_fallback"),
                "tampering_score": tamp["tampering_score"],
                "tampered_flag": tamp["tampered"]
            })
            
        # Calculate averages for this perturbation
        avg_conf = float(np.mean([x["classifier_confidence"] for x in p_res]))
        avg_tamp = float(np.mean([x["tampering_score"] for x in p_res]))
        tamp_detection_rate = float(np.mean([1.0 if x["tampered_flag"] else 0.0 for x in p_res]))

        results[p] = {
            "num_evaluated": len(p_res),
            "average_classifier_confidence": round(avg_conf, 4),
            "average_tampering_score": round(avg_tamp, 4),
            "tampering_detection_rate": round(tamp_detection_rate, 4),
            "detail": p_res
        }
        print(f"Perturbation '{p}' evaluated. Detection rate: {tamp_detection_rate:.2%}")

    # Save to JSON
    with open(JSON_OUT, 'w') as f:
        json.dump(results, f, indent=2)
    print("JSON report saved to:", JSON_OUT)

    # Save to CSV
    with open(CSV_OUT, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "perturbation", "num_evaluated", 
            "avg_classifier_confidence", "avg_tampering_score", 
            "tampering_detection_rate"
        ])
        for p, metric in results.items():
            writer.writerow([
                p, metric["num_evaluated"],
                metric["average_classifier_confidence"],
                metric["average_tampering_score"],
                metric["tampering_detection_rate"]
            ])
    print("CSV report saved to:", CSV_OUT)

if __name__ == '__main__':
    main()
