"""Application settings loaded from environment variables / .env."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SMC_", extra="ignore")

    app_name: str = "Institutional S&D Engine"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./smc.db"
    sync_database_url: str = "sqlite:///./smc.db"

    # Trading safety.
    live_trading_enabled: bool = False          # disabled by default
    paper_trading_enabled: bool = True
    default_equity: float = 1_000_000.0

    # Data.
    market_data_provider: str = "synthetic"     # synthetic | dhan | mt5
    data_max_age_seconds: float = 120.0

    # Universe.
    nifty500_refresh_on_start: bool = False

    # Auth (demo). In production use a real secret manager.
    jwt_secret: str = "change-me-in-production"
    jwt_expiry_minutes: int = 720
    admin_username: str = "admin"
    admin_password: str = "admin"               # change via env in real use

    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Broker (never commit real values; use env).
    dhan_client_id: str = ""
    dhan_access_token: str = ""
    mt5_login: str = ""
    mt5_password: str = ""
    mt5_server: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
