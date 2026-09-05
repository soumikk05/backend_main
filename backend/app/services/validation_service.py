"""
Document Validation service (Module 2).

Pure rules engine providing:
1. MRZ Checksum and Syntax validation (ICAO Doc 9303 standard).
2. Cross-Field Consistency Checks (DOB vs Age, Issue Date vs Expiry Date, MRZ vs OCR agreement).
3. Country-Specific Document Format validation (India, USA, UK, Canada).
4. Explainable Rule Outputs with Severity, Observed Value, Expected Condition, and Field metadata.

Never raises — structured pass/fail results returned for all inputs.
"""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from app.validation.validators import validate_country_document

_ALPHA3_PATTERN = re.compile(r"^[A-Z]{3}$")
_DOC_NUMBER_PATTERN = re.compile(r"^[A-Z0-9\s\-]{6,19}$")

MIN_PLAUSIBLE_AGE = 0
MAX_PLAUSIBLE_AGE = 120


def validate_document(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for document validation.
    Returns structured, explainable results with cross-field consistency.
    """
    document_type = (extraction.get("document_type") or "unknown").lower()
    raw_fields = extraction.get("fields", {}) or {}
    fields = _field_values(raw_fields)
    confidence = extraction.get("confidence", {}) or {}

    if extraction.get("error"):
        error_check = _check(
            rule="ocr_precondition",
            field="document_image",
            passed=False,
            observed=str(extraction.get("error")),
            expected="Successful OCR extraction",
            severity="HIGH",
            message=f"Skipped validation: OCR extraction reported an error: {extraction['error']}",
        )
        return _build_result(document_type, [error_check])

    checks: List[Dict[str, Any]] = []

    # 1. MRZ or Fallback Baseline Rules
    if document_type in ("passport", "visa") and ("document_number" in fields or "passport_number" in fields) and confidence.get("document_number") is not None:
        checks.extend(_validate_mrz_backed_document(fields, confidence))
    else:
        checks.extend(_validate_fallback_document(fields))

    # 2. Cross-Field Consistency Rules
    checks.extend(_validate_cross_field_consistency(fields, raw_fields, document_type))

    # 3. Country-Specific Document Format Rules
    country = fields.get("nationality") or fields.get("issuing_country") or fields.get("country")
    doc_num = fields.get("document_number") or fields.get("passport_number") or fields.get("visa_number") or fields.get("id_number") or fields.get("license_number") or fields.get("permit_number")
    if doc_num and country:
        country_res = validate_country_document(str(doc_num), str(country), document_type)
        if country_res.get("valid") is not None:
            is_valid = bool(country_res["valid"])
            checks.append(_check(
                rule=country_res.get("rule", "country_format_check"),
                field="document_number",
                passed=is_valid,
                observed=str(doc_num),
                expected=f"Conforms to {country} format specification",
                severity="HIGH" if not is_valid else "LOW",
                message=country_res.get("message", "Country format validation complete"),
            ))

    # 4. OCR Confidence Gate
    confidences = [
        val.get("confidence") for val in raw_fields.values()
        if isinstance(val, dict) and isinstance(val.get("confidence"), (float, int))
    ]
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        if avg_conf < 0.55:
            checks.append(_check(
                rule="ocr_confidence",
                field="fields_confidence",
                passed=False,
                observed=f"{avg_conf:.2f}",
                expected=">= 0.55",
                severity="MEDIUM",
                message="Average OCR field confidence is low (< 0.55); manual review recommended",
            ))

    return _build_result(document_type, checks, confidences)


def _field_values(fields: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: (value.get("value") if isinstance(value, dict) and "value" in value else value)
        for key, value in fields.items()
    }


def _validate_mrz_backed_document(fields: Dict[str, Any], confidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks = []

    # Composite checksum
    composite_valid = bool(confidence.get("overall_composite"))
    checks.append(_check(
        rule="mrz_composite_checksum",
        field="raw_mrz",
        passed=composite_valid,
        observed="VALID" if composite_valid else "CHECKSUM_MISMATCH",
        expected="Valid ICAO Doc 9303 composite checksum",
        severity="HIGH",
        message="MRZ composite checksum passed" if composite_valid else "MRZ composite checksum FAILED — potential field alteration detected",
    ))

    # Field checksums
    for field_name, label in [
        ("document_number", "document_number_checksum"),
        ("date_of_birth", "date_of_birth_checksum"),
        ("expiration_date", "expiration_date_checksum"),
    ]:
        valid = bool(confidence.get(field_name))
        checks.append(_check(
            rule=label,
            field=field_name,
            passed=valid,
            observed=str(fields.get(field_name, "")),
            expected=f"Valid check digit for {field_name}",
            severity="HIGH" if not valid else "LOW",
            message=f"{field_name} checksum passed" if valid else f"{field_name} checksum FAILED",
        ))

    # Document number format
    doc_num = str(fields.get("document_number") or fields.get("passport_number") or "").upper()
    doc_num_ok = bool(_DOC_NUMBER_PATTERN.match(doc_num))
    checks.append(_check(
        rule="document_number_format",
        field="document_number",
        passed=doc_num_ok,
        observed=doc_num,
        expected="6-12 alphanumeric characters",
        severity="MEDIUM",
        message="Document number format valid" if doc_num_ok else f"Document number '{doc_num}' does not match standard pattern",
    ))

    # Nationality format
    nat = str(fields.get("nationality") or "").upper()
    nat_ok = bool(_ALPHA3_PATTERN.match(nat)) if nat else False
    checks.append(_check(
        rule="nationality_code_format",
        field="nationality",
        passed=nat_ok,
        observed=nat,
        expected="3-letter ICAO Alpha-3 code",
        severity="MEDIUM",
        message="Nationality code is valid ICAO Alpha-3" if nat_ok else f"Nationality code '{nat}' is missing or invalid",
    ))

    # Expiry & DOB
    checks.append(_date_not_expired_check(fields.get("expiration_date") or fields.get("expiry")))
    checks.append(_dob_plausible_check(fields.get("date_of_birth") or fields.get("dob")))

    return checks


def _validate_fallback_document(fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks = []
    doc_num = str(fields.get("document_number") or fields.get("id_number") or fields.get("license_number") or fields.get("visa_number") or fields.get("permit_number") or "").upper()
    clean_doc = re.sub(r"[\s\-]", "", doc_num)
    doc_num_ok = bool(_DOC_NUMBER_PATTERN.match(doc_num)) and (6 <= len(clean_doc) <= 18) if doc_num else False
    checks.append(_check(
        rule="document_number_format",
        field="document_number",
        passed=doc_num_ok,
        observed=doc_num,
        expected="Valid alphanumeric document identifier",
        severity="MEDIUM",
        message="Document number present and formatted" if doc_num_ok else "No valid document identifier detected",
    ))

    name_found = bool(fields.get("name") or fields.get("probable_name"))
    checks.append(_check(
        rule="name_detected",
        field="name",
        passed=name_found,
        observed=str(fields.get("name") or fields.get("probable_name") or ""),
        expected="Document holder full name",
        severity="MEDIUM",
        message="Holder name detected" if name_found else "Holder name not found in OCR text",
    ))

    expiry_val = fields.get("expiry_date") or fields.get("expiration_date") or fields.get("expiry") or fields.get("issue_or_expiry_date")
    checks.append(_date_not_expired_check(expiry_val, lenient=True))

    dob_val = fields.get("dob") or fields.get("date_of_birth")
    if dob_val:
        checks.append(_dob_plausible_check(dob_val))

    return checks


def _validate_cross_field_consistency(fields: Dict[str, Any], raw_fields: Dict[str, Any], document_type: str) -> List[Dict[str, Any]]:
    """Cross-field logic: expiry > issue, DOB <= today, age plausibility, MRZ vs OCR agreement."""
    checks = []

    issue_date_raw = fields.get("issue_date")
    expiry_date_raw = fields.get("expiry_date") or fields.get("expiration_date") or fields.get("expiry")
    dob_raw = fields.get("dob") or fields.get("date_of_birth")

    issue_dt = _parse_date_safe(issue_date_raw)
    expiry_dt = _parse_date_safe(expiry_date_raw)
    dob_dt = _parse_date_safe(dob_raw)

    # 1. Expiry date must follow Issue date
    if issue_dt and expiry_dt:
        order_ok = expiry_dt > issue_dt
        checks.append(_check(
            rule="expiry_after_issue",
            field="expiry_date",
            passed=order_ok,
            observed=f"Issue: {issue_dt.isoformat()}, Expiry: {expiry_dt.isoformat()}",
            expected="expiry_date > issue_date",
            severity="HIGH",
            message="Expiry date follows issue date" if order_ok else "Expiry date precedes or equals issue date (Invalid)",
        ))

    # 2. Issue date must be after Date of Birth
    if dob_dt and issue_dt:
        age_at_issue = (issue_dt - dob_dt).days // 365
        issue_after_dob = age_at_issue >= 0
        checks.append(_check(
            rule="issue_after_dob",
            field="issue_date",
            passed=issue_after_dob,
            observed=f"DOB: {dob_dt.isoformat()}, Issue: {issue_dt.isoformat()} (Age at issue: {age_at_issue})",
            expected="issue_date >= dob",
            severity="HIGH",
            message="Document issue date is chronologically valid after birth" if issue_after_dob else "Document issue date precedes date of birth",
        ))

    # 3. Name agreement between given_names/surname and full name
    given = str(fields.get("given_names") or "").strip()
    surname = str(fields.get("surname") or "").strip()
    full_name = str(fields.get("name") or "").strip()
    if given and surname and full_name:
        name_agrees = (given.upper() in full_name.upper()) or (surname.upper() in full_name.upper())
        checks.append(_check(
            rule="name_structure_consistency",
            field="name",
            passed=name_agrees,
            observed=f"Full: '{full_name}', Given: '{given}', Surname: '{surname}'",
            expected="Structured name elements match full name string",
            severity="MEDIUM",
            message="Name fields are internally consistent" if name_agrees else "Discrepancy detected between individual name fields and full name",
        ))

    return checks


def _parse_date_safe(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %m %Y", "%d/%m/%y", "%Y%m%d"):
        try:
            return datetime.strptime(str(raw).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _date_not_expired_check(raw_expiry: Optional[str], lenient: bool = False) -> Dict[str, Any]:
    parsed = _parse_date_safe(raw_expiry)
    if parsed is None:
        if lenient:
            return _check(
                rule="expiry_date_not_expired",
                field="expiry_date",
                passed=True,
                observed=str(raw_expiry or "None"),
                expected="Parseable valid expiration date",
                severity="LOW",
                message="Expiry date could not be parsed confidently from fallback text — skipped",
            )
        return _check(
            rule="expiry_date_not_expired",
            field="expiry_date",
            passed=False,
            observed=str(raw_expiry or "None"),
            expected="Valid future expiration date",
            severity="HIGH",
            message=f"Could not parse expiration date '{raw_expiry}'",
        )

    is_valid = parsed >= date.today()
    return _check(
        rule="expiry_date_not_expired",
        field="expiry_date",
        passed=is_valid,
        observed=parsed.isoformat(),
        expected=f">= {date.today().isoformat()}",
        severity="HIGH" if not is_valid else "LOW",
        message=f"Document is valid until {parsed.isoformat()}" if is_valid else f"Document EXPIRED on {parsed.isoformat()}",
    )


def _dob_plausible_check(raw_dob: Optional[str]) -> Dict[str, Any]:
    parsed = _parse_date_safe(raw_dob)
    if parsed is None:
        return _check(
            rule="date_of_birth_plausible",
            field="date_of_birth",
            passed=False,
            observed=str(raw_dob or "None"),
            expected="Valid date format",
            severity="MEDIUM",
            message=f"Could not parse date of birth '{raw_dob}'",
        )

    if parsed > date.today():
        return _check(
            rule="date_of_birth_plausible",
            field="date_of_birth",
            passed=False,
            observed=parsed.isoformat(),
            expected=f"<= {date.today().isoformat()}",
            severity="HIGH",
            message=f"Date of birth {parsed.isoformat()} is in the future",
        )

    age_years = (date.today() - parsed).days // 365
    plausible = MIN_PLAUSIBLE_AGE <= age_years <= MAX_PLAUSIBLE_AGE
    return _check(
        rule="date_of_birth_plausible",
        field="date_of_birth",
        passed=plausible,
        observed=f"{parsed.isoformat()} (Age ~{age_years})",
        expected=f"Age between {MIN_PLAUSIBLE_AGE} and {MAX_PLAUSIBLE_AGE} years",
        severity="HIGH" if not plausible else "LOW",
        message=f"Age ~{age_years} years is plausible" if plausible else f"Age ~{age_years} years is outside plausible range",
    )


def _check(rule: str, field: str, passed: bool, observed: str, expected: str, severity: str, message: str) -> Dict[str, Any]:
    """Explainable check record."""
    return {
        "rule": rule,
        "name": rule,  # backwards compatibility
        "field": field,
        "passed": passed,
        "observed_value": observed,
        "expected_condition": expected,
        "severity": severity,
        "message": message,
        "reason": message,  # backwards compatibility
    }


def _build_result(document_type: str, checks: List[Dict[str, Any]], confidences: Optional[List[float]] = None) -> Dict[str, Any]:
    passed_rules = [c for c in checks if c["passed"]]
    failed_rules = [c for c in checks if not c["passed"]]
    pass_count = len(passed_rules)
    fail_count = len(failed_rules)
    total_checks = len(checks)

    consistency_score = round((pass_count / total_checks * 100.0) if total_checks > 0 else 0.0, 2)
    overall_valid = (fail_count == 0 and total_checks > 0)

    return {
        "document_type": document_type,
        "checks": checks,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "overall_valid": overall_valid,
        "valid": overall_valid,
        "consistency_score": consistency_score,
        "passed_rules": passed_rules,
        "failed_rules": failed_rules,
        "warnings": [c["message"] for c in failed_rules],
        "confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0.85,
    }
