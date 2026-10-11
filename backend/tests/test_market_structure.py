from app.core.candles import Candle, Timeframe
from app.core.config import BreakType, StructureConfig, SwingConfig
from app.core.market_structure import (
    Bias,
    EventType,
    detect_structure,
    find_swings,
)
from tests.helpers import mk

SW = SwingConfig(left=1, right=1)
ST = StructureConfig()

# (i, h, l, o, c) -> reorder to (o,h,l,c)
ROWS = [
    (11.0, 10.0, 10.5, 10.5),
    (12.0, 10.5, 10.6, 11.9),
    (11.5, 9.5, 11.0, 9.8),
    (12.6, 10.0, 10.0, 12.5),
    (13.5, 12.0, 12.5, 13.4),
    (13.0, 11.0, 13.0, 11.2),
    (12.0, 11.3, 11.3, 11.9),
    (11.5, 10.5, 11.4, 10.6),
    (10.8, 9.0, 10.6, 9.2),
]


def _candles():
    out = []
    for i, (h, l, o, c) in enumerate(ROWS):
        out.append(mk(i, o, h, l, c))
    return out


def test_swings_detected_and_labeled():
    swings = find_swings(_candles(), SW)
    kinds = [(s.kind.value, round(s.price, 2)) for s in swings]
    assert ("high", 12.0) in kinds
    assert ("low", 9.5) in kinds
    # HH / HL labels appear once a prior same-kind swing exists.
    labels = [s.label.value for s in swings if s.label]
    assert "HH" in labels and "HL" in labels


def test_bullish_bos_then_bearish_choch():
    state = detect_structure(_candles(), SW, ST)
    types = [(e.type, e.direction) for e in state.events]
    assert (EventType.BOS, "bullish") in types
    assert (EventType.CHOCH, "bearish") in types
    # CHOCH must flip the bias from bullish to bearish.
    choch = [e for e in state.events if e.type == EventType.CHOCH][0]
    assert choch.prev_bias == Bias.BULLISH and choch.new_bias == Bias.BEARISH
    assert state.bias == Bias.BEARISH


def test_no_lookahead_pivot_confirmation():
    # A swing is only confirmed `right` bars after the pivot.
    swings = find_swings(_candles(), SW)
    for s in swings:
        assert s.confirmed_index == s.index + SW.right


def test_wick_vs_close_break_definition():
    # A candle that only wicks above the swing high does not break on CLOSE mode.
    rows = [
        (10.0, 10.5, 9.5, 10.2),
        (10.2, 12.0, 10.0, 11.8),   # pivot high 12.0
        (11.8, 11.9, 10.0, 10.5),
        (10.5, 12.5, 10.4, 11.0),   # wick to 12.5 but closes 11.0 (< 12.0)
    ]
    candles = [mk(i, *r) for i, r in enumerate(rows)]
    close_state = detect_structure(candles, SW, StructureConfig(break_type=BreakType.CLOSE))
    assert not any(e.direction == "bullish" for e in close_state.events)
    wick_state = detect_structure(candles, SW, StructureConfig(break_type=BreakType.WICK))
    assert any(e.direction == "bullish" for e in wick_state.events)


def test_insufficient_data_bias():
    state = detect_structure([mk(0, 10, 11, 9, 10)], SW, ST)
    assert state.bias == Bias.INSUFFICIENT
