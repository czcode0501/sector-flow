import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

CMF_PERIOD = 20
CMF_PERIODS = (1, 5, 20)


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


def _yf_symbol(sym: str) -> str:
    return sym.replace(".", "-")


def fetch_quote(symbol: str) -> Quote | None:
    if not FINNHUB_API_KEY:
        return None
    try:
        r = requests.get(
            f"{FINNHUB_BASE}/quote",
            params={"symbol": symbol, "token": FINNHUB_API_KEY},
            timeout=5,
        )
        r.raise_for_status()
        d = r.json()
        if d.get("c") in (None, 0):
            return None
        return Quote(
            symbol=symbol,
            price=float(d["c"]),
            change_pct=float(d.get("dp") or 0.0),
            prev_close=float(d.get("pc") or 0.0),
            ts=int(d.get("t") or 0),
        )
    except Exception:
        return None


def fetch_profile(symbol: str) -> Profile | None:
    if not FINNHUB_API_KEY:
        return None
    try:
        r = requests.get(
            f"{FINNHUB_BASE}/stock/profile2",
            params={"symbol": symbol, "token": FINNHUB_API_KEY},
            timeout=5,
        )
        r.raise_for_status()
        d = r.json()
        if not d:
            return None
        mc = d.get("marketCapitalization") or 0
        return Profile(
            symbol=symbol,
            name=d.get("name") or symbol,
            market_cap=float(mc) * 1e6,
        )
    except Exception:
        return None


@st.cache_data(ttl=15)
def _fetch_quotes_raw(symbols: tuple[str, ...]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=15) as ex:
        for sym, q in zip(symbols, ex.map(fetch_quote, symbols)):
            if q:
                out[sym] = asdict(q)
    return out


def fetch_quotes(symbols: tuple[str, ...]) -> dict[str, Quote]:
    raw = _fetch_quotes_raw(symbols)
    return {s: Quote(**d) for s, d in raw.items()}


@st.cache_data(ttl=86400)
def _fetch_profiles_raw(symbols: tuple[str, ...]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=15) as ex:
        for sym, p in zip(symbols, ex.map(fetch_profile, symbols)):
            if p:
                out[sym] = asdict(p)
    return out


def fetch_profiles(symbols: tuple[str, ...]) -> dict[str, Profile]:
    raw = _fetch_profiles_raw(symbols)
    return {s: Profile(**d) for s, d in raw.items()}


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
            try:
                v = (close.iloc[-1] / close.iloc[-1 - p] - 1) * 100
                if pd.notna(v):
                    out[p] = float(v)
            except Exception:
                continue
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
    if df is None or period < 2 or len(df) < period + 1:
        return None
    tail = df.tail(period + 1)
    diffs = tail["Close"].diff().iloc[1:]
    vols = tail["Volume"].iloc[1:]
    up_vol = float(vols[diffs > 0].sum())
    down_vol = float(vols[diffs < 0].sum())
    if down_vol == 0:
        return None if up_vol == 0 else 999.0
    return up_vol / down_vol


def compute_rvol(df: pd.DataFrame, period: int = 20) -> float | None:
    if df is None or len(df) < period + 1:
        return None
    prior = df["Volume"].iloc[-1 - period:-1]
    avg = prior.mean()
    today = df["Volume"].iloc[-1]
    if avg == 0 or pd.isna(avg):
        return None
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


def compute_obv_pct_change(df: pd.DataFrame, period: int = 20) -> float | None:
    if df is None or len(df) < period + 1:
        return None
    direction = np.sign(df["Close"].diff()).fillna(0)
    obv = (direction * df["Volume"]).cumsum()
    prior = obv.iloc[-1 - period]
    now = obv.iloc[-1]
    if prior == 0 or pd.isna(prior):
        return None
    return float((now - prior) / abs(prior) * 100.0)


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


def compute_all_metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {}
    periods = CMF_PERIODS  # (1, 5, 20)
    return {
        "price_change": compute_period_returns(df, periods),
        "cmf":          {p: compute_cmf(df, p) for p in periods},
        "net_flow":     {p: compute_net_dollar_flow(df, p) for p in periods},
        "flow_ratio":   {p: compute_flow_ratio(df, p) for p in periods},
        "ud_vol":       {p: compute_up_down_vol_ratio(df, p) for p in periods},
        "rvol":         {p: compute_rvol(df, p) for p in periods},
        "close_loc":    {p: compute_close_location(df, p) for p in periods},
        "mfi":          {p: compute_mfi(df, p) for p in periods},
        "obv_pct":      {p: compute_obv_pct_change(df, p) for p in periods},
    }


def _download_daily(symbols: tuple[str, ...]) -> tuple[pd.DataFrame | None, dict[str, str]]:
    yf_syms = [_yf_symbol(s) for s in symbols]
    yf_to_orig = dict(zip(yf_syms, symbols))
    try:
        data = yf.download(
            yf_syms,
            period="3mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
        return data, yf_to_orig
    except Exception:
        return None, yf_to_orig


@st.cache_data(ttl=3600)
def fetch_metrics_map(symbols: tuple[str, ...]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    data, yf_to_orig = _download_daily(symbols)
    if data is None:
        return out
    for ys, orig in yf_to_orig.items():
        try:
            if isinstance(data.columns, pd.MultiIndex):
                sub = data[ys].dropna()
            else:
                sub = data.dropna()
            m = compute_all_metrics(sub)
            if m:
                out[orig] = m
        except Exception:
            continue
    return out


@st.cache_data(ttl=900)
def _search_stock_raw(symbol: str) -> dict | None:
    symbol = symbol.upper().strip()
    if not symbol:
        return None

    quote = fetch_quote(symbol)
    profile = fetch_profile(symbol)

    yf_sym = _yf_symbol(symbol)
    df = None
    try:
        raw = yf.download(
            yf_sym,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            group_by="column",
        )
        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            df = raw.dropna()
    except Exception:
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
        "quote_dict": asdict(quote) if quote else None,
        "profile_dict": asdict(profile) if profile else None,
        "period_changes": period_changes,
        "metrics": metrics,
    }


def search_stock(symbol: str) -> dict | None:
    raw = _search_stock_raw(symbol)
    if raw is None:
        return None
    return {
        "symbol": raw["symbol"],
        "quote": Quote(**raw["quote_dict"]) if raw["quote_dict"] else None,
        "profile": Profile(**raw["profile_dict"]) if raw["profile_dict"] else None,
        "period_changes": raw["period_changes"],
        "metrics": raw["metrics"],
    }
