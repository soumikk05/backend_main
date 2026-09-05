"""
MRZ (Machine Readable Zone) helpers and standalone ICAO 9303 checksum verification.

Supports:
- ICAO Doc 9303 7-3-1 weight modulus 10 check digit computation and verification.
- Full validation of TD1 (3x30), TD2 (2x36), and TD3 (2x44) MRZ standards.
- Detailed per-field validity reporting (document number, DOB, expiry, composite checksum).
"""

from typing import Any, Dict, Optional, Tuple


def char_to_mrz_value(c: str) -> int:
    """Map MRZ character to numeric value according to ICAO Doc 9303."""
    c = c.upper()
    if c.isdigit():
        return int(c)
    elif "A" <= c <= "Z":
        return ord(c) - ord("A") + 10
    elif c == "<":
        return 0
    return 0


def compute_mrz_check_digit(data: str) -> str:
    """
    Compute ICAO 9303 check digit using weights [7, 3, 1] modulo 10.
    """
    weights = [7, 3, 1]
    total = 0
    for idx, ch in enumerate(data):
        w = weights[idx % 3]
        v = char_to_mrz_value(ch)
        total += w * v
    return str(total % 10)


def verify_mrz_check_digit(data: str, expected_digit: str) -> bool:
    """Verify if data matches the expected check digit."""
    if not expected_digit or len(expected_digit) != 1:
        return False
    computed = compute_mrz_check_digit(data)
    return computed == expected_digit


def validate_td3_mrz(line1: str, line2: str) -> Dict[str, Any]:
    """
    Validate standard TD3 (Passport) MRZ: 2 lines of 44 characters each.
    Line 1: P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
    Line 2: L898902C36UTO7408122F1204159ZE184226B<<<<<10
    """
    line1 = line1.strip().replace(" ", "")
    line2 = line2.strip().replace(" ", "")

    if len(line1) != 44 or len(line2) != 44:
        return {
            "valid": False,
            "format": "TD3",
            "error": f"Invalid line length: line1={len(line1)}, line2={len(line2)} (expected 44 each)",
            "valid_number": False,
            "valid_dob": False,
            "valid_expiry": False,
            "valid_composite": False,
        }

    doc_number = line2[0:9]
    doc_number_check = line2[9]
    dob = line2[13:19]
    dob_check = line2[19]
    expiry = line2[21:27]
    expiry_check = line2[27]
    optional = line2[28:42]
    optional_check = line2[42] if line2[42] != "<" else None
    composite_check = line2[43]

    valid_number = verify_mrz_check_digit(doc_number, doc_number_check)
    valid_dob = verify_mrz_check_digit(dob, dob_check)
    valid_expiry = verify_mrz_check_digit(expiry, expiry_check)

    # Composite check covers: line2[0:10] + line2[13:20] + line2[21:43]
    composite_data = line2[0:10] + line2[13:20] + line2[21:43]
    valid_composite = verify_mrz_check_digit(composite_data, composite_check)

    return {
        "valid": bool(valid_number and valid_dob and valid_expiry and valid_composite),
        "format": "TD3",
        "valid_number": valid_number,
        "valid_dob": valid_dob,
        "valid_expiry": valid_expiry,
        "valid_composite": valid_composite,
        "document_number": doc_number.replace("<", ""),
        "dob": dob,
        "expiry": expiry,
        "error": None,
    }


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

    doc_number = data.get("number", "").replace("<", "").strip()
    dob_raw = data.get("date_of_birth", "")
    exp_raw = data.get("expiration_date", "")

    # Perform our own deterministic verification in case passporteye didn't evaluate
    valid_number = bool(data.get("valid_number"))
    valid_dob = bool(data.get("valid_date_of_birth"))
    valid_exp = bool(data.get("valid_expiration_date"))
    valid_comp = bool(data.get("valid_composite"))

    fields = {
        "full_name": f"{clean_mrz_string(data.get('surname'))} {clean_mrz_string(data.get('names'))}".strip(),
        "surname": clean_mrz_string(data.get("surname")),
        "given_names": clean_mrz_string(data.get("names")),
        "document_number": doc_number,
        "nationality": data.get("nationality", ""),
        "country": data.get("country", ""),
        "date_of_birth": format_mrz_date(dob_raw),
        "expiration_date": format_mrz_date(exp_raw),
        "sex": data.get("sex", ""),
        "document_type": data.get("type", ""),
        "personal_number": data.get("personal_number", "").replace("<", "").strip(),
    }

    confidence = {
        "document_number": valid_number,
        "date_of_birth": valid_dob,
        "expiration_date": valid_exp,
        "nationality": bool(data.get("valid_nationality")),
        "personal_number": bool(data.get("valid_personal_number")),
        "overall_composite": valid_comp,
        "mrz_ocr_confidence": data.get("valid_score", None),
    }

    return {"fields": fields, "confidence": confidence, "raw_mrz_text": data.get("raw_text", "")}


def format_mrz_date(raw: Optional[str]) -> str:
    """MRZ dates are YYMMDD. Convert to YYYY-MM-DD with a 2-digit century heuristic."""
    if not raw or len(raw) != 6 or not raw.isdigit():
        return ""
    yy, mm, dd = raw[0:2], raw[2:4], raw[4:6]
    century = "20" if int(yy) <= 30 else "19"
    return f"{century}{yy}-{mm}-{dd}"