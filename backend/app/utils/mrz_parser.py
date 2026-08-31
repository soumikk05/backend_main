"""
MRZ (Machine Readable Zone) helpers.

PassportEye already computes ICAO 9303 checksum validity per-field
(valid_number, valid_date_of_birth, valid_expiration_date, valid_composite,
valid_nationality, valid_personal_number) — we don't reimplement checksum
math here. This module just normalizes a PassportEye MRZ result into the
clean JSON shape the rest of the API expects, and does light cleanup of
MRZ's '<' filler characters.
"""

from typing import Any, Dict, Optional


def clean_mrz_string(value: Optional[str]) -> str:
    """MRZ pads unused space with '<' and uses '<' as a separator too."""
    if not value:
        return ""
    return value.replace("<", " ").strip()


def mrz_to_fields(mrz) -> Dict[str, Any]:
    """
    Convert a passporteye.MRZ object into our structured field + confidence
    dict. `mrz` is the object returned by passporteye.read_mrz(path).
    """
    data = mrz.to_dict()

    fields = {
        "full_name": f"{clean_mrz_string(data.get('surname'))} {clean_mrz_string(data.get('names'))}".strip(),
        "surname": clean_mrz_string(data.get("surname")),
        "given_names": clean_mrz_string(data.get("names")),
        "document_number": data.get("number", "").replace("<", "").strip(),
        "nationality": data.get("nationality", ""),
        "country": data.get("country", ""),
        "date_of_birth": format_mrz_date(data.get("date_of_birth")),
        "expiration_date": format_mrz_date(data.get("expiration_date")),
        "sex": data.get("sex", ""),
        "document_type": data.get("type", ""),
        "personal_number": data.get("personal_number", "").replace("<", "").strip(),
    }

    # PassportEye's per-field checksum validity flags (True/False), used
    # directly as our "confidence" signal for MRZ-derived fields since
    # they're deterministic checksum results, not probabilistic OCR scores.
    confidence = {
        "document_number": bool(data.get("valid_number")),
        "date_of_birth": bool(data.get("valid_date_of_birth")),
        "expiration_date": bool(data.get("valid_expiration_date")),
        "nationality": bool(data.get("valid_nationality")),
        "personal_number": bool(data.get("valid_personal_number")),
        "overall_composite": bool(data.get("valid_composite")),
        "mrz_ocr_confidence": data.get("valid_score", None),  # 0-100 from passporteye
    }

    return {"fields": fields, "confidence": confidence, "raw_mrz_text": data.get("raw_text", "")}


def format_mrz_date(raw: Optional[str]) -> str:
    """MRZ dates are YYMMDD. Convert to YYYY-MM-DD with a naive century guess."""
    if not raw or len(raw) != 6 or not raw.isdigit():
        return ""
    yy, mm, dd = raw[0:2], raw[2:4], raw[4:6]
    # Naive century rule: 00-30 => 2000s, 31-99 => 1900s. Good enough for a demo;
    # doesn't matter for expiration dates (always future) and is a common
    # simplification for date_of_birth in prototypes.
    century = "20" if int(yy) <= 30 else "19"
    return f"{century}{yy}-{mm}-{dd}"