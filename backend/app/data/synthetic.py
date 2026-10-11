"""Deterministic synthetic market-data adapter.

Generates reproducible OHLC series with realistic structure (trends, swings,
pullbacks and occasional displacement bursts) so the full engine, scanner,
paper trading and backtester can run entirely offline. Series are clearly
reported as ``FeedMode.SYNTHETIC`` and are never presented as real data.
"""
from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ..core.candles import Candle, Timeframe
from .base import FeedMode, FeedStatus, MarketDataAdapter


def _seed(symbol: str, timeframe: Timeframe) -> int:
    h = hashlib.sha256(f"{symbol}:{timeframe.value}".encode()).hexdigest()
    return int(h[:12], 16)


def _base_price(symbol: str) -> float:
    h = int(hashlib.sha256(symbol.encode()).hexdigest()[:8], 16)
    # Spread base prices across a plausible range.
    return 50 + (h % 300000) / 100.0


class SyntheticDataAdapter(MarketDataAdapter):
    provider = "synthetic"

    def __init__(self, volatility: float = 0.01, drift_bias: float = 0.0004):
        self.volatility = volatility
        self.drift_bias = drift_bias

    def get_candles(
        self, symbol: str, timeframe: Timeframe, count: int,
        end: Optional[datetime] = None,
    ) -> List[Candle]:
        rng = random.Random(_seed(symbol, timeframe))
        price = _base_price(symbol)
        # Symbol-derived drift direction: ~60% uptrend so demand setups appear.
        dir_sign = 1.0 if (_seed(symbol, timeframe) % 10) < 6 else -1.0
        drift = dir_sign * self.drift_bias

        end = end or datetime.now(timezone.utc)
        step = timedelta(minutes=timeframe.minutes)
        start = end - step * count

        candles: List[Candle] = []
        ts = start
        vol = self.volatility
        for i in range(count):
            # Occasional regime shifts to create swing structure.
            if rng.random() < 0.04:
                drift = -drift * rng.uniform(0.5, 1.2)
            o = price
            # Displacement burst roughly every ~25 candles.
            is_disp = rng.random() < 0.04
            mag = vol * (rng.uniform(3.5, 6.0) if is_disp else rng.uniform(0.3, 1.5))
            direction = 1 if (rng.random() < 0.5 + drift * 50) else -1
            if is_disp:
                direction = 1 if drift >= 0 else -1
            change = direction * mag * o
            c = max(0.01, o + change + drift * o)
            hi = max(o, c) + abs(rng.gauss(0, vol * o * 0.4))
            lo = min(o, c) - abs(rng.gauss(0, vol * o * 0.4))
            lo = max(0.01, lo)
            volume = rng.uniform(1000, 100000) * (3 if is_disp else 1)
            candles.append(
                Candle(
                    timestamp=ts,
                    open=round(o, 4),
                    high=round(hi, 4),
                    low=round(lo, 4),
                    close=round(c, 4),
                    volume=round(volume, 2),
                    timeframe=timeframe,
                    closed=True,
                )
            )
            price = c
            ts = ts + step
        return candles

    def status(self, symbol: Optional[str] = None) -> FeedStatus:
        return FeedStatus(
            provider=self.provider,
            mode=FeedMode.SYNTHETIC,
            last_update=datetime.now(timezone.utc),
            connected=True,
            coverage_pct=100.0,
            unavailable_symbols=[],
        )
