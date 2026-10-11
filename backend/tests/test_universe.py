from datetime import date

from app.universe.nifty500 import EligibilityFilters, Nifty500Universe


def test_seed_loads():
    uni = Nifty500Universe()
    syms = uni.state.active_symbols()
    assert "RELIANCE" in syms and "TCS" in syms
    assert uni.state.source == "bundled_seed"
    assert uni.state.warning  # clearly flagged as a partial fallback


def test_refresh_success_updates_list():
    uni = Nifty500Universe()
    csv = "Symbol,Company Name,Industry\n" + "\n".join(
        f"SYM{i},Company {i},IT" for i in range(60)
    )
    state = uni.refresh(fetcher=lambda: csv)
    assert state.last_refresh_ok
    assert state.source == "nse_archives"
    assert "SYM0" in state.constituents


def test_refresh_failure_keeps_previous_list():
    uni = Nifty500Universe()
    before = set(uni.state.active_symbols())

    def boom():
        raise RuntimeError("network down")

    state = uni.refresh(fetcher=boom)
    assert not state.last_refresh_ok
    assert set(uni.state.active_symbols()) == before
    assert "Refresh failed" in state.warning


def test_refresh_rejects_tiny_list():
    uni = Nifty500Universe()
    state = uni.refresh(fetcher=lambda: "Symbol\nAAA\nBBB")
    assert not state.last_refresh_ok


def test_point_in_time_membership():
    uni = Nifty500Universe()
    # Seed effective_from is 2024-01-01; a 2023 as-of excludes everything.
    assert uni.point_in_time_members(date(2023, 1, 1)) == []
    assert "RELIANCE" in uni.point_in_time_members(date(2024, 6, 1))


def test_eligibility_reasons():
    uni = Nifty500Universe()
    f = EligibilityFilters(min_price=10.0, min_history_bars=100)
    r = uni.evaluate_eligibility("X", price=5.0, avg_value=1e9, avg_volume=1e6,
                                 spread_frac=0.001, history_bars=500, tradable=True, filters=f)
    assert not r.eligible and "price_below_min" in r.reason
    ok = uni.evaluate_eligibility("Y", price=100.0, avg_value=1e9, avg_volume=1e6,
                                  spread_frac=0.001, history_bars=500, tradable=True, filters=f)
    assert ok.eligible
