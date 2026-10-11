"""Connections: in-app Dhan + OpenAI credential management and connection tests."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .. import credentials as creds
from ..brokers.base import BrokerError
from ..brokers.dhan import DhanBroker
from ..core.instruments import MarketUniverse
from ..db import get_session
from ..runtime import get_state
from ..security import current_user, require_role
from ..services.ai import OpenAIResearch
from ..services.scanner import scan_instrument, setup_to_row

router = APIRouter(prefix="/api/connections", tags=["connections"])


async def _reload(session: AsyncSession) -> None:
    get_state().apply_secrets(await creds.load_all(session))


@router.get("")
async def connections_status():
    st = get_state()
    dhan = creds.dhan_status(st.secrets)
    openai_key = st.secrets.get(creds.OPENAI_API_KEY) or ""
    return {
        "data_provider": st.data_provider_name(),
        "available_providers": ["synthetic", "dhan"],
        "dhan": {
            "configured": dhan.configured,
            "client_id": dhan.client_id_masked,
            "access_token": dhan.token_masked,
            "token_updated_at": dhan.token_updated_at,
            "token_age_hours": dhan.token_age_hours,
            "token_expired": dhan.token_expired,
            "expires_in_hours": dhan.expires_in_hours,
            "ttl_hours": creds.TOKEN_TTL_HOURS,
        },
        "openai": {
            "configured": bool(openai_key),
            "api_key": creds.mask(openai_key),
            "model": st.secrets.get(creds.OPENAI_MODEL) or "gpt-4o-mini",
        },
    }


class DhanBody(BaseModel):
    client_id: Optional[str] = None
    access_token: str


@router.put("/dhan")
async def set_dhan(body: DhanBody, session: AsyncSession = Depends(get_session),
                   user: dict = Depends(require_role("admin"))):
    if body.client_id is not None and body.client_id.strip():
        await creds.set_secret(session, creds.DHAN_CLIENT_ID, body.client_id.strip())
    if not body.access_token.strip():
        raise HTTPException(400, "access_token is required")
    await creds.set_secret(session, creds.DHAN_ACCESS_TOKEN, body.access_token.strip())
    await creds.set_secret(session, creds.DHAN_TOKEN_UPDATED,
                           datetime.now(timezone.utc).isoformat())
    await _reload(session)
    get_state().log_audit("dhan_credentials_updated",
                          {"client_id_set": bool(body.client_id)}, actor=user["sub"])
    return (await connections_status())


@router.post("/dhan/test")
async def test_dhan(user: dict = Depends(current_user)):
    st = get_state()
    cid = st.secrets.get(creds.DHAN_CLIENT_ID) or ""
    tok = st.secrets.get(creds.DHAN_ACCESS_TOKEN) or ""
    if not (cid and tok):
        raise HTTPException(400, "Dhan not configured. Save Client ID and Access Token first.")
    broker = DhanBroker(cid, tok)
    try:
        result = broker.test_connection()
        return {"ok": True, "detail": "Connected to Dhan.", "fund_limit": result.get("fund_limit")}
    except BrokerError as exc:
        return {"ok": False, "detail": str(exc)}


class ProviderBody(BaseModel):
    provider: str


@router.put("/provider")
async def set_provider(body: ProviderBody, session: AsyncSession = Depends(get_session),
                       user: dict = Depends(require_role("admin"))):
    if body.provider not in ("synthetic", "dhan"):
        raise HTTPException(400, "provider must be 'synthetic' or 'dhan'")
    if body.provider == "dhan":
        cid = get_state().secrets.get(creds.DHAN_CLIENT_ID) or ""
        tok = get_state().secrets.get(creds.DHAN_ACCESS_TOKEN) or ""
        if not (cid and tok):
            raise HTTPException(400, "Configure Dhan credentials before selecting the Dhan feed.")
    await creds.set_secret(session, creds.DATA_PROVIDER, body.provider)
    await _reload(session)
    get_state().log_audit("data_provider_changed", {"provider": body.provider}, actor=user["sub"])
    return {"data_provider": body.provider, "active_adapter": get_state().adapter.provider}


class OpenAIBody(BaseModel):
    api_key: str
    model: Optional[str] = None


@router.put("/openai")
async def set_openai(body: OpenAIBody, session: AsyncSession = Depends(get_session),
                     user: dict = Depends(require_role("admin"))):
    if not body.api_key.strip():
        raise HTTPException(400, "api_key is required")
    await creds.set_secret(session, creds.OPENAI_API_KEY, body.api_key.strip())
    if body.model:
        await creds.set_secret(session, creds.OPENAI_MODEL, body.model.strip())
    await _reload(session)
    get_state().log_audit("openai_credentials_updated", {}, actor=user["sub"])
    return (await connections_status())


@router.post("/openai/test")
async def test_openai(user: dict = Depends(current_user)):
    st = get_state()
    key = st.secrets.get(creds.OPENAI_API_KEY) or ""
    if not key:
        raise HTTPException(400, "OpenAI not configured. Save an API key first.")
    ai = OpenAIResearch(key, st.secrets.get(creds.OPENAI_MODEL) or "")
    try:
        return {"ok": True, **ai.test_connection()}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


# --- AI research ----------------------------------------------------------
ai_router = APIRouter(prefix="/api/ai", tags=["ai"])


class AnalyzeBody(BaseModel):
    symbol: str
    universe: str = MarketUniverse.NIFTY500.value


@ai_router.post("/analyze")
async def ai_analyze(body: AnalyzeBody, user: dict = Depends(current_user)):
    st = get_state()
    if not st.ai or not st.ai.configured:
        raise HTTPException(400, "OpenAI is not configured. Add an API key on the Connections page.")
    from ..core.instruments import DEFAULT_SPECS, equity_spec
    sym = body.symbol.upper()
    spec = DEFAULT_SPECS.get(sym) or equity_spec(
        sym, st.universe.state.constituents.get(sym).name
        if st.universe.state.constituents.get(sym) else sym)
    cfg = st.config_for(body.universe)
    res = scan_instrument(spec, st.adapter, cfg, st.settings.default_equity, count=cfg.max_lookback)
    row = setup_to_row(spec, res, st.adapter.provider, None)
    try:
        text = st.ai.analyze(sym, row)
        return {"symbol": sym, "analysis": text, "setup": row}
    except Exception as exc:
        raise HTTPException(502, f"AI analysis failed: {exc}")
