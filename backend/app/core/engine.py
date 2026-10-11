"""Strategy orchestration: run the full SMC pipeline for one instrument.

This is the single analysis entry point shared by the scanner, paper trading,
live trading and the backtester. Given per-timeframe candle data it produces a
fully-explained :class:`SetupResult` — biases, zone, entry/stop/target, size,
risk decision, score and the exact rejection reason when not tradable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .candles import Candle, Timeframe, atr, ensure_closed
from .config import StrategyConfig
from .displacement import detect_displacements
from .entries import EntrySignal, evaluate_entry
from .fvg import detect_fvgs
from .instruments import InstrumentSpec
from .market_structure import (
    Bias,
    EventType,
    classify_trend,
    detect_structure,
)
from .mtf import alignment_for, timeframe_bias
from .risk import AccountState, RiskConfig, RiskDecision, TradeProposal, evaluate as risk_evaluate
from .scoring import ScoreBreakdown, ScoreInputs, score_setup
from .sizing import SizingResult, size_position
from .zones import Zone, ZoneDirection, active_zones, build_zones


@dataclass
class SetupResult:
    symbol: str
    tradable: bool
    direction: Optional[str] = None
    biases: Dict[str, str] = field(default_factory=dict)
    zone: Optional[Zone] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    reward_risk: Optional[float] = None
    qty: Optional[float] = None
    risk_amount: Optional[float] = None
    risk_pct: Optional[float] = None
    order_type: Optional[str] = None
    entry_model: Optional[str] = None
    score: float = 0.0
    score_breakdown: Optional[dict] = None
    bos: Optional[str] = None
    fvg: Optional[str] = None
    zone_state: Optional[str] = None
    zone_fresh: Optional[bool] = None
    rejection_reason: Optional[str] = None
    risk_checks: Dict[str, bool] = field(default_factory=dict)
    current_price: Optional[float] = None


def _nearest_tradable_zone(
    zones: Sequence[Zone], direction: str, price: float
) -> Optional[Zone]:
    want = ZoneDirection.DEMAND if direction == "long" else ZoneDirection.SUPPLY
    cands = active_zones(zones, want)
    if not cands:
        return None
    if direction == "long":
        # Demand zones at or below price; prefer the closest below, then deepest
        below = [z for z in cands if z.top <= price * 1.001]
        pool = below or cands
        return max(pool, key=lambda z: z.top)  # closest below price
    else:
        above = [z for z in cands if z.bottom >= price * 0.999]
        pool = above or cands
        return min(pool, key=lambda z: z.bottom)


def analyze(
    spec: InstrumentSpec,
    data: Dict[Timeframe, List[Candle]],
    cfg: StrategyConfig,
    account: AccountState,
    spread_frac: float = 0.0,
    slippage_frac: float = 0.0,
) -> SetupResult:
    tf = cfg.timeframes
    res = SetupResult(symbol=spec.symbol, tradable=False)

    lb = cfg.max_lookback
    exec_candles = ensure_closed(data.get(tf.execution, []))[-lb:]
    zone_candles = ensure_closed(data.get(tf.zones, []))[-lb:]
    if len(zone_candles) < 20 or len(exec_candles) < 5:
        res.rejection_reason = "insufficient_data"
        return res
    price = exec_candles[-1].close
    res.current_price = price

    # 1. Multi-timeframe bias.
    biases: Dict[Timeframe, Bias] = {}
    for key in (tf.bias, tf.structure, tf.zones, tf.intermediate):
        series = ensure_closed(data.get(key, []))[-lb:]
        biases[key] = timeframe_bias(series, cfg.swing, cfg.structure)
    res.biases = {k.value: v.value for k, v in biases.items()}

    # 2. Decide candidate direction(s) from policy + bias.
    directions = _candidate_directions(cfg, biases, tf)
    if not directions:
        res.rejection_reason = "no_directional_bias"
        return res

    best: Optional[SetupResult] = None
    for direction in directions:
        cand = _analyze_direction(
            spec, data, cfg, account, direction, biases, price,
            zone_candles, exec_candles, spread_frac, slippage_frac,
        )
        if best is None or cand.score > best.score:
            best = cand
    return best or res


def _candidate_directions(cfg, biases, tf) -> List[str]:
    htf = biases.get(tf.bias, Bias.INSUFFICIENT)
    struct = biases.get(tf.structure, Bias.INSUFFICIENT)
    out: List[str] = []
    allow_long = cfg.direction in ("long", "both")
    allow_short = cfg.direction in ("short", "both")

    def supports(b, want) -> bool:
        if want == "long":
            return b in (Bias.BULLISH, Bias.TRANSITIONAL)
        return b in (Bias.BEARISH, Bias.TRANSITIONAL)

    if allow_long and (supports(htf, "long") or supports(struct, "long")):
        out.append("long")
    if allow_short and (supports(htf, "short") or supports(struct, "short")):
        out.append("short")
    return out


def _analyze_direction(
    spec, data, cfg, account, direction, biases, price,
    zone_candles, exec_candles, spread_frac, slippage_frac,
) -> SetupResult:
    tf = cfg.timeframes
    res = SetupResult(symbol=spec.symbol, tradable=False, direction=direction,
                      current_price=price)
    res.biases = {k.value: v.value for k, v in biases.items()}

    # 3. Structure + displacement + FVG + zones on the zone timeframe.
    state = detect_structure(zone_candles, cfg.swing, cfg.structure)
    disps = detect_displacements(zone_candles, cfg.displacement)
    fvgs = detect_fvgs(zone_candles, cfg.fvg, spec.tick_size)
    fvg_idx = {f.index for f in fvgs}
    zones = build_zones(zone_candles, disps, cfg.zone, fvg_idx)

    res.bos = _bos_status(state)
    res.fvg = "present" if fvgs else "none"

    zone = _nearest_tradable_zone(zones, direction, price)
    if zone is None:
        res.rejection_reason = "no_active_zone"
        return res
    res.zone = zone
    res.zone_state = zone.state.value
    res.zone_fresh = zone.is_fresh

    # 4. Entry evaluation on the execution timeframe.
    sig: EntrySignal = evaluate_entry(zone, exec_candles, cfg.entry)
    res.entry_model = cfg.entry.model.value
    res.order_type = sig.order_type

    entry_price = sig.entry_price if sig.triggered else (
        zone.proximal if direction == "long" else zone.proximal
    )
    # For a limit model the planned price is the limit even before trigger.
    if cfg.entry.model.value == "aggressive":
        from .entries import aggressive_limit_price
        entry_price = aggressive_limit_price(zone, cfg.entry)

    # 5. Stop and target.
    a = atr(zone_candles, cfg.displacement.atr_period) or (zone.height or spec.tick_size)
    buffer = max(spec.tick_size * spec.min_stop_distance_ticks, a * cfg.risk.sl_buffer_atr_frac)
    if direction == "long":
        stop = spec.round_price(zone.bottom - buffer)
        risk_dist = entry_price - stop
        target = _target_long(state, entry_price, risk_dist, cfg.risk.min_reward_risk, spec)
        reward = target - entry_price
    else:
        stop = spec.round_price(zone.top + buffer)
        risk_dist = stop - entry_price
        target = _target_short(state, entry_price, risk_dist, cfg.risk.min_reward_risk, spec)
        reward = entry_price - target

    if risk_dist <= 0:
        res.rejection_reason = "invalid_stop_distance"
        return res
    reward_risk = reward / risk_dist if risk_dist > 0 else 0.0
    res.entry = spec.round_price(entry_price)
    res.stop = stop
    res.target = spec.round_price(target)
    res.reward_risk = round(reward_risk, 2)

    # 6. Position sizing.
    sizing: SizingResult = size_position(
        spec, account.equity, cfg.risk.risk_per_trade, entry_price, stop
    )
    res.qty = sizing.qty
    res.risk_amount = sizing.actual_risk
    res.risk_pct = round(cfg.risk.risk_per_trade * 100, 3)

    # 7. Scoring.
    full_align, partial_align = alignment_for(
        direction, {k: biases[k] for k in (tf.bias, tf.structure, tf.intermediate) if k in biases}
    )
    score_inp = ScoreInputs(
        htf_aligned=full_align,
        htf_partial=partial_align,
        bos_confirmed=bool(state.events),
        bos_recent=_bos_recent(state, len(zone_candles)),
        displacement_strength=zone.displacement_strength,
        has_fvg=zone.has_fvg,
        fvg_overlaps_zone=zone.has_fvg,
        zone_fresh=zone.is_fresh,
        zone_touches=zone.touches,
        entry_confirmed=sig.confirmation or sig.triggered,
        flip_confluence=_flip_confluence(state, zone),
        reward_risk=reward_risk,
        rr_target=cfg.risk.min_reward_risk,
        liquidity_ok=spec.tradable and sizing.ok,
    )
    breakdown: ScoreBreakdown = score_setup(score_inp, cfg.score)
    res.score = round(breakdown.total, 2)
    res.score_breakdown = breakdown.as_dict()

    # 8. Risk engine (authoritative).
    proposal = TradeProposal(
        symbol=spec.symbol,
        direction=direction,
        risk_amount=sizing.actual_risk,
        reward_risk=reward_risk,
        qty=sizing.qty,
        notional=sizing.notional,
        spread_frac=spread_frac,
        slippage_frac=slippage_frac,
    )
    decision: RiskDecision = risk_evaluate(
        proposal, account, cfg.risk,
        max_spread_frac=cfg.entry.max_spread_frac,
        max_slippage_frac=cfg.entry.max_slippage_frac,
    )
    res.risk_checks = decision.checks

    # 9. Final eligibility — risk failure overrides score.
    if not sizing.ok:
        res.rejection_reason = sizing.reason or "sizing_failed"
        return res
    if not decision.approved:
        res.rejection_reason = "risk:" + ";".join(decision.reasons)
        return res
    if res.score < cfg.score.min_score:
        res.rejection_reason = f"score_below_threshold ({res.score} < {cfg.score.min_score})"
        return res
    if cfg.entry.model.value != "aggressive" and not sig.triggered:
        res.rejection_reason = f"entry_not_triggered ({sig.reason})"
        return res

    res.tradable = True
    return res


def _bos_status(state) -> str:
    if not state.events:
        return "none"
    last = state.events[-1]
    return f"{last.type.value}:{last.direction}"


def _bos_recent(state, n: int, window: int = 30) -> bool:
    if not state.events:
        return False
    return (n - 1 - state.events[-1].index) <= window


def _flip_confluence(state, zone: Zone) -> bool:
    """A broken structural level near the zone acting as flipped support/resist."""
    for ev in state.events[-6:]:
        if zone.bottom <= ev.level <= zone.top:
            return True
    return False


def _target_long(state, entry, risk_dist, min_rr, spec) -> float:
    rr_target = entry + min_rr * risk_dist
    # Nearest unbroken swing high above entry provides a structural objective.
    highs = [s.price for s in state.swings if s.kind.value == "high" and s.price > entry and not s.broken]
    if highs:
        structural = min(highs)
        if (structural - entry) / risk_dist >= min_rr:
            return structural
    return rr_target


def _target_short(state, entry, risk_dist, min_rr, spec) -> float:
    rr_target = entry - min_rr * risk_dist
    lows = [s.price for s in state.swings if s.kind.value == "low" and s.price < entry and not s.broken]
    if lows:
        structural = max(lows)
        if (entry - structural) / risk_dist >= min_rr:
            return structural
    return rr_target
