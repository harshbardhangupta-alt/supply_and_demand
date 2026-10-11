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

## Dhan (Indian markets) — scaffold

`brokers/dhan.py`. Covers eligible NSE/BSE cash, F&amp;O, currency and MCX
commodity instruments via security-id mapping. **Disabled** until
`SMC_DHAN_CLIENT_ID` and `SMC_DHAN_ACCESS_TOKEN` are set; without them every call
raises `BrokerError` rather than faking a session.

To enable (in a configured deployment):
1. Create a Dhan account and generate an access token.
2. Set `SMC_DHAN_CLIENT_ID` / `SMC_DHAN_ACCESS_TOKEN` in the backend `.env`.
3. Load the Dhan instrument master and populate the security-id map.
4. Implement the REST calls in the marked methods against current docs
   (<https://dhanhq.co/docs/v2/>): auth validation, market data, historical
   candles, order submit/modify/cancel/status, positions. Respect rate limits
   and token expiry.

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
