"""Fair Value Gap (FVG) detection using the standard three-candle model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .candles import Candle, atr
from .config import FVGConfig


@dataclass
class FVG:
    index: int               # index of the middle (displacement) candle
    timestamp: object
    direction: str           # "bullish" | "bearish"
    upper: float
    lower: float
    filled_pct: float = 0.0
    partially_filled: bool = False
    fully_filled: bool = False

    @property
    def midpoint(self) -> float:
        return (self.upper + self.lower) / 2

    @property
    def size(self) -> float:
        return self.upper - self.lower


def detect_fvgs(candles: Sequence[Candle], cfg: FVGConfig, tick_size: float = 0.0) -> List[FVG]:
    """Detect three-candle FVGs and compute their current fill state."""
    out: List[FVG] = []
    n = len(candles)
    if n < 3:
        return out
    a = atr(candles, 14) or 0.0
    min_gap = max(cfg.min_gap_ticks * tick_size, a * cfg.min_gap_atr_frac)

    for i in range(1, n - 1):
        c1, c2, c3 = candles[i - 1], candles[i], candles[i + 1]
        if not c2.closed:
            continue
        # Bullish FVG: gap between candle1.high and candle3.low.
        if c3.low > c1.high:
            gap = c3.low - c1.high
            if gap >= min_gap:
                fvg = FVG(i, c2.timestamp, "bullish", upper=c3.low, lower=c1.high)
                _update_fill(fvg, candles, i + 2)
                out.append(fvg)
        # Bearish FVG: gap between candle3.high and candle1.low.
        elif c1.low > c3.high:
            gap = c1.low - c3.high
            if gap >= min_gap:
                fvg = FVG(i, c2.timestamp, "bearish", upper=c1.low, lower=c3.high)
                _update_fill(fvg, candles, i + 2)
                out.append(fvg)
    return out


def _update_fill(fvg: FVG, candles: Sequence[Candle], start: int) -> None:
    """Track how much of the gap has since been retraced into."""
    size = fvg.size
    if size <= 0:
        fvg.fully_filled = True
        fvg.filled_pct = 1.0
        return
    deepest = 0.0
    for k in range(start, len(candles)):
        c = candles[k]
        if not c.closed:
            continue
        if fvg.direction == "bullish":
            # price trading down into the gap from the top
            penetration = fvg.upper - max(c.low, fvg.lower)
        else:
            penetration = min(c.high, fvg.upper) - fvg.lower
        deepest = max(deepest, min(penetration, size))
    fvg.filled_pct = round(deepest / size, 4)
    fvg.partially_filled = 0 < fvg.filled_pct < 1
    fvg.fully_filled = fvg.filled_pct >= 0.999
