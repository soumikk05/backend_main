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

def lookup_hash(value: Optional[str]) -> Optional[str]:
    return hashlib.sha256(value.strip().upper().encode()).hexdigest() if value else None

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
