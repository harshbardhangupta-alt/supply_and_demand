"""Multi-timeframe analysis helpers.

Computes directional bias per timeframe from confirmed structure and decides
higher-timeframe alignment for a candidate trade direction. Only closed candles
are used so higher-timeframe decisions never leak future information.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from .candles import Candle, Timeframe, ensure_closed
from .config import StructureConfig, SwingConfig
from .market_structure import Bias, classify_trend, detect_structure


@dataclass
class TimeframeBias:
    timeframe: Timeframe
    bias: Bias


def timeframe_bias(
    candles: Sequence[Candle], swing: SwingConfig, struct: StructureConfig
) -> Bias:
    closed = ensure_closed(candles)
    if len(closed) < (swing.left + swing.right + 2):
        return Bias.INSUFFICIENT
    state = detect_structure(closed, swing, struct)
    return classify_trend(state)


def alignment_for(direction: str, biases: Dict[Timeframe, Bias]) -> tuple[bool, bool]:
    """Return (fully_aligned, partially_aligned) for a trade ``direction``.

    "long"  -> bullish / transitional biases support the trade.
    "short" -> bearish / transitional biases support the trade.
    """
    def supportive(b: Bias) -> Optional[bool]:
        if b in (Bias.INSUFFICIENT, Bias.NEUTRAL):
            return None
        if direction == "long":
            return b in (Bias.BULLISH, Bias.TRANSITIONAL)
        return b in (Bias.BEARISH, Bias.TRANSITIONAL)

    votes = [supportive(b) for b in biases.values()]
    votes = [v for v in votes if v is not None]
    if not votes:
        return False, False
    full = all(votes)
    partial = any(votes)
    return full, partial
