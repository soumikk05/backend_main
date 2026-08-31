"""
API Key Authentication Dependency.

Enforces authentication on protected screening endpoints via `X-API-Key` header.
"""

import logging
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Header, HTTPException, Security, status, Depends
from fastapi.security import APIKeyHeader

from app.config import API_KEYS, REQUIRE_AUTH, JWT_SECRET, JWT_TTL_MINUTES, API_KEY_ROLES

logger = logging.getLogger(__name__)

api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def create_access_token(subject: str, role: str) -> str:
    header = _b64(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64(json.dumps({"sub": subject, "role": role, "exp": int((datetime.now(timezone.utc) + timedelta(minutes=JWT_TTL_MINUTES)).timestamp())}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): raise ValueError("signature")
        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(decoded["exp"]) < int(datetime.now(timezone.utc).timestamp()): raise ValueError("expired")
        return decoded
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token") from exc


def require_api_key(api_key: Optional[str] = Security(api_key_header_scheme), authorization: Optional[str] = Header(None)) -> str:
    """
    Validates the provided API key against configured valid keys.
    Exempts requests if REQUIRE_AUTH is explicitly set to false in development mode.
    """
    if authorization and authorization.startswith("Bearer "):
        return f"jwt:{decode_access_token(authorization[7:]).get('sub')}"
    if not REQUIRE_AUTH and not api_key:
        return "dev-mode-unauthenticated"

    if not api_key or api_key.strip() not in API_KEYS:
        logger.warning("Unauthorized request attempt with API key: %s", api_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header. Provide a valid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key.strip()


def require_roles(*roles: str):
    def dependency(api_key: Optional[str] = Security(api_key_header_scheme), authorization: Optional[str] = Header(None)) -> dict:
        if authorization and authorization.startswith("Bearer "):
            claims = decode_access_token(authorization[7:])
            if claims.get("role") not in roles: raise HTTPException(403, "Insufficient role")
            return claims
        if api_key in API_KEYS and API_KEY_ROLES.get(api_key, "admin") in roles:
            return {"sub": "api-key", "role": API_KEY_ROLES.get(api_key, "admin")}
        raise HTTPException(403, "A permitted role is required")
    return dependency
