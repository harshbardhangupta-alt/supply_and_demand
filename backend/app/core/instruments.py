"""Instrument specifications and asset-class metadata.

Position sizing and order validation depend on *real* contract specs: tick
size, lot size, contract multiplier, pip value, etc. These differ fundamentally
between Indian cash equities, index futures, options, forex, metals and energy
CFDs, so a single generic pip formula is never applied across all of them.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AssetClass(str, Enum):
    INDIAN_EQUITY = "indian_equity"
    INDIAN_INDEX = "indian_index"
    INDIAN_FUTURE = "indian_future"
    INDIAN_OPTION = "indian_option"
    FOREX = "forex"
    METAL = "metal"
    ENERGY = "energy"
    CRYPTO = "crypto"


class MarketUniverse(str, Enum):
    NIFTY500 = "nifty500"
    INDIAN_INDICES = "indian_indices"
    FOREX = "forex"
    METALS = "metals"
    COMMODITIES = "commodities"


@dataclass(frozen=True)
class InstrumentSpec:
    """Normalized contract specification for one tradable instrument."""

    symbol: str                 # internal canonical symbol, e.g. "RELIANCE"
    name: str
    asset_class: AssetClass
    universe: MarketUniverse
    currency: str = "INR"       # account/quote currency for P&L of this product
    tick_size: float = 0.05     # minimum price increment
    lot_size: float = 1.0       # minimum tradable quantity unit
    qty_step: float = 1.0       # increment above the minimum
    min_qty: float = 1.0
    max_qty: float = 1_000_000.0
    contract_multiplier: float = 1.0   # monetary value of 1 price unit * 1 qty
    # For forex/metals pip based products:
    pip_size: Optional[float] = None   # e.g. 0.0001 for EURUSD, 0.01 for USDJPY
    pip_value_per_lot: Optional[float] = None  # account-ccy value of 1 pip / lot
    # Execution metadata.
    broker_symbol: Optional[str] = None     # provider-specific symbol/suffix
    security_id: Optional[str] = None       # e.g. Dhan security id
    exchange: Optional[str] = None
    tradable: bool = True
    min_stop_distance_ticks: int = 1

    @property
    def is_pip_based(self) -> bool:
        return self.pip_size is not None and self.pip_value_per_lot is not None

    def round_price(self, price: float) -> float:
        if self.tick_size <= 0:
            return price
        return round(round(price / self.tick_size) * self.tick_size, 10)

    def round_qty(self, qty: float) -> float:
        """Round a desired quantity DOWN to a valid, tradable quantity."""
        if qty < self.min_qty:
            return 0.0
        step = self.qty_step if self.qty_step > 0 else 1.0
        steps = int((qty - self.min_qty) / step + 1e-9)
        q = self.min_qty + steps * step
        q = min(q, self.max_qty)
        return round(q, 10)

    def money_per_price_unit(self, qty: float) -> float:
        """Monetary P&L for a 1.0 price move holding ``qty`` units.

        For cash equity this is just ``qty`` (1 INR move * qty shares). For a
        future it includes the contract multiplier.
        """
        return qty * self.contract_multiplier


# ---------------------------------------------------------------------------
# A small built-in default catalogue. In production these come from the broker
# instrument master (Dhan/MT5). These defaults let the engine, paper trading
# and tests run entirely offline with realistic, non-fabricated-as-live specs.
# ---------------------------------------------------------------------------
DEFAULT_SPECS = {
    # Indian indices (analysis; execution via futures/ETF where eligible).
    "NIFTY50": InstrumentSpec(
        symbol="NIFTY50", name="Nifty 50", asset_class=AssetClass.INDIAN_INDEX,
        universe=MarketUniverse.INDIAN_INDICES, tick_size=0.05, tradable=False,
        exchange="NSE",
    ),
    "BANKNIFTY": InstrumentSpec(
        symbol="BANKNIFTY", name="Nifty Bank", asset_class=AssetClass.INDIAN_INDEX,
        universe=MarketUniverse.INDIAN_INDICES, tick_size=0.05, tradable=False,
        exchange="NSE",
    ),
    # Forex majors.
    "EURUSD": InstrumentSpec(
        symbol="EURUSD", name="Euro / US Dollar", asset_class=AssetClass.FOREX,
        universe=MarketUniverse.FOREX, currency="USD", tick_size=0.00001,
        pip_size=0.0001, pip_value_per_lot=10.0, lot_size=0.01, qty_step=0.01,
        min_qty=0.01, max_qty=100.0, contract_multiplier=100_000.0,
    ),
    "GBPUSD": InstrumentSpec(
        symbol="GBPUSD", name="British Pound / US Dollar", asset_class=AssetClass.FOREX,
        universe=MarketUniverse.FOREX, currency="USD", tick_size=0.00001,
        pip_size=0.0001, pip_value_per_lot=10.0, lot_size=0.01, qty_step=0.01,
        min_qty=0.01, max_qty=100.0, contract_multiplier=100_000.0,
    ),
    "USDJPY": InstrumentSpec(
        symbol="USDJPY", name="US Dollar / Japanese Yen", asset_class=AssetClass.FOREX,
        universe=MarketUniverse.FOREX, currency="USD", tick_size=0.001,
        pip_size=0.01, pip_value_per_lot=9.1, lot_size=0.01, qty_step=0.01,
        min_qty=0.01, max_qty=100.0, contract_multiplier=100_000.0,
    ),
    # Metals.
    "XAUUSD": InstrumentSpec(
        symbol="XAUUSD", name="Gold / US Dollar", asset_class=AssetClass.METAL,
        universe=MarketUniverse.METALS, currency="USD", tick_size=0.01,
        pip_size=0.1, pip_value_per_lot=10.0, lot_size=0.01, qty_step=0.01,
        min_qty=0.01, max_qty=100.0, contract_multiplier=100.0,
    ),
    "XAGUSD": InstrumentSpec(
        symbol="XAGUSD", name="Silver / US Dollar", asset_class=AssetClass.METAL,
        universe=MarketUniverse.METALS, currency="USD", tick_size=0.001,
        pip_size=0.01, pip_value_per_lot=5.0, lot_size=0.01, qty_step=0.01,
        min_qty=0.01, max_qty=100.0, contract_multiplier=5000.0,
    ),
    # Energy.
    "USOIL": InstrumentSpec(
        symbol="USOIL", name="WTI Crude Oil", asset_class=AssetClass.ENERGY,
        universe=MarketUniverse.COMMODITIES, currency="USD", tick_size=0.01,
        pip_size=0.01, pip_value_per_lot=10.0, lot_size=0.01, qty_step=0.01,
        min_qty=0.01, max_qty=1000.0, contract_multiplier=1000.0,
    ),
    "UKOIL": InstrumentSpec(
        symbol="UKOIL", name="Brent Crude Oil", asset_class=AssetClass.ENERGY,
        universe=MarketUniverse.COMMODITIES, currency="USD", tick_size=0.01,
        pip_size=0.01, pip_value_per_lot=10.0, lot_size=0.01, qty_step=0.01,
        min_qty=0.01, max_qty=1000.0, contract_multiplier=1000.0,
    ),
}


def equity_spec(symbol: str, name: str, tick_size: float = 0.05) -> InstrumentSpec:
    """Build a standard NSE cash-equity spec for a Nifty 500 constituent."""
    return InstrumentSpec(
        symbol=symbol,
        name=name,
        asset_class=AssetClass.INDIAN_EQUITY,
        universe=MarketUniverse.NIFTY500,
        currency="INR",
        tick_size=tick_size,
        lot_size=1.0,
        qty_step=1.0,
        min_qty=1.0,
        max_qty=1_000_000.0,
        contract_multiplier=1.0,
        exchange="NSE",
        tradable=True,
    )
