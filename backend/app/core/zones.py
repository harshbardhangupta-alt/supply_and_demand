"""Supply & Demand zone engine with a persistent lifecycle state machine.

Lifecycle: DETECTED -> VALIDATED -> ACTIVE -> TOUCHED -> MITIGATED / INVALIDATED
/ EXPIRED. A zone is created from the *origin candle* (the last opposite-colour
candle before a qualifying displacement) and is only known once the displacement
that produced it has closed, preserving look-ahead safety.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from .candles import Candle
from .config import BreakType, ZoneConfig, ZoneMode
from .displacement import Displacement


class ZoneDirection(str, Enum):
    DEMAND = "demand"
    SUPPLY = "supply"


class ZoneState(str, Enum):
    DETECTED = "DETECTED"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    TOUCHED = "TOUCHED"
    MITIGATED = "MITIGATED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


@dataclass
class Zone:
    direction: ZoneDirection
    origin_index: int
    created_index: int        # bar at which the zone becomes known
    timestamp: object
    distal: float             # the "far" boundary (stop sits beyond this)
    proximal: float           # the "near" boundary (price reaches this first)
    displacement_strength: float
    has_fvg: bool = False
    has_bos: bool = False
    state: ZoneState = ZoneState.DETECTED
    touches: int = 0
    first_touch_index: Optional[int] = None
    mitigation_index: Optional[int] = None
    invalidation_index: Optional[int] = None
    invalidation_reason: Optional[str] = None
    expiry_index: Optional[int] = None
    score: float = 0.0

    @property
    def top(self) -> float:
        return max(self.distal, self.proximal)

    @property
    def bottom(self) -> float:
        return min(self.distal, self.proximal)

    @property
    def height(self) -> float:
        return self.top - self.bottom

    @property
    def midpoint(self) -> float:
        return (self.distal + self.proximal) / 2

    def contains(self, price: float) -> bool:
        return self.bottom <= price <= self.top

    @property
    def is_fresh(self) -> bool:
        return self.touches == 0

    @property
    def is_tradable(self) -> bool:
        return self.state in (ZoneState.VALIDATED, ZoneState.ACTIVE, ZoneState.TOUCHED)


def _boundaries(origin: Candle, direction: ZoneDirection, mode: ZoneMode):
    if direction == ZoneDirection.DEMAND:
        wick_distal, wick_proximal = origin.low, origin.high
        body_distal, body_proximal = origin.body_bottom, origin.body_top
    else:
        wick_distal, wick_proximal = origin.high, origin.low
        body_distal, body_proximal = origin.body_top, origin.body_bottom

    if mode == ZoneMode.WICK:
        return wick_distal, wick_proximal
    if mode == ZoneMode.BODY:
        return body_distal, body_proximal
    # HYBRID: distal from wick (wider stop protection), proximal from body.
    return wick_distal, body_proximal


def build_zones(
    candles: Sequence[Candle],
    displacements: Sequence[Displacement],
    cfg: ZoneConfig,
    fvg_indices: Optional[set] = None,
) -> List[Zone]:
    """Create zones from displacements, then run each through its lifecycle."""
    fvg_indices = fvg_indices or set()
    zones: List[Zone] = []
    for disp in displacements:
        origin_idx = _find_origin(candles, disp)
        if origin_idx is None:
            continue
        origin = candles[origin_idx]
        direction = (
            ZoneDirection.DEMAND if disp.direction == "bullish" else ZoneDirection.SUPPLY
        )
        distal, proximal = _boundaries(origin, direction, cfg.mode)
        if distal == proximal:
            continue
        has_fvg = any(idx in fvg_indices for idx in range(disp.start_index, disp.end_index + 1))
        zone = Zone(
            direction=direction,
            origin_index=origin_idx,
            created_index=disp.end_index,
            timestamp=origin.timestamp,
            distal=distal,
            proximal=proximal,
            displacement_strength=disp.strength,
            has_fvg=has_fvg,
            has_bos=True,  # displacement with structural break; refined by engine
        )
        _validate(zone, cfg)
        _run_lifecycle(zone, candles, cfg)
        zones.append(zone)
    return zones


def _find_origin(candles: Sequence[Candle], disp: Displacement) -> Optional[int]:
    """Last opposite-colour candle immediately before the displacement."""
    want_bearish_origin = disp.direction == "bullish"
    i = disp.start_index - 1
    while i >= 0:
        c = candles[i]
        if want_bearish_origin and c.is_bearish:
            return i
        if (not want_bearish_origin) and c.is_bullish:
            return i
        # Allow skipping neutral/doji candles directly adjacent.
        if c.body == 0:
            i -= 1
            continue
        # First opposite-direction run end: stop if we hit a same-direction candle
        # that is not the base.
        i -= 1
    return None


def _validate(zone: Zone, cfg: ZoneConfig) -> None:
    if cfg.require_fvg and not zone.has_fvg:
        zone.state = ZoneState.DETECTED
        zone.invalidation_reason = "missing_required_fvg"
        return
    if cfg.require_bos and not zone.has_bos:
        zone.state = ZoneState.DETECTED
        zone.invalidation_reason = "missing_required_bos"
        return
    zone.state = ZoneState.VALIDATED


def _run_lifecycle(zone: Zone, candles: Sequence[Candle], cfg: ZoneConfig) -> None:
    if zone.state != ZoneState.VALIDATED:
        return
    zone.state = ZoneState.ACTIVE
    inside = False
    for i in range(zone.created_index + 1, len(candles)):
        c = candles[i]
        if not c.closed:
            continue

        # Invalidation: a closed candle closes beyond the distal boundary.
        if zone.direction == ZoneDirection.DEMAND:
            broke = (
                c.close < zone.bottom
                if cfg.invalidation_break == BreakType.CLOSE
                else c.low < zone.bottom
            )
        else:
            broke = (
                c.close > zone.top
                if cfg.invalidation_break == BreakType.CLOSE
                else c.high > zone.top
            )
        if broke:
            zone.state = ZoneState.INVALIDATED
            zone.invalidation_index = i
            zone.invalidation_reason = "distal_close_break"
            return

        # Touch tracking: count discrete visits, not repeated bars inside.
        overlaps = c.low <= zone.top and c.high >= zone.bottom
        if overlaps and not inside:
            zone.touches += 1
            inside = True
            if zone.first_touch_index is None:
                zone.first_touch_index = i
            if zone.state == ZoneState.ACTIVE:
                zone.state = ZoneState.TOUCHED
            if zone.touches > cfg.max_touches:
                zone.state = ZoneState.MITIGATED
                zone.mitigation_index = i
                return
        elif not overlaps:
            inside = False

        # Expiry: untouched for too long.
        if zone.touches == 0 and (i - zone.created_index) >= cfg.expiry_bars:
            zone.state = ZoneState.EXPIRED
            zone.expiry_index = i
            return


def active_zones(
    zones: Sequence[Zone], direction: Optional[ZoneDirection] = None
) -> List[Zone]:
    out = [z for z in zones if z.is_tradable]
    if direction is not None:
        out = [z for z in out if z.direction == direction]
    return out
