import logging
import math
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("sector_flow")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

# Finnhub free tier is 60 calls/min. Stay a little below it so bursts from
# several pages / sessions never trip 429.
FINNHUB_CALLS_PER_MIN = int(os.getenv("FINNHUB_CALLS_PER_MIN", "55"))

CMF_PERIOD = 20
CMF_PERIODS = (1, 5, 20)

QUOTE_TTL = 15            # seconds a quote counts as fresh
QUOTE_MAX_STALE = 600     # serve a stale quote for up to 10 min while refresh is throttled
PROFILE_TTL = 86400       # profiles barely change
PROFILE_RETRY = 120       # retry a failed profile after 2 min (not 24 h)
METRICS_TTL = 3600        # daily bars
METRICS_RETRY = 300       # retry a failed history download after 5 min (not 1 h)
SEARCH_TTL = 900
SEARCH_MAX_ENTRIES = 256

NY_TZ = ZoneInfo("America/New_York")
SESSION_OPEN_MIN = 9 * 60 + 30
SESSION_CLOSE_MIN = 16 * 60

# US tickers: letters/digits plus "." or "-" share-class separator (BRK.B / BRK-B).
_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9]{0,6}([.\-][A-Z0-9]{1,3})?$")


@dataclass
class Quote:
    symbol: str
    price: float
    change_pct: float
    prev_close: float
    ts: int


@dataclass
class Profile:
    symbol: str
    name: str
    market_cap: float  # USD


def normalize_symbol(raw: str) -> str | None:
    """Return a cleaned upper-case ticker, or None if it is not a plausible US ticker."""
    sym = (raw or "").strip().upper()
    if not _SYMBOL_RE.fullmatch(sym):
        return None
    return sym


def _yf_symbol(sym: str) -> str:
    return sym.replace(".", "-")


# ---------------------------------------------------------------------------
# Small thread-safe caches + Finnhub rate limiter
# ---------------------------------------------------------------------------

class _TTLStore:
    """Per-key cache that remembers successes and failures separately.

    Unlike ``st.cache_data`` on a whole batch, a transient failure for one
    symbol is retried soon instead of being frozen for the full TTL, and a
    last-known-good value can be served while a refresh is not possible.
    """

    def __init__(self, max_entries: int = 2048):
        self._data: dict[str, tuple[float, object]] = {}   # key -> (fetched_at, value)
        self._failed: dict[str, float] = {}                 # key -> failed_at
        self._lock = threading.Lock()
        self._max = max_entries

    def get(self, key: str) -> tuple[float, object] | None:
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, value: object) -> None:
        with self._lock:
            if key not in self._data and len(self._data) >= self._max:
                oldest = min(self._data, key=lambda k: self._data[k][0])
                del self._data[oldest]
            self._data[key] = (time.time(), value)
            self._failed.pop(key, None)

    def mark_failed(self, key: str) -> None:
        with self._lock:
            if len(self._failed) >= self._max:
                self._failed.clear()
            self._failed[key] = time.time()

    def recently_failed(self, key: str, retry_after: float) -> bool:
        with self._lock:
            ts = self._failed.get(key)
        return ts is not None and time.time() - ts < retry_after


class _RateLimiter:
    """Non-blocking sliding-window limiter shared by every Finnhub call in the process."""

    def __init__(self, per_minute: int):
        self._per_minute = max(1, per_minute)
        self._calls: list[float] = []
        self._blocked_until = 0.0
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        now = time.time()
        with self._lock:
            if now < self._blocked_until:
                return False
            self._calls = [t for t in self._calls if now - t < 60]
            if len(self._calls) >= self._per_minute:
                return False
            self._calls.append(now)
            return True

    def backoff(self, seconds: float) -> None:
        with self._lock:
            self._blocked_until = max(self._blocked_until, time.time() + seconds)


