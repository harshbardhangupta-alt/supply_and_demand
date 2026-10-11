# Institutional Supply &amp; Demand (SMC) Trading Engine

A multi-market, risk-controlled automated trading platform built on Institutional
Supply &amp; Demand / Smart-Money-Concepts methodology. The **Nifty 500** is the
mandatory Indian equity universe, with separate configurable universes for
Forex, Metals, Crude/Commodities and Indian Indices.

This is a working application — a deterministic strategy engine, a risk engine,
paper trading, a look-ahead-safe backtester, a FastAPI backend with a REST + WebSocket
API, a SQLAlchemy/SQLite/Postgres data layer, and a Next.js/TypeScript/Tailwind
trading terminal — not a mockup.

> **Honesty notes (read these).**
> - Live trading is **disabled by default**. The **Dhan** adapter now makes real
>   DhanHQ v2 calls (candles, fund limit, orders, positions) once you add your
>   credentials on the in-app **Connections** page; the MetaTrader 5 adapter is a
>   scaffold. Neither fabricates a connection, price, balance or fill — unconfigured
>   or failing calls raise a clear error.
> - The default market-data provider is a **synthetic generator** so the whole
>   system runs offline. Switch to the **Dhan live feed** from Connections once
>   configured. Synthetic data is always labelled as such in the UI and API. No
>   simulated price, balance, order or P&amp;L is ever presented as real.
> - **OpenAI** research/analysis is optional (add a key on Connections). It only
>   explains the deterministic engine's output — it never computes prices, levels,
>   sizing or risk, and the platform works fully without it.
> - The bundled Nifty 500 list is a **partial seed snapshot** of well-known
>   constituents, clearly flagged. The full list is fetched at runtime from NSE
>   (`/api/universe/nifty500/refresh`); on failure the last verified list is kept.
> - No performance figure is claimed. Backtests on synthetic data show the engine
>   *runs correctly*, not that it is profitable.

---

## What's implemented

| Area | Status |
|---|---|
| Market structure (swings, HH/HL/LH/LL, BOS, CHOCH, MSS, trend) | ✅ engine + tests |
| Displacement detection | ✅ engine + tests |
| Fair Value Gaps (3-candle, fill tracking) | ✅ engine + tests |
| Supply/Demand zones + lifecycle state machine | ✅ engine + tests |
| Multi-timeframe analysis (weekly→execution) | ✅ |
| 3 entry models (Normal, Conservative, Aggressive Limit) | ✅ engine + tests |
| 0–100 explainable setup score | ✅ engine + tests |
| Instrument-aware position sizing (equity/forex/metal/energy) | ✅ engine + tests |
| Central account risk engine | ✅ engine + tests |
| Nifty 500 universe manager (refresh, point-in-time membership, filters) | ✅ + tests |
| Synthetic data adapter + adapter interface | ✅ |
| Dhan live data adapter (DhanHQ v2 candles, scrip-master mapping, resampling) | ✅ |
| In-app credential management (Dhan + OpenAI) with 24h token rotation & tests | ✅ + tests |
| OpenAI research/analysis (optional, explains engine output) | ✅ |
| Paper broker (idempotent orders, SL/TP, fills) | ✅ + tests |
| Dhan broker (account/orders/positions, v2 REST) · MT5 scaffold | ✅ Dhan / scaffold MT5 |
| Look-ahead-safe backtester (reuses live pipeline) | ✅ + tests |
| Analytics (win rate, PF, expectancy, drawdown, breakdowns) | ✅ + tests |
| FastAPI REST API (29 endpoints) + WebSocket | ✅ + integration tests |
| Auth (PBKDF2 + HMAC tokens, role gating) | ✅ |
| SQLAlchemy models + Alembic migrations | ✅ |
| Next.js terminal — 14 pages (black + neon-green theme) wired to the API | ✅ builds clean |
| Docker + docker-compose (Postgres) | ✅ |

**Tests: 62 passing** (`scripts/test.sh`). Frontend type-checks and builds cleanly.

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for what is intentionally scaffolded.

---

## Quick start (local, offline, no credentials needed)

