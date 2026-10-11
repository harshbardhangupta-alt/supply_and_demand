"""Nifty 500 universe manager.

Responsibilities:
  * Load the current constituent list (from the DB, a refreshed provider feed,
    or a bundled seed snapshot as a last-resort fallback).
  * Refresh from an authoritative source (NSE archives) and, on failure, retain
    the last verified list rather than silently replacing it.
  * Preserve point-in-time membership so backtests avoid survivorship bias.
  * Apply configurable liquidity / eligibility filters, surfacing an explicit
    rejection reason for every excluded symbol instead of hiding it.

The bundled CSV is a PARTIAL snapshot of well-known constituents, clearly
labelled as a fallback. It is never presented as the authoritative full 500;
the real list is fetched at runtime and its provenance + timestamp recorded.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

SEED_PATH = Path(__file__).parent / "data" / "nifty500_seed.csv"
# Official NSE index constituents CSV (subject to change / access restrictions).
NSE_NIFTY500_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"


@dataclass
class Constituent:
    symbol: str
    name: str
    industry: str = ""
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    active: bool = True


@dataclass
class EligibilityFilters:
    min_price: float = 0.0
    min_avg_value: float = 0.0        # average daily traded value
    min_avg_volume: float = 0.0
    max_spread_frac: float = 0.02
    min_history_bars: int = 200
    require_tradable: bool = True


@dataclass
class EligibilityResult:
    symbol: str
    eligible: bool
    reason: Optional[str] = None


@dataclass
class UniverseState:
    constituents: Dict[str, Constituent] = field(default_factory=dict)
    source: str = "none"
    last_refresh: Optional[datetime] = None
    last_refresh_ok: bool = False
    warning: Optional[str] = None
    coverage_pct: float = 0.0
    unavailable: List[str] = field(default_factory=list)

    def active_symbols(self) -> List[str]:
        return sorted(s for s, c in self.constituents.items() if c.active)


class Nifty500Universe:
    def __init__(self) -> None:
        self.state = UniverseState()
        self._load_seed()

    def _load_seed(self) -> None:
        rows = self._parse_csv(SEED_PATH.read_text())
        self.state.constituents = {
            r["symbol"]: Constituent(
                symbol=r["symbol"], name=r.get("name", r["symbol"]),
                industry=r.get("industry", ""),
                effective_from=date(2024, 1, 1), active=True,
            )
            for r in rows
        }
        self.state.source = "bundled_seed"
        self.state.last_refresh = datetime.now(timezone.utc)
        self.state.last_refresh_ok = True
        self.state.warning = (
            "Using bundled partial seed snapshot (not the authoritative full "
            "Nifty 500). Call refresh() to fetch the live NSE constituent list."
        )

    @staticmethod
    def _parse_csv(text: str) -> List[dict]:
        reader = csv.DictReader(io.StringIO(text))
        out: List[dict] = []
        for row in reader:
            # Normalize NSE's column names ("Symbol", "Company Name", "Industry").
            sym = (row.get("symbol") or row.get("Symbol") or "").strip().upper()
            if not sym:
                continue
            out.append(
                {
                    "symbol": sym,
                    "name": (row.get("name") or row.get("Company Name") or sym).strip(),
                    "industry": (row.get("industry") or row.get("Industry") or "").strip(),
                }
            )
        return out

    def refresh(self, fetcher=None) -> UniverseState:
        """Refresh from the authoritative source.

        ``fetcher`` is an injectable callable returning CSV text (so tests and
        offline runs don't require network). On any failure the previous
        verified list is kept and a warning is set — never silently replaced
        with partial data.
        """
        try:
            text = fetcher() if fetcher else self._fetch_nse()
            rows = self._parse_csv(text)
            if len(rows) < 50:
                raise ValueError(f"refusing suspiciously small list ({len(rows)} rows)")
            today = date.today()
            new_syms = {r["symbol"] for r in rows}
            # Mark removed constituents inactive, keep their history.
            for sym, c in self.state.constituents.items():
                if sym not in new_syms and c.active:
                    c.active = False
                    c.effective_to = today
            for r in rows:
                if r["symbol"] in self.state.constituents:
                    c = self.state.constituents[r["symbol"]]
                    c.active = True
                    c.name = r["name"] or c.name
                    c.industry = r["industry"] or c.industry
                else:
                    self.state.constituents[r["symbol"]] = Constituent(
                        symbol=r["symbol"], name=r["name"], industry=r["industry"],
                        effective_from=today, active=True,
                    )
            self.state.source = "nse_archives"
            self.state.last_refresh = datetime.now(timezone.utc)
            self.state.last_refresh_ok = True
            self.state.warning = None
        except Exception as exc:  # keep last verified list
            self.state.last_refresh = datetime.now(timezone.utc)
            self.state.last_refresh_ok = False
            self.state.warning = (
                f"Refresh failed ({exc}); retained previous list of "
                f"{len(self.state.active_symbols())} constituents."
            )
        return self.state

    def _fetch_nse(self) -> str:
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SMC-Engine/1.0)",
            "Accept": "text/csv,application/csv",
        }
        with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(NSE_NIFTY500_URL)
            resp.raise_for_status()
            return resp.text

    def point_in_time_members(self, as_of: date) -> List[str]:
        """Constituents that were members on ``as_of`` (survivorship-safe)."""
        out = []
        for c in self.state.constituents.values():
            if c.effective_from and c.effective_from > as_of:
                continue
            if c.effective_to and c.effective_to < as_of:
                continue
            out.append(c.symbol)
        return sorted(out)

    def evaluate_eligibility(
        self, symbol: str, price: float, avg_value: float, avg_volume: float,
        spread_frac: float, history_bars: int, tradable: bool,
        filters: EligibilityFilters,
    ) -> EligibilityResult:
        if filters.require_tradable and not tradable:
            return EligibilityResult(symbol, False, "not_tradable_at_broker")
        if price < filters.min_price:
            return EligibilityResult(symbol, False, f"price_below_min ({price} < {filters.min_price})")
        if avg_value < filters.min_avg_value:
            return EligibilityResult(symbol, False, "avg_value_below_min")
        if avg_volume < filters.min_avg_volume:
            return EligibilityResult(symbol, False, "avg_volume_below_min")
        if spread_frac > filters.max_spread_frac:
            return EligibilityResult(symbol, False, "spread_too_wide")
        if history_bars < filters.min_history_bars:
            return EligibilityResult(symbol, False, "insufficient_history")
        return EligibilityResult(symbol, True, None)
