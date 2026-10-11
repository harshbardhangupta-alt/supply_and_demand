"""Minimal, dependency-free auth: PBKDF2 password hashing + HMAC-signed tokens.

This is intentionally self-contained so the demo runs without extra packages.
For production, swap in a vetted library (argon2/bcrypt + PyJWT) and a real
secret manager — never ship the default secret.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{_b64e(salt)}${_b64e(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, _ = stored.split("$")
        return hmac.compare_digest(hash_password(password, _b64d(salt_b64)), stored)
    except Exception:
        return False


def create_token(username: str, role: str) -> str:
    settings = get_settings()
    payload = {
        "sub": username,
        "role": role,
        "exp": int(time.time()) + settings.jwt_expiry_minutes * 60,
    }
    body = _b64e(json.dumps(payload).encode())
    sig = hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


def decode_token(token: str) -> Optional[dict]:
    settings = get_settings()
    try:
        body, sig = token.split(".")
        expected = hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64d(sig), expected):
            return None
        payload = json.loads(_b64d(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


async def current_user(token: Optional[str] = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload


def require_role(*roles: str):
    async def checker(user: dict = Depends(current_user)) -> dict:
        if roles and user.get("role") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return checker
