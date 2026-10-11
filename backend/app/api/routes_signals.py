"""Signals board: strategy stock selection, outcomes (target/SL hit) and accuracy.

This is an analysis/signal tool — it does NOT place real orders. It surfaces the
stocks the SMC strategy selects now (with entry/SL/target and a full "why"),
the stocks it rejects (with the reason), and, by replaying recent history, which
past signals hit target vs stop — from which it computes accuracy.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter

from ..backtest.engine import BacktestConfig, run_backtest
from ..core.instruments import MarketUniverse
from ..runtime import get_state
from ..services.scanner import scan_universe

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/board")
async def signals_board(
    universe: str = MarketUniverse.NIFTY500.value,
    scan_limit: int = 40,
    eval_limit: int = 8,
    bars: int = 300,
):
    st = get_state()
    specs = st.specs_for(universe, scan_limit)
    cfg = st.config_for(universe)
    rows = scan_universe(specs, st.adapter, cfg, st.settings.default_equity,
                         count=cfg.max_lookback, limit=scan_limit)

    selected = [_sel_row(r) for r in rows if r.get("eligible")]
    rejected = [_rej_row(r) for r in rows if not r.get("eligible")]

    # Replay recent history for the highest-scoring symbols to resolve outcomes.
    eval_syms = [r for r in rows][:eval_limit]
    history: List[dict] = []
    tfs = {cfg.timeframes.bias, cfg.timeframes.structure, cfg.timeframes.zones,
           cfg.timeframes.intermediate, cfg.timeframes.setup, cfg.timeframes.execution}
    spec_by_symbol = {s.symbol: s for s in specs}
    for r in eval_syms:
        spec = spec_by_symbol.get(r["symbol"])
        if not spec:
            continue
        data = {tf: st.adapter.get_candles(spec.symbol, tf, bars) for tf in tfs}
        bt = run_backtest(spec, data, cfg, st.settings.default_equity,
                          BacktestConfig(warmup_bars=min(120, bars // 2)))
        for t in bt.trades:
            history.append({
                "symbol": t.symbol, "name": spec.name, "direction": t.direction,
                "entry": round(t.entry, 2), "stop": round(t.stop, 2),
                "target": round(t.target, 2), "exit": round(t.exit, 2),
                "reward_risk": t.reward_risk_planned, "score": t.score,
                "outcome": "target" if t.exit_reason == "take_profit" else (
                    "stop" if t.exit_reason == "stop_loss" else t.exit_reason),
                "pnl": round(t.pnl, 2), "bars_held": t.bars_held,
                "entry_model": t.entry_model,
            })

    resolved = [h for h in history if h["outcome"] in ("target", "stop")]
    wins = sum(1 for h in resolved if h["outcome"] == "target")
    losses = sum(1 for h in resolved if h["outcome"] == "stop")
    accuracy = round(wins / len(resolved) * 100, 1) if resolved else None
    rr_vals = [r["reward_risk"] for r in selected if r.get("reward_risk")]
    avg_rr = round(sum(rr_vals) / len(rr_vals), 2) if rr_vals else None

    # Sparkline: cumulative win/loss path over resolved signals.
    spark = []
    acc = 0
    for h in resolved:
        acc += 1 if h["outcome"] == "target" else -1
        spark.append(acc)

    return {
        "universe": universe,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": st.adapter.provider,
        "feed_mode": st.adapter.status().mode.value,
        "summary": {
            "scanned": len(rows),
            "selected": len(selected),
            "rejected": len(rejected),
            "resolved": len(resolved),
            "wins": wins,
            "losses": losses,
            "accuracy": accuracy,
            "avg_reward_risk": avg_rr,
        },
        "sparkline": spark,
        "selected": selected,
        "rejected": rejected,
        "history": history,
    }


def _sel_row(r: dict) -> dict:
    return {
        "symbol": r["symbol"], "name": r.get("name"), "direction": r.get("direction"),
        "entry": r.get("entry"), "stop": r.get("stop"), "target": r.get("target"),
        "reward_risk": r.get("reward_risk"), "score": r.get("score"),
        "qty": r.get("qty"), "risk_pct": r.get("risk_pct"),
        "entry_model": r.get("entry_model"), "order_type": r.get("order_type"),
        "price": r.get("price"), "status": "pending",
        "why": r.get("why"),
    }


def _rej_row(r: dict) -> dict:
    return {
        "symbol": r["symbol"], "name": r.get("name"), "score": r.get("score"),
        "rejection_reason": r.get("rejection_reason"),
        "weekly_bias": r.get("weekly_bias"), "daily_bias": r.get("daily_bias"),
        "why": r.get("why"),
    }
