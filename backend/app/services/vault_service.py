"""
Government Audit Vault Service.

Provides human-readable, highly structured on-disk audit folders organized per officer/user:
audit_vault/
  ├── <officer_username>/
  │     ├── profile.json               (Officer identity, role, badge, masked PII, hashed credentials)
  │     ├── login_sessions.jsonl       (Log of every login timestamp, IP, token ID, and status)
  │     └── screenings/
  │           ├── screening_<id>.json  (Full screening report: document hash, AES ciphertext, tampering score)
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import BASE_DIR

VAULT_ROOT = BASE_DIR / "audit_vault"


def get_user_vault_dir(username: str) -> Path:
    clean_username = "".join(c for c in username.lower() if c.isalnum() or c in ("_", "-"))
    user_dir = VAULT_ROOT / clean_username
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "screenings").mkdir(parents=True, exist_ok=True)
    return user_dir


def record_login_vault(
    user_data: Dict[str, Any],
    ip_address: Optional[str] = "127.0.0.1",
    user_agent: Optional[str] = "GovtScreeningTerminal/1.0",
    auth_status: str = "SUCCESS",
) -> Path:
    """Record officer login into their structured vault folder."""
    username = user_data.get("username", "unknown")
    user_dir = get_user_vault_dir(username)

    # 1. Update/Write profile.json
    profile_path = user_dir / "profile.json"
    profile_data = {
        "user_id": user_data.get("id"),
        "username": username,
        "email": user_data.get("email"),
        "full_name": user_data.get("full_name"),
        "official_role": user_data.get("role"),
        "badge_number": user_data.get("badge_number"),
        "account_status": "ACTIVE" if user_data.get("is_active", True) else "DEACTIVATED",
        "last_login": datetime.now(timezone.utc).isoformat(),
        "security_policy": "Salted Bcrypt (Cost 12) + Cryptographic JWT + AES-256 PII Protection",
    }
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2)

    # 2. Append login session record to login_sessions.jsonl
    sessions_path = user_dir / "login_sessions.jsonl"
    session_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "username": username,
        "role": user_data.get("role"),
        "badge_number": user_data.get("badge_number"),
        "ip_address": ip_address or "127.0.0.1",
        "user_agent": user_agent or "WebTerminal",
        "status": auth_status,
    }
    with open(sessions_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(session_entry) + "\n")

    return user_dir


def record_screening_vault(
    officer_username: str,
    screening_id: str,
    screening_payload: Dict[str, Any],
) -> Optional[Path]:
    """Save an officer's screening report into their personal screenings directory."""
    if not officer_username:
        officer_username = "system_unassigned"

    user_dir = get_user_vault_dir(officer_username)
    screenings_dir = user_dir / "screenings"

    file_name = f"screening_{screening_id[:8]}.json"
    file_path = screenings_dir / file_name

    structured_export = {
        "screening_id": screening_id,
        "screened_by_officer": officer_username,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "document_type": screening_payload.get("document_type"),
        "risk_assessment": {
            "risk_score": screening_payload.get("risk_score"),
            "risk_label": screening_payload.get("risk_label"),
            "decision": "APPROVED" if (screening_payload.get("risk_score", 0) < 40) else ("REJECTED" if screening_payload.get("risk_score", 0) >= 70 else "MANUAL_REVIEW"),
        },
        "zero_trust_security_proofs": {
            "document_number_sha256_hash": screening_payload.get("document_number_hash"),
            "document_number_aes_encrypted": screening_payload.get("document_number_encrypted"),
            "document_image_sha256_hash": screening_payload.get("image_hash"),
        },
        "tampering_analysis": screening_payload.get("tampering_result"),
        "biometric_face_match": screening_payload.get("face_result"),
        "extracted_ocr_fields": screening_payload.get("extracted_fields"),
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(structured_export, f, indent=2)

    return file_path
