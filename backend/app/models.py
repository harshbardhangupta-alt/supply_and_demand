"""SQLAlchemy ORM models for persistent trading state and audit records."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="trader")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Nifty500Membership(Base):
    __tablename__ = "nifty500_membership"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    industry: Mapped[str] = mapped_column(String(64), default="")
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default="seed")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ConfigVersion(Base):
    __tablename__ = "config_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ZoneRecord(Base):
    __tablename__ = "zones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8))
    direction: Mapped[str] = mapped_column(String(8))
    distal: Mapped[float] = mapped_column(Float)
    proximal: Mapped[float] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(16))
    touches: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(8))
    entry: Mapped[float] = mapped_column(Float)
    stop: Mapped[float] = mapped_column(Float)
    target: Mapped[float] = mapped_column(Float)
    reward_risk: Mapped[float] = mapped_column(Float)
    qty: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    entry_model: Mapped[str] = mapped_column(String(16))
    config_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class OrderRecord(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_order_id: Mapped[str] = mapped_column(String(64), index=True)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))
    order_type: Mapped[str] = mapped_column(String(8))
    qty: Mapped[float] = mapped_column(Float)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class TradeRecord(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(8))
    entry: Mapped[float] = mapped_column(Float)
    exit: Mapped[float] = mapped_column(Float)
    qty: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float)
    reward_risk_planned: Mapped[float] = mapped_column(Float, default=0.0)
    entry_model: Mapped[str] = mapped_column(String(16), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    exit_reason: Mapped[str] = mapped_column(String(32), default="")
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    closed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class RiskEvent(Base):
    __tablename__ = "risk_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(48))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    config_name: Mapped[str] = mapped_column(String(64))
    starting_equity: Mapped[float] = mapped_column(Float)
    metrics: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    action: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
