from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.auth import create_access_token
from app.config import AUTH_USERS

router = APIRouter(prefix="/api/auth", tags=["authentication"])

VALID_ROLES = {"officer", "supervisor", "admin", "auditor"}
COMMON_DEMO_PASSWORDS = {"demo", "password", "123456", "admin123", "demo-admin", "demo-officer", "demo-supervisor", "demo-auditor"}

class TokenRequest(BaseModel):
    username: str
    password: str
    role: str

@router.post("/token")
def token(request: TokenRequest):
    username = request.username.strip().lower()
    role = request.role.strip().lower()
    password = request.password.strip()

    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")

    # Check against configured AUTH_USERS or standard demo credentials
    expected_pw = AUTH_USERS.get(username)
    is_valid = False

    if expected_pw and password == expected_pw:
        is_valid = True
    elif password == username:
        # Allow username as password for quick convenience (e.g. admin/admin, officer/officer)
        is_valid = True
    elif password == f"demo-{username}":
        is_valid = True
    elif password in COMMON_DEMO_PASSWORDS and username in VALID_ROLES:
        is_valid = True
    elif username == "admin" and (password in {"admin", "demo-admin", "admin123", "password"}):
        is_valid = True

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials. Use demo credentials (e.g., username: admin, password: admin or demo-admin)."
        )

    access_token = create_access_token(username, role)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role,
        "username": username
    }

