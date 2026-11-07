"""Offline tests: synthetic OHLCV bars and a mocked Finnhub / yfinance."""
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data  # noqa: E402


def make_bars(n=40, start="2026-01-02", seed=0):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.2, 1.0, n)
    low = close - rng.uniform(0.2, 1.0, n)
    vol = rng.integers(1_000_000, 2_000_000, n).astype(float)
    idx = pd.bdate_range(start, periods=n)
    return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx)


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    monkeypatch.setattr(data, "_quote_store", data._TTLStore())
    monkeypatch.setattr(data, "_profile_store", data._TTLStore())
    monkeypatch.setattr(data, "_metrics_store", data._TTLStore())
    monkeypatch.setattr(data, "_search_store", data._TTLStore(max_entries=data.SEARCH_MAX_ENTRIES))
    monkeypatch.setattr(data, "_finnhub_limiter", data._RateLimiter(55))
    monkeypatch.setattr(data, "FINNHUB_API_KEY", "test-key")


# --- 1. failures are not cached for the full TTL -----------------------------

def test_metrics_failure_not_frozen_for_an_hour(monkeypatch):
    calls = []

    def fake_batch(symbols):
        calls.append(tuple(symbols))
        return {} if len(calls) == 1 else {s: {"cmf": {1: 1.0}} for s in symbols}

    monkeypatch.setattr(data, "_metrics_batch", fake_batch)
    assert data.fetch_metrics_map(("XLK",)) == {}
    # within the retry window: no hammering
    assert data.fetch_metrics_map(("XLK",)) == {}
    assert len(calls) == 1
    # after the retry window: refetched and served
    t0 = time.time()
    monkeypatch.setattr(data.time, "time", lambda: t0 + data.METRICS_RETRY + 1)
    assert "XLK" in data.fetch_metrics_map(("XLK",))
    assert len(calls) == 2


def test_metrics_only_missing_symbols_redownloaded(monkeypatch):
    seen = []

    def fake_batch(symbols):
        seen.append(tuple(symbols))
        return {s: {"x": 1} for s in symbols if s != "BAD"}

    monkeypatch.setattr(data, "_metrics_batch", fake_batch)
    data.fetch_metrics_map(("A", "B", "BAD"))
    t0 = time.time()
    monkeypatch.setattr(data.time, "time", lambda: t0 + data.METRICS_RETRY + 1)
    data.fetch_metrics_map(("A", "B", "BAD"))
    assert seen == [("A", "B", "BAD"), ("BAD",)]


def test_failed_profile_retried_soon_and_good_quote_kept(monkeypatch):
    results = iter([None, data.Profile("AAPL", "Apple", 3e12)])
    monkeypatch.setattr(data, "fetch_profile", lambda s: next(results))
    assert data.fetch_profiles(("AAPL",)) == {}
    t0 = time.time()
    monkeypatch.setattr(data.time, "time", lambda: t0 + data.PROFILE_RETRY + 1)
    assert data.fetch_profiles(("AAPL",))["AAPL"].name == "Apple"


def test_stale_quote_served_while_refresh_fails(monkeypatch):
    q = data.Quote("XLK", 200.0, 1.0, 198.0, 0)
    results = iter([q, None])
    monkeypatch.setattr(data, "fetch_quote", lambda s: next(results))
    assert data.fetch_quotes(("XLK",))["XLK"].price == 200.0
    t0 = time.time()
    monkeypatch.setattr(data.time, "time", lambda: t0 + data.QUOTE_TTL + 1)
    assert data.fetch_quotes(("XLK",))["XLK"].price == 200.0  # stale but shown


# --- 2. Finnhub rate limit ---------------------------------------------------

def test_rate_limiter_caps_burst():
    lim = data._RateLimiter(55)
    assert sum(lim.try_acquire() for _ in range(100)) == 55


def test_detail_page_burst_stays_under_limit(monkeypatch):
    sent = []

    class R:
        status_code = 200
        headers = {}
        def raise_for_status(self): pass
        def json(self): return {"c": 10, "dp": 1, "pc": 9, "t": 1, "name": "X", "marketCapitalization": 1}

    def fake_get(url, params=None, headers=None, timeout=None):
        sent.append((url, params, headers))
        return R()

    monkeypatch.setattr(data._session, "get", fake_get)
    syms = tuple(f"S{i}" for i in range(30))
    data.fetch_quotes(syms)
    data.fetch_profiles(syms)
    assert len(sent) == 55  # 60 wanted, 5 deferred to the next refresh instead of a 429


