"""Broker-independent execution interface and order/position domain models."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    qty: float
    order_type: OrderType
    price: Optional[float] = None       # limit/stop price
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    client_order_id: Optional[str] = None   # idempotency key
    expire_at: Optional[datetime] = None
    tag: Optional[str] = None


@dataclass
class Order:
    id: str
    request: OrderRequest
    status: OrderStatus
    filled_qty: float = 0.0
    avg_fill_price: Optional[float] = None
    broker_order_id: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Position:
    symbol: str
    side: OrderSide
    qty: float
    avg_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AccountInfo:
    account_id: str
    currency: str
    equity: float
    balance: float
    free_margin: float
    used_margin: float
    is_live: bool = False


class BrokerError(Exception):
    pass


class BrokerAdapter(abc.ABC):
    """Common execution contract. Implementations never claim a fill without a
    broker confirmation and must support idempotent order submission."""

    name: str = "base"
    supports_live: bool = False

    @abc.abstractmethod
    def connect(self) -> bool: ...

    @abc.abstractmethod
    def account(self) -> AccountInfo: ...

    @abc.abstractmethod
    def submit_order(self, req: OrderRequest) -> Order: ...

    @abc.abstractmethod
    def cancel_order(self, order_id: str) -> Order: ...

    @abc.abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]: ...

    @abc.abstractmethod
    def positions(self) -> List[Position]: ...

    @abc.abstractmethod
    def orders(self) -> List[Order]: ...

    def reconcile(self) -> Dict[str, object]:
        """Return the broker's authoritative order/position state for
        startup/restart reconciliation."""
        return {"orders": self.orders(), "positions": self.positions()}

    def supported_instruments(self) -> List[str]:
        return []
