from app.core.instruments import DEFAULT_SPECS, equity_spec
from app.core.sizing import size_position


def test_equity_position_sizing():
    spec = equity_spec("RELIANCE", "Reliance Industries")
    r = size_position(spec, equity=100_000, risk_fraction=0.005, entry=1000.0, stop=990.0)
    assert r.ok
    assert r.qty == 50            # 500 risk / (10 points * 1)
    assert abs(r.actual_risk - 500.0) < 1e-6


def test_forex_pip_sizing():
    spec = DEFAULT_SPECS["EURUSD"]
    r = size_position(spec, equity=10_000, risk_fraction=0.01, entry=1.1000, stop=1.0950)
    assert r.ok
    # 50 pips * $10/pip = $500 per lot; $100 budget -> 0.20 lots
    assert abs(r.qty - 0.20) < 1e-9
    assert abs(r.actual_risk - 100.0) < 1e-6


def test_gold_sizing_differs_from_pip_default():
    spec = DEFAULT_SPECS["XAUUSD"]
    r = size_position(spec, equity=10_000, risk_fraction=0.01, entry=2000.0, stop=1995.0)
    assert r.ok
    assert r.qty > 0


def test_zero_stop_distance_rejected():
    spec = equity_spec("TCS", "TCS")
    r = size_position(spec, 100_000, 0.005, 1000.0, 1000.0)
    assert not r.ok and r.reason == "zero_stop_distance"


def test_below_min_qty_rejected():
    spec = equity_spec("BIGCO", "Big", tick_size=0.05)
    # Huge price + tiny equity -> sub-1-share -> rejected.
    r = size_position(spec, equity=10.0, risk_fraction=0.005, entry=50_000.0, stop=49_000.0)
    assert not r.ok and r.reason == "below_min_qty"


def test_qty_rounding_down_to_step():
    spec = DEFAULT_SPECS["EURUSD"]
    r = size_position(spec, equity=10_000, risk_fraction=0.0133, entry=1.1000, stop=1.0950)
    # raw ~0.266 lots -> rounds down to 0.26
    assert r.qty <= 0.266 and r.qty >= 0.25
