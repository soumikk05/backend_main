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
from typing import Any, Dict, List, Optional, Tuple

# Pre-import torch so that Windows C DLLs initialize without access violation
try:
    import torch
except ImportError:
    torch = None

from app.config import EASYOCR_LANGS
from app.utils.mrz_parser import mrz_to_fields

logger = logging.getLogger(__name__)

_easyocr_reader = None

_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[\/\-. ](?:\d{1,2}|[A-Za-z]{3})[\/\-. ]\d{2,4}|\d{4}[\/\-. ]\d{1,2}[\/\-. ]\d{1,2})\b"
)
_GLUED_DATE_PATTERN = re.compile(r"\b(\d{1,2})[\/\-.](\d{1,2})(\d{4})\b")

_DOB_LABELS = [
    "dob", "date of birth", "birth date", "birth", "d.o.b", "d.o.b.", "born",
    "जन्म तिथि", "जन्म", "तिथि", "tarikh", "janam", "year of birth", "yob",
    "date de naissance", "fecha de nacimiento", "geburtstag",
]
_EXPIRY_LABELS = [
    "expiry", "expiry date", "expiration date", "valid until", "valid till",
    "expires", "valid upto", "valid to", "exp date", "exp", "val",
    "date of expiry", "expiration", "validity", "date d'expiration",
]
_ISSUE_LABELS = [
    "issue", "date of issue", "issue date", "issued", "issuing date",
    "doi", "d.o.i", "d.o.i.", "issued on", "jari", "जारी", "जारी करने की तिथि", "date de delivrance",
]

_TYPE_KEYWORDS = {
    "visa": ["visa", "entry permit", "multiple entry", "single entry"],
    "national_id": [
        "identity card", "national id", "id card", "resident card", "aadhaar",
        "unique identification", "income tax department", "pan card", "election commission", "voter id",
    ],
    "driving_license": ["driving licence", "driver's license", "driving license", "dl no", "transport department"],
    "permit": ["permit", "work permit", "residence permit", "issued to"],
}

_NAME_STOPWORDS = {
    "government", "govt", "india", "authority", "identification", "aadhaar", "uidai",
    "enrolment", "republic", "passport", "driving", "licence", "license",
    "permit", "ministry", "department", "state", "district", "signature",
    "bearer", "holder", "nationality", "helpdesk", "website", "sale", "card",
    "male", "female", "transgender", "purush", "mahila", "sex", "gender",
    "father", "mother", "spouse", "husband", "wife", "address", "flat",
    "street", "road", "vtc", "post", "pin", "pincode", "mobile", "phone",
    "email", "issued", "valid", "expiry", "date", "birth", "portal", "help",
    "wwwetcprintin", "etcprint", "proof", "citizenship", "your", "vid",
    "mera", "meri", "pehchan", "sarkar", "bharat", "delhi", "grugram",
    "gurgaon", "haryana", "mumbai", "maharashtra", "karnataka", "bangalore",
    "postal", "order", "sample", "specimen", "official", "national", "id",
    "union", "commission", "election", "income", "tax", "permanent", "account",
    "number", "no", "card", "proof of identity", "not of citizenship",
}

_ADDRESS_KEYWORDS = (
    "c/o", "cio", "s/o", "d/o", "w/o", "care of", "son of", "daughter of", "wife of",
    "vtc", "flat", "house", "building", "road", "street", "lane", "nagar", "marg",
    "po:", "po ", "post office", "sub district", "district", "state", "pin", "pincode",
    "postal code", "village", "town", "city", "colony", "sector", "block", "floor", "apartment"
)


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        gpu_enabled = False
        if torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available():
            gpu_enabled = True
        _easyocr_reader = easyocr.Reader(EASYOCR_LANGS, gpu=gpu_enabled)
    return _easyocr_reader


def _find_date_near_label(
    lines: List[str],
    labels: List[str],
    fallback: str = "",
    max_lookahead: int = 2,
) -> Tuple[str, float]:
    """
    Search lines for one of the target label keywords, then extract the first date
    found either on the same line or in the immediate subsequent lines.
    Supports standard dates and glued formats (e.g. 01/012000).
    Returns (extracted_date_str, confidence).
    """
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(lbl in line_lower for lbl in labels):
            # Check glued format first if separator is missing
            glued = _GLUED_DATE_PATTERN.search(line)
            if glued:
                return f"{glued.group(1)}/{glued.group(2)}/{glued.group(3)}", 0.90
            same_line_dates = _DATE_PATTERN.findall(line)
            if same_line_dates:
                return same_line_dates[0], 0.92
            for offset in range(1, max_lookahead + 1):
                if i + offset < len(lines):
                    subsequent = lines[i + offset]
                    glued_sub = _GLUED_DATE_PATTERN.search(subsequent)
                    if glued_sub:
                        return f"{glued_sub.group(1)}/{glued_sub.group(2)}/{glued_sub.group(3)}", 0.88
                    next_line_dates = _DATE_PATTERN.findall(subsequent)
                    if next_line_dates:
                        return next_line_dates[0], 0.90
    return fallback, 0.75 if fallback else 0.0