```bash
# 1. Setup (creates .venv, installs backend + frontend deps, copies .env files)
./scripts/setup.sh

# 2. Start the backend (http://localhost:8005, docs at /docs)
./scripts/dev_backend.sh

# 3. In another terminal, start the frontend (http://localhost:3005)
./scripts/dev_frontend.sh
```

Then open <http://localhost:3005>. Sign in with `admin` / `admin` (change via
`SMC_ADMIN_USERNAME` / `SMC_ADMIN_PASSWORD`).

### With Docker (Postgres)

```bash
cd infra
docker compose up --build
# frontend -> http://localhost:3005 , backend -> http://localhost:8005
```

### Connecting Dhan &amp; OpenAI (real data + AI)

Open **Connections** in the sidebar (sign in as admin first):

- **Dhan** — enter your **Client ID** (fixed) and **Access Token**. Dhan tokens
  expire ~every 24h, so paste a fresh token here daily; the page shows the token
  age and time remaining. Click **Test connection** (hits Dhan's fund-limit
  endpoint), then switch the **market-data feed** to *Dhan (live)*. Credentials
  are stored server-side and never exposed to the browser.
- **OpenAI** — paste an API key and model (default `gpt-4o-mini`) and **Test
  connection**. Then use **✦ Analyze** on the Chart page for a natural-language
  explanation of a setup.

Everything is stored in the backend DB and survives restarts. These calls go
directly from your backend to Dhan/OpenAI, so they work from your own machine
(a locked-down sandbox may block the outbound hosts).

### Run the tests

```bash
./scripts/test.sh        # backend pytest (no live credentials required)
cd frontend && npm run typecheck && npm run build
```

---

## Architecture (bird's eye)

```
frontend/ (Next.js 14, TS, Tailwind)  ──REST/WS──►  backend/ (FastAPI)
                                                      │
                     ┌────────────────────────────────┼─────────────────────────────┐
                     ▼                                 ▼                              ▼
             core/ strategy engine            risk.py (authoritative)         data adapters
   market_structure · displacement · fvg      ← every order passes here       synthetic / Dhan* / MT5*
   zones · mtf · entries · scoring · sizing                                    (*scaffolded)
                     │
      ┌──────────────┼───────────────┬──────────────┬───────────────┐
      ▼              ▼               ▼              ▼               ▼
  scanner       paper engine     backtester      universe        brokers
 (per-symbol    (PaperBroker)   (bar-by-bar,    (Nifty 500)     (paper + scaffolds)
  setups)                        no look-ahead)
```

The **same `app.core.engine.analyze()` pipeline** powers the scanner, paper
trading and the backtester — there is no separate, divergent strategy code.

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — modules, data flow, services
- [docs/STRATEGY.md](docs/STRATEGY.md) — how each SMC concept is computed
- [docs/RISK.md](docs/RISK.md) — the risk engine and safety model
- [docs/BROKERS.md](docs/BROKERS.md) — Dhan &amp; MT5 setup, symbol mapping
- [docs/API.md](docs/API.md) — endpoint reference
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)

---

## Default Indian-equity policy

Universe Nifty 500 · **buy-only** · weekly bias · daily/4H confirmation · 1H
intermediate · 15M setup · 5M execution · 0.5% risk/trade (1% hard cap) · min
1:3 reward:risk · paper on, live off. All configurable (risk is always clamped
to the hard cap). A buy-only equity config does **not** make Forex/Metals/Crude
buy-only — each universe has its own config.

---

## Safety model

- Live trading disabled by default and gated behind server config + explicit
  confirmation + role check.
- **Emergency stop** disables new entries and cancels pending entry orders. It
  does **not** auto-liquidate open positions — liquidation is a separate confirmed
  action.
- When market data is stale or the broker is disconnected, new entries are blocked.
- The risk engine keeps running even if the scanner or (optional) AI explanation
  service fails.

## Security

Never commit real secrets. `.env` is gitignored; `.env.example` ships with
placeholders. The demo auth is self-contained (PBKDF2 + HMAC) — swap in a vetted
library and a real secret manager for production, and change the default admin
password.

## License

Provided as-is for educational and research use. Trading involves substantial
risk of loss. Nothing here is financial advice.
