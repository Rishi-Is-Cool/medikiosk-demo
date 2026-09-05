"""
MediKiosk Backend — Authentication API
Handles kiosk terminal login, doctor authentication, and JWT token issuance.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models.pydantic_models import Token
from app.utils.security import create_access_token, decode_token, oauth2_scheme

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ─── In-memory credential store (replace with DB-backed user table in production) ─
# Credentials can be overridden via environment variables
_KIOSK_CREDENTIALS = {
    os.getenv("KIOSK_USERNAME", "kiosk_terminal_01"): {
        "password": os.getenv("KIOSK_PASSWORD", "kiosk@MediK2026"),
        "role": "kiosk"
    },
    os.getenv("DOCTOR_USERNAME", "doctor_opd_101"): {
        "password": os.getenv("DOCTOR_PASSWORD", "doc@MediK2026"),
        "role": "doctor"
    },
    os.getenv("ADMIN_USERNAME", "admin"): {
        "password": os.getenv("ADMIN_PASSWORD", "admin@MediK2026"),
        "role": "admin"
    },
    # Legacy / test credentials (also accept simple test passwords)
    "kiosk123": {"password": "kiosk123", "role": "kiosk"},
    "doc123": {"password": "doc123", "role": "doctor"},
    "admin123": {"password": "admin123", "role": "admin"},
}


@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate kiosk terminal or doctor and receive JWT token"
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 password flow for kiosk terminal / physician authentication.
    Returns a JWT bearer token valid for 24 hours.
    """
    user_entry = _KIOSK_CREDENTIALS.get(form_data.username)

    # Also check simple username=password pattern for test clients
    if not user_entry:
        # Allow username to be used as lookup where username in passwords
        for uname, udata in _KIOSK_CREDENTIALS.items():
            if udata["password"] == form_data.password and form_data.username in uname:
                user_entry = udata
                break

    if not user_entry or user_entry["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = user_entry["role"]
    access_token = create_access_token(data={"sub": form_data.username, "role": role})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role
    }


@router.get(
    "/me",
    summary="Get current authenticated user identity from JWT token"
)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Returns the identity (username + role) of the authenticated user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    payload = decode_token(token)
    return {
        "username": payload.get("sub"),
        "role": payload.get("role"),
        "token_valid": True
    }
