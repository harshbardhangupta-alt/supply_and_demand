"""Dhan broker adapter (scaffold).

Implements the broker-independent interface against the Dhan REST API. It stays
DISABLED unless real credentials (DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN) are
configured; without them every call raises :class:`BrokerError` rather than
fabricating a connection, price, balance or order.

Dhan covers eligible Indian exchange instruments (NSE/BSE cash, F&O, currency,
commodity) via security-id mapping. It does NOT cover international forex, gold
CFDs or international commodities — those route to an MT5-type broker instead.

Reference: https://dhanhq.co/docs/v2/ (consult current docs before going live;
endpoints, rate limits and token-expiry behaviour change).
"""
from __future__ import annotations

import os
from typing import List, Optional

from .base import (
    AccountInfo,
    BrokerAdapter,
    BrokerError,
    Order,
    OrderRequest,
    Position,
)

DHAN_BASE_URL = "https://api.dhan.co/v2"


class DhanBroker(BrokerAdapter):
    name = "dhan"
    supports_live = True

    # Instruments Dhan can actually trade (asset classes). Used to reject
    # unsupported instruments explicitly instead of silent substitution.
    SUPPORTED_EXCHANGES = {"NSE", "BSE", "NSE_FNO", "MCX", "CDS"}

    def __init__(self, client_id: Optional[str] = None, access_token: Optional[str] = None):
        self.client_id = client_id or os.getenv("DHAN_CLIENT_ID")
        self.access_token = access_token or os.getenv("DHAN_ACCESS_TOKEN")
        self.connected = False
        self._security_map: dict[str, str] = {}

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.access_token)

    def _require(self) -> None:
        if not self.configured:
            raise BrokerError(
                "Dhan adapter is not configured. Set DHAN_CLIENT_ID and "
                "DHAN_ACCESS_TOKEN to enable live Dhan execution."
            )

    def _headers(self) -> dict:
        return {
            "access-token": self.access_token or "",
            "client-id": self.client_id or "",
            "Content-Type": "application/json",
        }

    def connect(self) -> bool:
        self._require()
        # Real implementation validates the token via GET /fundlimit.
        # Left unexecuted here to avoid pretending a live session exists.
        raise BrokerError(
            "Dhan live connection requires valid credentials and network access "
            "to api.dhan.co; enable in a configured deployment."
        )

    def account(self) -> AccountInfo:
        self._require()
        raise BrokerError("Dhan account() requires a live configured session.")

    def submit_order(self, req: OrderRequest) -> Order:
        self._require()
        raise BrokerError("Dhan submit_order() requires a live configured session.")

    def cancel_order(self, order_id: str) -> Order:
        self._require()
        raise BrokerError("Dhan cancel_order() requires a live configured session.")

    def get_order(self, order_id: str) -> Optional[Order]:
        self._require()
        raise BrokerError("Dhan get_order() requires a live configured session.")

    def positions(self) -> List[Position]:
        self._require()
        raise BrokerError("Dhan positions() requires a live configured session.")

    def orders(self) -> List[Order]:
        self._require()
        raise BrokerError("Dhan orders() requires a live configured session.")

    def map_security_id(self, symbol: str, exchange: str) -> Optional[str]:
        """Map a canonical symbol to Dhan's security id (from the instrument
        master CSV). Returns None when unmapped — callers must reject rather
        than guess."""
        return self._security_map.get(f"{exchange}:{symbol}")

    def supports_instrument(self, exchange: str) -> bool:
        return exchange in self.SUPPORTED_EXCHANGES
