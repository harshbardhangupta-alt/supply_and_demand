"""Null market-data adapter.

Used when the live provider (Dhan) is not configured. It returns NO candles and
reports the feed as disconnected — so the app never shows dummy/synthetic data.
The UI surfaces a "connect Dhan" state instead.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..core.candles import Candle, Timeframe
from .base import FeedMode, FeedStatus, MarketDataAdapter


class NullDataAdapter(MarketDataAdapter):
    provider = "dhan"   # the intended provider; just not connected yet

    def get_candles(self, symbol: str, timeframe: Timeframe, count: int,
                    end: Optional[datetime] = None) -> List[Candle]:
        return []

    def status(self, symbol: Optional[str] = None) -> FeedStatus:
        return FeedStatus(
            provider=self.provider, mode=FeedMode.HISTORICAL, last_update=None,
            connected=False, coverage_pct=0.0, unavailable_symbols=[],
        )
