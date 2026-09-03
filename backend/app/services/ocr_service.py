"""
OCR extraction service (Module 1).

Routes intake images to document-specific extractors:
- Passport: MRZ + OCR (Name, Passport Number, Nationality, DOB, Expiry, Gender, MRZ)
- Visa: OCR (Visa Number, Visa Type, Issue Date, Expiry Date, Entry Type, Stay Duration)
- National ID: OCR (Name, ID Number, DOB, Gender, Address)
- Driving License: OCR (Name, License Number, DOB, Issue Date, Expiry Date, Vehicle Class)
- Permit: OCR (Permit Number, Name, Permit Type, Issue Date, Expiry Date)

Each extracted field is confidence-annotated with:
{
    "value": str,
    "confidence": float,
    "source": "mrz" | "easyocr" | "template" | "fallback",
    "validated": bool
}
"""

import re
import logging
from typing import Any, Dict, List, Optional

from app.config import EASYOCR_LANGS
from app.utils.mrz_parser import mrz_to_fields

logger = logging.getLogger(__name__)

_easyocr_reader = None

_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[\/\-. ](?:\d{1,2}|[A-Za-z]{3})[\/\-. ]\d{2,4}|\d{4}[\/\-. ]\d{1,2}[\/\-. ]\d{1,2})\b"
)
_DOC_NUMBER_PATTERN = re.compile(r"\b[A-Z0-9]{6,12}\b")
_GENDER_PATTERN = re.compile(r"\b(M|F|MALE|FEMALE|X)\b", re.IGNORECASE)

_DOB_LABELS = [
    "dob", "date of birth", "birth date", "birth", "d.o.b", "d.o.b.", "born",
    "date de naissance", "fecha de nacimiento", "geburtstag",
]
_EXPIRY_LABELS = [
    "expiry", "expiry date", "expiration date", "valid until", "valid till",
    "expires", "valid upto", "valid to", "exp date", "exp", "val",
    "date of expiry", "expiration", "validity", "date d'expiration",
]
_ISSUE_LABELS = [
    "issue", "date of issue", "issue date", "issued", "issuing date",
    "doi", "d.o.i", "d.o.i.", "issued on", "date de delivrance",
]

_TYPE_KEYWORDS = {
    "visa": ["visa", "entry permit", "multiple entry", "single entry"],
    "national_id": ["identity card", "national id", "id card", "resident card", "aadhaar"],
    "driving_license": ["driving licence", "driver's license", "driving license", "dl no"],
    "permit": ["permit", "work permit", "residence permit", "issued to"],
}


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(EASYOCR_LANGS, gpu=False)
    return _easyocr_reader


def _find_date_near_label(
    lines: List[str],
    labels: List[str],
    fallback: str = "",
    max_lookahead: int = 2,
) -> str:
    """
    Search lines for one of the target label keywords, then extract the first date
    found either on the same line or in the immediate subsequent lines.
    Falls back to `fallback` if no date is found near any matching label.
    """
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(lbl in line_lower for lbl in labels):
            same_line_dates = _DATE_PATTERN.findall(line)
            if same_line_dates:
                return same_line_dates[0]
            for offset in range(1, max_lookahead + 1):
                if i + offset < len(lines):
                    next_line_dates = _DATE_PATTERN.findall(lines[i + offset])
                    if next_line_dates:
                        return next_line_dates[0]
    return fallback


def read_document_text(image_path: str) -> str:
    """Read raw text from document image without structured parsing."""
    try:
        reader = _get_easyocr_reader()
        return " ".join(text.strip() for _, text, _ in reader.readtext(image_path) if text.strip())
    except Exception as exc:
        logger.warning("read_document_text failed: %s", exc)
        return ""


