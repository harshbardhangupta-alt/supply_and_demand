from app.core.config import ZoneConfig, ZoneMode
from app.core.displacement import Displacement
from app.core.zones import ZoneDirection, ZoneState, build_zones
from tests.helpers import mk


def _demand_series():
    rows = [
        (11.0, 11.1, 9.9, 10.0),    # 0 bearish origin -> demand base
        (10.0, 12.0, 10.0, 11.9),   # 1 bullish displacement
        (11.9, 13.0, 11.8, 12.9),   # 2 bullish displacement
        (12.9, 13.0, 12.5, 12.6),   # 3 drift
        (12.6, 12.7, 10.5, 10.8),   # 4 wick into zone -> touch
        (10.8, 11.0, 9.0, 9.2),     # 5 closes below distal -> invalidation
    ]
    return [mk(i, *r) for i, r in enumerate(rows)]


def test_demand_zone_boundaries_wick_mode():
    candles = _demand_series()
    disp = Displacement(1, 2, "bullish", body=2.0, atr_at_start=0.5,
                        body_to_range=0.8, close_strength=0.9, strength=1.5)
    zones = build_zones(candles[:4], [disp], ZoneConfig(mode=ZoneMode.WICK))
    assert len(zones) == 1
    z = zones[0]
    assert z.direction == ZoneDirection.DEMAND
    assert abs(z.distal - 9.9) < 1e-9
    assert abs(z.proximal - 11.1) < 1e-9
    assert z.origin_index == 0


def test_zone_touch_then_invalidation():
    candles = _demand_series()
    disp = Displacement(1, 2, "bullish", 2.0, 0.5, 0.8, 0.9, 1.5)
    zones = build_zones(candles, [disp], ZoneConfig(mode=ZoneMode.WICK, max_touches=1))
    z = zones[0]
    assert z.touches >= 1
    assert z.state == ZoneState.INVALIDATED
    assert z.invalidation_reason == "distal_close_break"


def test_fresh_zone_is_tradable():
    candles = _demand_series()[:4]
    disp = Displacement(1, 2, "bullish", 2.0, 0.5, 0.8, 0.9, 1.5)
    z = build_zones(candles, [disp], ZoneConfig(mode=ZoneMode.WICK))[0]
    assert z.is_fresh
    assert z.is_tradable


def test_body_mode_boundaries():
    candles = _demand_series()[:4]
    disp = Displacement(1, 2, "bullish", 2.0, 0.5, 0.8, 0.9, 1.5)
    z = build_zones(candles, [disp], ZoneConfig(mode=ZoneMode.BODY))[0]
    # body of origin candle: open 11.0, close 10.0
    assert abs(z.distal - 10.0) < 1e-9
    assert abs(z.proximal - 11.0) < 1e-9