_finnhub_limiter = _RateLimiter(FINNHUB_CALLS_PER_MIN)
_session = requests.Session()
_quote_store = _TTLStore()
_profile_store = _TTLStore()
_metrics_store = _TTLStore()
_search_store = _TTLStore(max_entries=SEARCH_MAX_ENTRIES)


class _Throttled(Exception):
    """Local rate limit reached — the request was not sent."""


def _finnhub_get(path: str, symbol: str) -> dict:
    if not _finnhub_limiter.try_acquire():
        raise _Throttled()
    # Token goes in a header, not the URL, so it never lands in proxy/access logs
    # or in exception messages that embed the request URL.
    r = _session.get(
        f"{FINNHUB_BASE}{path}",
        params={"symbol": symbol},
        headers={"X-Finnhub-Token": FINNHUB_API_KEY},
        timeout=5,
    )
    if r.status_code == 429:
        retry = r.headers.get("Retry-After")
        _finnhub_limiter.backoff(float(retry) if retry and retry.isdigit() else 30.0)
        log.warning("Finnhub 429 on %s %s — backing off", path, symbol)
        raise _Throttled()
    r.raise_for_status()
    d = r.json()
    return d if isinstance(d, dict) else {}


def fetch_quote(symbol: str) -> Quote | None:
    """Uncached single quote. Returns None on any failure (including throttling)."""
    if not FINNHUB_API_KEY:
        return None
    try:
        d = _finnhub_get("/quote", symbol)
    except _Throttled:
        return None
    except Exception as e:
        log.warning("quote %s failed: %s", symbol, type(e).__name__)
        return None
    try:
        if d.get("c") in (None, 0):
            return None
        return Quote(
            symbol=symbol,
            price=float(d["c"]),
            change_pct=float(d.get("dp") or 0.0),
            prev_close=float(d.get("pc") or 0.0),
            ts=int(d.get("t") or 0),
        )
    except (TypeError, ValueError, KeyError) as e:
        log.warning("quote %s: bad payload (%s)", symbol, e)
        return None


def fetch_profile(symbol: str) -> Profile | None:
    if not FINNHUB_API_KEY:
        return None
    try:
        d = _finnhub_get("/stock/profile2", symbol)
    except _Throttled:
        return None
    except Exception as e:
        log.warning("profile %s failed: %s", symbol, type(e).__name__)
        return None
    if not d:
        return None
    try:
        mc = d.get("marketCapitalization") or 0
        return Profile(
            symbol=symbol,
            name=str(d.get("name") or symbol),
            market_cap=float(mc) * 1e6,
        )
    except (TypeError, ValueError) as e:
        log.warning("profile %s: bad payload (%s)", symbol, e)
        return None


def _cached_many(symbols, store: _TTLStore, ttl: float, retry: float,
                 max_stale: float | None, fetch_one) -> dict:
    """Return {symbol: value}; refresh only symbols that are stale and not in failure back-off."""
    now = time.time()
    out: dict = {}
    to_fetch: list[str] = []
    for s in symbols:
        hit = store.get(s)
        if hit and now - hit[0] < ttl:
            out[s] = hit[1]
            continue
        if store.recently_failed(s, retry):
            if hit and (max_stale is None or now - hit[0] < max_stale):
                out[s] = hit[1]
            continue
        to_fetch.append(s)
    if to_fetch:
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(fetch_one, to_fetch))
        for s, v in zip(to_fetch, results):
            if v is not None:
                store.put(s, v)
                out[s] = v
            else:
                store.mark_failed(s)
                hit = store.get(s)
                if hit and (max_stale is None or now - hit[0] < max_stale):
                    out[s] = hit[1]
    return out


def fetch_quotes(symbols: tuple[str, ...]) -> dict[str, Quote]:
    # Quotes refresh fast, so a "failure" (often just local throttling) is retried
    # on the very next tick while the last good quote keeps being shown.
    return _cached_many(symbols, _quote_store, QUOTE_TTL, QUOTE_TTL, QUOTE_MAX_STALE, fetch_quote)


