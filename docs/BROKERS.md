# Broker integration

All brokers implement one interface: `backend/app/brokers/base.py`
(`BrokerAdapter`). The engine, risk and paper/live routing are broker-agnostic.

Adapters never claim an order filled without a broker confirmation, support
idempotent submission via `client_order_id`, and expose `reconcile()` for
startup/restart reconciliation.

## Paper broker (default, fully working)

`brokers/paper.py` — in-memory simulation: market/limit/stop orders, resting
limit fills on genuine touch, SL/TP protective exits, idempotent client order
ids, realized/unrealized P&amp;L, closed-trade history for analytics. All output is
labelled PAPER; nothing is presented as real.

## Dhan (Indian markets) — implemented

`brokers/dhan.py` (execution/account) + `data/dhan_data.py` (market data).
Covers eligible NSE instruments via security-id mapping from the public scrip
master. **Disabled** until credentials are set; without them every call raises
`BrokerError` rather than faking a session.

**Add credentials in the app — no code or env edits needed:**
1. Create a Dhan account and generate an access token (dhanhq.co).
2. Open the **Connections** page in the UI → enter Client ID (fixed) + Access
   Token → **Test connection** (calls `GET /v2/fundlimit`).
3. Switch the market-data feed to *Dhan (live)*.
4. Because Dhan access tokens expire ~every 24h, paste a fresh token daily; the
   page shows the token's age and remaining validity and warns when expired.

Implemented v2 calls: `/v2/charts/historical` (daily), `/v2/charts/intraday`
(1/5/15/60-min), `/v2/fundlimit`, `/v2/orders`, `/v2/positions`. 4H and weekly
are derived by calendar resampling. **Verify request/response shapes against the
current DhanHQ v2 docs before live order placement** — the data path is the
primary, tested use; live order placement should be validated with small sizes.

Credentials can also be provided via env fallback (`SMC_DHAN_CLIENT_ID` /
`SMC_DHAN_ACCESS_TOKEN`) but the Connections page is preferred (DB-stored,
token-rotation aware).

Dhan does **not** support international Forex, Gold CFDs or international
commodities — those route to an MT5-type broker. Unsupported instruments are
rejected explicitly (`supports_instrument()`), never silently substituted.

## MetaTrader 5 (Forex / Metals / Commodities) — scaffold

`brokers/mt5.py`. **Disabled** until `SMC_MT5_LOGIN` / `SMC_MT5_PASSWORD` /
`SMC_MT5_SERVER` are set and a reachable MT5 terminal exists.

- The `MetaTrader5` Python package is **Windows-only** (or a Wine/bridge
  deployment). Document this constraint for operators on Linux/macOS.
- Broker symbol variants (suffixes/prefixes like `EURUSD.r`, `XAUUSD-ECN`) are
  resolved dynamically via terminal discovery (`resolve_symbol()`), never
  hardcoded to one convention.
- Implement connect/account/symbol-spec/prices/candles/order/position in the
  marked methods, with reconciliation and disconnection recovery.

## Adding another broker

Subclass `BrokerAdapter`, implement the abstract methods, map canonical symbols
to the provider's identifiers, and register it. No strategy or risk code changes.
