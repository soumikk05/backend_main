"""
Authentication & Authorization System (RBAC + JWT + Bcrypt).

Enforces authentication on protected screening endpoints via:
- Bearer JWT tokens (Header: Authorization: Bearer <token>)
- API Key headers (Header: X-API-Key: <key>)
- Salted Bcrypt password hashing
- Role-Based Access Control (RBAC) with roles: 'admin', 'investigator', 'officer'
"""

import logging
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import bcrypt
from fastapi import Header, HTTPException, Security, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import API_KEYS, REQUIRE_AUTH, JWT_SECRET, JWT_TTL_MINUTES, API_KEY_ROLES
from app.db import get_db

logger = logging.getLogger(__name__)

api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


# ---------------------------------------------------------------------------
# Password Hashing Primitives (Bcrypt + Salt)
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using salted bcrypt (cost factor 12)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as exc:
        logger.warning("Password verification failure: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Cryptographic JWT Tokens (HMAC-SHA256)
# ---------------------------------------------------------------------------

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def create_access_token(
    subject: str,
    role: str = "officer",
    username: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed, base64-encoded JWT token."""
    ttl = expires_delta or timedelta(minutes=JWT_TTL_MINUTES)
    exp_timestamp = int((datetime.now(timezone.utc) + ttl).timestamp())

    payload_dict = {
        "sub": subject,
        "username": username or subject,
        "role": role,
        "exp": exp_timestamp,
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }

    header = _b64(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64(json.dumps(payload_dict, separators=(",", ":")).encode())
    signature = _b64(
        hmac.new(
            JWT_SECRET.encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256,
        ).digest()
    )
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Validate token signature and expiration, returning decoded payload."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed token")
        header, payload, signature = parts

        expected_sig = _b64(
            hmac.new(
                JWT_SECRET.encode(),
                f"{header}.{payload}".encode(),
                hashlib.sha256,
            ).digest()
        )
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid signature")

        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(decoded.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Token expired")

        return decoded
    except Exception as exc:
        logger.warning("Token decoding failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# FastAPI Auth & RBAC Dependencies
# ---------------------------------------------------------------------------

def require_api_key(
    api_key: Optional[str] = Security(api_key_header_scheme),
    authorization: Optional[str] = Header(None),
) -> str:
    """
    Validates API key or Bearer JWT token.
    Exempts requests if REQUIRE_AUTH is explicitly set to false in development mode.
    """
    if authorization and authorization.startswith("Bearer "):
        claims = decode_access_token(authorization[7:])
        return f"jwt:{claims.get('sub')}"

    if not REQUIRE_AUTH and not api_key:
        return "dev-mode-unauthenticated"

    if not api_key or api_key.strip() not in API_KEYS:
        logger.warning("Unauthorized request attempt with API key: %s", api_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication credentials (provide X-API-Key or Bearer token).",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key.strip()


def get_current_user(
    authorization: Optional[str] = Header(None),
    api_key: Optional[str] = Security(api_key_header_scheme),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Resolve the current authenticated user/officer context from JWT or API key.
    """
    if authorization and authorization.startswith("Bearer "):
        claims = decode_access_token(authorization[7:])
        user_id = claims.get("sub")
        # Try resolving full user model from DB
        from app.models.database import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if not user.is_active:
                raise HTTPException(status_code=403, detail="User account is deactivated")
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "badge_number": user.badge_number,
                "auth_type": "jwt",
            }
        return {
            "id": user_id,
            "username": claims.get("username", "unknown"),
            "role": claims.get("role", "officer"),
            "auth_type": "jwt",
        }

    if api_key and api_key.strip() in API_KEYS:
        role = API_KEY_ROLES.get(api_key.strip(), "admin")
        return {
            "id": "api-key-user",
            "username": "api-key",
            "role": role,
            "auth_type": "api_key",
        }

    if not REQUIRE_AUTH:
        return {
            "id": "dev-user-id",
            "username": "dev-officer",
            "role": "admin",
            "auth_type": "dev_bypass",
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Authorization: Bearer <jwt> or X-API-Key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(*roles: str):
    """
    Dependency factory enforcing Role-Based Access Control (RBAC).
    Example: Depends(require_roles('admin', 'investigator'))
    """
    def dependency(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        user_role = current_user.get("role", "")
        if user_role not in roles:
            logger.warning(
                "Access denied for user %s with role %s (required: %s)",
                current_user.get("username"),
                user_role,
                roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles: {list(roles)}",
            )
        return current_user

    return dependency
