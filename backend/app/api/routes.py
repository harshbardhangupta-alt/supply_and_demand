"""Primary REST API: market data, scanner, zones, trading, backtest, analytics."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..analytics.metrics import ClosedTrade, compute_metrics
from ..backtest.engine import BacktestConfig, run_backtest
from ..core.candles import Timeframe, ensure_closed
from ..core.config import ZoneConfig
from ..core.displacement import detect_displacements
from ..core.fvg import detect_fvgs
from ..core.instruments import DEFAULT_SPECS, MarketUniverse, equity_spec
from ..core.market_structure import detect_structure
from ..core.zones import build_zones
from ..runtime import UNIVERSE_WATCHLISTS, get_state
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["app"])


# --------------------------------------------------------------------------- #
# Health / overview
# --------------------------------------------------------------------------- #
@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/overview")
async def overview():
    return get_state().overview()


# --------------------------------------------------------------------------- #
# Instruments & universe
# --------------------------------------------------------------------------- #
@router.get("/instruments")
async def instruments(universe: str = MarketUniverse.NIFTY500.value, limit: int = 500):
    st = get_state()
    specs = st.specs_for(universe, limit)
    return [
        {
            "symbol": s.symbol, "name": s.name, "asset_class": s.asset_class.value,
            "universe": s.universe.value, "currency": s.currency,
            "tick_size": s.tick_size, "lot_size": s.lot_size,
            "tradable": s.tradable, "exchange": s.exchange,
        }
        for s in specs
    ]


@router.get("/universe/nifty500")
async def nifty500():
    st = get_state()
    s = st.universe.state
    return {
        "source": s.source,
        "last_refresh": s.last_refresh.isoformat() if s.last_refresh else None,
        "last_refresh_ok": s.last_refresh_ok,
        "warning": s.warning,
        "count": len(s.active_symbols()),
        "constituents": [
            {"symbol": c.symbol, "name": c.name, "industry": c.industry,
             "active": c.active,
             "effective_from": c.effective_from.isoformat() if c.effective_from else None}
            for c in s.constituents.values()
        ],
    }


@router.post("/universe/nifty500/refresh")
async def refresh_nifty500(user: dict = Depends(require_role("admin"))):
    st = get_state()
    state = st.universe.refresh()
    st.log_audit("universe_refresh", {"ok": state.last_refresh_ok, "source": state.source},
                 actor=user["sub"])
    return {
        "ok": state.last_refresh_ok, "source": state.source,
        "warning": state.warning, "count": len(state.active_symbols()),
    }


# --------------------------------------------------------------------------- #
# Scanner
# --------------------------------------------------------------------------- #
@router.get("/scanner/{universe}")
async def scanner(universe: str, limit: Optional[int] = None, refresh: bool = True):
    st = get_state()
    if not refresh:
        cached = st.cached_scan(universe)
        if cached:
            return cached
    try:
        return st.scan(universe, limit=limit)
    except Exception as exc:
        raise HTTPException(400, f"scan failed: {exc}")


@router.get("/signals")
async def signals(universe: str = MarketUniverse.NIFTY500.value):
    st = get_state()
    cached = st.cached_scan(universe) or st.scan(universe, limit=50)
    rows = [r for r in cached["rows"] if r.get("eligible")]
    return {"universe": universe, "count": len(rows), "signals": rows}


# --------------------------------------------------------------------------- #
# Chart data with overlays
# --------------------------------------------------------------------------- #
@router.get("/chart/{symbol}")
async def chart(symbol: str, timeframe: str = "1h", count: int = 300):
    st = get_state()
    try:
        tf = Timeframe(timeframe)
    except ValueError:
        raise HTTPException(400, f"unknown timeframe {timeframe}")
    spec = _spec_for_symbol(st, symbol)
    candles = st.adapter.get_candles(symbol, tf, count)
    closed = ensure_closed(candles)
    cfg = st.config_for(_universe_for_spec(spec))
    state = detect_structure(closed, cfg.swing, cfg.structure)
    disps = detect_displacements(closed, cfg.displacement)
    fvgs = detect_fvgs(closed, cfg.fvg, spec.tick_size)
    zones = build_zones(closed, disps, cfg.zone, {f.index for f in fvgs})
    return {
        "symbol": symbol, "timeframe": tf.value, "provider": st.adapter.provider,
        "feed_mode": st.adapter.status().mode.value,
        "candles": [
            {"t": c.timestamp.isoformat(), "o": c.open, "h": c.high,
             "l": c.low, "c": c.close, "v": c.volume} for c in closed
        ],
        "swings": [
            {"index": s.index, "price": s.price, "kind": s.kind.value,
             "label": s.label.value if s.label else None} for s in state.swings
        ],
        "events": [
            {"type": e.type.value, "direction": e.direction, "index": e.index,
             "level": e.level} for e in state.events
        ],
        "zones": [
            {"direction": z.direction.value, "distal": z.distal, "proximal": z.proximal,
             "state": z.state.value, "origin_index": z.origin_index,
             "created_index": z.created_index, "touches": z.touches,
             "fresh": z.is_fresh} for z in zones
        ],
        "fvgs": [
            {"index": f.index, "direction": f.direction, "upper": f.upper,
             "lower": f.lower, "filled_pct": f.filled_pct} for f in fvgs
        ],
    }


@router.get("/zones/{symbol}")
async def zones(symbol: str, timeframe: str = "4h", count: int = 300):
    st = get_state()
    tf = Timeframe(timeframe)
    spec = _spec_for_symbol(st, symbol)
    closed = ensure_closed(st.adapter.get_candles(symbol, tf, count))
    cfg = st.config_for(_universe_for_spec(spec))
    disps = detect_displacements(closed, cfg.displacement)
    fvgs = detect_fvgs(closed, cfg.fvg, spec.tick_size)
    zs = build_zones(closed, disps, cfg.zone, {f.index for f in fvgs})
    return {"symbol": symbol, "timeframe": tf.value, "zones": [
        {"direction": z.direction.value, "distal": z.distal, "proximal": z.proximal,
         "state": z.state.value, "touches": z.touches, "fresh": z.is_fresh,
         "created_index": z.created_index, "invalidation_reason": z.invalidation_reason}
        for z in zs]}


# --------------------------------------------------------------------------- #
# Trading controls
# --------------------------------------------------------------------------- #
class AutoEntryBody(BaseModel):
    enabled: bool


@router.post("/trading/start")
async def trading_start(user: dict = Depends(current_user)):
    st = get_state()
    st.control.running = True
    st.log_audit("engine_start", {}, actor=user["sub"])
    return {"running": True}


@router.post("/trading/stop")
async def trading_stop(user: dict = Depends(current_user)):
    st = get_state()
    st.control.running = False
    st.log_audit("engine_stop", {}, actor=user["sub"])
    return {"running": False}


@router.post("/trading/auto-entry")
async def trading_auto_entry(body: AutoEntryBody, user: dict = Depends(current_user)):
    st = get_state()
    st.control.auto_entry = body.enabled
    st.paper_engine.enabled = body.enabled
    st.log_audit("auto_entry", {"enabled": body.enabled}, actor=user["sub"])
    return {"auto_entry": body.enabled}


class LiveEnableBody(BaseModel):
    confirm: bool = False


@router.post("/trading/live/enable")
async def live_enable(body: LiveEnableBody, user: dict = Depends(require_role("admin"))):
    st = get_state()
    # Live trading is disabled by default and requires explicit confirmation
    # plus configured broker credentials.
    if not st.settings.live_trading_enabled:
        raise HTTPException(403, "Live trading is disabled by server configuration "
                                 "(set SMC_LIVE_TRADING_ENABLED=true and configure a broker).")
    if not body.confirm:
        raise HTTPException(400, "Explicit confirmation required to enable live mode.")
    st.control.live_mode = True
    st.log_audit("live_enable", {"by": user["sub"]}, actor=user["sub"])
    return {"live_mode": True}


@router.post("/trading/emergency-stop")
async def emergency_stop(user: dict = Depends(current_user)):
    st = get_state()
    st.control.running = False
    st.control.auto_entry = False
    st.paper_engine.enabled = False
    cancelled = 0
    for o in st.paper_broker.orders():
        if o.status.value in ("submitted", "pending"):
            st.paper_broker.cancel_order(o.id)
            cancelled += 1
    st.log_audit("emergency_stop", {"cancelled_orders": cancelled}, actor=user["sub"])
    st.log_risk("emergency_stop", f"cancelled {cancelled} pending orders; new entries disabled")
    return {
        "stopped": True, "cancelled_orders": cancelled,
        "note": "New entries disabled and pending entry orders cancelled. "
                "Open positions are NOT auto-liquidated — use /trading/liquidate.",
    }


@router.post("/trading/liquidate")
async def liquidate(user: dict = Depends(require_role("admin"))):
    st = get_state()
    closed = 0
    for p in list(st.paper_broker.positions()):
        price = st.paper_broker._prices.get(p.symbol, p.avg_price)
        st.paper_broker._close(p.symbol, price, "manual_liquidation")
        closed += 1
    st.log_audit("liquidate", {"closed_positions": closed}, actor=user["sub"])
    return {"closed_positions": closed}


@router.post("/trading/paper/run")
async def paper_run(universe: str = MarketUniverse.NIFTY500.value, limit: int = 25,
                    user: dict = Depends(current_user)):
    """Run one evaluation pass over a universe, routing eligible setups to the
    paper broker (simulated)."""
    st = get_state()
    specs = st.specs_for(universe, limit)
    cfg = st.config_for(universe)
    submitted = 0
    for spec in specs:
        data = {tf: st.adapter.get_candles(spec.symbol, tf, cfg.max_lookback)
                for tf in {cfg.timeframes.bias, cfg.timeframes.structure,
                           cfg.timeframes.zones, cfg.timeframes.intermediate,
                           cfg.timeframes.setup, cfg.timeframes.execution}}
        before = len(st.paper_broker.orders())
        res = st.paper_engine.evaluate_and_trade(spec, data, cfg)
        if len(st.paper_broker.orders()) > before:
            submitted += 1
            st.log_audit("paper_order", {"symbol": spec.symbol, "entry": res.entry,
                                         "stop": res.stop, "target": res.target}, actor=user["sub"])
    return {"evaluated": len(specs), "orders_submitted": submitted,
            "positions": len(st.paper_broker.positions())}


# --------------------------------------------------------------------------- #
# Positions / orders
# --------------------------------------------------------------------------- #
@router.get("/positions")
async def positions():
    st = get_state()
    out = []
    for p in st.paper_broker.positions():
        price = st.paper_broker._prices.get(p.symbol, p.avg_price)
        out.append({
            "symbol": p.symbol, "side": p.side.value, "qty": p.qty,
            "avg_price": p.avg_price, "current_price": price,
            "stop_loss": p.stop_loss, "take_profit": p.take_profit,
            "unrealized_pnl": round(p.unrealized_pnl, 2),
            "opened_at": p.opened_at.isoformat(), "is_paper": True,
        })
    return {"positions": out}


@router.get("/orders")
async def orders():
    st = get_state()
    out = []
    for o in st.paper_broker.orders():
        out.append({
            "id": o.id, "broker_order_id": o.broker_order_id,
            "symbol": o.request.symbol, "side": o.request.side.value,
            "type": o.request.order_type.value, "qty": o.request.qty,
            "price": o.request.price, "status": o.status.value,
            "filled_qty": o.filled_qty, "avg_fill_price": o.avg_fill_price,
            "reason": o.reason, "is_paper": True,
            "created_at": o.created_at.isoformat(),
        })
    return {"orders": out}


# --------------------------------------------------------------------------- #
# Backtest
# --------------------------------------------------------------------------- #
class BacktestBody(BaseModel):
    symbol: str
    universe: str = MarketUniverse.NIFTY500.value
    bars: int = 400
    warmup: int = 120
    starting_equity: float = 1_000_000.0
    fee_frac: float = 0.0003
    slippage_frac: float = 0.0005


@router.post("/backtest")
async def backtest(body: BacktestBody, user: dict = Depends(current_user)):
    st = get_state()
    spec = _spec_for_symbol(st, body.symbol)
    cfg = st.config_for(body.universe)
    bars = min(body.bars, 800)
    tfs = {cfg.timeframes.bias, cfg.timeframes.structure, cfg.timeframes.zones,
           cfg.timeframes.intermediate, cfg.timeframes.setup, cfg.timeframes.execution}
    data = {tf: st.adapter.get_candles(body.symbol, tf, bars) for tf in tfs}
    res = run_backtest(spec, data, cfg, body.starting_equity,
                       BacktestConfig(warmup_bars=body.warmup, fee_frac=body.fee_frac,
                                      slippage_frac=body.slippage_frac))
    st.log_audit("backtest", {"symbol": body.symbol, "trades": res.metrics.trades},
                 actor=user["sub"])
    return {
        "symbol": body.symbol, "bars_tested": res.bars_tested,
        "notes": res.notes,
        "metrics": res.metrics.as_dict(),
        "equity_curve": res.equity_curve,
        "trades": [t.__dict__ for t in res.trades],
        "disclaimer": "Results are from synthetic/historical simulation with a "
                      "conservative intrabar assumption; not a guarantee of future "
                      "performance.",
    }


# --------------------------------------------------------------------------- #
# Analytics (from paper closed trades)
# --------------------------------------------------------------------------- #
@router.get("/analytics")
async def analytics():
    st = get_state()
    raw = st.paper_broker.closed_trades
    trades = [
        ClosedTrade(
            symbol=t["symbol"], direction=t["direction"], entry=t["entry"],
            exit=t["exit"], qty=t["qty"], pnl=t["pnl"], reward_risk_planned=0.0,
            entry_model="paper", score=0.0, timeframe="", exit_reason=t.get("exit_reason", ""),
        )
        for t in raw
    ]
    return {"source": "paper", "trade_count": len(trades),
            "metrics": compute_metrics(trades).as_dict(),
            "trades": raw}


@router.get("/trades")
async def trades():
    st = get_state()
    return {"trades": st.paper_broker.closed_trades}


# --------------------------------------------------------------------------- #
# Settings / config
# --------------------------------------------------------------------------- #
@router.get("/settings")
async def settings_get():
    st = get_state()
    return {
        "universes": list(st.configs.keys()),
        "configs": {k: v.to_dict() for k, v in st.configs.items()},
        "live_trading_enabled": st.settings.live_trading_enabled,
        "paper_trading_enabled": st.settings.paper_trading_enabled,
        "default_equity": st.settings.default_equity,
        "data_provider": st.adapter.provider,
    }


class ConfigPatch(BaseModel):
    universe: str
    risk_per_trade: Optional[float] = None
    min_reward_risk: Optional[float] = None
    min_score: Optional[float] = None
    entry_model: Optional[str] = None
    direction: Optional[str] = None


@router.put("/settings/config")
async def settings_update(patch: ConfigPatch, user: dict = Depends(require_role("admin"))):
    st = get_state()
    cfg = st.configs.get(patch.universe)
    if not cfg:
        raise HTTPException(404, "unknown universe")
    if patch.risk_per_trade is not None:
        # Enforce the hard cap: configuration can never exceed max_risk_per_trade.
        cfg.risk.risk_per_trade = min(patch.risk_per_trade, cfg.risk.max_risk_per_trade)
    if patch.min_reward_risk is not None:
        cfg.risk.min_reward_risk = patch.min_reward_risk
    if patch.min_score is not None:
        cfg.score.min_score = patch.min_score
    if patch.entry_model is not None:
        from ..core.config import EntryModel
        cfg.entry.model = EntryModel(patch.entry_model)
    if patch.direction is not None:
        cfg.direction = patch.direction
    cfg.version += 1
    st.log_audit("config_update", {"universe": patch.universe, "version": cfg.version},
                 actor=user["sub"])
    return {"universe": patch.universe, "version": cfg.version, "config": cfg.to_dict()}


# --------------------------------------------------------------------------- #
# System health / audit
# --------------------------------------------------------------------------- #
@router.get("/system/health")
async def system_health():
    st = get_state()
    status = st.adapter.status()
    return {
        "market_data": {"provider": st.adapter.provider, "mode": status.mode.value,
                        "connected": status.connected,
                        "last_update": status.last_update.isoformat() if status.last_update else None},
        "strategy_engine": "ok",
        "risk_engine": "ok",
        "execution_engine": "paper" if not st.control.live_mode else "live",
        "database": "ok",
        "broker": {"name": st.paper_broker.name, "connected": st.paper_broker.connected},
        "websocket": "available",
        "started_at": st.started_at.isoformat(),
        "recent_errors": st.risk_events[-10:],
    }


@router.get("/audit")
async def audit(user: dict = Depends(current_user)):
    st = get_state()
    return {"events": list(reversed(st.audit[-200:]))}


@router.get("/risk/events")
async def risk_events(user: dict = Depends(current_user)):
    st = get_state()
    return {"events": list(reversed(st.risk_events[-200:]))}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _spec_for_symbol(st, symbol: str):
    symbol = symbol.upper()
    if symbol in DEFAULT_SPECS:
        return DEFAULT_SPECS[symbol]
    cons = st.universe.state.constituents.get(symbol)
    name = cons.name if cons else symbol
    return equity_spec(symbol, name)


def _universe_for_spec(spec) -> str:
    return spec.universe.value
