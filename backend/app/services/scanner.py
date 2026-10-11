"""Universe scanner.

Runs the shared strategy engine across a set of instruments and returns a row
per instrument — including instruments that do NOT qualify, each with its exact
rejection reason, so the whole universe stays visible rather than silently
filtered.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Optional

from ..core.candles import Timeframe
from ..core.config import StrategyConfig
from ..core.engine import SetupResult, analyze
from ..core.instruments import InstrumentSpec
from ..core.risk import AccountState
from ..data.base import MarketDataAdapter


def _tfs(cfg: StrategyConfig) -> List[Timeframe]:
    t = cfg.timeframes
    return list({t.bias, t.structure, t.zones, t.intermediate, t.setup, t.execution})


def scan_instrument(
    spec: InstrumentSpec, adapter: MarketDataAdapter, cfg: StrategyConfig,
    equity: float, count: int = 300,
) -> SetupResult:
    data = {tf: adapter.get_candles(spec.symbol, tf, count) for tf in _tfs(cfg)}
    account = AccountState(
        equity=equity, start_of_day_equity=equity,
        start_of_week_equity=equity, free_margin=equity,
    )
    return analyze(spec, data, cfg, account)


def setup_to_row(spec: InstrumentSpec, res: SetupResult, provider: str,
                 last_update: Optional[str]) -> dict:
    tfb = res.biases
    return {
        "symbol": res.symbol,
        "name": spec.name,
        "asset_class": spec.asset_class.value,
        "price": res.current_price,
        "last_update": last_update,
        "provider": provider,
        "weekly_bias": tfb.get("1w"),
        "daily_bias": tfb.get("1d"),
        "h4_structure": tfb.get("4h"),
        "h1_structure": tfb.get("1h"),
        "direction": res.direction,
        "bos": res.bos,
        "fvg": res.fvg,
        "zone_state": res.zone_state,
        "zone_fresh": res.zone_fresh,
        "score": res.score,
        "score_breakdown": res.score_breakdown,
        "entry": res.entry,
        "stop": res.stop,
        "target": res.target,
        "reward_risk": res.reward_risk,
        "qty": res.qty,
        "risk_pct": res.risk_pct,
        "risk_amount": res.risk_amount,
        "entry_model": res.entry_model,
        "order_type": res.order_type,
        "eligible": res.tradable,
        "rejection_reason": res.rejection_reason,
        "zone": _zone_dict(res),
    }


def _zone_dict(res: SetupResult) -> Optional[dict]:
    z = res.zone
    if not z:
        return None
    return {
        "direction": z.direction.value,
        "distal": z.distal,
        "proximal": z.proximal,
        "state": z.state.value,
        "touches": z.touches,
        "fresh": z.is_fresh,
    }


def scan_universe(
    specs: List[InstrumentSpec], adapter: MarketDataAdapter, cfg: StrategyConfig,
    equity: float, count: int = 300, limit: Optional[int] = None,
) -> List[dict]:
    rows: List[dict] = []
    status = adapter.status()
    last_update = status.last_update.isoformat() if status.last_update else None
    use = specs[:limit] if limit else specs
    for spec in use:
        try:
            res = scan_instrument(spec, adapter, cfg, equity, count)
            rows.append(setup_to_row(spec, res, adapter.provider, last_update))
        except Exception as exc:  # keep the symbol visible with the error
            rows.append({
                "symbol": spec.symbol, "name": spec.name, "eligible": False,
                "rejection_reason": f"scan_error: {exc}", "score": 0,
            })
    # Qualified setups first, then by score.
    rows.sort(key=lambda r: (not r.get("eligible", False), -(r.get("score") or 0)))
    return rows
