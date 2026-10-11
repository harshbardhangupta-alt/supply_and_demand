"""The three entry models: Normal, Conservative and Aggressive Limit.

All candle patterns are defined mathematically (no subjective visual rules) and
every entry requires confirmed/closed candles. Aggressive limit entries are
rejected when price approaches the zone with excessive adverse momentum.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .candles import Candle, atr
from .config import EntryConfig, EntryModel
from .zones import Zone, ZoneDirection


@dataclass
class EntrySignal:
    triggered: bool
    model: EntryModel
    order_type: str              # "market" | "limit"
    entry_price: float
    reason: str
    confirmation: bool = False


# --- candle patterns (mathematical definitions) ---------------------------

def is_bullish_engulfing(prev: Candle, cur: Candle) -> bool:
    return (
        prev.is_bearish
        and cur.is_bullish
        and cur.close >= prev.open
        and cur.open <= prev.close
        and cur.body > prev.body
    )


def is_bearish_engulfing(prev: Candle, cur: Candle) -> bool:
    return (
        prev.is_bullish
        and cur.is_bearish
        and cur.close <= prev.open
        and cur.open >= prev.close
        and cur.body > prev.body
    )


def is_bullish_pin(cur: Candle) -> bool:
    return cur.range > 0 and cur.lower_wick >= 2 * cur.body and cur.close_strength() > 0.6


def is_bearish_pin(cur: Candle) -> bool:
    return cur.range > 0 and cur.upper_wick >= 2 * cur.body and cur.close_strength() < 0.4


def _confirmation(prev: Candle, cur: Candle, direction: ZoneDirection, cfg: EntryConfig) -> bool:
    pats = cfg.confirmation_patterns
    if direction == ZoneDirection.DEMAND:
        if "engulfing" in pats and is_bullish_engulfing(prev, cur):
            return True
        if "pin" in pats and is_bullish_pin(cur):
            return True
    else:
        if "engulfing" in pats and is_bearish_engulfing(prev, cur):
            return True
        if "pin" in pats and is_bearish_pin(cur):
            return True
    return False


def aggressive_limit_price(zone: Zone, cfg: EntryConfig) -> float:
    """Limit price inside the zone: 0.0 = proximal, 1.0 = distal."""
    f = min(1.0, max(0.0, cfg.zone_entry_fraction))
    return zone.proximal + f * (zone.distal - zone.proximal)


def evaluate_entry(
    zone: Zone,
    candles: Sequence[Candle],
    cfg: EntryConfig,
) -> EntrySignal:
    """Evaluate the configured entry model on the latest closed candle."""
    closed = [c for c in candles if c.closed]
    if len(closed) < 2:
        return EntrySignal(False, cfg.model, "market", 0.0, "insufficient_candles")
    prev, cur = closed[-2], closed[-1]
    demand = zone.direction == ZoneDirection.DEMAND

    if cfg.model == EntryModel.NORMAL:
        return _normal(zone, prev, cur, cfg, demand)
    if cfg.model == EntryModel.CONSERVATIVE:
        return _conservative(zone, prev, cur, cfg, demand)
    return _aggressive(zone, closed, cfg, demand)


def _normal(zone, prev, cur, cfg, demand) -> EntrySignal:
    # Price must have entered the zone, then a closed candle closes back out past
    # the proximal boundary in the trade direction.
    entered = prev.low <= zone.top and prev.high >= zone.bottom
    entered = entered or (cur.low <= zone.top and cur.high >= zone.bottom)
    if not entered:
        return EntrySignal(False, EntryModel.NORMAL, "market", 0.0, "no_zone_interaction")
    if demand and cur.close > zone.proximal and cur.is_bullish:
        return EntrySignal(True, EntryModel.NORMAL, "market", cur.close,
                           "closed_back_above_proximal")
    if (not demand) and cur.close < zone.proximal and cur.is_bearish:
        return EntrySignal(True, EntryModel.NORMAL, "market", cur.close,
                           "closed_back_below_proximal")
    return EntrySignal(False, EntryModel.NORMAL, "market", 0.0, "no_reclaim")


def _conservative(zone, prev, cur, cfg, demand) -> EntrySignal:
    entered = (cur.low <= zone.top and cur.high >= zone.bottom) or (
        prev.low <= zone.top and prev.high >= zone.bottom
    )
    if not entered:
        return EntrySignal(False, EntryModel.CONSERVATIVE, "market", 0.0, "no_zone_interaction")
    direction = ZoneDirection.DEMAND if demand else ZoneDirection.SUPPLY
    if _confirmation(prev, cur, direction, cfg):
        return EntrySignal(True, EntryModel.CONSERVATIVE, "market", cur.close,
                           "confirmation_pattern", confirmation=True)
    return EntrySignal(False, EntryModel.CONSERVATIVE, "market", 0.0, "no_confirmation")


def _aggressive(zone, closed, cfg, demand) -> EntrySignal:
    price = aggressive_limit_price(zone, cfg)
    cur = closed[-1]
    a = atr(closed, 14) or 0.0
    # Adverse momentum: price slamming toward the zone fast is rejected.
    if a > 0:
        if demand and cur.is_bearish and cur.body >= cfg.adverse_momentum_atr * a:
            # only reject if price is still above the zone (approaching)
            if cur.close > zone.top:
                return EntrySignal(False, EntryModel.AGGRESSIVE, "limit", price,
                                   "adverse_momentum_into_zone")
        if (not demand) and cur.is_bullish and cur.body >= cfg.adverse_momentum_atr * a:
            if cur.close < zone.bottom:
                return EntrySignal(False, EntryModel.AGGRESSIVE, "limit", price,
                                   "adverse_momentum_into_zone")
    return EntrySignal(True, EntryModel.AGGRESSIVE, "limit", price,
                       "limit_at_zone_level")
