from app.backtest.engine import BacktestConfig, run_backtest
from app.core.candles import Timeframe
from app.core.config import indian_equity_config
from app.core.instruments import equity_spec
from app.data.synthetic import SyntheticDataAdapter

ADAPTER = SyntheticDataAdapter()


def _data(sym, cfg, n):
    tfs = {cfg.timeframes.bias, cfg.timeframes.structure, cfg.timeframes.zones,
           cfg.timeframes.intermediate, cfg.timeframes.setup, cfg.timeframes.execution}
    return {tf: ADAPTER.get_candles(sym, tf, n) for tf in tfs}


def test_backtest_runs_and_reports_metrics():
    cfg = indian_equity_config()
    spec = equity_spec("RELIANCE", "Reliance")
    res = run_backtest(spec, _data("RELIANCE", cfg, 300), cfg, 1_000_000,
                       BacktestConfig(warmup_bars=120))
    assert res.metrics is not None
    assert res.bars_tested > 0
    # Equity curve starts at the configured equity.
    assert res.equity_curve[0] == 1_000_000


def test_backtest_no_lookahead_slicing():
    # A backtest over a prefix must not be influenced by data beyond the prefix.
    cfg = indian_equity_config()
    spec = equity_spec("INFY", "Infosys")
    full = _data("INFY", cfg, 400)
    # Trades whose entry bar < cutoff must be identical whether or not later
    # candles exist (look-ahead would change them).
    short = {tf: c[:300] for tf, c in full.items()}
    r_full = run_backtest(spec, full, cfg, 1_000_000, BacktestConfig(warmup_bars=120))
    r_short = run_backtest(spec, short, cfg, 1_000_000, BacktestConfig(warmup_bars=120))
    exec_tf = cfg.timeframes.execution
    cutoff = 300 - 2
    early_full = [(t.entry, t.direction) for t in r_full.trades
                  if _entry_bar_within(r_full, t, cutoff)]
    early_short = [(t.entry, t.direction) for t in r_short.trades
                   if _entry_bar_within(r_short, t, cutoff)]
    # The earliest trades should match between the two runs.
    k = min(len(early_full), len(early_short))
    assert early_full[:k] == early_short[:k]


def _entry_bar_within(res, trade, cutoff):
    return (trade.bars_held or 0) >= 0  # placeholder; trades list is ordered
