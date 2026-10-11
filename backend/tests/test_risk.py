from app.core.config import RiskConfig
from app.core.risk import (
    AccountState,
    OpenPositionRisk,
    TradeProposal,
    evaluate,
    is_trading_halted,
)


def _account(**kw):
    base = dict(equity=100_000, start_of_day_equity=100_000,
               start_of_week_equity=100_000, free_margin=100_000)
    base.update(kw)
    return AccountState(**base)


def _proposal(**kw):
    base = dict(symbol="RELIANCE", direction="long", risk_amount=500.0,
               reward_risk=3.0, qty=50, notional=50_000)
    base.update(kw)
    return TradeProposal(**base)


def test_valid_proposal_approved():
    d = evaluate(_proposal(), _account(), RiskConfig())
    assert d.approved, d.reasons


def test_reward_risk_below_min_rejected():
    d = evaluate(_proposal(reward_risk=2.0), _account(), RiskConfig())
    assert not d.approved and not d.checks["reward_risk"]


def test_risk_per_trade_cap_enforced():
    d = evaluate(_proposal(risk_amount=2000.0), _account(), RiskConfig())
    assert not d.approved and not d.checks["risk_per_trade"]


def test_stale_data_blocks_entry():
    d = evaluate(_proposal(), _account(data_fresh=False), RiskConfig())
    assert not d.approved and not d.checks["data_fresh"]


def test_daily_loss_limit_blocks_entry():
    acc = _account(realized_pnl_today=-2500)  # -2.5% > 2% limit
    d = evaluate(_proposal(), acc, RiskConfig())
    assert not d.approved and not d.checks["daily_loss_limit"]


def test_max_positions_per_instrument():
    acc = _account(open_positions=[OpenPositionRisk("RELIANCE", 500)])
    d = evaluate(_proposal(), acc, RiskConfig())
    assert not d.approved and not d.checks["max_per_instrument"]


def test_aggregate_open_risk_limit():
    positions = [OpenPositionRisk(f"S{i}", 1000) for i in range(6)]
    acc = _account(open_positions=positions)
    d = evaluate(_proposal(symbol="NEW", risk_amount=1000), acc, RiskConfig())
    assert not d.checks["aggregate_open_risk"]


def test_trading_halt_detection():
    acc = _account(consecutive_losses=5)
    halts = is_trading_halted(acc, RiskConfig())
    assert "max_consecutive_losses" in halts