def test_429_triggers_backoff(monkeypatch):
    class R:
        status_code = 429
        headers = {"Retry-After": "20"}

    monkeypatch.setattr(data._session, "get", lambda *a, **k: R())
    assert data.fetch_quote("AAPL") is None
    assert data._finnhub_limiter.try_acquire() is False


# --- 3/9. API key is sent as a header, never in the URL -----------------------

def test_token_in_header_not_query(monkeypatch):
    captured = {}

    class R:
        status_code = 200
        headers = {}
        def raise_for_status(self): pass
        def json(self): return {"c": 1}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured.update(url=url, params=params, headers=headers)
        return R()

    monkeypatch.setattr(data._session, "get", fake_get)
    data.fetch_quote("AAPL")
    assert "token" not in captured["params"]
    assert "test-key" not in captured["url"]
    assert captured["headers"]["X-Finnhub-Token"] == "test-key"


# --- 5. input validation / bounded cache --------------------------------------

@pytest.mark.parametrize("raw,ok", [
    ("aapl", "AAPL"), (" BRK.B ", "BRK.B"), ("BRK-B", "BRK-B"), ("GOOGL", "GOOGL"),
    ("<img src=x>", None), ("A" * 20, None), ("", None), ("AAPL;rm", None), ("../x", None),
])
def test_normalize_symbol(raw, ok):
    assert data.normalize_symbol(raw) == ok


def test_invalid_search_never_hits_network(monkeypatch):
    monkeypatch.setattr(data, "_search_stock_raw", lambda s: pytest.fail("network called"))
    assert data.search_stock("<svg onload=alert(1)>") is None


def test_search_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(data, "_search_stock_raw",
                        lambda s: {"symbol": s, "quote": None, "profile": None, "period_changes": {}, "metrics": {}})
    for i in range(data.SEARCH_MAX_ENTRIES + 100):
        data.search_stock(f"Z{i}")
    assert len(data._search_store._data) <= data.SEARCH_MAX_ENTRIES


# --- 6. adjusted prices -------------------------------------------------------

def test_download_uses_adjusted_prices(monkeypatch):
    kw = {}
    monkeypatch.setattr(data.yf, "download", lambda *a, **k: kw.update(k) or None)
    data._download_daily(["AAPL"])
    assert kw["auto_adjust"] is True


# --- 7. partial intraday bar --------------------------------------------------

def test_rvol_prorated_intraday():
    df = make_bars(30)
    df.iloc[-1, df.columns.get_loc("Volume")] = df["Volume"].iloc[-21:-1].mean() / 2
    today = df.index[-1]
    noon_ish = datetime(today.year, today.month, today.day, 12, 45, tzinfo=data.NY_TZ)  # half session
    assert data.last_bar_is_partial(df, noon_ish)
    m = data.compute_all_metrics(df, now=noon_ish)
    assert m["partial_day"] is True
    assert m["rvol"][20] == pytest.approx(1.0, rel=0.02)  # half the volume at half time = normal pace
    after_close = datetime(today.year, today.month, today.day, 17, 0, tzinfo=data.NY_TZ)
    assert data.compute_all_metrics(df, now=after_close)["rvol"][20] == pytest.approx(0.5, rel=0.02)


# --- 8. OBV -------------------------------------------------------------------

def test_obv_net_bounded_and_window_independent():
    df = make_bars(60, seed=3)
    v_full = data.compute_obv_net_pct(df, 20)
    v_short = data.compute_obv_net_pct(df.tail(25), 20)  # different download start
    assert v_full == pytest.approx(v_short)
    assert -100 <= v_full <= 100
    assert data.compute_obv_net_pct(df, 1) is None
    up = make_bars(25)
    up["Close"] = np.arange(25, dtype=float) + 100
    assert data.compute_obv_net_pct(up, 20) == pytest.approx(100.0)


# --- 12. no magic 999 sentinel ------------------------------------------------

def test_up_down_ratio_infinite_when_no_down_days():
    df = make_bars(25)
    df["Close"] = np.arange(25, dtype=float) + 100
    assert math.isinf(data.compute_up_down_vol_ratio(df, 20))


def test_all_metrics_shape():
    m = data.compute_all_metrics(make_bars(60), now=datetime(2030, 1, 1, tzinfo=data.NY_TZ))
    for key in ("price_change", "cmf", "net_flow", "flow_ratio", "ud_vol", "rvol", "close_loc", "mfi", "obv_pct"):
        assert key in m


def test_extract_handles_missing_ticker_in_multiindex():
    df = make_bars(10)
    multi = pd.concat({"AAPL": df}, axis=1)
    assert data._extract(multi, "MSFT") is None
    assert len(data._extract(multi, "AAPL")) == 10
