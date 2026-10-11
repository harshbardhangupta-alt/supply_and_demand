from app.core.config import FVGConfig
from app.core.fvg import detect_fvgs
from tests.helpers import mk


def test_bullish_fvg_detected():
    rows = [
        (10.0, 10.5, 9.5, 10.4),
        (10.4, 12.0, 10.3, 11.9),
        (11.9, 12.5, 11.0, 12.3),
    ]
    candles = [mk(i, *r) for i, r in enumerate(rows)]
    fvgs = detect_fvgs(candles, FVGConfig(), tick_size=0.05)
    assert len(fvgs) == 1
    f = fvgs[0]
    assert f.direction == "bullish"
    assert abs(f.lower - 10.5) < 1e-9 and abs(f.upper - 11.0) < 1e-9


def test_bearish_fvg_detected():
    rows = [
        (12.0, 12.5, 11.8, 12.0),
        (12.0, 12.1, 10.0, 10.2),
        (10.2, 11.0, 9.5, 9.8),
    ]
    candles = [mk(i, *r) for i, r in enumerate(rows)]
    fvgs = detect_fvgs(candles, FVGConfig(), tick_size=0.05)
    assert len(fvgs) == 1
    assert fvgs[0].direction == "bearish"
    assert abs(fvgs[0].upper - 11.8) < 1e-9 and abs(fvgs[0].lower - 11.0) < 1e-9


def test_no_fvg_when_no_gap():
    rows = [
        (10.0, 11.0, 9.5, 10.5),
        (10.5, 11.2, 10.0, 11.0),
        (11.0, 11.5, 10.2, 11.3),
    ]
    candles = [mk(i, *r) for i, r in enumerate(rows)]
    assert detect_fvgs(candles, FVGConfig(), tick_size=0.05) == []


def test_fvg_fill_tracking():
    rows = [
        (10.0, 10.5, 9.5, 10.4),
        (10.4, 12.0, 10.3, 11.9),
        (11.9, 12.5, 11.0, 12.3),
        (12.3, 12.4, 10.6, 10.7),   # trades back down into the gap (10.5-11.0)
    ]
    candles = [mk(i, *r) for i, r in enumerate(rows)]
    f = detect_fvgs(candles, FVGConfig(), tick_size=0.05)[0]
    assert f.partially_filled and not f.fully_filled
