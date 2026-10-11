"""Displacement (aggressive directional expansion) detection.

Displacement is treated strictly as a *price-action* signal of forceful one-way
movement — not as proof that any particular institution placed an order. It is
scored statistically against ATR and candle geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .candles import Candle, atr_series
from .config import DisplacementConfig


@dataclass
class Displacement:
    start_index: int
    end_index: int
    direction: str          # "bullish" | "bearish"
    body: float
    atr_at_start: float
    body_to_range: float
    close_strength: float
    strength: float         # normalized 0..1+ score used by setup scoring


def detect_displacements(
    candles: Sequence[Candle], cfg: DisplacementConfig
) -> List[Displacement]:
    """Return every qualifying displacement run in the series."""
    out: List[Displacement] = []
    n = len(candles)
    if n < cfg.atr_period + 2:
        return out

    atrs = atr_series(candles, cfg.atr_period)  # precomputed once, O(n)
    i = cfg.atr_period
    while i < n:
        c = candles[i]
        if not c.closed:
            i += 1
            continue
        a = atrs[i]
        if not a or a <= 0:
            i += 1
            continue
        disp = _qualify(candles, i, a, cfg)
        if disp is not None:
            out.append(disp)
            i = disp.end_index + 1
        else:
            i += 1
    return out


def _qualify(
    candles: Sequence[Candle], i: int, a: float, cfg: DisplacementConfig
) -> Optional[Displacement]:
    c = candles[i]
    direction = "bullish" if c.is_bullish else "bearish"

    def is_strong(cd: Candle) -> bool:
        if cd.range <= 0:
            return False
        body_to_range = cd.body / cd.range
        if cd.body < cfg.body_atr_mult * a:
            return False
        if body_to_range < cfg.min_body_to_range:
            return False
        cs = cd.close_strength()
        if direction == "bullish" and cs < cfg.min_close_strength:
            return False
        if direction == "bearish" and (1 - cs) < cfg.min_close_strength:
            return False
        if direction == "bullish" and not cd.is_bullish:
            return False
        if direction == "bearish" and not cd.is_bearish:
            return False
        return True

    if not is_strong(c):
        return None

    # Extend the run over consecutive same-direction strong candles.
    end = i
    j = i + 1
    while j < len(candles) and candles[j].closed:
        nxt = candles[j]
        same_dir = (nxt.is_bullish and direction == "bullish") or (
            nxt.is_bearish and direction == "bearish"
        )
        if same_dir and is_strong(nxt):
            end = j
            j += 1
        else:
            break

    run = candles[i : end + 1]
    if (end - i + 1) < cfg.min_sequence:
        return None

    total_body = sum(x.body for x in run)
    total_range = sum(x.range for x in run) or 1e-9
    btr = total_body / total_range
    cs = run[-1].close_strength()
    strength = min(2.0, total_body / (cfg.body_atr_mult * a))
    return Displacement(
        start_index=i,
        end_index=end,
        direction=direction,
        body=total_body,
        atr_at_start=a,
        body_to_range=btr,
        close_strength=cs if direction == "bullish" else 1 - cs,
        strength=strength,
    )