def _extract_probable_name(lines_with_conf: List[Tuple[str, float]]) -> Tuple[str, float]:
    """
    Extract the most probable human holder name using linguistic heuristics,
    case weighting, stopword exclusion, contextual proximity to DOB/Address,
    and repeated occurrences.
    """
    lines = [t for t, _ in lines_with_conf]
    candidates: Dict[str, Tuple[float, float]] = {}

    for i, (line, conf) in enumerate(lines_with_conf):
        clean_line = re.sub(r"^[^\w]+|[^\w]+$", "", line).strip()
        clean_line = re.sub(r"^(?:name|holder name|given name|given names|surname|to|naam|नाम)[\s:]+", "", clean_line, flags=re.IGNORECASE).strip()
        tokens = [re.sub(r"[^A-Za-z]", "", tok) for tok in clean_line.split() if tok]
        tokens = [t for t in tokens if t]

        if not (2 <= len(tokens) <= 4):
            continue

        if any(len(t) < 2 for t in tokens):
            continue

        # Reject if any token is a known stopword
        if any(t.lower() in _NAME_STOPWORDS for t in tokens):
            continue

        # Phonetic validity: every token must contain at least one vowel
        has_vowels = all(any(c in "aeiouy" for c in t.lower()) for t in tokens)
        if not has_vowels:
            continue

        candidate_name = " ".join(tokens)
        score = conf * 50.0

        # Title Case bonus (most typical on ID cards)
        if all(t.istitle() for t in tokens):
            score += 40.0
        elif all(t.isupper() for t in tokens):
            score += 25.0

        # Proximity lookahead: immediately followed by DOB or date line
        if i + 1 < len(lines):
            next_line = lines[i + 1].lower()
            if any(k in next_line for k in ("dob", "birth", "जन्म", "01/", "19", "20")):
                score += 45.0
            if any(k in next_line for k in ("c/o", "s/o", "d/o", "w/o", "vtc", "flat")):
                score += 35.0

        # Proximity lookbehind: preceded by "To", "Name", "नाम"
        if i > 0:
            prev_line = lines[i - 1].lower()
            if any(k in prev_line for k in ("to", "name", "नाम", "enrolment")):
                score += 30.0

        prev_score, prev_conf = candidates.get(candidate_name, (0.0, 0.0))
        # Frequency bonus: identical name appearing multiple times on document
        if prev_score > 0:
            score += 45.0
        candidates[candidate_name] = (prev_score + score, max(prev_conf, conf))

    if not candidates:
        fallback_candidates = [ln for ln in lines if len(ln.split()) >= 2 and not any(ch.isdigit() for ch in ln)]
        fallback = fallback_candidates[0] if fallback_candidates else (lines[0] if lines else "")
        return fallback, 0.50

    best_name, (_, best_conf) = max(candidates.items(), key=lambda x: x[1][0])
    return best_name, round(best_conf, 4)


