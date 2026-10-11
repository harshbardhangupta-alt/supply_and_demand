from app.core.config import DisplacementConfig
from app.core.displacement import detect_displacements
from tests.helpers import mk


def _base_then_displacement():
    rows = []
    price = 100.0
    # 16 small oscillating candles to establish ATR.
    for i in range(16):
        up = i % 2 == 0
        o = price
        c = price + (0.1 if up else -0.1)
        h = max(o, c) + 0.05
        l = min(o, c) - 0.05
        rows.append((o, h, l, c))
        price = c
    # one large bullish displacement candle.
    o = price
    c = price + 3.0
    rows.append((o, c + 0.05, o - 0.05, c))
    return [mk(i, *r) for i, r in enumerate(rows)]


def test_displacement_detected():
    candles = _base_then_displacement()
    disps = detect_displacements(candles, DisplacementConfig(min_sequence=1))
    assert disps, "expected at least one displacement"
    last = disps[-1]
    assert last.direction == "bullish"
    assert last.strength > 1.0


def test_small_candles_not_displacement():
    rows = [(100 + i * 0.01, 100 + i * 0.01 + 0.02, 100 + i * 0.01 - 0.02,
             100 + i * 0.01 + 0.01) for i in range(20)]
    candles = [mk(i, *r) for i, r in enumerate(rows)]
    disps = detect_displacements(candles, DisplacementConfig())
    assert disps == []
