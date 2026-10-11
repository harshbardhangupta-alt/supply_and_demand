# Architecture

## Layers

```
backend/app/
  core/            Pure, deterministic strategy engine (no I/O)
    candles.py         Candle type, Timeframe, ATR, aggregation, validation
    instruments.py     InstrumentSpec + asset-class catalogue (sizing inputs)
    config.py          Versionable StrategyConfig (every tunable parameter)
    market_structure.py Swings, HH/HL/LH/LL, BOS, CHOCH, MSS, trend
    displacement.py    Statistical displacement detection
    fvg.py             3-candle Fair Value Gaps + fill tracking
    zones.py           Supply/Demand zones + lifecycle state machine
    mtf.py             Multi-timeframe bias + alignment
    entries.py         Normal / Conservative / Aggressive-limit entry models
    scoring.py         Explainable 0–100 setup score
    sizing.py          Instrument-aware position sizing
    risk.py            Central account risk engine (authoritative)
    engine.py          analyze(): orchestrates the full pipeline -> SetupResult
  data/            Market-data adapters (base interface + synthetic)
  brokers/         Broker interface + paper broker + Dhan/MT5 scaffolds
  universe/        Nifty 500 manager (constituents, membership, filters)
  backtest/        Event-driven, look-ahead-safe backtester
  paper/           Paper-trading engine (strategy + risk + paper broker)
  analytics/       Performance metrics from completed trades
  services/        Scanner (universe -> rows with rejection reasons)
  api/             FastAPI routers (auth, routes, ws)
  models.py        SQLAlchemy ORM
  db.py            Async engine/session + create_all
  runtime.py       In-process app state (adapter, universe, paper engine, configs)
  settings.py      Env-based settings
  security.py      PBKDF2 hashing + HMAC tokens + role gating
  main.py          FastAPI app factory + lifespan
```

## The one pipeline

`app.core.engine.analyze(spec, data, cfg, account)` is the single analysis entry
point. It is consumed identically by:

- **Scanner** (`services/scanner.py`) — one pass per instrument, returns a row
  (including rejected instruments with their exact reason).
- **Paper engine** (`paper/engine.py`) — same `analyze`, routes eligible setups
  to the `PaperBroker`.
- **Backtester** (`backtest/engine.py`) — calls `analyze` per execution bar on a
  look-ahead-safe slice of the data.

This guarantees live, paper and backtest behaviour cannot diverge.

## Look-ahead safety

- Swing pivots are confirmed only `right` bars after the pivot
  (`Swing.confirmed_index`); the structural scan consults a swing only from that
  index onward.
- `Candle.closed` gates every confirmed decision; unconfirmed bars are excluded.
- The backtester passes each higher-timeframe candle to the engine only once its
  **close time** has passed the current execution moment (`_slice_htf`).
- `StrategyConfig.max_lookback` bounds the analysis window (recent structure is
  what matters) which also keeps per-bar backtesting fast.

## Data flow (scan)

```
adapter.get_candles(symbol, tf) per timeframe
        │
        ▼
analyze():
  1 timeframe_bias() for weekly/daily/4H/1H
  2 candidate direction(s) from policy + bias
  3 detect_structure / detect_displacements / detect_fvgs / build_zones (zone TF)
  4 pick nearest tradable zone to price
  5 evaluate_entry() on execution TF
  6 stop (beyond distal + buffer) / target (RR or structural) / reward:risk
  7 size_position()
  8 score_setup()
  9 risk.evaluate()  ← authoritative; risk failure overrides score
        │
        ▼
SetupResult (tradable + full explanation, or rejection_reason)
```

## Persistence

SQLAlchemy 2.0 async. SQLite for dev (default), PostgreSQL for production (via
`asyncpg`/`psycopg`). Tables auto-create on startup; Alembic migrations are
provided for production (`backend/alembic`). Models cover users, Nifty 500
membership history, config versions, zones, signals, orders, trades, risk
events, backtest runs and immutable audit events.

## Real-time

`/ws/stream` pushes overview + positions every few seconds; the frontend falls
back to REST polling when the socket is unavailable.
