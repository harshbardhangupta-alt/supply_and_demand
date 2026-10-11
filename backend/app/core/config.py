"""Strategy configuration objects.

Every magic number in the engine lives here so configurations can be versioned,
persisted, linked to generated signals, and A/B tested. Defaults follow the
institutional S&D / SMC policy described in the project specification.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List

from .candles import Timeframe


class ZoneMode(str, Enum):
    WICK = "wick"            # full wick-to-wick boundaries
    BODY = "body"           # candle body only
    HYBRID = "hybrid"       # distal=wick, proximal=body


class EntryModel(str, Enum):
    NORMAL = "normal"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"


class BreakType(str, Enum):
    CLOSE = "close"         # structural break requires candle close beyond level
    WICK = "wick"           # a wick beyond the level breaks structure


@dataclass
class SwingConfig:
    left: int = 2
    right: int = 2
    min_swing_atr_frac: float = 0.0   # minimum pivot prominence as fraction of ATR
    atr_period: int = 14


@dataclass
class StructureConfig:
    break_type: BreakType = BreakType.CLOSE
    # A CHOCH requires breaking a swing that is meaningful, not every micro swing.
    min_break_atr_frac: float = 0.1


@dataclass
class DisplacementConfig:
    body_atr_mult: float = 1.2        # body must exceed this * ATR
    min_body_to_range: float = 0.5    # body / range
    min_close_strength: float = 0.6   # close position within range (bull) / 1-pos (bear)
    min_sequence: int = 1             # consecutive directional candles
    require_bos: bool = True
    max_bars_to_bos: int = 5          # displacement -> structural break window
    atr_period: int = 14


@dataclass
class FVGConfig:
    min_gap_atr_frac: float = 0.05    # minimum gap size relative to ATR
    min_gap_ticks: int = 1
    require_for_zone: bool = False    # require an FVG inside/near a validated zone


@dataclass
class ZoneConfig:
    mode: ZoneMode = ZoneMode.WICK
    require_fvg: bool = False
    require_bos: bool = True
    max_touches: int = 1              # freshness: how many prior touches allowed
    allow_once_touched: bool = False
    expiry_bars: int = 500            # zone expires if untouched for this many bars
    invalidation_break: BreakType = BreakType.CLOSE


@dataclass
class EntryConfig:
    model: EntryModel = EntryModel.NORMAL
    # Aggressive limit placement inside the zone: 0.0 = proximal, 1.0 = distal.
    zone_entry_fraction: float = 0.5
    order_expiry_bars: int = 48
    max_spread_frac: float = 0.0015   # max spread as fraction of price
    max_slippage_frac: float = 0.002
    max_distance_atr: float = 1.0     # max distance of price from planned entry
    # Adverse-momentum rejection for aggressive entries.
    adverse_momentum_atr: float = 1.5
    allow_reentry: bool = False
    confirmation_patterns: List[str] = field(
        default_factory=lambda: ["engulfing"]
    )


@dataclass
class ScoreConfig:
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "htf_alignment": 20.0,
            "bos_structure": 15.0,
            "displacement": 15.0,
            "fvg": 10.0,
            "zone_quality": 10.0,
            "entry_confirmation": 10.0,
            "flip_confluence": 10.0,
            "rr_feasibility": 5.0,
            "liquidity": 5.0,
        }
    )
    min_score: float = 70.0
    high_quality: float = 80.0


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.005          # 0.5%
    max_risk_per_trade: float = 0.01       # hard cap 1%
    min_reward_risk: float = 3.0           # 1:3 minimum
    max_open_positions: int = 10
    max_positions_per_instrument: int = 1
    max_aggregate_open_risk: float = 0.06  # 6% of equity across open positions
    daily_loss_limit: float = 0.02         # 2% of start-of-day equity
    weekly_loss_limit: float = 0.05
    max_consecutive_losses: int = 5
    max_margin_utilization: float = 0.8
    cooldown_bars_after_loss: int = 0
    sl_buffer_atr_frac: float = 0.1        # stop buffer beyond distal boundary


@dataclass
class TimeframeConfig:
    bias: Timeframe = Timeframe.W1
    structure: Timeframe = Timeframe.D1
    zones: Timeframe = Timeframe.H4
    intermediate: Timeframe = Timeframe.H1
    setup: Timeframe = Timeframe.M15
    execution: Timeframe = Timeframe.M5


@dataclass
class StrategyConfig:
    """Complete, versionable strategy configuration."""

    name: str = "default"
    version: int = 1
    direction: str = "both"   # "long", "short", or "both"
    # Only recent structure is relevant to SMC; capping the analysis window
    # keeps live scanning and per-bar backtesting fast and bounded.
    max_lookback: int = 400
    swing: SwingConfig = field(default_factory=SwingConfig)
    structure: StructureConfig = field(default_factory=StructureConfig)
    displacement: DisplacementConfig = field(default_factory=DisplacementConfig)
    fvg: FVGConfig = field(default_factory=FVGConfig)
    zone: ZoneConfig = field(default_factory=ZoneConfig)
    entry: EntryConfig = field(default_factory=EntryConfig)
    score: ScoreConfig = field(default_factory=ScoreConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    timeframes: TimeframeConfig = field(default_factory=TimeframeConfig)

    def to_dict(self) -> dict:
        return asdict(self)


def indian_equity_config() -> StrategyConfig:
    """Buy-only Nifty 500 policy (weekly bias, daily/4H confirmation)."""
    cfg = StrategyConfig(name="indian_equity_buy_only", direction="long")
    cfg.timeframes = TimeframeConfig(
        bias=Timeframe.W1,
        structure=Timeframe.D1,
        zones=Timeframe.H4,
        intermediate=Timeframe.H1,
        setup=Timeframe.M15,
        execution=Timeframe.M5,
    )
    return cfg


def forex_config() -> StrategyConfig:
    """Two-sided forex/metal policy with an intraday hierarchy."""
    cfg = StrategyConfig(name="forex_both", direction="both")
    cfg.timeframes = TimeframeConfig(
        bias=Timeframe.D1,
        structure=Timeframe.H4,
        zones=Timeframe.H1,
        intermediate=Timeframe.M15,
        setup=Timeframe.M15,
        execution=Timeframe.M5,
    )
    return cfg