def fetch_profiles(symbols: tuple[str, ...]) -> dict[str, Profile]:
    return _cached_many(symbols, _profile_store, PROFILE_TTL, PROFILE_RETRY, None, fetch_profile)


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def compute_period_returns(
    df: pd.DataFrame,
    periods: tuple[int, ...] = CMF_PERIODS,
) -> dict[int, float]:
    if df is None or df.empty or "Close" not in df.columns:
        return {}
    close = df["Close"].dropna()
    out: dict[int, float] = {}
    for p in periods:
        if len(close) > p:
            base = close.iloc[-1 - p]
            if base and pd.notna(base):
                v = (close.iloc[-1] / base - 1) * 100
                if pd.notna(v):
                    out[p] = float(v)
    return out


def compute_cmf(df: pd.DataFrame, period: int = CMF_PERIOD) -> float | None:
    if df is None or len(df) < period:
        return None
    high, low, close, vol = df["High"], df["Low"], df["Close"], df["Volume"]
    hl_range = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / hl_range
    mfv = (mfm * vol).fillna(0)
    denom = vol.tail(period).sum()
    if denom == 0:
        return None
    cmf = mfv.tail(period).sum() / denom
    if pd.isna(cmf):
        return None
    return float(cmf) * 100.0


def compute_net_dollar_flow(df: pd.DataFrame, period: int = 20) -> float | None:
    if df is None or len(df) < period:
        return None
    tail = df.tail(period)
    hl_range = (tail["High"] - tail["Low"]).replace(0, np.nan)
    mfm = ((tail["Close"] - tail["Low"]) - (tail["High"] - tail["Close"])) / hl_range
    typical = (tail["High"] + tail["Low"] + tail["Close"]) / 3.0
    mfv = (mfm * tail["Volume"] * typical).fillna(0)
    val = mfv.sum()
    if pd.isna(val):
        return None
    return float(val)


def compute_flow_ratio(df: pd.DataFrame, period: int = 20) -> float | None:
    if df is None or len(df) < period:
        return None
    net = compute_net_dollar_flow(df, period)
    if net is None:
        return None
    tail = df.tail(period)
    typical = (tail["High"] + tail["Low"] + tail["Close"]) / 3.0
    total = (tail["Volume"] * typical).sum()
    if total == 0 or pd.isna(total):
        return None
    return float(net / total * 100.0)


def compute_up_down_vol_ratio(df: pd.DataFrame, period: int = 20) -> float | None:
    """Up-day volume / down-day volume. ``math.inf`` when there were no down days."""
    if df is None or period < 2 or len(df) < period + 1:
        return None
    tail = df.tail(period + 1)
    diffs = tail["Close"].diff().iloc[1:]
    vols = tail["Volume"].iloc[1:]
    up_vol = float(vols[diffs > 0].sum())
    down_vol = float(vols[diffs < 0].sum())
    if down_vol == 0:
        return None if up_vol == 0 else math.inf
    return up_vol / down_vol


def session_elapsed_fraction(now: datetime | None = None) -> float:
    """Fraction (0–1] of today's regular NYSE session that has elapsed, in New York time."""
    now = (now or datetime.now(NY_TZ)).astimezone(NY_TZ)
    minutes = now.hour * 60 + now.minute - SESSION_OPEN_MIN
    total = SESSION_CLOSE_MIN - SESSION_OPEN_MIN
    return min(max(minutes / total, 0.0), 1.0)


def last_bar_is_partial(df: pd.DataFrame, now: datetime | None = None) -> bool:
    """True when the last daily bar is today's still-forming session."""
    if df is None or df.empty:
        return False
    now = (now or datetime.now(NY_TZ)).astimezone(NY_TZ)
    last = pd.Timestamp(df.index[-1])
    last_date = (last.tz_convert(NY_TZ) if last.tzinfo else last).date()
    return last_date == now.date() and session_elapsed_fraction(now) < 1.0


