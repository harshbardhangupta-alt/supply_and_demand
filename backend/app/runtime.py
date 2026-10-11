"""Application runtime state.

A single in-process coordinator holding the data adapter, universe manager,
strategy configurations, paper-trading engine and engine control flags. API
routers call into this; it owns no web concerns itself.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .brokers.paper import PaperBroker
from .core.candles import Timeframe
from .core.config import StrategyConfig, forex_config, indian_equity_config
from .core.instruments import (
    DEFAULT_SPECS,
    InstrumentSpec,
    MarketUniverse,
    equity_spec,
)
from .data.synthetic import SyntheticDataAdapter
from .paper.engine import PaperEngine
from .services.scanner import scan_universe
from .settings import get_settings
from .universe.nifty500 import Nifty500Universe

UNIVERSE_WATCHLISTS: Dict[MarketUniverse, List[str]] = {
    MarketUniverse.INDIAN_INDICES: ["NIFTY50", "BANKNIFTY"],
    MarketUniverse.FOREX: ["EURUSD", "GBPUSD", "USDJPY"],
    MarketUniverse.METALS: ["XAUUSD", "XAGUSD"],
    MarketUniverse.COMMODITIES: ["USOIL", "UKOIL"],
}


@dataclass
class EngineControl:
    running: bool = False
    auto_entry: bool = False
    live_mode: bool = False
    started_at: Optional[datetime] = None


class AppState:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.adapter = SyntheticDataAdapter()
        self.universe = Nifty500Universe()
        self.configs: Dict[str, StrategyConfig] = {
            MarketUniverse.NIFTY500.value: indian_equity_config(),
            MarketUniverse.INDIAN_INDICES.value: forex_config(),
            MarketUniverse.FOREX.value: forex_config(),
            MarketUniverse.METALS.value: forex_config(),
            MarketUniverse.COMMODITIES.value: forex_config(),
        }
        self.paper_broker = PaperBroker(equity=self.settings.default_equity)
        self.paper_broker.connect()
        self.paper_engine = PaperEngine(broker=self.paper_broker,
                                        enabled=self.settings.paper_trading_enabled)
        self.control = EngineControl(live_mode=False)
        self.audit: List[dict] = []
        self.risk_events: List[dict] = []
        self._scan_cache: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self.started_at = datetime.now(timezone.utc)

    # --- universe/specs ---
    def specs_for(self, universe: str, limit: Optional[int] = None) -> List[InstrumentSpec]:
        if universe == MarketUniverse.NIFTY500.value:
            syms = self.universe.state.active_symbols()
            if limit:
                syms = syms[:limit]
            return [
                equity_spec(s, self.universe.state.constituents[s].name)
                for s in syms
            ]
        uni = MarketUniverse(universe)
        return [DEFAULT_SPECS[s] for s in UNIVERSE_WATCHLISTS.get(uni, []) if s in DEFAULT_SPECS]

    def config_for(self, universe: str) -> StrategyConfig:
        return self.configs.get(universe, forex_config())

    # --- scanning ---
    def scan(self, universe: str, limit: Optional[int] = None) -> dict:
        specs = self.specs_for(universe, limit)
        cfg = self.config_for(universe)
        rows = scan_universe(specs, self.adapter, cfg, self.settings.default_equity,
                             count=cfg.max_lookback, limit=limit)
        status = self.adapter.status()
        result = {
            "universe": universe,
            "provider": self.adapter.provider,
            "feed_mode": status.mode.value,
            "last_update": status.last_update.isoformat() if status.last_update else None,
            "coverage_pct": status.coverage_pct,
            "total": len(rows),
            "eligible": sum(1 for r in rows if r.get("eligible")),
            "rows": rows,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._scan_cache[universe] = result
        return result

    def cached_scan(self, universe: str) -> Optional[dict]:
        return self._scan_cache.get(universe)

    # --- audit ---
    def log_audit(self, action: str, detail: dict, actor: str = "system") -> None:
        self.audit.append({
            "action": action, "detail": detail, "actor": actor,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self.audit = self.audit[-500:]

    def log_risk(self, kind: str, detail: str) -> None:
        self.risk_events.append({
            "kind": kind, "detail": detail,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self.risk_events = self.risk_events[-500:]

    # --- overview ---
    def overview(self) -> dict:
        acc = self.paper_broker.account()
        positions = self.paper_broker.positions()
        orders = self.paper_broker.orders()
        pending = [o for o in orders if o.status.value in ("submitted", "pending")]
        return {
            "equity": round(acc.equity, 2),
            "balance": round(acc.balance, 2),
            "free_margin": round(acc.free_margin, 2),
            "used_margin": round(acc.used_margin, 2),
            "realized_pnl": round(self.paper_broker.realized_pnl, 2),
            "unrealized_pnl": round(sum(p.unrealized_pnl for p in positions), 2),
            "open_positions": len(positions),
            "active_orders": len(pending),
            "engine_running": self.control.running,
            "auto_entry": self.control.auto_entry,
            "live_mode": self.control.live_mode,
            "paper_trading": self.paper_engine.enabled,
            "broker_status": "connected" if self.paper_broker.connected else "disconnected",
            "universe_source": self.universe.state.source,
            "universe_size": len(self.universe.state.active_symbols()),
            "data_provider": self.adapter.provider,
            "data_feed_mode": self.adapter.status().mode.value,
        }


_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state
