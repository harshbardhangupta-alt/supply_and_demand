# API reference

Base URL `http://localhost:8000`. Interactive docs at `/docs` (Swagger) and
`/redoc`. Auth is a bearer token from `/api/auth/login`; endpoints that change
state or expose the audit trail require it (admin role for universe refresh,
config changes, liquidation, live enable).

## Auth
| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/login` | form `username`/`password` → `{access_token, role}` |
| GET | `/api/auth/me` | current user |

## Overview & health
| Method | Path | Auth |
|---|---|---|
| GET | `/api/health` | — |
| GET | `/api/overview` | — |
| GET | `/api/system/health` | — |

## Instruments & universe
| Method | Path | Auth |
|---|---|---|
| GET | `/api/instruments?universe=&limit=` | — |
| GET | `/api/universe/nifty500` | — |
| POST | `/api/universe/nifty500/refresh` | admin |

## Scanner & signals
| Method | Path | Auth |
|---|---|---|
| GET | `/api/scanner/{universe}?limit=&refresh=` | — |
| GET | `/api/signals?universe=` | — |

`{universe}` ∈ `nifty500 · indian_indices · forex · metals · commodities`.
Every row includes per-timeframe bias, zone, BOS/FVG, score, entry/stop/target,
reward:risk, quantity, risk%, eligibility and — when not eligible — the exact
`rejection_reason`.

## Chart & zones
| Method | Path |
|---|---|
| GET | `/api/chart/{symbol}?timeframe=&count=` |
| GET | `/api/zones/{symbol}?timeframe=&count=` |

Chart returns candles plus overlays: zones, FVGs, swings, structure events.

## Trading controls
| Method | Path | Auth |
|---|---|---|
| POST | `/api/trading/start` · `/stop` | user |
| POST | `/api/trading/auto-entry` `{enabled}` | user |
| POST | `/api/trading/paper/run?universe=&limit=` | user |
| POST | `/api/trading/emergency-stop` | user |
| POST | `/api/trading/liquidate` | admin |
| POST | `/api/trading/live/enable` `{confirm}` | admin (403 unless server-enabled) |

## Positions / orders / trades
| Method | Path |
|---|---|
| GET | `/api/positions` |
| GET | `/api/orders` |
| GET | `/api/trades` |

## Backtest & analytics
| Method | Path | Auth |
|---|---|---|
| POST | `/api/backtest` `{symbol,universe,bars,warmup,…}` | user |
| GET | `/api/analytics` | — |

## Settings & audit
| Method | Path | Auth |
|---|---|---|
| GET | `/api/settings` | — |
| PUT | `/api/settings/config` `{universe, risk_per_trade, …}` | admin (risk clamped to cap) |
| GET | `/api/audit` | user |
| GET | `/api/risk/events` | user |

## WebSocket
| Path | Payload |
|---|---|
| `/ws/stream` | `{type:"tick", overview, positions}` every ~3s |