def compute_rvol(df: pd.DataFrame, period: int = 20, partial_fraction: float | None = None) -> float | None:
    """Today's volume vs. the prior ``period`` days' average.

    If today's bar is still forming, ``partial_fraction`` (elapsed share of the
    session) is used to pro-rate the comparison so mid-day RVOL is not
    systematically below 1.
    """
    if df is None or len(df) < period + 1:
        return None
    prior = df["Volume"].iloc[-1 - period:-1]
    avg = prior.mean()
    today = df["Volume"].iloc[-1]
    if avg == 0 or pd.isna(avg):
        return None
    if partial_fraction is not None:
        if partial_fraction <= 0.02:      # first few minutes — too noisy to project
            return None
        avg = avg * partial_fraction
    return float(today / avg)


def compute_close_location(df: pd.DataFrame, period: int = 1) -> float | None:
    if df is None or len(df) < period:
        return None
    tail = df.tail(period)
    rng = (tail["High"] - tail["Low"]).replace(0, np.nan)
    clv = (tail["Close"] - tail["Low"]) / rng
    val = clv.mean()
    if pd.isna(val):
        return None
    return float(val)


def compute_obv_net_pct(df: pd.DataFrame, period: int = 20) -> float | None:
    """Net OBV over the window as a share of total volume: Σ(sign·Vol) / ΣVol × 100.

    Bounded to ±100 % and independent of where the download window starts, unlike
    a percent change of the cumulative OBV line (whose origin is arbitrary and can
    sit near zero, producing huge or sign-flipped numbers).
    """
    if df is None or period < 2 or len(df) < period + 1:
        return None
    tail = df.tail(period + 1)
    direction = np.sign(tail["Close"].diff().iloc[1:])
    vols = tail["Volume"].iloc[1:]
    total = float(vols.sum())
    if total == 0 or pd.isna(total):
        return None
    return float((direction * vols).sum() / total * 100.0)


def compute_mfi(df: pd.DataFrame, period: int = 14) -> float | None:
    if df is None or period < 2 or len(df) < period + 1:
        return None
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    money_flow = typical * df["Volume"]
    delta = typical.diff()
    pos_flow = money_flow.where(delta > 0, 0)
    neg_flow = money_flow.where(delta < 0, 0)
    pos_sum = pos_flow.tail(period).sum()
    neg_sum = neg_flow.tail(period).sum()
    if neg_sum == 0:
        return 100.0 if pos_sum > 0 else 50.0
    money_ratio = pos_sum / neg_sum
    val = 100.0 - (100.0 / (1.0 + money_ratio))
    if pd.isna(val):
        return None
    return float(val)


def compute_all_metrics(df: pd.DataFrame, now: datetime | None = None) -> dict:
    if df is None or df.empty:
        return {}
    periods = CMF_PERIODS  # (1, 5, 20)
    partial = session_elapsed_fraction(now) if last_bar_is_partial(df, now) else None
    return {
        "price_change": compute_period_returns(df, periods),
        "cmf":          {p: compute_cmf(df, p) for p in periods},
        "net_flow":     {p: compute_net_dollar_flow(df, p) for p in periods},
        "flow_ratio":   {p: compute_flow_ratio(df, p) for p in periods},
        "ud_vol":       {p: compute_up_down_vol_ratio(df, p) for p in periods},
        "rvol":         {p: compute_rvol(df, p, partial) for p in periods},
        "close_loc":    {p: compute_close_location(df, p) for p in periods},
        "mfi":          {p: compute_mfi(df, p) for p in periods},
        "obv_pct":      {p: compute_obv_net_pct(df, p) for p in periods},
        "partial_day":  partial is not None,
    }


# ---------------------------------------------------------------------------
# Historical bars (yfinance)
# ---------------------------------------------------------------------------

