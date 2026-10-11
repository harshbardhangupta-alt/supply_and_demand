"""Tests for credential handling, Dhan candle parsing and resampling (offline)."""
from datetime import datetime, timedelta, timezone

from app import credentials as creds
from app.core.candles import Candle, Timeframe, resample
from app.data.dhan_data import _parse_candles


def test_mask_hides_secret():
    assert creds.mask("") is None
    assert creds.mask("short") == "••••"
    assert creds.mask("1234567890abcd") == "1234••••abcd"


def test_dhan_token_status_age_and_expiry():
    now = datetime.now(timezone.utc)
    fresh = {creds.DHAN_CLIENT_ID: "c", creds.DHAN_ACCESS_TOKEN: "t",
             creds.DHAN_TOKEN_UPDATED: now.isoformat()}
    s = creds.dhan_status(fresh)
    assert s.configured and not s.token_expired
    assert s.expires_in_hours is not None and s.expires_in_hours <= 24.0

    old = {creds.DHAN_CLIENT_ID: "c", creds.DHAN_ACCESS_TOKEN: "t",
           creds.DHAN_TOKEN_UPDATED: (now - timedelta(hours=25)).isoformat()}
    assert creds.dhan_status(old).token_expired


def test_dhan_status_unconfigured():
    assert not creds.dhan_status({}).configured


def test_parse_dhan_columnar_candles():
    base = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())
    payload = {
        "open": [100, 101], "high": [102, 103], "low": [99, 100],
        "close": [101, 102], "volume": [1000, 1200],
        "timestamp": [base, base + 86400],
    }
    candles = _parse_candles(payload, Timeframe.D1)
    assert len(candles) == 2
    assert candles[0].open == 100 and candles[1].close == 102


def test_parse_dhan_skips_bad_rows():
    payload = {"open": [100], "high": [90], "low": [95], "close": [97],
               "timestamp": [1704067200]}  # high<low -> invalid candle skipped
    assert _parse_candles(payload, Timeframe.D1) == []


def test_resample_hourly_to_4h():
    t0 = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    hourly = [
        Candle(timestamp=t0 + timedelta(hours=i), open=100 + i, high=101 + i,
               low=99 + i, close=100 + i, timeframe=Timeframe.H1)
        for i in range(8)
    ]
    four = resample(hourly, Timeframe.H4)
    assert len(four) == 2
    assert four[0].open == hourly[0].open
    assert four[0].high == max(c.high for c in hourly[:4])


def test_resample_daily_to_weekly():
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)  # Monday
    daily = [
        Candle(timestamp=t0 + timedelta(days=i), open=10, high=11, low=9, close=10,
               timeframe=Timeframe.D1)
        for i in range(10)
    ]
    weekly = resample(daily, Timeframe.W1)
    # 10 consecutive days spans 2 ISO weeks.
    assert len(weekly) == 2
