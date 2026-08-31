# SIH COMPLETION BASELINE

Date: 2026-08-26T22:27:00+05:30
Command: python -m pytest tests/ -v --tb=short --no-header -q
Backend: d:\backend-scaffold (2)\backend

## Results
- Total Tests: 72
- Passed:      72
- Failed:      0
- Skipped:     0
- Errors:      0
- Warnings:    12 (non-fatal: torch.ao.quantization deprecation, passporteye FutureWarning)
- Execution:   27.03s

## Environment
- mediapipe: NOT AVAILABLE (numpy 2.2.6 incompatible with tensorflow-intel 2.15.0)
- Temporal liveness method: OpenCV Haar + EAR via facial geometry
- MIDV500 dataset: 2408 TIF images (9 document categories)
- CNN weights: absent - will train from MIDV500 + adversarial generation
- Keras classifier: absent - will train from MIDV500
