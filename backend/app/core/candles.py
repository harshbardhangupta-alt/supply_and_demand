"""Core market-data domain types and helpers.

A :class:`Candle` is the normalized unit every engine module consumes. The
``closed`` flag is load-bearing: the strategy engine must never make a confirmed
decision from a candle that is still forming, otherwise live and backtest
behaviour diverge (look-ahead bias).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, List, Optional, Sequence


class Timeframe(str, Enum):
    """Supported timeframes, ordered from fastest to slowest."""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

    @property
    def minutes(self) -> int:
        return {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.D1: 60 * 24,
            Timeframe.W1: 60 * 24 * 7,
        }[self]

    @property
    def rank(self) -> int:
        order = [
            Timeframe.M1,
            Timeframe.M5,
            Timeframe.M15,
            Timeframe.H1,
            Timeframe.H4,
            Timeframe.D1,
            Timeframe.W1,
        ]
        return order.index(self)


@dataclass(frozen=True)
class Candle:
    """A single OHLCV bar.

    ``timestamp`` is the bar OPEN time in UTC. ``closed`` indicates whether the
    bar has fully formed; unconfirmed bars must be excluded from confirmed
    structural decisions.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    timeframe: Optional[Timeframe] = None
    closed: bool = True

    def __post_init__(self) -> None:
        # OHLC sanity — reject physically impossible candles early.
        if self.high < self.low:
            raise ValueError(f"candle high {self.high} < low {self.low}")
        if not (self.low <= self.open <= self.high):
            raise ValueError("open outside [low, high]")
        if not (self.low <= self.close <= self.high):
            raise ValueError("close outside [low, high]")

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body_top(self) -> float:
        return max(self.open, self.close)

    @property
    def body_bottom(self) -> float:
        return min(self.open, self.close)

    @property
    def upper_wick(self) -> float:
        return self.high - self.body_top

    @property
    def lower_wick(self) -> float:
        return self.body_bottom - self.low

    def close_strength(self) -> float:
        """Where the close sits within the candle range, 0..1.

        1.0 means the candle closed exactly at its high, 0.0 at its low.
        Returns 0.5 for a zero-range (doji/flat) candle.
        """
        if self.range <= 0:
            return 0.5
        return (self.close - self.low) / self.range


def ensure_closed(candles: Sequence[Candle]) -> List[Candle]:
    """Return only confirmed (closed) candles, preserving order."""
    return [c for c in candles if c.closed]


def true_range(prev_close: float, candle: Candle) -> float:
    return max(
        candle.high - candle.low,
        abs(candle.high - prev_close),
        abs(candle.low - prev_close),
    )


def atr(candles: Sequence[Candle], period: int = 14) -> Optional[float]:
    """Wilder-style Average True Range over the last ``period`` candles.

    Returns ``None`` when there is insufficient data. Uses only the data
    provided, so callers control look-ahead by slicing beforehand.
    """
    if len(candles) < period + 1:
        return None
    trs: List[float] = []
    for i in range(1, len(candles)):
        trs.append(true_range(candles[i - 1].close, candles[i]))
    if len(trs) < period:
        return None
    # Wilder smoothing.
    atr_val = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val


def atr_series(candles: Sequence[Candle], period: int = 14) -> List[Optional[float]]:
    """Rolling Wilder ATR aligned to each index (None until enough data).

    Computed once in O(n) so callers that need ATR at many points don't recompute
    it per bar (which would be O(n^2)).
    """
    n = len(candles)
    out: List[Optional[float]] = [None] * n
    if n < period + 1:
        return out
    trs = [0.0] * n
    for i in range(1, n):
        trs[i] = true_range(candles[i - 1].close, candles[i])
    atr_val = sum(trs[1 : period + 1]) / period
    out[period] = atr_val
    for i in range(period + 1, n):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        out[i] = atr_val
    return out


def validate_series(candles: Sequence[Candle]) -> List[str]:
    """Return a list of data-integrity problems (empty == clean)."""
    problems: List[str] = []
    seen = set()
    prev_ts: Optional[datetime] = None
    for c in candles:
        if c.timestamp in seen:
            problems.append(f"duplicate timestamp {c.timestamp.isoformat()}")
        seen.add(c.timestamp)
        if prev_ts is not None and c.timestamp <= prev_ts:
            problems.append(f"non-monotonic timestamp {c.timestamp.isoformat()}")
        prev_ts = c.timestamp
    return problems


def aggregate(
    candles: Sequence[Candle], target: Timeframe, source: Timeframe
) -> List[Candle]:
    """Aggregate lower-timeframe candles into a higher timeframe.

    Only aggregates when ``target`` is an exact multiple of ``source`` minutes.
    Partial groups at the tail are marked ``closed=False`` so the caller knows
    the bar is still forming. Never fabricates candles for missing data.
    """
    if target.minutes % source.minutes != 0:
        raise ValueError(
            f"cannot aggregate {source.value} -> {target.value}: not a multiple"
        )
    factor = target.minutes // source.minutes
    if factor == 1:
        return list(candles)

    out: List[Candle] = []
    bucket: List[Candle] = []
    for c in candles:
        bucket.append(c)
        if len(bucket) == factor:
            out.append(_merge_bucket(bucket, target, closed=True))
            bucket = []
    if bucket:
        out.append(_merge_bucket(bucket, target, closed=False))
    return out


def resample(candles: Sequence[Candle], target: Timeframe) -> List[Candle]:
    """Resample candles into ``target`` by calendar-aligned time buckets.

    Unlike :func:`aggregate` (fixed count), this groups by the natural time
    boundary of the target timeframe, so gaps (weekends, closed sessions) don't
    corrupt higher-timeframe bars. Used to derive 4H from 1H and weekly from
    daily when a provider doesn't serve those directly.
    """
    buckets: "dict[object, List[Candle]]" = {}
    order: List[object] = []
    for c in candles:
        key = _bucket_key(c.timestamp, target)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(c)
    out: List[Candle] = []
    for key in order:
        grp = buckets[key]
        out.append(
            Candle(
                timestamp=grp[0].timestamp,
                open=grp[0].open,
                high=max(c.high for c in grp),
                low=min(c.low for c in grp),
                close=grp[-1].close,
                volume=sum(c.volume for c in grp),
                timeframe=target,
                closed=all(c.closed for c in grp),
            )
        )
    return out


def _bucket_key(ts: datetime, tf: Timeframe):
    if tf == Timeframe.W1:
        iso = ts.isocalendar()
        return (iso[0], iso[1])
    if tf == Timeframe.D1:
        return (ts.year, ts.month, ts.day)
    # Intraday: floor epoch minutes to the timeframe width.
    epoch_min = int(ts.timestamp() // 60)
    return epoch_min - (epoch_min % tf.minutes)


def _merge_bucket(bucket: List[Candle], tf: Timeframe, closed: bool) -> Candle:
    return Candle(
        timestamp=bucket[0].timestamp,
        open=bucket[0].open,
        high=max(c.high for c in bucket),
        low=min(c.low for c in bucket),
        close=bucket[-1].close,
        volume=sum(c.volume for c in bucket),
        timeframe=tf,
        closed=closed and all(c.closed for c in bucket),
    )
