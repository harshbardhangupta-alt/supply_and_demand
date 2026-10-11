from app.core.config import EntryConfig, EntryModel, ZoneConfig, ZoneMode
from app.core.displacement import Displacement
from app.core.entries import (
    aggressive_limit_price,
    evaluate_entry,
    is_bearish_engulfing,
    is_bullish_engulfing,
)
from app.core.zones import Zone, ZoneDirection, ZoneState
from tests.helpers import mk


def _demand_zone():
    return Zone(
        direction=ZoneDirection.DEMAND, origin_index=0, created_index=0,
        timestamp=None, distal=9.9, proximal=11.1, displacement_strength=1.5,
        state=ZoneState.ACTIVE,
    )


def test_bullish_engulfing_math():
    prev = mk(0, 11.0, 11.1, 10.0, 10.2)   # bearish
    cur = mk(1, 10.1, 11.5, 10.0, 11.4)    # bullish engulfs
    assert is_bullish_engulfing(prev, cur)
    assert not is_bearish_engulfing(prev, cur)


def test_normal_entry_triggers_on_reclaim():
    zone = _demand_zone()
    prev = mk(0, 11.0, 11.2, 10.4, 10.5)   # inside zone
    cur = mk(1, 10.6, 11.6, 10.5, 11.5)    # closes back above proximal 11.1
    sig = evaluate_entry(zone, [prev, cur], EntryConfig(model=EntryModel.NORMAL))
    assert sig.triggered and sig.order_type == "market"


def test_conservative_requires_confirmation():
    zone = _demand_zone()
    prev = mk(0, 11.0, 11.1, 10.0, 10.2)   # bearish inside
    cur = mk(1, 10.1, 11.5, 10.0, 11.4)    # bullish engulfing inside
    sig = evaluate_entry(zone, [prev, cur], EntryConfig(model=EntryModel.CONSERVATIVE))
    assert sig.triggered and sig.confirmation


def test_aggressive_limit_price_midpoint():
    zone = _demand_zone()
    cfg = EntryConfig(model=EntryModel.AGGRESSIVE, zone_entry_fraction=0.5)
    price = aggressive_limit_price(zone, cfg)
    assert abs(price - 10.5) < 1e-9   # midpoint of 11.1 and 9.9


def test_aggressive_rejects_adverse_momentum():
    zone = _demand_zone()
    # strong bearish candle slamming toward the zone from above
    candles = [mk(i, 20 - i, 20 - i + 0.1, 20 - i - 0.1, 20 - i) for i in range(16)]
    candles.append(mk(16, 14.0, 14.0, 11.5, 11.6))  # big down body above zone
    cfg = EntryConfig(model=EntryModel.AGGRESSIVE, adverse_momentum_atr=0.5)
    sig = evaluate_entry(zone, candles, cfg)
    assert not sig.triggered and sig.reason == "adverse_momentum_into_zone"
