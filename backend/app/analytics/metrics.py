"""Deterministic performance metrics over a list of completed trades."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ClosedTrade:
    symbol: str
    direction: str
    entry: float
    exit: float
    qty: float
    pnl: float
    reward_risk_planned: float
    entry_model: str
    score: float
    timeframe: str
    bars_held: int = 0
    fees: float = 0.0
    slippage: float = 0.0
    exit_reason: str = ""
    mae: float = 0.0
    mfe: float = 0.0


@dataclass
class Metrics:
    trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    avg_reward_risk: float = 0.0
    avg_bars_held: float = 0.0
    long_trades: int = 0
    short_trades: int = 0
    by_symbol: Dict[str, float] = field(default_factory=dict)
    by_timeframe: Dict[str, float] = field(default_factory=dict)
    by_entry_model: Dict[str, float] = field(default_factory=dict)
    by_score_bucket: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        return d


def compute_metrics(trades: List[ClosedTrade]) -> Metrics:
    m = Metrics()
    if not trades:
        return m
    m.trades = len(trades)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    streak_w = streak_l = cur_w = cur_l = 0
    rr_sum = 0.0

    for t in trades:
        net = t.pnl - t.fees
        equity += net
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        rr_sum += t.reward_risk_planned
        m.avg_bars_held += t.bars_held
        if t.direction == "long":
            m.long_trades += 1
        else:
            m.short_trades += 1
        if net > 0:
            m.wins += 1
            m.gross_profit += net
            cur_w += 1
            cur_l = 0
        else:
            m.losses += 1
            m.gross_loss += -net
            cur_l += 1
            cur_w = 0
        streak_w = max(streak_w, cur_w)
        streak_l = max(streak_l, cur_l)
        m.by_symbol[t.symbol] = round(m.by_symbol.get(t.symbol, 0.0) + net, 4)
        m.by_timeframe[t.timeframe] = round(m.by_timeframe.get(t.timeframe, 0.0) + net, 4)
        m.by_entry_model[t.entry_model] = round(m.by_entry_model.get(t.entry_model, 0.0) + net, 4)
        bucket = _score_bucket(t.score)
        m.by_score_bucket[bucket] = round(m.by_score_bucket.get(bucket, 0.0) + net, 4)

    m.net_profit = round(m.gross_profit - m.gross_loss, 4)
    m.win_rate = round(m.wins / m.trades, 4)
    m.profit_factor = round(m.gross_profit / m.gross_loss, 4) if m.gross_loss > 0 else float("inf")
    m.avg_win = round(m.gross_profit / m.wins, 4) if m.wins else 0.0
    m.avg_loss = round(m.gross_loss / m.losses, 4) if m.losses else 0.0
    m.expectancy = round(m.net_profit / m.trades, 4)
    m.max_drawdown = round(max_dd, 4)
    m.max_consecutive_wins = streak_w
    m.max_consecutive_losses = streak_l
    m.avg_reward_risk = round(rr_sum / m.trades, 4)
    m.avg_bars_held = round(m.avg_bars_held / m.trades, 2)
    m.gross_profit = round(m.gross_profit, 4)
    m.gross_loss = round(m.gross_loss, 4)
    return m


def _score_bucket(score: float) -> str:
    if score >= 90:
        return "90-100"
    if score >= 80:
        return "80-89"
    if score >= 70:
        return "70-79"
    return "<70"
