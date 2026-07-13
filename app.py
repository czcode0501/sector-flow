from datetime import datetime

import streamlit as st

from data import (
    FINNHUB_API_KEY,
    fetch_metrics_map,
    fetch_profiles,
    fetch_quotes,
    search_stock,
)
from i18n import LANGUAGES, sector_display_html, sector_page_title, t
from sectors import SECTOR_NAME, SECTOR_STOCKS, SECTORS

st.set_page_config(page_title="Sector Flow", page_icon="📊", layout="wide")

st.markdown(
    """
<style>
/* Hide Streamlit's "Running" indicator and top-right toolbar so refresh is invisible */
[data-testid="stStatusWidget"],
[data-testid="stToolbar"],
[data-testid="stDeployButton"],
[data-testid="stAppDeployButton"],
div[class*="StatusWidget"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; }

.block-container { padding-top: 1.5rem; padding-bottom: 1rem; max-width: 1400px; }
.card {
    border-radius: 14px;
    padding: 16px 18px;
    color: white;
    min-height: 130px;
    box-shadow: 0 2px 10px rgba(0,0,0,.15);
    display: flex; flex-direction: column; justify-content: space-between;
    text-decoration: none;
}
a.card { color: white !important; }
a.card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,.25); transition: all .15s ease; }
.card .sym { font-size: 13px; opacity: .85; letter-spacing: .5px; }
.card .name { font-size: 18px; font-weight: 700; margin-top: 2px; }
.card .row { display: flex; justify-content: space-between; margin-top: 8px; gap: 8px; }
.card .label { font-size: 11px; opacity: .8; text-transform: uppercase; letter-spacing: .5px; }
.card .val { font-size: 22px; font-weight: 700; line-height: 1.1; }
.card .val.sub { font-size: 18px; }
.card .missing { font-size: 14px; opacity: .7; font-weight: 500; }
.card .cmf-block { margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,.2); }
.card .cmf-block .title { font-size: 10px; opacity: .8; text-transform: uppercase; letter-spacing: .4px; margin-bottom: 4px; }
.card .cmf-block .items { display: flex; justify-content: space-between; }
.card .cmf-block .item { text-align: center; flex: 1; }
.card .cmf-block .item .p { font-size: 10px; opacity: .75; }
.card .cmf-block .item .v { font-size: 15px; font-weight: 700; line-height: 1.1; margin-top: 2px; }
.legend { font-size: 12px; opacity: .7; }

.search-result {
    border-radius: 14px;
    padding: 18px 20px;
    color: white;
    box-shadow: 0 2px 10px rgba(0,0,0,.15);
    margin-top: 8px;
    margin-bottom: 20px;
}
.search-result .head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }
.search-result .head .sym { font-size: 26px; font-weight: 800; }
.search-result .head .price { font-size: 20px; font-weight: 700; opacity: .9; }
.search-result .name { font-size: 14px; opacity: .8; margin-bottom: 14px; }
.search-result .row-title { font-size: 12px; opacity: .8; text-transform: uppercase; letter-spacing: .4px; margin-top: 10px; margin-bottom: 4px; }
.search-result .row-values { display: flex; gap: 12px; }
.search-result .row-values .cell { flex: 1; text-align: center; padding: 8px; background: rgba(0,0,0,.15); border-radius: 8px; }
.search-result .row-values .cell .p { font-size: 11px; opacity: .8; }
.search-result .row-values .cell .v { font-size: 20px; font-weight: 700; margin-top: 2px; }
.search-result .foot { display: flex; justify-content: space-between; margin-top: 12px; font-size: 12px; opacity: .8; }

.stock-card {
    border-radius: 10px;
    padding: 10px 12px;
    color: white;
    box-shadow: 0 1px 6px rgba(0,0,0,.15);
    margin-bottom: 8px;
}
.stock-card .top { display: flex; justify-content: space-between; align-items: baseline; }
.stock-card .sym { font-size: 15px; font-weight: 700; }
.stock-card .price { font-size: 12px; opacity: .85; }
.stock-card .name { font-size: 11px; opacity: .75; margin-top: 2px; height: 14px; overflow: hidden; }
.stock-card .metrics { display: flex; justify-content: space-between; margin-top: 6px; gap: 8px; }
.stock-card .metric .lbl { font-size: 9px; opacity: .75; text-transform: uppercase; letter-spacing: .3px; }
.stock-card .metric .val { font-size: 15px; font-weight: 700; }
.stock-card .metric .val.sub { font-size: 13px; }
.stock-card .mcap { font-size: 10px; opacity: .8; }

.cmf-row { margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,.18); }
.cmf-title { font-size: 9px; opacity: .75; text-transform: uppercase; letter-spacing: .3px; margin-bottom: 3px; }
.cmf-values { display: flex; justify-content: space-between; }
.cmf-item { display: flex; flex-direction: column; align-items: center; flex: 1; }
.cmf-item .p { font-size: 9px; opacity: .7; }
.cmf-item .v { font-size: 13px; font-weight: 700; line-height: 1.1; margin-top: 1px; }
.cmf-in { color: #86efac; }
.cmf-out { color: #fca5a5; }
.cmf-na { opacity: .5; font-weight: 500; }

@keyframes number-flip {
  0%   { transform: rotateX(-90deg); opacity: 0; }
  55%  { transform: rotateX(15deg);  opacity: 1; }
  100% { transform: rotateX(0deg);   opacity: 1; }
}
.card .val,
.stock-card .metric .val,
.mtbl .cell {
  display: inline-block;
  transform-origin: center center;
  backface-visibility: hidden;
  animation: number-flip 0.45s ease-out;
}
.card, .stock-card, .search-result {
  transition: background-color 0.35s ease;
  overflow: hidden;
}

/* Metrics table — 4-column grid: label + 1D + 5D + 20D */
.mtbl {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255,255,255,.2);
  display: grid;
  grid-template-columns: minmax(0, 82px) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 2px 4px;
  font-variant-numeric: tabular-nums;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
.mtbl .row { display: contents; }
.mtbl .lbl {
  font-size: 11px;
  color: #cbd5e1;
  align-self: center;
  padding: 2px 0;
  white-space: nowrap;
  letter-spacing: .2px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mtbl .cell {
  text-align: center;
  padding: 3px 2px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mtbl .head {
  font-size: 10px;
  color: #94a3b8;
  text-align: center;
  font-weight: 500;
  letter-spacing: .3px;
  padding-bottom: 2px;
}
.mtbl .head.lbl { text-align: left; }
.mtbl .cell.pos { color: #4ade80; }
.mtbl .cell.neg { color: #f87171; }
.mtbl .cell.neu { color: #e5e7eb; opacity: .5; }

/* Compact variant on the small sector cards (narrow columns) */
.card .mtbl { grid-template-columns: minmax(0, 66px) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr); }
.card .mtbl .lbl { font-size: 10px; }
.card .mtbl .cell { font-size: 11px; padding: 2px 1px; }
.card .mtbl .head { font-size: 9px; }

/* Stock cards live in dense 5- or 2-column grids — extra compact */
.stock-card .mtbl {
  grid-template-columns: minmax(0, 58px) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 1px 3px;
  margin-top: 8px;
  padding-top: 6px;
}
.stock-card .mtbl .lbl { font-size: 10px; }
.stock-card .mtbl .cell { font-size: 10.5px; padding: 2px 1px; font-weight: 700; }
.stock-card .mtbl .head { font-size: 9px; padding-bottom: 1px; }

/* Roomier layout for the full-width search result */
.search-result .mtbl {
  grid-template-columns: 130px 1fr 1fr 1fr;
  gap: 4px 12px;
  margin-top: 16px;
  padding-top: 14px;
}
.search-result .mtbl .lbl { font-size: 13px; }
.search-result .mtbl .cell { font-size: 16px; padding: 5px 4px; }

.section-title { font-size: 18px; font-weight: 700; margin: 12px 0 8px; }
</style>
""",
    unsafe_allow_html=True,
)