def _extract_document_number(
    full_text: str,
    lines_with_conf: List[Tuple[str, float]],
    detected_type: str = "unknown"
) -> Tuple[str, float]:
    """
    Extract the actual official document identifier with negative exclusions
    to prevent picking postal PIN codes, mobile numbers, VIDs, or enrolment IDs.
    """
    def is_negative_context(cand: str, line_text: str) -> bool:
        lt = line_text.lower()
        if any(k in lt for k in ("pin", "pincode", "pin code", "postal")) and cand in line_text:
            return True
        if any(k in lt for k in ("mobile", "mob", "phone", "tel")) and cand in line_text:
            return True
        if any(k in lt for k in ("vid", "virtual id")) and cand in line_text:
            return True
        if any(k in lt for k in ("enrolment", "enrollment")) and cand in line_text:
            return True
        return False

    # Aadhaar Number (12 digits with spaces or masked)
    aadhaar_matches = re.findall(
        r"\b(?:\d{4}\s\d{4}\s\d{4}|[Xx*]{4}\s[Xx*]{4}\s\d{4}|\d{12})\b",
        full_text
    )
    if aadhaar_matches and detected_type in ("national_id", "unknown"):
        for cand in aadhaar_matches:
            cand_lines = [l for l, _ in lines_with_conf if cand in l]
            if not any(is_negative_context(cand, cl) for cl in cand_lines):
                conf = 0.88
                for l, c in lines_with_conf:
                    if cand in l:
                        conf = max(conf, c)
                return cand, round(conf, 4)

    # PAN Card (5 uppercase + 4 digits + 1 uppercase)
    pan_matches = re.findall(r"\b([A-Z]{5}\d{4}[A-Z])\b", full_text)
    if pan_matches and detected_type in ("national_id", "unknown"):
        cand = pan_matches[0]
        conf = 0.92
        for l, c in lines_with_conf:
            if cand in l:
                conf = max(conf, c)
        return cand, round(conf, 4)

    # Passport Number
    if detected_type in ("passport", "unknown"):
        passport_matches = re.findall(r"\b([A-PR-WY-Z][0-9]{7,8})\b", full_text)
        if passport_matches:
            cand = passport_matches[0]
            conf = 0.90
            for l, c in lines_with_conf:
                if cand in l:
                    conf = max(conf, c)
            return cand, round(conf, 4)

    # Driving License Number
    if detected_type in ("driving_license", "unknown"):
        dl_matches = re.findall(r"\b([A-Z]{2}[-\s]?\d{2}[-\s]?(?:19|20)\d{2}[-\s]?\d{7})\b", full_text)
        if dl_matches:
            cand = dl_matches[0]
            conf = 0.90
            for l, c in lines_with_conf:
                if cand in l:
                    conf = max(conf, c)
            return cand, round(conf, 4)

    # General alphanumeric fallback: length 6-14 with at least one digit
    generic_candidates = re.findall(r"\b[A-Z0-9]{6,14}\b", full_text)
    for cand in generic_candidates:
        if not any(c.isdigit() for c in cand):
            continue
        cand_lines = [l for l, _ in lines_with_conf if cand in l]
        if any(is_negative_context(cand, cl) for cl in cand_lines):
            continue
        if len(cand) == 6 and any("pin" in l.lower() for l, _ in lines_with_conf):
            continue
        if len(cand) == 10 and any("mob" in l.lower() for l, _ in lines_with_conf):
            continue
        conf = 0.80
        for l, c in lines_with_conf:
            if cand in l:
                conf = max(conf, c)
        return cand, round(conf, 4)

    return "", 0.0


def _extract_gender(full_text: str, lines_with_conf: List[Tuple[str, float]]) -> Tuple[str, float]:
    """Extract gender with normalization and confidence."""
    lowered = full_text.lower()
    val = ""
    conf = 0.90
    if re.search(r"\b(female|mahila|महिला)\b", lowered):
        val = "FEMALE"
    elif re.search(r"\b(male|purush|पुरुष)\b", lowered):
        val = "MALE"
    elif re.search(r"\b(transgender|third gender)\b", lowered):
        val = "OTHER"
    elif re.search(r"\b\/?F\b", full_text):
        val = "F"
    elif re.search(r"\b\/?M\b", full_text):
        val = "M"

    if val:
        for l, c in lines_with_conf:
            if val.lower() in l.lower():
                conf = max(conf, c)
        return val, round(conf, 4)
    return "", 0.0


