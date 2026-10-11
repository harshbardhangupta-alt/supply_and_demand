# Strategy: how each SMC concept is computed

All definitions are deterministic and configurable via `StrategyConfig`
(`backend/app/core/config.py`). None of them infer institutional intent — they
are price-action rules.

## Market structure (`market_structure.py`)

- **Swing high/low** — fractal pivot: `high[i]` strictly greater than the `left`
  candles before and `right` after (lows symmetric). Confirmed at `i + right`.
- **HH / HL / LH / LL** — each swing labelled vs. the previous same-kind swing.
- **BOS (Break of Structure)** — continuation break: price breaks the active
  confirmed swing in the direction of the prevailing bias (candle-**close** by
  default; wick mode optional).
- **CHOCH (Change of Character)** — first break against the prevailing bias
  (e.g. in an uptrend, closing below the protected higher-low).
- **MSS** — a CHOCH is treated as a market-structure shift / transition; trend
  classification returns `TRANSITIONAL` immediately after one.
- **Trend** — `bullish / bearish / neutral / transitional / insufficient`.

## Displacement (`displacement.py`)

A candle (or run) qualifies when, relative to ATR:
`body ≥ body_atr_mult·ATR`, `body/range ≥ min_body_to_range`, close near the
directional extreme (`min_close_strength`), correct direction. Defaults:
1.2×ATR body, 0.6 close strength. Strength is normalized to a 0–2 score used by
the setup score.

## Fair Value Gap (`fvg.py`)

Three-candle model. Bullish: `candle1.high < candle3.low`; bearish:
`candle1.low > candle3.high`. Minimum gap = `max(min_gap_ticks·tick, ATR·frac)`.
Fill percentage is tracked from subsequent candles (partial / full).

## Supply &amp; Demand zones (`zones.py`)

- **Demand** = last bearish candle before a qualifying bullish displacement.
- **Supply** = last bullish candle before a qualifying bearish displacement.
- **Boundaries** — `WICK` (wick-to-wick), `BODY`, or `HYBRID` (distal=wick,
  proximal=body). Distal is the far boundary (stop sits beyond it); proximal is
  the near one (price reaches first).
- **Lifecycle** — `DETECTED → VALIDATED → ACTIVE → TOUCHED →
  MITIGATED / INVALIDATED / EXPIRED`:
  - *Invalidated* when a closed candle closes beyond the distal boundary (a wick
    alone does not invalidate a close-based zone).
  - *Touched* counts discrete visits, not repeated bars inside.
  - *Mitigated* when touches exceed `max_touches` (freshness exhausted).
  - *Expired* when untouched for `expiry_bars`.

## Multi-timeframe (`mtf.py`)

Default hierarchy: Weekly bias · Daily structure · 4H zones · 1H intermediate ·
15M setup · 5M execution. Higher-timeframe alignment feeds the score; only
closed higher-timeframe candles are used.

## Entry models (`entries.py`)

- **Normal** — price enters the zone, then a closed candle closes back past the
  proximal boundary in the trade direction → market entry.
- **Conservative** — price enters the zone and a confirmation pattern closes
  (bullish/bearish engulfing or pin, defined mathematically) → market entry.
- **Aggressive Limit** — resting limit at a configurable level inside the zone
  (default midpoint). Rejected when price approaches the zone with excessive
  adverse momentum (`adverse_momentum_atr`). A limit may never fill — a touch
  does not guarantee a fill.

## Setup score (`scoring.py`)

| Component | Max |
|---|---:|
| HTF alignment | 20 |
| BOS / structure | 15 |
| Displacement quality | 15 |
| FVG / imbalance | 10 |
| Zone freshness/quality | 10 |
| Entry confirmation | 10 |
| Flip-zone confluence | 10 |
| Reward:risk feasibility | 5 |
| Liquidity/execution | 5 |

Default threshold 70 (80+ high quality). Weights and threshold configurable.
Missing evidence scores zero; a risk rejection overrides the score entirely.

## Stops, targets, sizing

- **Stop** — beyond the distal boundary plus a buffer
  (`max(tick·min_ticks, ATR·sl_buffer_frac)`).
- **Target** — nearest unbroken opposing swing if it yields ≥ min reward:risk,
  otherwise a fixed `min_rr` multiple. If no realistic target reaches the minimum
  the trade is rejected rather than faking an achievable target.
- **Sizing** — `sizing.py`: pip-based for forex/metals/energy
  (`pips × pip_value_per_lot × lots`), price-distance × contract multiplier for
  equities/futures. Quantity is rounded **down** to a tradable size; below the
  minimum → rejected.
