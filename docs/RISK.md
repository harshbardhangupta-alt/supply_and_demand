# Risk management &amp; safety

The risk engine (`backend/app/core/risk.py`) is the single authoritative gate:
**every** order — scanner, paper, backtest, live — passes through
`risk.evaluate()`. It is deterministic and independent of the scanner and the
optional AI service, so it keeps protecting the account even when those fail. A
risk rejection is absolute and overrides any setup score.

## Per-order checks

| Check | Default |
|---|---|
| Market data fresh | required |
| Broker connected (live) | required |
| Risk per trade ≤ hard cap | 1% hard cap (0.5% default) |
| Reward:risk ≥ minimum | 1:3 |
| Max open positions | 10 |
| Max positions per instrument | 1 |
| Aggregate open risk | 6% of equity |
| Daily loss limit | 2% of start-of-day equity |
| Weekly loss limit | 5% |
| Max consecutive losses | 5 |
| Margin utilization / free margin | 80% max util |
| Spread / slippage | per-config caps |
| Positive quantity | required |

`is_trading_halted()` reports account-level halts (daily loss hit, consecutive
losses, stale data) that block new entries.

## Behaviour when a limit is reached

1. Reject new entries.
2. Cancel pending entry orders where appropriate (emergency stop).
3. Keep monitoring and protecting existing positions.
4. Record the event (risk events + audit log).
5. Surface it to the user.

Hitting a limit does **not** auto-close open positions. Emergency liquidation is
a separate, explicit, confirmed action (`POST /api/trading/liquidate`).

## Position sizing &amp; the hard cap

Configuration changes can never raise per-trade risk above
`max_risk_per_trade` — `PUT /api/settings/config` clamps `risk_per_trade` to the
cap (see `test_api.py::test_config_risk_cap_enforced`). Changing config never
silently increases risk on an already-open trade.

## Live-trading safeguards

Live is disabled by default (`SMC_LIVE_TRADING_ENABLED=false`). Enabling requires:
server config on, admin role, explicit confirmation, and a configured broker.
The intended pre-flight sequence (broker connection, account identity, instrument
mapping, data freshness, risk limits, protective-order capability, explicit
confirmation, audit record) is documented in the code and the trading page; the
reference deployment ships with live disabled and the broker adapters as
scaffolds, so nothing can route a real order without deliberate configuration.

## What the emergency stop can and cannot guarantee

The emergency stop disables new entries and *requests* cancellation of pending
entry orders. During a broker/network outage, cancellation cannot be guaranteed;
the system surfaces unresolved state rather than implying success. It never
claims an order filled or cancelled without broker confirmation.