def _extract_address(lines: List[str]) -> Tuple[str, float]:
    """Extract and aggregate address lines into a structured string."""
    addr_lines = []
    for ln in lines:
        ln_lower = ln.lower()
        if any(k in ln_lower for k in _ADDRESS_KEYWORDS):
            if any(hdr in ln_lower for hdr in ("government", "authority", "identification", "proof of")):
                continue
            cleaned = ln.strip().strip(",;").strip()
            if cleaned and cleaned not in addr_lines:
                addr_lines.append(cleaned)
    if addr_lines:
        return ", ".join(addr_lines), 0.88
    return "", 0.0


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

    lines_with_conf: List[Tuple[str, float]] = [
        (text.strip(), float(conf)) for _, text, conf in results if text.strip()
    ]
    lines: List[str] = [t for t, _ in lines_with_conf]
    full_text = " \n ".join(lines)
    lowered = full_text.lower()

    detected_type = expected_type or "unknown"
    if detected_type == "unknown":
        for dtype, keywords in _TYPE_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                detected_type = dtype
                break

    dates_found = _DATE_PATTERN.findall(full_text)
    glued_dates = _GLUED_DATE_PATTERN.findall(full_text)
    for g in glued_dates:
        dates_found.append(f"{g[0]}/{g[1]}/{g[2]}")

    doc_num, doc_num_conf = _extract_document_number(full_text, lines_with_conf, detected_type)
    probable_name, name_conf = _extract_probable_name(lines_with_conf)
    gender_val, gender_conf = _extract_gender(full_text, lines_with_conf)

    fields: Dict[str, Any] = {
        "document_number": doc_num,
        "name": probable_name,
        "dates_found": dates_found,
        "raw_text_lines": lines,
    }

    field_confidences: Dict[str, float] = {
        "document_number": doc_num_conf,
        "name": name_conf,
        "gender": gender_conf,
    }

    # Document-specific mapping with label proximity date extraction
    if detected_type == "passport":
        dob_val, dob_c = _find_date_near_label(lines, _DOB_LABELS, dates_found[0] if dates_found else "")
        expiry_val, exp_c = _find_date_near_label(lines, _EXPIRY_LABELS, dates_found[1] if len(dates_found) > 1 else "")
        nat_val = "IND" if "india" in lowered else ("USA" if "usa" in lowered else "")
        fields.update({
            "passport_number": doc_num,
            "name": probable_name,
            "nationality": nat_val,
            "dob": dob_val,
            "date_of_birth": dob_val,
            "expiry": expiry_val,
            "expiration_date": expiry_val,
            "gender": gender_val,
            "mrz": "",
        })
        field_confidences.update({
            "passport_number": doc_num_conf,
            "nationality": 0.90 if nat_val else 0.50,
            "dob": dob_c,
            "date_of_birth": dob_c,
            "expiry": exp_c,
            "expiration_date": exp_c,
        })
    elif detected_type == "visa":
        issue_val, iss_c = _find_date_near_label(lines, _ISSUE_LABELS, dates_found[0] if dates_found else "")
        expiry_val, exp_c = _find_date_near_label(lines, _EXPIRY_LABELS, dates_found[1] if len(dates_found) > 1 else "")
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
        field_confidences.update({
            "visa_number": doc_num_conf,
            "issue_date": iss_c,
            "expiry_date": exp_c,
            "expiration_date": exp_c,
        })
    elif detected_type == "national_id":
        dob_val, dob_c = _find_date_near_label(lines, _DOB_LABELS, dates_found[0] if dates_found else "")
        addr_val, addr_c = _extract_address(lines)
        fields.update({
            "id_number": doc_num,
            "name": probable_name,
            "dob": dob_val,
            "date_of_birth": dob_val,
            "gender": gender_val,
            "address": addr_val,
        })
        field_confidences.update({
            "id_number": doc_num_conf,
            "dob": dob_c,
            "date_of_birth": dob_c,
            "address": addr_c,
        })
    elif detected_type == "driving_license":
        issue_val, iss_c = _find_date_near_label(lines, _ISSUE_LABELS, dates_found[0] if dates_found else "")
        expiry_val, exp_c = _find_date_near_label(lines, _EXPIRY_LABELS, dates_found[1] if len(dates_found) > 1 else "")
        dob_val, dob_c = _find_date_near_label(lines, _DOB_LABELS, dates_found[2] if len(dates_found) > 2 else "")
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
        field_confidences.update({
            "license_number": doc_num_conf,
            "issue_date": iss_c,
            "expiry_date": exp_c,
            "expiration_date": exp_c,
            "dob": dob_c,
            "date_of_birth": dob_c,
        })
    elif detected_type == "permit":
        issue_val, iss_c = _find_date_near_label(lines, _ISSUE_LABELS, dates_found[0] if dates_found else "")
        expiry_val, exp_c = _find_date_near_label(lines, _EXPIRY_LABELS, dates_found[1] if len(dates_found) > 1 else "")
        fields.update({
            "permit_number": doc_num,
            "name": probable_name,
            "permit_type": "Work" if "work" in lowered else "Residence",
            "issue_date": issue_val,
            "expiry_date": expiry_val,
            "expiration_date": expiry_val,
        })
        field_confidences.update({
            "permit_number": doc_num_conf,
            "issue_date": iss_c,
            "expiry_date": exp_c,
            "expiration_date": exp_c,
        })

    avg_conf = sum(c for _, _, c in results) / len(results) if results else 0.0
    confidence = {
        "ocr_average_confidence": round(avg_conf, 3),
        "document_type_guess": "keyword_match" if detected_type != "unknown" else "none",
        **field_confidences,
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
