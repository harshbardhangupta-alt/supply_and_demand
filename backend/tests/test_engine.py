from app.core.candles import Timeframe
from app.core.config import indian_equity_config, forex_config
from app.core.engine import analyze
from app.core.instruments import DEFAULT_SPECS, equity_spec
from app.core.risk import AccountState
from app.data.synthetic import SyntheticDataAdapter

ADAPTER = SyntheticDataAdapter()


def _account(**kw):
    base = dict(equity=1_000_000, start_of_day_equity=1_000_000,
               start_of_week_equity=1_000_000, free_margin=1_000_000)
    base.update(kw)
    return AccountState(**base)


def _data(symbol, cfg):
    tfs = [cfg.timeframes.bias, cfg.timeframes.structure, cfg.timeframes.zones,
           cfg.timeframes.intermediate, cfg.timeframes.setup, cfg.timeframes.execution]
    return {tf: ADAPTER.get_candles(symbol, tf, 300) for tf in set(tfs)}


def test_engine_produces_full_result():
    cfg = indian_equity_config()
    spec = equity_spec("RELIANCE", "Reliance")
    res = analyze(spec, _data("RELIANCE", cfg), cfg, _account())
    assert res.symbol == "RELIANCE"
    assert res.biases  # per-timeframe bias populated
    assert res.current_price is not None
    # Either tradable with full fields, or rejected with an explicit reason.
    if res.tradable:
        assert res.entry and res.stop and res.target and res.qty
        assert res.reward_risk >= cfg.risk.min_reward_risk - 1e-9
        assert res.score >= cfg.score.min_score
    else:
        assert res.rejection_reason


def test_buy_only_config_never_shorts():
    cfg = indian_equity_config()
    for sym in ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ITC", "WIPRO", "SBIN"]:
        res = analyze(equity_spec(sym, sym), _data(sym, cfg), cfg, _account())
        assert res.direction in (None, "long")


def test_stale_data_makes_untradable():
    cfg = indian_equity_config()
    spec = equity_spec("RELIANCE", "Reliance")
    acc = _account(data_fresh=False)
    res = analyze(spec, _data("RELIANCE", cfg), cfg, acc)
    # With stale data no setup may be approved.
    assert not res.tradable


def test_forex_config_two_sided_runs():
    cfg = forex_config()
    spec = DEFAULT_SPECS["EURUSD"]
    res = analyze(spec, _data("EURUSD", cfg), cfg, _account(equity=50_000,
                 start_of_day_equity=50_000, start_of_week_equity=50_000,
                 free_margin=50_000))
    assert res.symbol == "EURUSD"
    assert res.direction in (None, "long", "short")


def test_insufficient_data_rejected():
    cfg = indian_equity_config()
    spec = equity_spec("TINY", "Tiny")
    data = {tf: ADAPTER.get_candles("TINY", tf, 5) for tf in [
        cfg.timeframes.bias, cfg.timeframes.structure, cfg.timeframes.zones,
        cfg.timeframes.intermediate, cfg.timeframes.setup, cfg.timeframes.execution]}
    res = analyze(spec, data, cfg, _account())
    assert not res.tradable and res.rejection_reason == "insufficient_data"
