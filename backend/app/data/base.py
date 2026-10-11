"""Market-data adapter interface and feed status metadata."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from ..core.candles import Candle, Timeframe


class FeedMode(str, Enum):
    REALTIME = "realtime"
    DELAYED = "delayed"
    HISTORICAL = "historical"
    SYNTHETIC = "synthetic"


@dataclass
class FeedStatus:
    provider: str
    mode: FeedMode
    last_update: Optional[datetime]
    connected: bool
    coverage_pct: float = 100.0
    unavailable_symbols: List[str] = None  # type: ignore

    def is_stale(self, max_age_seconds: float) -> bool:
        if self.last_update is None:
            return True
        age = (datetime.now(timezone.utc) - self.last_update).total_seconds()
        return age > max_age_seconds


class MarketDataAdapter(abc.ABC):
    """Base class for all market-data providers.

    Implementations must never fabricate live prices or silently substitute
    delayed data for real-time data. ``status`` always reports the true feed
    mode and last update time.
    """

    provider: str = "base"

    @abc.abstractmethod
    def get_candles(
        self, symbol: str, timeframe: Timeframe, count: int,
        end: Optional[datetime] = None,
    ) -> List[Candle]:
        ...

    @abc.abstractmethod
    def status(self, symbol: Optional[str] = None) -> FeedStatus:
        ...

    def get_multi(
        self, symbol: str, timeframes: List[Timeframe], count: int
    ) -> Dict[Timeframe, List[Candle]]:
        return {tf: self.get_candles(symbol, tf, count) for tf in timeframes}
