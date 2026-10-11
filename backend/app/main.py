"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, routes, routes_connections, routes_signals, ws
from .db import init_db
from .runtime import get_state
from .settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("smc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("Starting %s (env=%s, live_trading=%s)", settings.app_name,
             settings.environment, settings.live_trading_enabled)
    await init_db()
    state = get_state()
    await _load_secrets(state)
    await _persist_universe(state)
    if settings.nifty500_refresh_on_start:
        state.universe.refresh()
    # Startup reconciliation placeholder: in a live deployment, reconcile broker
    # positions/orders here before enabling new entries.
    log.info("Universe loaded: %d constituents (source=%s)",
             len(state.universe.state.active_symbols()), state.universe.state.source)
    yield
    log.info("Shutting down")


async def _load_secrets(state) -> None:
    from . import credentials as creds
    from .db import SessionLocal
    async with SessionLocal() as session:
        state.apply_secrets(await creds.load_all(session))
    log.info("Integrations: data provider=%s, dhan=%s, openai=%s",
             state.data_provider_name(), bool(state.dhan_broker), bool(state.ai))


async def _persist_universe(state) -> None:
    from sqlalchemy import select
    from .db import SessionLocal
    from .models import Nifty500Membership
    async with SessionLocal() as session:
        existing = (await session.execute(select(Nifty500Membership.symbol))).scalars().all()
        existing = set(existing)
        for c in state.universe.state.constituents.values():
            if c.symbol not in existing:
                session.add(Nifty500Membership(
                    symbol=c.symbol, name=c.name, industry=c.industry,
                    effective_from=c.effective_from, active=c.active,
                    source=state.universe.state.source,
                ))
        await session.commit()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(routes.router)
    app.include_router(routes_connections.router)
    app.include_router(routes_connections.ai_router)
    app.include_router(routes_signals.router)
    app.include_router(ws.router)

    @app.get("/")
    async def root():
        return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
