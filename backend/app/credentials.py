"""Credential / secret store for Dhan and OpenAI, persisted in the DB.

Values are written only server-side and never returned raw to the frontend
(always masked). The Dhan access token is expected to be rotated roughly every
24 hours, so its update time is tracked and exposed as an age / expiry hint.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AppSecret

# Secret keys.
DHAN_CLIENT_ID = "dhan_client_id"
DHAN_ACCESS_TOKEN = "dhan_access_token"
DHAN_TOKEN_UPDATED = "dhan_token_updated_at"
OPENAI_API_KEY = "openai_api_key"
OPENAI_MODEL = "openai_model"
DATA_PROVIDER = "data_provider"  # "synthetic" | "dhan"

TOKEN_TTL_HOURS = 24.0


def mask(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 8:
        return "••••"
    return f"{value[:4]}••••{value[-4:]}"


async def load_all(session: AsyncSession) -> Dict[str, str]:
    rows = (await session.execute(select(AppSecret))).scalars().all()
    return {r.key: r.value for r in rows}


async def set_secret(session: AsyncSession, key: str, value: str) -> None:
    existing = await session.get(AppSecret, key)
    if existing:
        existing.value = value
        existing.updated_at = datetime.now(timezone.utc)
    else:
        session.add(AppSecret(key=key, value=value))
    await session.commit()


@dataclass
class DhanStatus:
    configured: bool
    client_id_masked: Optional[str]
    token_masked: Optional[str]
    token_updated_at: Optional[str]
    token_age_hours: Optional[float]
    token_expired: bool
    expires_in_hours: Optional[float]


def dhan_status(secrets: Dict[str, str]) -> DhanStatus:
    cid = secrets.get(DHAN_CLIENT_ID) or ""
    tok = secrets.get(DHAN_ACCESS_TOKEN) or ""
    updated = secrets.get(DHAN_TOKEN_UPDATED) or ""
    age = None
    expired = False
    remaining = None
    if updated:
        try:
            ts = datetime.fromisoformat(updated)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = round((datetime.now(timezone.utc) - ts).total_seconds() / 3600, 2)
            remaining = round(TOKEN_TTL_HOURS - age, 2)
            expired = age >= TOKEN_TTL_HOURS
        except ValueError:
            pass
    return DhanStatus(
        configured=bool(cid and tok),
        client_id_masked=mask(cid),
        token_masked=mask(tok),
        token_updated_at=updated or None,
        token_age_hours=age,
        token_expired=expired,
        expires_in_hours=remaining,
    )
