# Limitations &amp; what is intentionally scaffolded

This project is honest about its boundaries. Everything below is a deliberate,
documented limitation — not a hidden gap.

## Live broker execution is scaffolded
`Dhan` and `MT5` adapters implement the full broker interface but stay disabled
without credentials/terminals and raise `BrokerError` instead of fabricating a
session, price, balance or fill. Enabling them requires implementing the marked
REST/terminal calls against current provider docs in a configured deployment.
See [BROKERS.md](BROKERS.md).

## Default data is synthetic
The default provider is a deterministic synthetic generator so the whole system
runs offline. It is always reported as `FeedMode.SYNTHETIC` in the API and UI.
Real data requires a configured provider (Dhan historical/live, MT5, or another
adapter you add). No synthetic value is ever presented as real.

## Nifty 500 list is a partial seed until refreshed
The bundled CSV contains ~80 well-known real constituents, clearly flagged as a
fallback snapshot. The authoritative full list is fetched at runtime from NSE
(`/api/universe/nifty500/refresh`). Point-in-time membership is preserved from
the moment it is recorded; deep historical membership (for multi-year
survivorship-safe backtests) is only as complete as the data you feed in — this
limitation is reported rather than hidden.

## Backtester performance &amp; fills
The backtester re-runs the engine per bar (bounded by `max_lookback`). It models
market/limit/stop orders, SL/TP, fees and slippage, and uses a conservative
intrabar assumption (stop before target when a bar spans both). It does not model
every microstructure effect (partial fills beyond the simple case, queue
position, latency). Lower-timeframe intrabar resolution is a documented
extension point.

## No performance claims
No win rate or return figure is claimed. Backtests on synthetic data demonstrate
the engine runs correctly and avoids look-ahead/survivorship bias to the extent
the data supports — they are not evidence of profitability.

## AI assistance is optional and absent by default
The architecture keeps AI strictly optional (explanations only) and the
deterministic engine computes every number. No AI service is wired in by default;
its absence never disables the risk engine or core trading.

## Auth is demo-grade
Self-contained PBKDF2 + HMAC tokens with an in-memory admin user seeded from env.
For production, use a vetted auth library, DB-backed users, a real secret
manager, and change the default credentials.

## Options sizing
Instrument specs include an options asset class and the sizing module is
asset-class aware, but a full options pricing/greeks model is not implemented.
Options execution is out of scope for the reference build.
