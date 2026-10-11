"""API integration tests using FastAPI's TestClient (no live credentials)."""
import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/auth/login", data={"username": "admin", "password": "admin"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_overview_shape(client):
    o = client.get("/api/overview").json()
    for key in ("equity", "open_positions", "paper_trading", "live_mode"):
        assert key in o
    assert o["live_mode"] is False  # live disabled by default


def test_nifty500_universe(client):
    n = client.get("/api/universe/nifty500").json()
    assert n["count"] > 0
    assert any(c["symbol"] == "RELIANCE" for c in n["constituents"])
    assert n["warning"]  # bundled-seed warning surfaced


def test_scanner_returns_rows_with_reasons(client):
    s = client.get("/api/scanner/nifty500?limit=6").json()
    assert s["total"] == 6
    # Every non-eligible row carries an explicit rejection reason.
    for row in s["rows"]:
        if not row.get("eligible"):
            assert row.get("rejection_reason")


def test_chart_overlays(client):
    c = client.get("/api/chart/RELIANCE?timeframe=4h&count=150").json()
    assert len(c["candles"]) > 0
    assert "zones" in c and "swings" in c and "fvgs" in c


def test_backtest_requires_auth(client):
    r = client.post("/api/backtest", json={"symbol": "RELIANCE", "bars": 200})
    assert r.status_code == 401


def test_backtest_runs(client, auth):
    r = client.post("/api/backtest", json={"symbol": "RELIANCE", "bars": 220, "warmup": 100},
                    headers=auth)
    assert r.status_code == 200
    assert "metrics" in r.json()


def test_live_enable_blocked_by_default(client, auth):
    r = client.post("/api/trading/live/enable", json={"confirm": True}, headers=auth)
    assert r.status_code == 403  # disabled by server config


def test_emergency_stop(client, auth):
    r = client.post("/api/trading/emergency-stop", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["stopped"] is True
    assert "not" in body["note"].lower()  # clarifies positions not auto-liquidated


def test_config_risk_cap_enforced(client, auth):
    # Requesting 5% risk must be clamped to the hard cap (<=1%).
    r = client.put("/api/settings/config",
                   json={"universe": "nifty500", "risk_per_trade": 0.05}, headers=auth)
    assert r.status_code == 200
    assert r.json()["config"]["risk"]["risk_per_trade"] <= 0.01 + 1e-9
