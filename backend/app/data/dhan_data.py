"""Dhan market-data adapter (DhanHQ v2 charts API).

Fetches real NSE candles when Dhan credentials are configured. Maps canonical
symbols to Dhan security ids via the public scrip master, requests the right
chart resolution per timeframe, and derives 4H/weekly by calendar resampling.
Never fabricates prices — on error it reports the feed as disconnected and
returns no candles (the engine then reports insufficient data).
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from ..core.candles import Candle, Timeframe, resample
from .base import FeedMode, FeedStatus, MarketDataAdapter

log = logging.getLogger("smc.dhan_data")

DHAN_BASE_URL = "https://api.dhan.co/v2"
SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

# Well-known index security ids (IDX_I segment).
INDEX_MAP: Dict[str, str] = {"NIFTY50": "13", "BANKNIFTY": "25"}

# Canonical timeframe -> Dhan intraday interval (minutes as string).
_INTRADAY = {
    Timeframe.M1: "1",
    Timeframe.M5: "5",
    Timeframe.M15: "15",
    Timeframe.H1: "60",
}


class DhanDataAdapter(MarketDataAdapter):
    provider = "dhan"

    def __init__(self, client_id: str, access_token: str, timeout: float = 20.0):
        self.client_id = client_id
        self.access_token = access_token
        self.timeout = timeout
        self._sec_map: Dict[str, Tuple[str, str, str]] = {}  # symbol -> (secid, segment, instrument)
        self._last_update: Optional[datetime] = None
        self._connected = False
        self._cache: Dict[str, Tuple[datetime, list]] = {}  # (symbol,tf,count) -> (ts, candles)
        self._cache_ttl = 60.0  # seconds

    # --- credentials / headers --------------------------------------------
    def _headers(self) -> dict:
        return {
            "access-token": self.access_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # --- symbol mapping ----------------------------------------------------
    def _resolve(self, symbol: str) -> Optional[Tuple[str, str, str]]:
        symbol = symbol.upper()
        if symbol in INDEX_MAP:
            return (INDEX_MAP[symbol], "IDX_I", "INDEX")
        if not self._sec_map:
            self._load_scrip_master()
        return self._sec_map.get(symbol)

    def _load_scrip_master(self) -> None:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(SCRIP_MASTER_URL)
                r.raise_for_status()
            reader = csv.DictReader(io.StringIO(r.text))
            for row in reader:
                exch = (row.get("SEM_EXM_EXCH_ID") or "").strip().upper()
                instrument = (row.get("SEM_INSTRUMENT_NAME") or "").strip().upper()
                sym = (row.get("SEM_TRADING_SYMBOL") or "").strip().upper()
                secid = (row.get("SEM_SMST_SECURITY_ID") or "").strip()
                if exch == "NSE" and instrument == "EQUITY" and sym and secid:
                    self._sec_map.setdefault(sym, (secid, "NSE_EQ", "EQUITY"))
            log.info("Dhan scrip master loaded: %d NSE equities", len(self._sec_map))
        except Exception as exc:  # keep running; symbols just won't resolve
            log.warning("Dhan scrip master load failed: %s", exc)

    # --- candle fetch ------------------------------------------------------
    def get_candles(self, symbol: str, timeframe: Timeframe, count: int,
                    end: Optional[datetime] = None) -> List[Candle]:
        ck = f"{symbol}:{timeframe.value}:{count}"
        hit = self._cache.get(ck)
        if hit and (datetime.now(timezone.utc) - hit[0]).total_seconds() < self._cache_ttl:
            return hit[1]
        resolved = self._resolve(symbol)
        if not resolved:
            log.warning("Dhan: no security id for %s", symbol)
            return []
        secid, segment, instrument = resolved
        try:
            if timeframe in _INTRADAY:
                candles = self._intraday(secid, segment, instrument, timeframe, count)
            elif timeframe == Timeframe.H4:
                base = self._intraday(secid, segment, instrument, Timeframe.H1, count * 4)
                candles = resample(base, Timeframe.H4)
            elif timeframe == Timeframe.D1:
                candles = self._daily(secid, segment, instrument, count)
            elif timeframe == Timeframe.W1:
                base = self._daily(secid, segment, instrument, count * 7)
                candles = resample(base, Timeframe.W1)
            else:
                return []
            self._connected = True
            self._last_update = datetime.now(timezone.utc)
            result = candles[-count:]
            self._cache[ck] = (datetime.now(timezone.utc), result)
            return result
        except Exception as exc:
            self._connected = False
            log.warning("Dhan candle fetch failed for %s %s: %s", symbol, timeframe.value, exc)
            return []

    def _intraday(self, secid, segment, instrument, tf: Timeframe, count: int) -> List[Candle]:
        # Request a generous window; intraday history is limited, so cap days.
        minutes_needed = count * tf.minutes
        days = min(90, max(5, minutes_needed // (60 * 6) + 5))  # ~6 trading hours/day
        to = datetime.now(timezone.utc)
        frm = to - timedelta(days=days)
        body = {
            "securityId": secid, "exchangeSegment": segment, "instrument": instrument,
            "interval": _INTRADAY[tf],
            "fromDate": frm.strftime("%Y-%m-%d"), "toDate": to.strftime("%Y-%m-%d"),
        }
        return self._post_candles("/charts/intraday", body, tf)

    def _daily(self, secid, segment, instrument, count: int) -> List[Candle]:
        to = datetime.now(timezone.utc)
        frm = to - timedelta(days=int(count * 1.6) + 10)
        body = {
            "securityId": secid, "exchangeSegment": segment, "instrument": instrument,
            "expiryCode": 0,
            "fromDate": frm.strftime("%Y-%m-%d"), "toDate": to.strftime("%Y-%m-%d"),
        }
        return self._post_candles("/charts/historical", body, Timeframe.D1)

    def _post_candles(self, path: str, body: dict, tf: Timeframe) -> List[Candle]:
        with httpx.Client(base_url=DHAN_BASE_URL, headers=self._headers(),
                          timeout=self.timeout) as c:
            r = c.post(path, json=body)
            if r.status_code == 401:
                raise RuntimeError("401 unauthorized (access token expired?)")
            r.raise_for_status()
            d = r.json()
        return _parse_candles(d, tf)

    def status(self, symbol: Optional[str] = None) -> FeedStatus:
        return FeedStatus(
            provider=self.provider,
            mode=FeedMode.DELAYED if self._connected else FeedMode.HISTORICAL,
            last_update=self._last_update,
            connected=self._connected,
            coverage_pct=100.0 if self._connected else 0.0,
            unavailable_symbols=[],
        )


def _parse_candles(d: dict, tf: Timeframe) -> List[Candle]:
    """Parse Dhan's columnar candle response into Candle objects."""
    if not isinstance(d, dict):
        return []
    opens = d.get("open") or []
    highs = d.get("high") or []
    lows = d.get("low") or []
    closes = d.get("close") or []
    vols = d.get("volume") or [0] * len(opens)
    ts = d.get("timestamp") or d.get("start_Time") or []
    out: List[Candle] = []
    n = min(len(opens), len(highs), len(lows), len(closes), len(ts))
    for i in range(n):
        epoch = ts[i]
        try:
            when = datetime.fromtimestamp(float(epoch), tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            continue
        try:
            out.append(Candle(
                timestamp=when, open=float(opens[i]), high=float(highs[i]),
                low=float(lows[i]), close=float(closes[i]),
                volume=float(vols[i]) if i < len(vols) else 0.0,
                timeframe=tf, closed=True,
            ))
        except ValueError:
            continue
    return out
