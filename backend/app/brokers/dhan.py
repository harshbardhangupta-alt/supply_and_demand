"""Dhan broker adapter (DhanHQ v2 REST).

Covers eligible Indian exchange instruments via security-id mapping. Stays
disabled unless a client id + access token are supplied (from the in-app
Connections page or env). It never fabricates a session, price, balance or
fill — unconfigured or failing calls raise :class:`BrokerError`.

Endpoints follow DhanHQ v2 (https://dhanhq.co/docs/v2/). Verify against current
docs before live use; rate limits and token expiry (≈24h) apply.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from .base import (
    AccountInfo,
    BrokerAdapter,
    BrokerError,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)

DHAN_BASE_URL = "https://api.dhan.co/v2"

# Our canonical order enums -> Dhan constants.
_SIDE = {OrderSide.BUY: "BUY", OrderSide.SELL: "SELL"}
_OTYPE = {OrderType.MARKET: "MARKET", OrderType.LIMIT: "LIMIT", OrderType.STOP: "STOP_LOSS_MARKET"}


class DhanBroker(BrokerAdapter):
    name = "dhan"
    supports_live = True
    SUPPORTED_EXCHANGES = {"NSE_EQ", "NSE_FNO", "BSE_EQ", "MCX_COMM", "IDX_I"}

    def __init__(self, client_id: Optional[str] = None, access_token: Optional[str] = None,
                 timeout: float = 15.0):
        self.client_id = client_id or os.getenv("SMC_DHAN_CLIENT_ID") or os.getenv("DHAN_CLIENT_ID")
        self.access_token = (
            access_token or os.getenv("SMC_DHAN_ACCESS_TOKEN") or os.getenv("DHAN_ACCESS_TOKEN")
        )
        self.timeout = timeout
        self.connected = False

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.access_token)

    def _headers(self) -> dict:
        return {
            "access-token": self.access_token or "",
            "client-id": self.client_id or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _require(self) -> None:
        if not self.configured:
            raise BrokerError(
                "Dhan is not configured. Add your Client ID and Access Token on the "
                "Connections page (the token must be refreshed roughly every 24h)."
            )

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=DHAN_BASE_URL, headers=self._headers(),
                            timeout=self.timeout)

    # --- connection / account ---------------------------------------------
    def test_connection(self) -> dict:
        """Validate credentials against the fund-limit endpoint."""
        self._require()
        try:
            with self._client() as c:
                r = c.get("/fundlimit")
            if r.status_code == 401:
                raise BrokerError("Dhan rejected the credentials (401). The access token "
                                  "may have expired — generate a new one and update it.")
            r.raise_for_status()
            data = r.json()
            self.connected = True
            return {"ok": True, "fund_limit": data}
        except httpx.HTTPError as exc:
            raise BrokerError(f"Dhan connection failed: {exc}") from exc

    def connect(self) -> bool:
        self.test_connection()
        return True

    def account(self) -> AccountInfo:
        self._require()
        with self._client() as c:
            r = c.get("/fundlimit")
            r.raise_for_status()
            d = r.json()
        avail = float(d.get("availabelBalance", d.get("availableBalance", 0)) or 0)
        util = float(d.get("utilizedAmount", 0) or 0)
        return AccountInfo(
            account_id=self.client_id or "DHAN", currency="INR",
            equity=avail + util, balance=avail, free_margin=avail,
            used_margin=util, is_live=True,
        )

    # --- orders ------------------------------------------------------------
    def submit_order(self, req: OrderRequest) -> Order:
        self._require()
        body = {
            "dhanClientId": self.client_id,
            "correlationId": (req.client_order_id or "")[:25],
            "transactionType": _SIDE[req.side],
            "exchangeSegment": "NSE_EQ",
            "productType": "CNC",
            "orderType": _OTYPE[req.order_type],
            "validity": "DAY",
            "securityId": req.tag or "",   # caller sets tag to the Dhan security id
            "quantity": int(req.qty),
            "price": req.price or 0,
            "triggerPrice": 0,
        }
        try:
            with self._client() as c:
                r = c.post("/orders", json=body)
            r.raise_for_status()
            d = r.json()
            oid = str(d.get("orderId", ""))
            status = _map_status(d.get("orderStatus", "PENDING"))
            return Order(id=oid, request=req, status=status, broker_order_id=oid)
        except httpx.HTTPError as exc:
            raise BrokerError(f"Dhan order submission failed: {exc}") from exc

    def cancel_order(self, order_id: str) -> Order:
        self._require()
        with self._client() as c:
            r = c.delete(f"/orders/{order_id}")
            r.raise_for_status()
        return Order(id=order_id, request=None, status=OrderStatus.CANCELLED,  # type: ignore[arg-type]
                     broker_order_id=order_id)

    def get_order(self, order_id: str) -> Optional[Order]:
        self._require()
        with self._client() as c:
            r = c.get(f"/orders/{order_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            d = r.json()
        d = d[0] if isinstance(d, list) and d else d
        return Order(id=order_id, request=None, status=_map_status(d.get("orderStatus", "PENDING")),  # type: ignore[arg-type]
                     broker_order_id=order_id, avg_fill_price=d.get("averageTradedPrice"))

    def orders(self) -> List[Order]:
        self._require()
        with self._client() as c:
            r = c.get("/orders")
            r.raise_for_status()
            data = r.json() or []
        out = []
        for d in data:
            out.append(Order(id=str(d.get("orderId", "")), request=None,  # type: ignore[arg-type]
                             status=_map_status(d.get("orderStatus", "PENDING")),
                             broker_order_id=str(d.get("orderId", ""))))
        return out

    def positions(self) -> List[Position]:
        self._require()
        with self._client() as c:
            r = c.get("/positions")
            r.raise_for_status()
            data = r.json() or []
        out = []
        for d in data:
            qty = float(d.get("netQty", 0) or 0)
            if qty == 0:
                continue
            side = OrderSide.BUY if qty > 0 else OrderSide.SELL
            out.append(Position(
                symbol=d.get("tradingSymbol", ""), side=side, qty=abs(qty),
                avg_price=float(d.get("costPrice", d.get("buyAvg", 0)) or 0),
                unrealized_pnl=float(d.get("unrealizedProfit", 0) or 0),
            ))
        return out

    def supports_instrument(self, exchange: str) -> bool:
        return exchange in self.SUPPORTED_EXCHANGES


def _map_status(s: str) -> OrderStatus:
    s = (s or "").upper()
    return {
        "TRANSIT": OrderStatus.SUBMITTED,
        "PENDING": OrderStatus.SUBMITTED,
        "TRADED": OrderStatus.FILLED,
        "EXECUTED": OrderStatus.FILLED,
        "CANCELLED": OrderStatus.CANCELLED,
        "REJECTED": OrderStatus.REJECTED,
        "EXPIRED": OrderStatus.EXPIRED,
    }.get(s, OrderStatus.SUBMITTED)
