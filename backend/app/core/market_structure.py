"""Market-structure detection: swings, HH/HL/LH/LL, BOS, CHOCH, MSS, trend.

Look-ahead safety is the central invariant of this module. A pivot that needs
``right`` future candles to confirm is not *known* until those candles have
closed; the structural scan therefore only consults a swing from the bar index
at which it becomes confirmable. This is what makes the live engine and the
backtester produce identical structure on identical data.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

from .candles import Candle, atr
from .config import BreakType, StructureConfig, SwingConfig


class SwingKind(str, Enum):
    HIGH = "high"
    LOW = "low"


class SwingLabel(str, Enum):
    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"


class Bias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    TRANSITIONAL = "transitional"
    INSUFFICIENT = "insufficient"


class EventType(str, Enum):
    BOS = "BOS"
    CHOCH = "CHOCH"
    MSS = "MSS"


@dataclass
class Swing:
    index: int               # bar index of the pivot itself
    timestamp: object
    price: float
    kind: SwingKind
    confirmed_index: int     # first bar index at which the pivot is known
    label: Optional[SwingLabel] = None
    broken: bool = False


@dataclass
class StructureEvent:
    type: EventType
    direction: str           # "bullish" | "bearish"
    index: int               # bar index that produced the break
    timestamp: object
    level: float             # the structural level that was broken
    prev_bias: Bias
    new_bias: Bias
    confirmed: bool = True


def find_swings(candles: Sequence[Candle], cfg: SwingConfig) -> List[Swing]:
    """Detect confirmed fractal swing highs/lows and label HH/HL/LH/LL.

    A swing high at ``i`` requires ``high[i]`` to be strictly greater than the
    ``left`` candles before and the ``right`` candles after it. The swing is
    marked confirmed at index ``i + right``.
    """
    n = len(candles)
    swings: List[Swing] = []
    if n < cfg.left + cfg.right + 1:
        return swings

    # Optional ATR-based prominence filter.
    min_prom = 0.0
    if cfg.min_swing_atr_frac > 0:
        a = atr(candles, cfg.atr_period)
        if a:
            min_prom = a * cfg.min_swing_atr_frac

    for i in range(cfg.left, n - cfg.right):
        hi = candles[i].high
        lo = candles[i].low
        left = candles[i - cfg.left : i]
        right = candles[i + 1 : i + 1 + cfg.right]

        is_high = all(hi > c.high for c in left) and all(hi > c.high for c in right)
        is_low = all(lo < c.low for c in left) and all(lo < c.low for c in right)

        if is_high and min_prom > 0:
            nearby_low = min(c.low for c in left + right)
            if hi - nearby_low < min_prom:
                is_high = False
        if is_low and min_prom > 0:
            nearby_high = max(c.high for c in left + right)
            if nearby_high - lo < min_prom:
                is_low = False

        if is_high:
            swings.append(
                Swing(i, candles[i].timestamp, hi, SwingKind.HIGH, i + cfg.right)
            )
        elif is_low:
            swings.append(
                Swing(i, candles[i].timestamp, lo, SwingKind.LOW, i + cfg.right)
            )

    _label_swings(swings)
    return swings


def _label_swings(swings: List[Swing]) -> None:
    last_high: Optional[float] = None
    last_low: Optional[float] = None
    for s in swings:
        if s.kind == SwingKind.HIGH:
            if last_high is not None:
                s.label = SwingLabel.HH if s.price > last_high else SwingLabel.LH
            last_high = s.price
        else:
            if last_low is not None:
                s.label = SwingLabel.HL if s.price > last_low else SwingLabel.LL
            last_low = s.price


def _broke_above(candle: Candle, level: float, bt: BreakType) -> bool:
    return candle.close > level if bt == BreakType.CLOSE else candle.high > level


def _broke_below(candle: Candle, level: float, bt: BreakType) -> bool:
    return candle.close < level if bt == BreakType.CLOSE else candle.low < level


@dataclass
class StructureState:
    bias: Bias
    events: List[StructureEvent]
    swings: List[Swing]
    active_high: Optional[Swing]
    active_low: Optional[Swing]


def detect_structure(
    candles: Sequence[Candle],
    swing_cfg: SwingConfig,
    struct_cfg: StructureConfig,
) -> StructureState:
    """Walk the series bar-by-bar emitting BOS / CHOCH / MSS events.

    Only swings confirmed on or before the current bar are consulted, so no
    event depends on future information.
    """
    swings = find_swings(candles, swing_cfg)
    events: List[StructureEvent] = []
    bias = Bias.INSUFFICIENT if not swings else Bias.NEUTRAL
    bt = struct_cfg.break_type

    # Index swings by the bar at which they become confirmed.
    by_confirm: dict[int, List[Swing]] = {}
    for s in swings:
        by_confirm.setdefault(s.confirmed_index, []).append(s)

    active_high: Optional[Swing] = None
    active_low: Optional[Swing] = None

    a = atr(candles, swing_cfg.atr_period) or 0.0
    min_break = a * struct_cfg.min_break_atr_frac

    for i, candle in enumerate(candles):
        if not candle.closed:
            continue
        # Register swings that became confirmable at this bar.
        for s in by_confirm.get(i, []):
            # Arm as a reference only if the level is a valid barrier w.r.t.
            # the current close (resistance above / support below), so a swing
            # that formed inside already-traversed price does not fire instantly.
            if s.kind == SwingKind.HIGH and s.price >= candle.close:
                active_high = s
            elif s.kind == SwingKind.LOW and s.price <= candle.close:
                active_low = s

        # Check for an upward break of the active swing high.
        if active_high is not None and _broke_above(candle, active_high.price, bt):
            if min_break == 0 or (candle.close - active_high.price) >= -min_break:
                prev = bias
                if prev == Bias.BEARISH:
                    etype = EventType.CHOCH
                    new_bias = Bias.BULLISH
                else:
                    etype = EventType.BOS
                    new_bias = Bias.BULLISH
                events.append(
                    StructureEvent(
                        etype, "bullish", i, candle.timestamp,
                        active_high.price, prev, new_bias,
                    )
                )
                active_high.broken = True
                bias = new_bias
                active_high = None

        # Check for a downward break of the active swing low.
        if active_low is not None and _broke_below(candle, active_low.price, bt):
            if min_break == 0 or (active_low.price - candle.close) >= -min_break:
                prev = bias
                if prev == Bias.BULLISH:
                    etype = EventType.CHOCH
                    new_bias = Bias.BEARISH
                else:
                    etype = EventType.BOS
                    new_bias = Bias.BEARISH
                events.append(
                    StructureEvent(
                        etype, "bearish", i, candle.timestamp,
                        active_low.price, prev, new_bias,
                    )
                )
                active_low.broken = True
                bias = new_bias
                active_low = None

    return StructureState(bias, events, swings, active_high, active_low)


def classify_trend(state: StructureState) -> Bias:
    """Classify the overall trend from the latest structural events."""
    if state.bias == Bias.INSUFFICIENT:
        return Bias.INSUFFICIENT
    if not state.events:
        return Bias.NEUTRAL
    last = state.events[-1]
    # A fresh CHOCH is a transition, not yet an established trend.
    if last.type == EventType.CHOCH:
        return Bias.TRANSITIONAL
    return last.new_bias