def extract_document_fields(image_path: str, document_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for document OCR extraction.
    Supports Passport, Visa, National ID, Driving License, Permit.
    """
    target_type = (document_type or "").lower()

    # 1. Attempt Passport MRZ extraction if target is passport, visa, or unspecified
    if not target_type or target_type in ("passport", "visa"):
        try:
            mrz_result = _try_passporteye(image_path)
            if mrz_result is not None:
                # Merge MRZ specific fields
                return _add_field_metadata(mrz_result, "mrz")
        except Exception as exc:
            logger.warning("PassportEye MRZ read failed, falling back to EasyOCR: %s", exc)

    # 2. EasyOCR extraction with category-specific parser
    try:
        raw_extraction = _extract_via_easyocr(image_path, target_type or None)
        return _add_field_metadata(raw_extraction, "easyocr")
    except Exception as exc:
        logger.error("EasyOCR extraction failed: %s", exc)
        return {
            "document_type": target_type or "unknown",
            "fields": {},
            "confidence": {},
            "error": f"OCR failed on this image: {exc}",
        }


def _try_passporteye(image_path: str) -> Optional[Dict[str, Any]]:
    from passporteye import read_mrz

    mrz = read_mrz(image_path)
    if mrz is None:
        return None

    parsed = mrz_to_fields(mrz)
    ocr_confidence = parsed["confidence"].get("mrz_ocr_confidence")
    if ocr_confidence is not None and ocr_confidence < 30:
        return None

    doc_type_raw = parsed["fields"].get("document_type", "")
    doc_type = "passport" if doc_type_raw.upper().startswith("P") else "visa"

    raw_fields = parsed["fields"]
    surname = raw_fields.get("surname", "")
    given_names = raw_fields.get("names", raw_fields.get("given_names", ""))
    full_name = f"{given_names} {surname}".strip() or raw_fields.get("name", "")

    fields = {
        "document_type": doc_type,
        "name": full_name,
        "given_names": given_names,
        "surname": surname,
        "passport_number": raw_fields.get("number", raw_fields.get("document_number", "")),
        "document_number": raw_fields.get("number", raw_fields.get("document_number", "")),
        "nationality": raw_fields.get("nationality", raw_fields.get("country", "")),
        "dob": raw_fields.get("date_of_birth", ""),
        "date_of_birth": raw_fields.get("date_of_birth", ""),
        "expiry": raw_fields.get("expiration_date", ""),
        "expiration_date": raw_fields.get("expiration_date", ""),
        "gender": raw_fields.get("sex", raw_fields.get("gender", "")),
        "mrz": raw_fields.get("raw_mrz", parsed.get("raw_mrz", "")),
    }

    return {
        "document_type": doc_type,
        "fields": fields,
        "confidence": parsed["confidence"],
        "raw_mrz": parsed.get("raw_mrz"),
        "engine": "PassportEye_MRZ",
        "error": None,
    }


def _extract_via_easyocr(image_path: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    reader = _get_easyocr_reader()
    results = reader.readtext(image_path)

    if not results:
        return {
            "document_type": expected_type or "unknown",
            "fields": {},
            "confidence": {},
            "engine": "EasyOCR",
            "error": "No readable text detected in image (blurry or empty upload?)",
        }

    lines: List[str] = [text.strip() for _, text, _ in results if text.strip()]
    full_text = " | ".join(lines)
    lowered = full_text.lower()

    detected_type = expected_type or "unknown"
    if detected_type == "unknown":
        for dtype, keywords in _TYPE_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                detected_type = dtype
                break

    dates_found = _DATE_PATTERN.findall(full_text)
    doc_numbers_found = [
        tok for tok in _DOC_NUMBER_PATTERN.findall(full_text)
        if any(ch.isdigit() for ch in tok)
    ]

    caps_lines = [ln for ln in lines if ln.isupper() and len(ln.split()) >= 2]
    probable_name = max(caps_lines, key=len) if caps_lines else (lines[0] if lines else "")

    gender_match = _GENDER_PATTERN.search(full_text)
    gender_val = gender_match.group(0).upper() if gender_match else ""
    doc_num = doc_numbers_found[0] if doc_numbers_found else ""

    fields: Dict[str, Any] = {
        "document_number": doc_num,
        "name": probable_name,
        "dates_found": dates_found,
        "raw_text_lines": lines,
    }

    # Document-specific mapping with label proximity date extraction
    if detected_type == "passport":
        dob_val = _find_date_near_label(lines, _DOB_LABELS, dates_found[0] if dates_found else "")
        expiry_val = _find_date_near_label(lines, _EXPIRY_LABELS, dates_found[1] if len(dates_found) > 1 else "")
        fields.update({
            "passport_number": doc_num,
            "name": probable_name,
            "nationality": "IND" if "india" in lowered else ("USA" if "usa" in lowered else ""),
            "dob": dob_val,
            "date_of_birth": dob_val,
            "expiry": expiry_val,
            "expiration_date": expiry_val,
            "gender": gender_val,
            "mrz": "",
        })
    elif detected_type == "visa":
        issue_val = _find_date_near_label(lines, _ISSUE_LABELS, dates_found[0] if dates_found else "")
        expiry_val = _find_date_near_label(lines, _EXPIRY_LABELS, dates_found[1] if len(dates_found) > 1 else "")
        fields.update({
            "visa_number": doc_num,
            "name": probable_name,
            "visa_type": "Tourist" if "tourist" in lowered else ("Business" if "business" in lowered else "Standard"),
            "issue_date": issue_val,
            "expiry_date": expiry_val,
            "expiration_date": expiry_val,
            "entry_type": "Multiple" if "multiple" in lowered else "Single",
            "stay_duration": "90 days" if "90" in lowered else "30 days",
        })
    elif detected_type == "national_id":
        dob_val = _find_date_near_label(lines, _DOB_LABELS, dates_found[0] if dates_found else "")
        fields.update({
            "id_number": doc_num,
            "name": probable_name,
            "dob": dob_val,
            "date_of_birth": dob_val,
            "gender": gender_val,
            "address": " ".join([ln for ln in lines if any(w in ln.lower() for w in ("road", "street", "dist", "nagar", "pin", "po"))]),
        })
    elif detected_type == "driving_license":
        issue_val = _find_date_near_label(lines, _ISSUE_LABELS, dates_found[0] if dates_found else "")
        expiry_val = _find_date_near_label(lines, _EXPIRY_LABELS, dates_found[1] if len(dates_found) > 1 else "")
        dob_val = _find_date_near_label(lines, _DOB_LABELS, dates_found[2] if len(dates_found) > 2 else "")
        fields.update({
            "license_number": doc_num,
            "name": probable_name,
            "issue_date": issue_val,
            "expiry_date": expiry_val,
            "expiration_date": expiry_val,
            "dob": dob_val,
            "date_of_birth": dob_val,
            "vehicle_class": "LMV" if "lmv" in lowered else ("MCWG" if "mcwg" in lowered else "Class C"),
        })
    elif detected_type == "permit":
        issue_val = _find_date_near_label(lines, _ISSUE_LABELS, dates_found[0] if dates_found else "")
        expiry_val = _find_date_near_label(lines, _EXPIRY_LABELS, dates_found[1] if len(dates_found) > 1 else "")
        fields.update({
            "permit_number": doc_num,
            "name": probable_name,
            "permit_type": "Work" if "work" in lowered else "Residence",
            "issue_date": issue_val,
            "expiry_date": expiry_val,
            "expiration_date": expiry_val,
        })

    avg_conf = sum(c for _, _, c in results) / len(results) if results else 0.0
    confidence = {
        "ocr_average_confidence": round(avg_conf, 3),
        "document_type_guess": "keyword_match" if detected_type != "unknown" else "none",
    }

    return {
        "document_type": detected_type,
        "fields": fields,
        "confidence": confidence,
        "engine": "EasyOCR",
        "error": None,
    }


def _add_field_metadata(result: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Annotate every field with value, confidence, source, and validated status."""
    raw_fields = result.get("fields", {}) or {}
    confidence = result.get("confidence", {}) or {}
    default_conf = float(confidence.get("ocr_average_confidence", confidence.get("mrz_ocr_confidence", 0.85)) or 0.85)
    if default_conf > 1.0:
        default_conf /= 100.0

    structured_fields = {}
    for key, value in raw_fields.items():
        if key in ("raw_text_lines", "dates_found", "document_number_candidates"):
            continue
        field_conf = confidence.get(key, default_conf)
        if isinstance(field_conf, (int, float)):
            conf_val = float(field_conf)
            if conf_val > 1.0:
                conf_val /= 100.0
        else:
            conf_val = default_conf

        structured_fields[key] = {
            "value": value,
            "confidence": round(conf_val, 4),
            "source": source,
            "validated": bool(value and conf_val >= 0.50),
            "extraction_source": source,
            "validation_status": "validated" if (value and conf_val >= 0.50) else "pending",
        }

    result["fields"] = structured_fields
    return result
