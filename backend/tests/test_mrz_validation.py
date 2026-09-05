"""
Rigorous Unit & Integration Tests for ICAO Doc 9303 MRZ Validation.

Tests:
1. Valid TD3 Passport MRZ with all check digits correct.
2. Invalid document number check digit detection.
3. Invalid DOB check digit detection.
4. Invalid expiration check digit detection.
5. Malformed and incomplete MRZ lines.
6. Checksum arithmetic corner cases (weights 7-3-1, letters A-Z mapping, '<' filler).
"""

import pytest
from app.utils.mrz_parser import (
    compute_mrz_check_digit,
    verify_mrz_check_digit,
    validate_td3_mrz,
    char_to_mrz_value,
    format_mrz_date,
)


def test_char_to_mrz_value():
    assert char_to_mrz_value("0") == 0
    assert char_to_mrz_value("9") == 9
    assert char_to_mrz_value("A") == 10
    assert char_to_mrz_value("Z") == 35
    assert char_to_mrz_value("<") == 0
    assert char_to_mrz_value("a") == 10  # Case insensitive


def test_compute_mrz_check_digit_standard():
    # ICAO 9303 standard example: AB2134 -> A(10)*7 + B(11)*3 + 2*1 + 1*7 + 3*3 + 4*1 = 70+33+2+7+9+4 = 125 -> 125 % 10 = 5
    res = compute_mrz_check_digit("AB2134")
    assert res == "5"


def test_valid_td3_passport():
    # Real standard specimen from ICAO Doc 9303 Part 4
    # Line 1: P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
    # Line 2: L898902C36UTO7408122F1204159ZE184226B<<<<<10
    line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"

    res = validate_td3_mrz(line1, line2)
    assert res["valid"] is True
    assert res["valid_number"] is True
    assert res["valid_dob"] is True
    assert res["valid_expiry"] is True
    assert res["valid_composite"] is True
    assert res["document_number"] == "L898902C3"
    assert res["dob"] == "740812"
    assert res["expiry"] == "120415"


def test_tampered_document_number_checksum():
    # Modifying document number from L898902C3 to L898902C4 while keeping check digit 6
    line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    line2 = "L898902C46UTO7408122F1204159ZE184226B<<<<<10"

    res = validate_td3_mrz(line1, line2)
    assert res["valid"] is False
    assert res["valid_number"] is False
    assert res["valid_composite"] is False  # Composite will also fail


def test_tampered_dob_checksum():
    # Modifying DOB from 740812 to 740813 (different birth date) with check digit 2
    line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    line2 = "L898902C36UTO7408132F1204159ZE184226B<<<<<10"

    res = validate_td3_mrz(line1, line2)
    assert res["valid"] is False
    assert res["valid_dob"] is False


def test_tampered_expiry_checksum():
    # Modifying expiry from 120415 to 130415 with check digit 9
    line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    line2 = "L898902C36UTO7408122F1304159ZE184226B<<<<<10"

    res = validate_td3_mrz(line1, line2)
    assert res["valid"] is False
    assert res["valid_expiry"] is False


def test_malformed_mrz_length():
    # Too short
    res = validate_td3_mrz("P<UTOERIKSSON", "L898902C36UTO")
    assert res["valid"] is False
    assert "Invalid line length" in res["error"]


def test_format_mrz_date():
    assert format_mrz_date("950512") == "1995-05-12"
    assert format_mrz_date("050512") == "2005-05-12"
    assert format_mrz_date("") == ""
    assert format_mrz_date("ABCDEF") == ""
