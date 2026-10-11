"""Paper-trading engine.

Reuses the exact same strategy + risk pipeline as live trading, but routes
orders to the in-memory :class:`PaperBroker`. Every resulting position/trade is
labelled PAPER by construction (the broker's account_id is ``PAPER`` and
``is_live`` is False).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from ..brokers.base import OrderRequest, OrderSide, OrderType
from ..brokers.paper import PaperBroker
from ..core.candles import Candle, Timeframe, ensure_closed
from ..core.config import StrategyConfig
from ..core.engine import SetupResult, analyze
from ..core.instruments import InstrumentSpec
from ..core.risk import AccountState, OpenPositionRisk


@dataclass
class PaperEngine:
    broker: PaperBroker
    enabled: bool = True
    submitted: Dict[str, str] = field(default_factory=dict)  # symbol -> client id

    def account_state(self) -> AccountState:
        acc = self.broker.account()
        open_pos = [
            OpenPositionRisk(symbol=p.symbol, risk_amount=abs(p.qty * p.avg_price) * 0.0)
            for p in self.broker.positions()
        ]
        return AccountState(
            equity=acc.equity, start_of_day_equity=acc.balance,
            start_of_week_equity=acc.balance, free_margin=acc.free_margin,
            used_margin=acc.used_margin, open_positions=open_pos,
            data_fresh=True, broker_connected=True,
        )

    def evaluate_and_trade(
        self, spec: InstrumentSpec, data: Dict[Timeframe, List[Candle]],
        cfg: StrategyConfig,
    ) -> SetupResult:
        setup = analyze(spec, data, cfg, self.account_state())
        price = setup.current_price
        if price is not None:
            self.broker.set_price(spec.symbol, price)
        if not (self.enabled and setup.tradable):
            return setup
        if any(p.symbol == spec.symbol for p in self.broker.positions()):
            return setup
        # Idempotency key ties an order to the zone + entry so restarts don't
        # resubmit a duplicate for the same setup.
        key_src = f"{spec.symbol}:{setup.entry}:{setup.stop}:{setup.zone.created_index if setup.zone else 0}"
        client_id = hashlib.sha1(key_src.encode()).hexdigest()[:16]
        if client_id in self.submitted.values():
            return setup
        side = OrderSide.BUY if setup.direction == "long" else OrderSide.SELL
        otype = OrderType.LIMIT if setup.order_type == "limit" else OrderType.MARKET
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=cfg.entry.order_expiry_bars * cfg.timeframes.execution.minutes
        )
        req = OrderRequest(
            symbol=spec.symbol, side=side, qty=setup.qty, order_type=otype,
            price=setup.entry if otype == OrderType.LIMIT else None,
            stop_loss=setup.stop, take_profit=setup.target,
            client_order_id=client_id, expire_at=expire, tag="PAPER",
        )
        self.broker.submit_order(req)
        self.submitted[spec.symbol] = client_id
        return setup