def color_for(pct: float | None, scale: float = 3.0) -> str:
    """Dark card background tinted subtly by direction. Numbers stay bright."""
    if pct is None:
        return "#1e293b"  # slate-800 neutral
    magnitude = min(abs(pct) / scale, 1.0)
    if pct >= 0:
        # Deep emerald wash
        r = int(6 + 6 * magnitude)     # 6–12
        g = int(46 + 34 * magnitude)   # 46–80
        b = int(28 + 6 * magnitude)    # 28–34
        return f"rgb({r},{g},{b})"
    # Deep crimson wash
    r = int(66 + 44 * magnitude)       # 66–110
    g = int(18 + 6 * magnitude)        # 18–24
    b = int(28 + 6 * magnitude)        # 28–34
    return f"rgb({r},{g},{b})"


def fmt_pct(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2f}%"


def fmt_mcap(v: float | None) -> str:
    if v is None or v <= 0:
        return "—"
    if v >= 1e12:
        return f"${v/1e12:.2f}T"
    if v >= 1e9:
        return f"${v/1e9:.1f}B"
    if v >= 1e6:
        return f"${v/1e6:.0f}M"
    return f"${v:.0f}"


def fmt_dollar_signed(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ("−" if v < 0 else "")
    a = abs(v)
    if a >= 1e12:
        return f"{sign}${a/1e12:.1f}T"
    if a >= 1e9:
        return f"{sign}${a/1e9:.1f}B"
    if a >= 1e6:
        return f"{sign}${a/1e6:.0f}M"
    if a >= 1e3:
        return f"{sign}${a/1e3:.0f}K"
    return f"{sign}${a:.0f}"


def fmt_ratio(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}x"


def _sign_cls(v: float | None, threshold: float = 0.0) -> str:
    if v is None:
        return "neu"
    if v > threshold:
        return "pos"
    if v < threshold:
        return "neg"
    return "neu"


def _ind_row(label: str, val: str, cls: str) -> str:
    return f'<div class="ind"><span class="ind-lbl">{label}</span><span class="ind-val {cls}">{val}</span></div>'


INDICATOR_ROWS = [
    ("ind_price_change", "price_change", "pct"),
    ("ind_cmf",          "cmf",          "pct"),
    ("ind_net_flow",     "net_flow",     "dollar"),
    ("ind_flow_ratio",   "flow_ratio",   "pct"),
    ("ind_ud_vol",       "ud_vol",       "ratio"),
    ("ind_rvol",         "rvol",         "ratio"),
    ("ind_close_loc",    "close_loc",    "clv"),
    ("ind_mfi",          "mfi",          "mfi"),
    ("ind_obv",          "obv_pct",      "pct"),
]

PERIODS = (1, 5, 20)


def _metric_cell(v, kind: str) -> str:
    if v is None:
        return '<div class="cell neu">—</div>'
    if kind == "pct":
        cls = "pos" if v > 0 else ("neg" if v < 0 else "neu")
        sign = "+" if v > 0 else ""
        return f'<div class="cell {cls}">{sign}{v:.2f}%</div>'
    if kind == "dollar":
        cls = "pos" if v > 0 else ("neg" if v < 0 else "neu")
        return f'<div class="cell {cls}">{fmt_dollar_signed(v)}</div>'
    if kind == "ratio":
        cls = "pos" if v > 1 else ("neg" if v < 1 else "neu")
        return f'<div class="cell {cls}">{v:.2f}x</div>'
    if kind == "clv":
        cls = "pos" if v > 0.5 else ("neg" if v < 0.5 else "neu")
        return f'<div class="cell {cls}">{v:.2f}</div>'
    if kind == "mfi":
        cls = "pos" if v > 50 else ("neg" if v < 50 else "neu")
        return f'<div class="cell {cls}">{v:.0f}</div>'
    return f'<div class="cell neu">{v}</div>'


def render_metrics_table_html(metrics: dict | None, live_change_1d: float | None = None) -> str:
    if not metrics:
        return ""
    parts = ['<div class="mtbl">']
    parts.append(
        f'<div class="row">'
        f'<div class="head lbl">{t("tbl_header_indicator")}</div>'
        f'<div class="head">1D</div><div class="head">5D</div><div class="head">20D</div>'
        f'</div>'
    )
    for label_key, key, kind in INDICATOR_ROWS:
        vals = metrics.get(key) or {}
        if not isinstance(vals, dict):
            vals = {}
        cells = []
        for p in PERIODS:
            v = vals.get(p)
            if key == "price_change" and p == 1 and live_change_1d is not None:
                v = live_change_1d
            cells.append(_metric_cell(v, kind))
        parts.append(f'<div class="row"><div class="lbl">{t(label_key)}</div>{"".join(cells)}</div>')
    parts.append('</div>')
    return "".join(parts)


def _period_cells_html(vals: dict[int, float], cell_cls: str = "item") -> str:
    parts = []
    for period, lbl in CMF_LABELS:
        v = vals.get(period)
        if v is None:
            inner = '<div class="v cmf-na">—</div>'
        else:
            cls = "cmf-in" if v >= 0 else "cmf-out"
            sign = "+" if v > 0 else ""
            inner = f'<div class="v {cls}">{sign}{v:.2f}%</div>'
        parts.append(f'<div class="{cell_cls}"><div class="p">{lbl}</div>{inner}</div>')
    return "".join(parts)


def render_search_result(r: dict) -> str:
    sym = r["symbol"]
    q = r["quote"]
    p = r["profile"]
    changes = r["period_changes"]
    metrics = r.get("metrics", {}) or {}

    change_1d = changes.get(1) if q is None else q.change_pct
    bg = color_for(change_1d)
    price = f"${q.price:,.2f}" if q else "—"
    name = p.name if p else sym
    mcap = fmt_mcap(p.market_cap if p else None)
    table_html = render_metrics_table_html(metrics, live_change_1d=change_1d)

    return f"""
    <div class="search-result" style="background:{bg};">
      <div class="head">
        <div>
          <div class="sym">{sym}</div>
          <div class="name">{name}</div>
        </div>
        <div><div class="price">{price}</div></div>
      </div>
      {table_html}
      <div class="foot">
        <div>{t("market_cap_full")}: {mcap}</div>
        <div>{t("sources_footer")}</div>
      </div>
    </div>
    """


def render_main():
    st.title(t("app_title"))

    with st.sidebar:
        st.subheader(t("settings"))
        refresh_sec = st.slider(t("refresh_interval"), 5, 60, 15, step=5)
        st.caption(t("cmf_windows_note"))
        st.caption(t("data_source_note"))
        st.markdown("---")
        st.markdown(
            f'<div class="legend">{t("legend_main")}</div>',
            unsafe_allow_html=True,
        )

    # Top-of-page ticker search
    sc1, sc2 = st.columns([5, 1])
    with sc1:
        ticker = st.text_input(
            t("search_input_label"),
            placeholder=t("search_placeholder"),
            label_visibility="collapsed",
            key="search_ticker",
        )
    with sc2:
        st.button(t("search_btn"), use_container_width=True, key="search_btn")

    if ticker and ticker.strip():
        sym_up = ticker.strip().upper()
        with st.spinner(t("search_spinner", sym=sym_up)):
            result = search_stock(ticker.strip())
        if result is None:
            st.warning(t("search_not_found", sym=sym_up))
        else:
            st.markdown(render_search_result(result), unsafe_allow_html=True)

    st.markdown("---")

    @st.fragment(run_every=f"{refresh_sec}s")
    def sector_grid():
        symbols = tuple(s[0] for s in SECTORS)
        quotes = fetch_quotes(symbols)
        metrics_map = fetch_metrics_map(symbols)

        def _inflow_key(sec):
            code = sec[0]
            cmf1 = ((metrics_map.get(code) or {}).get("cmf") or {}).get(1)
            return cmf1 if cmf1 is not None else float("-inf")

        sorted_sectors = sorted(SECTORS, key=_inflow_key, reverse=True)

        cols = st.columns(4, gap="small")
        for idx, (sym, name_en, name_cn) in enumerate(sorted_sectors):
            q = quotes.get(sym)
            change_pct = q.change_pct if q else None
            metrics = metrics_map.get(sym, {})

            bg = color_for(change_pct)
            price_html = f"${q.price:,.2f}" if q else "—"
            table_html = render_metrics_table_html(metrics, live_change_1d=change_pct)
            name_html = sector_display_html(name_en, name_cn)

            card = f"""
            <a class="card" href="?sector={sym}" target="_self" style="background:{bg};">
              <div>
                <div class="sym">{sym} · {price_html}</div>
                <div class="name">{name_html}</div>
              </div>
              {table_html}
            </a>
            """
            with cols[idx % 4]:
                st.markdown(card, unsafe_allow_html=True)
                st.write("")

        st.caption(t("last_update", time=datetime.now().strftime('%H:%M:%S'), sec=refresh_sec))

    sector_grid()


CMF_LABELS = [(1, "1D"), (5, "5D"), (20, "20D")]


def _cmf_item_html(period_label: str, v: float | None) -> str:
    if v is None:
        return f'<div class="cmf-item"><div class="p">{period_label}</div><div class="v cmf-na">—</div></div>'
    cls = "cmf-in" if v >= 0 else "cmf-out"
    sign = "+" if v > 0 else ""
    return f'<div class="cmf-item"><div class="p">{period_label}</div><div class="v {cls}">{sign}{v:.1f}%</div></div>'


def render_stock_card(sym: str, quote, profile, metrics: dict | None):
    change_pct = quote.change_pct if quote else None
    bg = color_for(change_pct)
    price = f"${quote.price:,.2f}" if quote else "—"
    name = profile.name if profile else sym
    mcap = fmt_mcap(profile.market_cap if profile else None)

    table_html = render_metrics_table_html(metrics, live_change_1d=change_pct)

    return f"""
    <div class="stock-card" style="background:{bg};">
      <div class="top">
        <div class="sym">{sym}</div>
        <div class="price">{price}</div>
      </div>
      <div class="name">{name} · <span style="opacity:.75;font-weight:500;">{t("market_cap_short")} {mcap}</span></div>
      {table_html}
    </div>
    """


def render_detail(sector_code: str):
    name_en, name_cn = SECTOR_NAME.get(sector_code, ("Unknown", "未知"))

    top_col1, top_col2 = st.columns([1, 5])
    with top_col1:
        if st.button(t("back_home"), use_container_width=True, key="back_btn"):
            st.query_params.clear()
            st.rerun()
    with top_col2:
        st.title(sector_page_title(sector_code, name_en, name_cn))

    stocks = SECTOR_STOCKS.get(sector_code, [])
    if not stocks:
        st.warning(t("no_constituents", code=sector_code))
        return

    with st.sidebar:
        if st.button(t("back_home"), use_container_width=True, key="back_btn_sidebar"):
            st.query_params.clear()
            st.rerun()
        st.markdown("---")
        st.subheader(t("settings"))
        refresh_sec = st.slider(t("refresh_interval"), 5, 60, 15, step=5, key="ref_detail")
        st.caption(t("candidate_pool", n=len(stocks)))
        st.markdown("---")
        st.markdown(
            f'<div class="legend">{t("legend_detail")}</div>',
            unsafe_allow_html=True,
        )

    @st.fragment(run_every=f"{refresh_sec}s")
    def detail_grid():
        with st.spinner(t("fetching_stocks", n=len(stocks))):
            symbols = tuple(stocks)
            quotes = fetch_quotes(symbols)
            profiles = fetch_profiles(symbols)
            metrics_map = fetch_metrics_map(symbols)

        universe = []
        for s in stocks:
            q = quotes.get(s)
            p = profiles.get(s)
            m = metrics_map.get(s, {})
            if q is None and p is None:
                continue
            cmf_periods = m.get("cmf") or {}
            cmf_20 = cmf_periods.get(20)
            universe.append({
                "sym": s,
                "quote": q,
                "profile": p,
                "metrics": m,
                "change_pct": q.change_pct if q else 0.0,
                "cmf_val": cmf_20 if cmf_20 is not None else 0.0,
                "mcap": p.market_cap if p else 0.0,
            })

        if not universe:
            st.error(t("no_stocks_data"))
            return

        st.markdown(f'<div class="section-title">{t("sec_mcap")}</div>', unsafe_allow_html=True)
        top_mcap = sorted(universe, key=lambda x: x["mcap"], reverse=True)[:10]
        cols = st.columns(5, gap="small")
        for i, item in enumerate(top_mcap):
            with cols[i % 5]:
                st.markdown(
                    render_stock_card(item["sym"], item["quote"], item["profile"], item["metrics"]),
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        left, right = st.columns(2, gap="medium")

        with left:
            st.markdown(f'<div class="section-title">{t("sec_flow")}</div>', unsafe_allow_html=True)
            top_cmf = sorted(
                [x for x in universe if (x["metrics"].get("net_flow") or {}).get(20) is not None],
                key=lambda x: abs((x["metrics"].get("net_flow") or {}).get(20) or 0),
                reverse=True,
            )[:10]
            if not top_cmf:
                st.info(t("loading_net_flow"))
            else:
                sub_cols = st.columns(2, gap="small")
                for i, item in enumerate(top_cmf):
                    with sub_cols[i % 2]:
                        st.markdown(
                            render_stock_card(item["sym"], item["quote"], item["profile"], item["metrics"]),
                            unsafe_allow_html=True,
                        )

        with right:
            st.markdown(f'<div class="section-title">{t("sec_movers")}</div>', unsafe_allow_html=True)
            top_change = sorted(
                [x for x in universe if x["quote"] is not None],
                key=lambda x: abs(x["change_pct"]),
                reverse=True,
            )[:10]
            if not top_change:
                st.info(t("loading_quotes"))
            else:
                sub_cols = st.columns(2, gap="small")
                for i, item in enumerate(top_change):
                    with sub_cols[i % 2]:
                        st.markdown(
                            render_stock_card(item["sym"], item["quote"], item["profile"], item["metrics"]),
                            unsafe_allow_html=True,
                        )

        st.caption(t("last_update", time=datetime.now().strftime('%H:%M:%S'), sec=refresh_sec))

    detail_grid()


# Language selector — always at the very top of the sidebar
with st.sidebar:
    st.selectbox(
        t("language_label"),
        options=list(LANGUAGES.keys()),
        format_func=lambda code: LANGUAGES[code],
        index=0,
        key="lang",
    )
    st.markdown("---")

# Routing
if not FINNHUB_API_KEY:
    st.error(t("api_key_missing"))
    st.stop()

params = st.query_params
sector = params.get("sector")

if sector and sector in SECTOR_NAME:
    render_detail(sector)
else:
    render_main()
