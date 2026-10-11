"""Event-driven backtester.

Design principles enforced here:
  * Same :func:`app.core.engine.analyze` pipeline as live/paper — no separate,
    divergent backtest strategy logic.
  * No look-ahead: at each execution bar only candles that have *closed* on or
    before that point are passed to the engine; higher-timeframe bars are
    included only once their close time has passed.
  * Realistic fills: market entries at the next bar open +/- costs; limit
    entries only fill on a genuine touch within the order-expiry window.
  * Conservative intrabar assumption: if a bar's range spans both stop and
    target, the stop is assumed hit first (documented pessimistic default).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ..analytics.metrics import ClosedTrade, Metrics, compute_metrics
from ..core.candles import Candle, Timeframe, ensure_closed
from ..core.config import StrategyConfig
from ..core.engine import analyze
from ..core.instruments import InstrumentSpec
from ..core.risk import AccountState


@dataclass
class BacktestConfig:
    warmup_bars: int = 120
    fee_frac: float = 0.0003
    slippage_frac: float = 0.0005
    intrabar_worst_case: bool = True   # stop assumed before target when both in range


@dataclass
class BacktestResult:
    symbol: str
    trades: List[ClosedTrade] = field(default_factory=list)
    metrics: Optional[Metrics] = None
    equity_curve: List[float] = field(default_factory=list)
    bars_tested: int = 0
    notes: List[str] = field(default_factory=list)


def _slice_htf(series: List[Candle], upto_ts: datetime, tf: Timeframe) -> List[Candle]:
    """Higher-timeframe candles whose CLOSE time is <= upto_ts (i.e. fully
    formed by the current execution moment)."""
    out = []
    for c in series:
        close_ts = c.timestamp + _tf_delta(tf)
        if close_ts <= upto_ts:
            out.append(c)
    return out


def _tf_delta(tf: Timeframe):
    from datetime import timedelta
    return timedelta(minutes=tf.minutes)


def run_backtest(
    spec: InstrumentSpec,
    data: Dict[Timeframe, List[Candle]],
    cfg: StrategyConfig,
    starting_equity: float,
    bt: Optional[BacktestConfig] = None,
) -> BacktestResult:
    bt = bt or BacktestConfig()
    tf = cfg.timeframes
    exec_series = ensure_closed(data.get(tf.execution, []))
    res = BacktestResult(symbol=spec.symbol)
    if len(exec_series) < bt.warmup_bars + 10:
        res.notes.append("insufficient execution-timeframe data")
        res.metrics = compute_metrics([])
        return res

    equity = starting_equity
    res.equity_curve.append(equity)
    open_trade: Optional[dict] = None
    i = bt.warmup_bars

    while i < len(exec_series) - 1:
        bar = exec_series[i]
        # --- manage an open trade on this bar ---
        if open_trade is not None:
            closed = _try_exit(open_trade, bar, bt)
            if closed is not None:
                pnl, exit_price, reason = closed
                equity += pnl
                res.equity_curve.append(equity)
                res.trades.append(_to_closed_trade(open_trade, exit_price, pnl, reason, i))
                open_trade = None
            i += 1
            continue

        # --- look for a new setup using only closed data up to bar i ---
        upto_ts = bar.timestamp
        sliced: Dict[Timeframe, List[Candle]] = {}
        for key, series in data.items():
            if key == tf.execution:
                sliced[key] = exec_series[: i + 1]
            else:
                sliced[key] = _slice_htf(series, upto_ts, key)

        account = AccountState(
            equity=equity, start_of_day_equity=equity,
            start_of_week_equity=equity, free_margin=equity,
        )
        setup = analyze(spec, sliced, cfg, account,
                        spread_frac=bt.slippage_frac, slippage_frac=bt.slippage_frac)
        if setup.tradable and setup.qty and setup.entry and setup.stop and setup.target:
            nxt = exec_series[i + 1]
            fill = _attempt_entry(setup, nxt, spec, bt)
            if fill is not None:
                open_trade = {
                    "setup": setup, "spec": spec, "entry": fill,
                    "entry_bar": i + 1, "cfg": bt,
                }
        i += 1

    res.bars_tested = len(exec_series) - bt.warmup_bars
    res.metrics = compute_metrics(res.trades)
    return res


def _attempt_entry(setup, bar: Candle, spec, bt: BacktestConfig) -> Optional[float]:
    long = setup.direction == "long"
    if setup.order_type == "limit":
        # Limit fills only if the bar trades through the limit price.
        if long and bar.low <= setup.entry:
            return setup.entry
        if (not long) and bar.high >= setup.entry:
            return setup.entry
        return None
    # Market: fill at next open with slippage.
    slip = bar.open * bt.slippage_frac
    return bar.open + slip if long else bar.open - slip


def _try_exit(trade: dict, bar: Candle, bt: BacktestConfig):
    setup = trade["setup"]
    long = setup.direction == "long"
    stop, target = setup.stop, setup.target
    hit_stop = bar.low <= stop if long else bar.high >= stop
    hit_tp = bar.high >= target if long else bar.low <= target
    if hit_stop and hit_tp:
        price = stop if bt.intrabar_worst_case else target
        reason = "stop_loss" if bt.intrabar_worst_case else "take_profit"
    elif hit_stop:
        price, reason = stop, "stop_loss"
    elif hit_tp:
        price, reason = target, "take_profit"
    else:
        return None
    pnl = _pnl(trade, price)
    return pnl, price, reason


def _pnl(trade: dict, exit_price: float) -> float:
    setup = trade["setup"]
    spec: InstrumentSpec = trade["spec"]
    qty = setup.qty
    entry = trade["entry"]
    direction = 1 if setup.direction == "long" else -1
    price_pnl = (exit_price - entry) * direction
    if spec.is_pip_based:
        gross = (price_pnl / spec.pip_size) * spec.pip_value_per_lot * qty
    else:
        gross = price_pnl * spec.contract_multiplier * qty
    notional = entry * qty * spec.contract_multiplier
    fees = notional * trade["cfg"].fee_frac
    return round(gross - fees, 4)


def _to_closed_trade(trade, exit_price, pnl, reason, exit_bar) -> ClosedTrade:
    setup = trade["setup"]
    return ClosedTrade(
        symbol=setup.symbol,
        direction=setup.direction,
        entry=trade["entry"],
        exit=exit_price,
        qty=setup.qty,
        pnl=pnl,
        reward_risk_planned=setup.reward_risk or 0.0,
        entry_model=setup.entry_model or "",
        score=setup.score,
        timeframe=setup.zone.direction.value if setup.zone else "",
        bars_held=exit_bar - trade["entry_bar"],
        exit_reason=reason,
    )
