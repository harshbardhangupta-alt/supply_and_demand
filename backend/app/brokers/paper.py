"""In-memory paper-trading broker.

Simulates the full order lifecycle without sending anything to a real venue.
Trades/positions are always labelled PAPER by the caller. Balances and fills
are simulated and must never be presented as real broker data.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .base import (
    AccountInfo,
    BrokerAdapter,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


class PaperBroker(BrokerAdapter):
    name = "paper"
    supports_live = False

    def __init__(self, equity: float = 1_000_000.0, currency: str = "INR",
                 spread_frac: float = 0.0002, slippage_frac: float = 0.0):
        self.balance = equity
        self.currency = currency
        self.spread_frac = spread_frac
        self.slippage_frac = slippage_frac
        self._orders: Dict[str, Order] = {}
        self._by_client: Dict[str, str] = {}
        self._positions: Dict[str, Position] = {}
        self._prices: Dict[str, float] = {}
        self.realized_pnl = 0.0
        self.connected = False
        self.closed_trades: List[dict] = []

    # --- lifecycle ---
    def connect(self) -> bool:
        self.connected = True
        return True

    def set_price(self, symbol: str, price: float) -> None:
        self._prices[symbol] = price

    def account(self) -> AccountInfo:
        unreal = sum(p.unrealized_pnl for p in self._positions.values())
        equity = self.balance + unreal
        used = sum(abs(p.qty * p.avg_price) * 0.2 for p in self._positions.values())
        return AccountInfo(
            account_id="PAPER", currency=self.currency, equity=equity,
            balance=self.balance, free_margin=max(0.0, equity - used),
            used_margin=used, is_live=False,
        )

    # --- orders ---
    def submit_order(self, req: OrderRequest) -> Order:
        # Idempotency: a repeat of a known client_order_id returns the same order.
        if req.client_order_id and req.client_order_id in self._by_client:
            return self._orders[self._by_client[req.client_order_id]]
        oid = uuid.uuid4().hex
        order = Order(id=oid, request=req, status=OrderStatus.SUBMITTED,
                      broker_order_id=f"PAPER-{oid[:8]}")
        self._orders[oid] = order
        if req.client_order_id:
            self._by_client[req.client_order_id] = oid

        price = self._prices.get(req.symbol)
        if req.order_type == OrderType.MARKET:
            if price is None:
                order.status = OrderStatus.REJECTED
                order.reason = "no_market_price"
            else:
                self._fill(order, self._apply_slippage(price, req.side))
        # limit/stop orders rest until on_tick triggers them.
        return order

    def cancel_order(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if not order:
            raise KeyError(order_id)
        if order.status in (OrderStatus.SUBMITTED, OrderStatus.PENDING):
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now(timezone.utc)
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def orders(self) -> List[Order]:
        return list(self._orders.values())

    def positions(self) -> List[Position]:
        return list(self._positions.values())

    # --- simulation tick ---
    def on_tick(self, symbol: str, price: float, ts: Optional[datetime] = None) -> None:
        """Advance simulation: trigger resting limits, SL/TP, mark positions."""
        self._prices[symbol] = price
        ts = ts or datetime.now(timezone.utc)
        for order in list(self._orders.values()):
            if order.request.symbol != symbol:
                continue
            if order.status != OrderStatus.SUBMITTED:
                continue
            if order.request.expire_at and ts >= order.request.expire_at:
                order.status = OrderStatus.EXPIRED
                continue
            r = order.request
            if r.order_type == OrderType.LIMIT and r.price is not None:
                if (r.side == OrderSide.BUY and price <= r.price) or (
                    r.side == OrderSide.SELL and price >= r.price
                ):
                    self._fill(order, r.price)
            elif r.order_type == OrderType.STOP and r.price is not None:
                if (r.side == OrderSide.BUY and price >= r.price) or (
                    r.side == OrderSide.SELL and price <= r.price
                ):
                    self._fill(order, self._apply_slippage(price, r.side))

        self._mark_and_protect(symbol, price, ts)

    def _mark_and_protect(self, symbol: str, price: float, ts: datetime) -> None:
        pos = self._positions.get(symbol)
        if not pos:
            return
        direction = 1 if pos.side == OrderSide.BUY else -1
        pos.unrealized_pnl = (price - pos.avg_price) * pos.qty * direction
        # Protective exits.
        if pos.side == OrderSide.BUY:
            if pos.stop_loss is not None and price <= pos.stop_loss:
                self._close(symbol, pos.stop_loss, "stop_loss")
            elif pos.take_profit is not None and price >= pos.take_profit:
                self._close(symbol, pos.take_profit, "take_profit")
        else:
            if pos.stop_loss is not None and price >= pos.stop_loss:
                self._close(symbol, pos.stop_loss, "stop_loss")
            elif pos.take_profit is not None and price <= pos.take_profit:
                self._close(symbol, pos.take_profit, "take_profit")

    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        slip = price * self.slippage_frac
        half_spread = price * self.spread_frac / 2
        return price + slip + half_spread if side == OrderSide.BUY else price - slip - half_spread

    def _fill(self, order: Order, fill_price: float) -> None:
        r = order.request
        order.status = OrderStatus.FILLED
        order.filled_qty = r.qty
        order.avg_fill_price = fill_price
        order.updated_at = datetime.now(timezone.utc)
        self._apply_fill(r.symbol, r.side, r.qty, fill_price, r.stop_loss, r.take_profit)

    def _apply_fill(self, symbol, side, qty, price, sl, tp) -> None:
        pos = self._positions.get(symbol)
        if pos is None:
            self._positions[symbol] = Position(
                symbol=symbol, side=side, qty=qty, avg_price=price,
                stop_loss=sl, take_profit=tp,
            )
            return
        # Same direction -> average in; opposite -> reduce/close/flip.
        if pos.side == side:
            total = pos.qty + qty
            pos.avg_price = (pos.avg_price * pos.qty + price * qty) / total
            pos.qty = total
            if sl is not None:
                pos.stop_loss = sl
            if tp is not None:
                pos.take_profit = tp
        else:
            if qty >= pos.qty:
                self._close(symbol, price, "opposite_fill")
                remaining = qty - pos.qty
                if remaining > 0:
                    self._positions[symbol] = Position(symbol, side, remaining, price, sl, tp)
            else:
                self._realize(pos, price, pos_qty=qty)
                pos.qty -= qty

    def _close(self, symbol: str, price: float, reason: str) -> None:
        pos = self._positions.get(symbol)
        if not pos:
            return
        self._realize(pos, price, pos.qty, reason)
        del self._positions[symbol]

    def _realize(self, pos: Position, price: float, pos_qty: float,
                 reason: str = "") -> None:
        direction = 1 if pos.side == OrderSide.BUY else -1
        pnl = (price - pos.avg_price) * pos_qty * direction
        self.realized_pnl += pnl
        self.balance += pnl
        self.closed_trades.append({
            "symbol": pos.symbol,
            "direction": "long" if pos.side == OrderSide.BUY else "short",
            "entry": pos.avg_price,
            "exit": price,
            "qty": pos_qty,
            "pnl": round(pnl, 4),
            "exit_reason": reason,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        })
