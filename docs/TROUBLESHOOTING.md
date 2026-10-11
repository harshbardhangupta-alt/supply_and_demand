# Troubleshooting

### `ModuleNotFoundError` on startup (python-multipart, aiosqlite, …) / Python 3.14
Install the full runtime set in one go (no venv required):

```
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings sqlalchemy greenlet aiosqlite python-multipart python-dotenv
```

The app is pure-Python on SQLite — it does **not** need pandas, numpy, asyncpg or
psycopg (those are only for the optional Docker/Postgres path and may fail to
build on brand-new Python releases). `requirements.txt` lists only what's needed;
the Postgres drivers are commented out.

### Backend won't import / `greenlet` error
SQLAlchemy async needs `greenlet`. `pip install -r backend/requirements.txt`
installs it. Ensure the virtualenv is active.

### `python-multipart` error on login
The OAuth2 form login needs `python-multipart` (in `requirements.txt`).

### Scanner shows 0 eligible / backtest shows 0 trades
This is expected on some symbols and windows. The default policy is strict
(score ≥ 70, reward:risk ≥ 1:3, confirmed entry). Synthetic data is random, so
many instruments legitimately have no valid setup at a given moment — they stay
visible with a `rejection_reason`. Try more symbols, a different timeframe, or
loosen `min_score` / `min_reward_risk` in Settings.

### Backtest is slow
Each bar re-runs the full engine. `max_lookback` (default 400) bounds the work.
Keep `bars` modest (≤ 800) in the UI; the API caps it at 800. For large sweeps,
run the backtester directly in Python.

### Nifty 500 refresh fails / warning shown
`/api/universe/nifty500/refresh` fetches the live NSE CSV. NSE may block
automated requests or the network may be restricted. On failure the **last
verified list is kept** and a warning is surfaced — this is by design, not a bug.
The bundled seed is a partial snapshot until a successful refresh.

### Frontend can't reach the backend
The frontend proxies `/api` and `/ws` to `NEXT_PUBLIC_API_BASE`
(default `http://localhost:8005`). Set it in `frontend/.env.local`. Check CORS
origins (`SMC_CORS_ORIGINS`) if calling cross-origin.

### Live trading returns 403
Live is disabled by default. Set `SMC_LIVE_TRADING_ENABLED=true`, configure a
broker, sign in as admin, and confirm. Without a configured broker the adapters
intentionally raise `BrokerError`.

### MetaTrader5 package won't install (Linux/macOS)
`MetaTrader5` is Windows-only. Run MT5 on Windows or a bridge; the rest of the
platform runs anywhere. The adapter stays disabled and raises a clear error
until a terminal is reachable.

### Docker: backend can't connect to Postgres
Compose waits for the DB healthcheck. If the backend still fails, confirm the
`SMC_DATABASE_URL`/`SMC_SYNC_DATABASE_URL` env values match the `db` service
credentials and that `asyncpg`/`psycopg` are installed (they are in
`requirements.txt`).

### Reset local state
Stop the server and delete `backend/smc.db` (SQLite) to start fresh. Paper
account state is in-memory and resets on restart.
