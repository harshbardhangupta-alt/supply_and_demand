"""Shared test helpers for constructing candle fixtures."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.core.candles import Candle, Timeframe

T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)


def mk(i: int, o: float, h: float, l: float, c: float, tf: Timeframe = Timeframe.H1,
       vol: float = 1000.0, closed: bool = True) -> Candle:
    return Candle(
        timestamp=T0 + timedelta(hours=i),
        open=o, high=h, low=l, close=c, volume=vol, timeframe=tf, closed=closed,
    )


def series(rows: List[tuple], tf: Timeframe = Timeframe.H1) -> List[Candle]:
    """rows are (o, h, l, c) tuples."""
    return [mk(i, *r, tf=tf) for i, r in enumerate(rows)]
