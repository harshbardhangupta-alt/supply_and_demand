"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..security import create_token, current_user, hash_password, verify_password
from ..settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Demo in-memory user store seeded from settings. Replace with DB-backed users
# and a real secret manager in production.
_settings = get_settings()
_USERS = {
    _settings.admin_username: {
        "password_hash": hash_password(_settings.admin_password),
        "role": "admin",
    }
}


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = _USERS.get(form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_token(form.username, user["role"])
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    return {"username": user["sub"], "role": user.get("role")}