def _download_daily(yf_syms: list[str]) -> pd.DataFrame | None:
    try:
        # auto_adjust=True: split/dividend-adjusted OHLC, so multi-day returns,
        # OBV and up/down volume are not distorted by corporate actions.
        return yf.download(
            yf_syms,
            period="3mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        log.warning("yfinance download failed for %d symbols: %s", len(yf_syms), e)
        return None


def _extract(data: pd.DataFrame, yf_sym: str) -> pd.DataFrame | None:
    if data is None or data.empty:
        return None
    if isinstance(data.columns, pd.MultiIndex):
        if yf_sym not in data.columns.get_level_values(0):
            return None
        sub = data[yf_sym]
    else:
        sub = data
    sub = sub.dropna(how="all").dropna(subset=[c for c in ("High", "Low", "Close", "Volume") if c in sub.columns])
    return sub if not sub.empty else None


def _metrics_batch(symbols: list[str]) -> dict[str, dict]:
    yf_syms = [_yf_symbol(s) for s in symbols]
    data = _download_daily(yf_syms)
    out: dict[str, dict] = {}
    for orig, ys in zip(symbols, yf_syms):
        try:
            sub = _extract(data, ys)
            m = compute_all_metrics(sub) if sub is not None else {}
            if m:
                out[orig] = m
        except Exception as e:
            log.warning("metrics %s failed: %s", orig, e)
    return out


def fetch_metrics_map(symbols: tuple[str, ...]) -> dict[str, dict]:
    """Per-symbol cached metrics; only stale / missing symbols are downloaded.

    A symbol that fails is retried after METRICS_RETRY seconds instead of the
    empty result being cached for the whole hour.
    """
    now = time.time()
    out: dict[str, dict] = {}
    need: list[str] = []
    for s in symbols:
        hit = _metrics_store.get(s)
        if hit and now - hit[0] < METRICS_TTL:
            out[s] = hit[1]
            continue
        if _metrics_store.recently_failed(s, METRICS_RETRY):
            if hit:
                out[s] = hit[1]
            continue
        need.append(s)
    if need:
        fresh = _metrics_batch(need)
        for s in need:
            if s in fresh:
                _metrics_store.put(s, fresh[s])
                out[s] = fresh[s]
            else:
                _metrics_store.mark_failed(s)
                hit = _metrics_store.get(s)
                if hit:
                    out[s] = hit[1]
    return out


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _search_stock_raw(symbol: str) -> dict | None:
    quote = fetch_quote(symbol)
    profile = fetch_profile(symbol)

    df = None
    try:
        raw = yf.download(
            _yf_symbol(symbol),
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=True,
            group_by="column",
        )
        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            df = raw.dropna()
    except Exception as e:
        log.warning("yfinance search %s failed: %s", symbol, e)
        df = None

    period_changes: dict[int, float] = {}
    metrics: dict = {}
    if df is not None and not df.empty:
        period_changes = compute_period_returns(df, CMF_PERIODS)
        metrics = compute_all_metrics(df)

    if quote is not None:
        period_changes[1] = quote.change_pct

    if quote is None and profile is None and not period_changes and not metrics:
        return None

    return {
        "symbol": symbol,
        "quote": quote,
        "profile": profile,
        "period_changes": period_changes,
        "metrics": metrics,
    }


def search_stock(raw_symbol: str) -> dict | None:
    """Look up one ticker. Invalid input never reaches the network.

    Results (including "not found") are cached with a bounded size so random
    input cannot grow memory without limit; a "not found" caused by throttling
    is only remembered briefly.
    """
    symbol = normalize_symbol(raw_symbol)
    if symbol is None:
        return None
    hit = _search_store.get(symbol)
    if hit:
        res = hit[1]
        complete = res["quote"] is not None and res["profile"] is not None and bool(res["metrics"])
        # Partial results (e.g. a throttled quote) are only reused briefly.
        if time.time() - hit[0] < (SEARCH_TTL if complete else 60):
            return res
    if _search_store.recently_failed(symbol, 60):
        return None
    result = _search_stock_raw(symbol)
    if result is None:
        _search_store.mark_failed(symbol)
    else:
        _search_store.put(symbol, result)
    return result
