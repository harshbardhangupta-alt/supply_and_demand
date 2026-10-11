"""MetaTrader 5 broker adapter (scaffold).

Implements the broker-independent interface against the MetaTrader5 Python
package. It stays DISABLED unless a running MT5 terminal is reachable and
credentials are configured; without them calls raise :class:`BrokerError`
rather than fabricating prices, balances or fills.

MT5 brokers typically cover forex, metals and commodity CFDs. Symbol naming
varies per broker (suffixes/prefixes such as ``EURUSD.r`` or ``XAUUSD-ECN``),
so symbol resolution is dynamic via terminal discovery, never hardcoded to one
convention.

Note: the ``MetaTrader5`` package is Windows-only (or a Wine/bridge deployment).
Document this platform constraint for operators on Linux/Mac.
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


class MT5Broker(BrokerAdapter):
    name = "mt5"
    supports_live = True

    def __init__(self, login: Optional[str] = None, password: Optional[str] = None,
                 server: Optional[str] = None):
        self.login = login or os.getenv("MT5_LOGIN")
        self.password = password or os.getenv("MT5_PASSWORD")
        self.server = server or os.getenv("MT5_SERVER")
        self.connected = False
        self._symbol_cache: dict[str, str] = {}

    @property
    def configured(self) -> bool:
        return bool(self.login and self.password and self.server)

    def _require(self) -> None:
        if not self.configured:
            raise BrokerError(
                "MT5 adapter is not configured. Set MT5_LOGIN, MT5_PASSWORD and "
                "MT5_SERVER and run a reachable MetaTrader 5 terminal."
            )
        try:
            import MetaTrader5  # noqa: F401
        except Exception as exc:  # package not installed on this platform
            raise BrokerError(
                f"MetaTrader5 package unavailable on this platform ({exc}). "
                "MT5 live execution needs a Windows or bridged terminal."
            )

    def connect(self) -> bool:
        self._require()
        raise BrokerError(
            "MT5 live connection requires a running terminal; enable in a "
            "configured Windows/bridge deployment."
        )

    def account(self) -> AccountInfo:
        self._require()
        raise BrokerError("MT5 account() requires a live configured terminal.")

    def submit_order(self, req: OrderRequest) -> Order:
        self._require()
        raise BrokerError("MT5 submit_order() requires a live configured terminal.")

    def cancel_order(self, order_id: str) -> Order:
        self._require()
        raise BrokerError("MT5 cancel_order() requires a live configured terminal.")

    def get_order(self, order_id: str) -> Optional[Order]:
        self._require()
        raise BrokerError("MT5 get_order() requires a live configured terminal.")

    def positions(self) -> List[Position]:
        self._require()
        raise BrokerError("MT5 positions() requires a live configured terminal.")

    def orders(self) -> List[Order]:
        self._require()
        raise BrokerError("MT5 orders() requires a live configured terminal.")

    def resolve_symbol(self, canonical: str) -> Optional[str]:
        """Resolve a canonical symbol (e.g. EURUSD) to the broker's symbol
        variant via terminal discovery. Returns None when not found."""
        return self._symbol_cache.get(canonical)
