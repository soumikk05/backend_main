"""Encryption, masking, and retention primitives for sensitive screening data."""
from __future__ import annotations
import base64
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet

from app.config import DATA_ENCRYPTION_KEY, EVIDENCE_RETENTION_DAYS

def _fernet() -> Fernet:
    key = DATA_ENCRYPTION_KEY.encode()
    if len(key) != 44: key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
    return Fernet(key)

def encrypt_value(value: Optional[str]) -> Optional[str]:
    return _fernet().encrypt(value.encode()).decode() if value else None

def decrypt_value(value: Optional[str]) -> Optional[str]:
    return _fernet().decrypt(value.encode()).decode() if value else None

def normalize_doc_number(value: Optional[str]) -> Optional[str]:
    """Normalize document identifier by removing spaces, hyphens, slashes, and standardizing casing."""
    if not value:
        return None
    cleaned = "".join(ch for ch in str(value).strip().upper() if ch.isalnum())
    return cleaned if cleaned else None


def lookup_hash(value: Optional[str]) -> Optional[str]:
    """Compute deterministic SHA-256 blind index hash with automatic normalization."""
    if not value:
        return None
    v_str = str(value).strip().upper()
    # If it contains digits (like document number / ID), normalize by stripping whitespace and dashes
    if any(ch.isdigit() for ch in v_str):
        clean = "".join(ch for ch in v_str if ch.isalnum())
    else:
        # For names, normalize multiple spaces to a single space
        clean = " ".join(v_str.split())
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def keyed_lookup_hash(value: Optional[str], key: Optional[str] = None) -> Optional[str]:
    """
    Keyed HMAC-SHA-256 blind index construction (Requirement 24).
    Prevents dictionary and rainbow-table pre-computation attacks by tying search hashes to a server secret key.
    """
    import hmac
    if not value:
        return None
    secret = (key or DATA_ENCRYPTION_KEY).encode("utf-8")
    v_str = str(value).strip().upper()
    if any(ch.isdigit() for ch in v_str):
        clean = "".join(ch for ch in v_str if ch.isalnum())
    else:
        clean = " ".join(v_str.split())
    return hmac.new(secret, clean.encode("utf-8"), hashlib.sha256).hexdigest()


def mask_identifier(value: Optional[str], visible: int = 2) -> Optional[str]:
    if not value: return value
    return "*" * max(0, len(value) - visible) + value[-visible:]

def mask_name(value: Optional[str]) -> Optional[str]:
    if not value: return value
    return " ".join(f"{part[:1]}***" for part in value.split())

def purge_expired_evidence(root: str) -> int:
    cutoff = datetime.now() - timedelta(days=EVIDENCE_RETENTION_DAYS)
    removed = 0
    for path in Path(root).glob("*/*"):
        if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
            path.unlink(); removed += 1
    return removed
