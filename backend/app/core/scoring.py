"""Explainable, deterministic 0-100 setup-quality score.

Each component contributes up to a configured maximum. Missing evidence scores
zero (never a free full mark), correlated signals are not double counted, and a
risk rejection overrides the score entirely at the engine level.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .config import ScoreConfig


@dataclass
class ScoreBreakdown:
    components: Dict[str, float] = field(default_factory=dict)
    total: float = 0.0

    def as_dict(self) -> dict:
        return {"components": self.components, "total": round(self.total, 2)}


@dataclass
class ScoreInputs:
    htf_aligned: bool = False
    htf_partial: bool = False
    bos_confirmed: bool = False
    bos_recent: bool = False
    displacement_strength: float = 0.0   # 0..2 from displacement engine
    has_fvg: bool = False
    fvg_overlaps_zone: bool = False
    zone_fresh: bool = False
    zone_touches: int = 0
    entry_confirmed: bool = False
    flip_confluence: bool = False
    reward_risk: float = 0.0
    rr_target: float = 3.0
    liquidity_ok: bool = False


def score_setup(inp: ScoreInputs, cfg: ScoreConfig) -> ScoreBreakdown:
    w = cfg.weights
    comp: Dict[str, float] = {}

    # Higher-timeframe alignment (full for aligned, partial credit otherwise).
    if inp.htf_aligned:
        comp["htf_alignment"] = w["htf_alignment"]
    elif inp.htf_partial:
        comp["htf_alignment"] = w["htf_alignment"] * 0.5
    else:
        comp["htf_alignment"] = 0.0

    # BOS / structure.
    bos = 0.0
    if inp.bos_confirmed:
        bos += w["bos_structure"] * 0.7
    if inp.bos_recent:
        bos += w["bos_structure"] * 0.3
    comp["bos_structure"] = min(w["bos_structure"], bos)

    # Displacement quality (strength normalized to 0..1 against 1.5x baseline).
    comp["displacement"] = min(1.0, inp.displacement_strength / 1.5) * w["displacement"]

    # FVG / imbalance.
    fvg = 0.0
    if inp.has_fvg:
        fvg += w["fvg"] * 0.6
        if inp.fvg_overlaps_zone:
            fvg += w["fvg"] * 0.4
    comp["fvg"] = min(w["fvg"], fvg)

    # Zone freshness / quality.
    if inp.zone_fresh:
        comp["zone_quality"] = w["zone_quality"]
    elif inp.zone_touches == 1:
        comp["zone_quality"] = w["zone_quality"] * 0.5
    else:
        comp["zone_quality"] = 0.0

    # Entry confirmation.
    comp["entry_confirmation"] = w["entry_confirmation"] if inp.entry_confirmed else 0.0

    # Flip-zone confluence.
    comp["flip_confluence"] = w["flip_confluence"] if inp.flip_confluence else 0.0

    # Reward-to-risk feasibility (scaled toward the configured target).
    if inp.reward_risk <= 0 or inp.rr_target <= 0:
        comp["rr_feasibility"] = 0.0
    else:
        comp["rr_feasibility"] = min(1.0, inp.reward_risk / inp.rr_target) * w["rr_feasibility"]

    # Liquidity / execution conditions.
    comp["liquidity"] = w["liquidity"] if inp.liquidity_ok else 0.0

    total = sum(comp.values())
    return ScoreBreakdown(components={k: round(v, 2) for k, v in comp.items()}, total=total)
