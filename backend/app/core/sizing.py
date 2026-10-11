"""Instrument-aware position sizing and stop/target computation.

Different asset classes require fundamentally different math. Pip-based products
(forex, metals, energy CFDs) size by pip value per lot; cash equities and
futures size by price distance * contract multiplier. A generic pip formula is
never applied to equities, and vice versa.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .instruments import InstrumentSpec


@dataclass
class SizingResult:
    qty: float
    risk_amount: float            # requested monetary risk
    actual_risk: float            # risk after rounding qty to a tradable size
    stop_distance: float
    notional: float
    ok: bool
    reason: Optional[str] = None


def monetary_loss_per_qty(spec: InstrumentSpec, price_distance: float) -> float:
    """Monetary loss for one tradable quantity unit over ``price_distance``."""
    if spec.is_pip_based:
        pips = price_distance / spec.pip_size
        # pip_value_per_lot is quoted per 1.0 standard lot.
        return pips * spec.pip_value_per_lot
    return price_distance * spec.contract_multiplier


def size_position(
    spec: InstrumentSpec,
    equity: float,
    risk_fraction: float,
    entry: float,
    stop: float,
    fee_fraction: float = 0.0,
) -> SizingResult:
    """Compute a tradable position size for a fixed fractional risk budget."""
    stop_distance = abs(entry - stop)
    risk_amount = max(0.0, equity) * max(0.0, risk_fraction)
    if stop_distance <= 0:
        return SizingResult(0, risk_amount, 0, 0, 0, False, "zero_stop_distance")
    if risk_amount <= 0:
        return SizingResult(0, risk_amount, 0, stop_distance, 0, False, "zero_risk_budget")

    loss_per_unit = monetary_loss_per_qty(spec, stop_distance)
    if loss_per_unit <= 0:
        return SizingResult(0, risk_amount, 0, stop_distance, 0, False, "zero_unit_loss")

    raw_qty = risk_amount / loss_per_unit
    qty = spec.round_qty(raw_qty)
    if qty <= 0:
        return SizingResult(
            0, risk_amount, 0, stop_distance, 0, False, "below_min_qty"
        )

    actual_risk = monetary_loss_per_qty(spec, stop_distance) * (
        qty / (1.0 if spec.is_pip_based else 1.0)
    )
    # For pip-based, loss scales linearly with lot qty.
    if spec.is_pip_based:
        actual_risk = (stop_distance / spec.pip_size) * spec.pip_value_per_lot * qty
    else:
        actual_risk = stop_distance * spec.contract_multiplier * qty

    notional = _notional(spec, entry, qty)
    fees = notional * fee_fraction
    actual_risk += fees
    return SizingResult(
        qty=qty,
        risk_amount=risk_amount,
        actual_risk=round(actual_risk, 4),
        stop_distance=stop_distance,
        notional=round(notional, 4),
        ok=True,
    )


def _notional(spec: InstrumentSpec, price: float, qty: float) -> float:
    if spec.is_pip_based:
        return price * qty * spec.contract_multiplier
    return price * qty * spec.contract_multiplier
