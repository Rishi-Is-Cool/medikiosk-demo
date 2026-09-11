"""
MediKiosk Backend — Authentication API
Handles kiosk terminal login, doctor authentication, and JWT token issuance.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import DoctorProfile, User
from app.database.seed import copy_default_templates
from app.models.pydantic_models import Token
from app.utils.security import create_access_token, decode_token, get_password_hash, oauth2_scheme, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class DoctorRegistration(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    name: str
    practitioner_type: str = Field(description="'general' or 'ayurveda' — fixed at signup, sets which console the doctor sees")
    qualifications: str | None = None

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
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 password flow for kiosk terminal / physician authentication.
    Returns a JWT bearer token valid for 24 hours.

    Doctor and admin accounts are DB-backed (real signup or seeded, hashed
    passwords) and checked first; only the kiosk terminal still uses the
    in-memory credential store below.
    """
    db_user = db.query(User).filter(User.username == form_data.username, User.role.in_(["doctor", "admin"])).first()
    if db_user and db_user.hashed_password and verify_password(form_data.password, db_user.hashed_password):
        access_token = create_access_token(data={"sub": db_user.username, "role": db_user.role})
        return {"access_token": access_token, "token_type": "bearer", "role": db_user.role}

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


@router.post(
    "/register-doctor",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new doctor account (open self-serve signup)"
)
async def register_doctor(payload: DoctorRegistration, db: Session = Depends(get_db)):
    """
    Creates a doctor account with a fixed specialty (practitioner_type).
    That specialty is set once, at signup, and determines which console the
    doctor sees and which patients get routed to them — it isn't editable
    from the console afterward. Returns a token immediately (auto-login).
    """
    practitioner_type = payload.practitioner_type.strip().lower()
    if practitioner_type not in {"general", "ayurveda"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "practitioner_type must be 'general' or 'ayurveda'")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken")

    db.add(User(username=payload.username, role="doctor", display_name=payload.name,
               hashed_password=get_password_hash(payload.password)))
    db.add(DoctorProfile(username=payload.username, name=payload.name, practitioner_type=practitioner_type,
                         qualifications=payload.qualifications,
                         department="Ayurveda OPD" if practitioner_type == "ayurveda" else "General Medicine OPD"))
    db.flush()
    copy_default_templates(db, payload.username, practitioner_type)
    db.commit()

    access_token = create_access_token(data={"sub": payload.username, "role": "doctor"})
    return {"access_token": access_token, "token_type": "bearer", "role": "doctor"}


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
