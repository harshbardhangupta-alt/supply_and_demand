"""Central account-level risk engine.

Every order — paper, backtest or live — passes through :func:`evaluate`. The
engine is deterministic and independent of the scanner and AI services, so it
keeps protecting the account even when those subsystems fail. A risk rejection
is absolute: it overrides any setup score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import RiskConfig


@dataclass
class OpenPositionRisk:
    symbol: str
    risk_amount: float
    margin: float = 0.0
    correlation_group: Optional[str] = None


@dataclass
class AccountState:
    equity: float
    start_of_day_equity: float
    start_of_week_equity: float
    free_margin: float = 0.0
    used_margin: float = 0.0
    realized_pnl_today: float = 0.0
    realized_pnl_week: float = 0.0
    consecutive_losses: int = 0
    data_fresh: bool = True
    broker_connected: bool = True
    open_positions: List[OpenPositionRisk] = field(default_factory=list)
    bars_since_last_loss: int = 10_000


@dataclass
class TradeProposal:
    symbol: str
    direction: str
    risk_amount: float
    reward_risk: float
    qty: float
    notional: float
    margin_required: float = 0.0
    spread_frac: float = 0.0
    slippage_frac: float = 0.0
    correlation_group: Optional[str] = None
    is_live: bool = False


@dataclass
class RiskDecision:
    approved: bool
    reasons: List[str] = field(default_factory=list)
    checks: Dict[str, bool] = field(default_factory=dict)

    def record(self, name: str, passed: bool, reason: str) -> None:
        self.checks[name] = passed
        if not passed:
            self.reasons.append(reason)
            self.approved = False


def evaluate(
    proposal: TradeProposal,
    account: AccountState,
    cfg: RiskConfig,
    max_spread_frac: float = 0.0015,
    max_slippage_frac: float = 0.002,
) -> RiskDecision:
    d = RiskDecision(approved=True)

    # --- hard gating conditions ---
    d.record("data_fresh", account.data_fresh, "market_data_stale")
    if proposal.is_live:
        d.record("broker_connected", account.broker_connected, "broker_disconnected")

    # --- per-trade risk ---
    risk_frac = proposal.risk_amount / account.equity if account.equity > 0 else 1.0
    d.record(
        "risk_per_trade",
        risk_frac <= cfg.max_risk_per_trade + 1e-9,
        f"risk_per_trade {risk_frac:.4f} exceeds cap {cfg.max_risk_per_trade}",
    )

    # --- reward:risk ---
    d.record(
        "reward_risk",
        proposal.reward_risk >= cfg.min_reward_risk - 1e-9,
        f"reward_risk {proposal.reward_risk:.2f} below minimum {cfg.min_reward_risk}",
    )

    # --- position count limits ---
    d.record(
        "max_open_positions",
        len(account.open_positions) < cfg.max_open_positions,
        "max_open_positions_reached",
    )
    same_symbol = sum(1 for p in account.open_positions if p.symbol == proposal.symbol)
    d.record(
        "max_per_instrument",
        same_symbol < cfg.max_positions_per_instrument,
        "max_positions_per_instrument_reached",
    )

    # --- aggregate open risk ---
    open_risk = sum(p.risk_amount for p in account.open_positions) + proposal.risk_amount
    agg_frac = open_risk / account.equity if account.equity > 0 else 1.0
    d.record(
        "aggregate_open_risk",
        agg_frac <= cfg.max_aggregate_open_risk + 1e-9,
        f"aggregate_open_risk {agg_frac:.4f} exceeds {cfg.max_aggregate_open_risk}",
    )

    # --- daily / weekly loss limits ---
    day_loss = -account.realized_pnl_today / account.start_of_day_equity if account.start_of_day_equity > 0 else 0.0
    d.record(
        "daily_loss_limit",
        day_loss < cfg.daily_loss_limit,
        f"daily_loss_limit reached ({day_loss:.4f})",
    )
    week_loss = -account.realized_pnl_week / account.start_of_week_equity if account.start_of_week_equity > 0 else 0.0
    d.record(
        "weekly_loss_limit",
        week_loss < cfg.weekly_loss_limit,
        f"weekly_loss_limit reached ({week_loss:.4f})",
    )

    # --- consecutive losses + cooldown ---
    d.record(
        "consecutive_losses",
        account.consecutive_losses < cfg.max_consecutive_losses,
        "max_consecutive_losses_reached",
    )
    if cfg.cooldown_bars_after_loss > 0:
        d.record(
            "cooldown",
            account.bars_since_last_loss >= cfg.cooldown_bars_after_loss,
            "cooldown_active_after_loss",
        )

    # --- margin ---
    if proposal.margin_required > 0:
        d.record(
            "free_margin",
            proposal.margin_required <= account.free_margin + 1e-9,
            "insufficient_free_margin",
        )
        new_util = (
            (account.used_margin + proposal.margin_required) / account.equity
            if account.equity > 0
            else 1.0
        )
        d.record(
            "margin_utilization",
            new_util <= cfg.max_margin_utilization + 1e-9,
            "margin_utilization_exceeded",
        )

    # --- execution conditions ---
    d.record(
        "spread",
        proposal.spread_frac <= max_spread_frac + 1e-9,
        f"spread {proposal.spread_frac:.4f} exceeds {max_spread_frac}",
    )
    d.record(
        "slippage",
        proposal.slippage_frac <= max_slippage_frac + 1e-9,
        f"slippage {proposal.slippage_frac:.4f} exceeds {max_slippage_frac}",
    )
    d.record("positive_qty", proposal.qty > 0, "non_positive_quantity")

    return d


def is_trading_halted(account: AccountState, cfg: RiskConfig) -> List[str]:
    """Return account-level halt reasons (new entries blocked) if any."""
    halts: List[str] = []
    if account.start_of_day_equity > 0:
        day_loss = -account.realized_pnl_today / account.start_of_day_equity
        if day_loss >= cfg.daily_loss_limit:
            halts.append("daily_loss_limit")
    if account.consecutive_losses >= cfg.max_consecutive_losses:
        halts.append("max_consecutive_losses")
    if not account.data_fresh:
        halts.append("market_data_stale")
    return halts
