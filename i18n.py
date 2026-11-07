"""Tiny i18n helper. English is the default; Chinese is the alternate."""
from html import escape

import streamlit as st

LANGUAGES = {"en": "English", "zh": "中文"}
DEFAULT_LANG = "en"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # App shell
        "app_title": "📊 US Sector Money Flow",
        "language_label": "Language / 语言",
        "settings": "Settings",
        "refresh_interval": "Refresh interval (seconds)",
        "cmf_windows_note": "CMF windows: 1D / 5D / 20D",
        "data_source_note": "Data: Finnhub (real-time quotes) + yfinance (historical bars)",
        "legend_main": (
            "🟢 Green = inflow / up<br>"
            "🔴 Red = outflow / down<br>"
            "Shade ~ magnitude<br><br>"
            "💡 Click a sector card to drill into stocks"
        ),
        "legend_detail": (
            "🟢 Green = inflow / up<br>"
            "🔴 Red = outflow / down"
        ),
        "candidate_pool": "Candidate pool: {n} constituent stocks",
        "back_home": "← Back to home",
        # Search
        "search_input_label": "Ticker",
        "search_placeholder": "🔍  Enter a US ticker and press Enter — e.g. AAPL / NVDA / TSLA",
        "search_btn": "Search",
        "search_spinner": "Searching {sym}…",
        "search_not_found": "No data found for **{sym}** — check the ticker.",
        "search_invalid": "That does not look like a US ticker (letters/digits, optional .B / -B class suffix).",
        # Fragments
        "loading_data": "Loading data…",
        "fetching_stocks": "Fetching {n} stocks…",
        "no_stocks_data": "No data yet — try again in a moment.",
        "missing_symbols": "No data yet for: {syms} (retrying automatically; persistent gaps usually mean a delisted ticker in sectors.py)",
        "no_constituents": "No constituent list configured for {code}",
        "loading_net_flow": "Loading Net $Flow…",
        "loading_quotes": "Loading quotes…",
        "last_update": "Last update: {time} · silent refresh every {sec}s",
        "api_key_missing": "FINNHUB_API_KEY not detected — configure it in the `.env` file in the project root.",
        # Section titles on detail page
        "sec_mcap": "💰 Market Cap Top 10",
        "sec_flow": "🌊 Most Extreme Money Flow Top 10 (|Net $Flow 20D|)",
        "sec_movers": "⚡ Biggest Movers Top 10 (|%|)",
        # Card labels
        "market_cap_short": "Cap",
        "market_cap_full": "Market cap",
        "sources_footer": "Sources: Finnhub + yfinance · Green = inflow/up · Red = outflow/down",
        # Table header + indicator row labels
        "tbl_header_indicator": "Indicator",
        "ind_price_change": "Change",
        "ind_cmf": "CMF",
        "ind_net_flow": "Net $Flow",
        "ind_flow_ratio": "Flow %",
        "ind_ud_vol": "Up/Dn Vol",
        "ind_rvol": "RVOL",
        "ind_close_loc": "Close Loc",
        "ind_mfi": "MFI",
        "ind_obv": "OBV Net %",
        # Sector names (English is authoritative already)
    },
    "zh": {
        "app_title": "📊 美股板块资金流",
        "language_label": "Language / 语言",
        "settings": "设置",
        "refresh_interval": "刷新间隔(秒)",
        "cmf_windows_note": "CMF 窗口:1D / 5D / 20D",
        "data_source_note": "数据源:Finnhub(实时报价)+ yfinance(历史 K 线)",
        "legend_main": (
            "🟢 绿 = 资金流入 / 上涨<br>"
            "🔴 红 = 资金流出 / 下跌<br>"
            "颜色深浅 ~ 幅度大小<br><br>"
            "💡 点击板块卡片查看个股"
        ),
        "legend_detail": (
            "🟢 绿 = 资金流入 / 上涨<br>"
            "🔴 红 = 资金流出 / 下跌"
        ),
        "candidate_pool": "候选池:{n} 只主要成分股",
        "back_home": "← 返回主页",
        "search_input_label": "股票代码",
        "search_placeholder": "🔍  输入股票代码回车搜索,如 AAPL / NVDA / TSLA",
        "search_btn": "搜索",
        "search_spinner": "搜索 {sym}…",
        "search_not_found": "未找到 **{sym}** 的数据,请检查代码是否正确。",
        "search_invalid": "输入的不是有效的美股代码(字母/数字,可带 .B / -B 类别后缀)。",
        "loading_data": "数据加载中…",
        "fetching_stocks": "拉取 {n} 只股票数据…",
        "no_stocks_data": "没有拿到任何股票数据,请稍后再试",
        "missing_symbols": "暂无数据:{syms}(会自动重试;长期缺失通常表示 sectors.py 中的代码已退市)",
        "no_constituents": "未配置 {code} 的成分股列表",
        "loading_net_flow": "Net $Flow 数据加载中…",
        "loading_quotes": "报价数据加载中…",
        "last_update": "最后更新:{time} · 每 {sec}s 静默刷新",
        "api_key_missing": "未检测到 FINNHUB_API_KEY,请在项目根目录的 `.env` 文件中配置。",
        "sec_mcap": "💰 市值最大 Top 10",
        "sec_flow": "🌊 资金流最剧烈 Top 10(|Net $Flow 20D|)",
        "sec_movers": "⚡ 涨跌幅最大 Top 10(|%|)",
        "market_cap_short": "市值",
        "market_cap_full": "市值",
        "sources_footer": "数据源:Finnhub + yfinance · 绿=资金流入/上涨 · 红=流出/下跌",
        "tbl_header_indicator": "指标",
        "ind_price_change": "涨跌幅",
        "ind_cmf": "CMF",
        "ind_net_flow": "Net $Flow",
        "ind_flow_ratio": "Flow %",
        "ind_ud_vol": "Up/Dn Vol",
        "ind_rvol": "RVOL",
        "ind_close_loc": "Close Loc",
        "ind_mfi": "MFI",
        "ind_obv": "OBV Net %",
    },
}


def get_lang() -> str:
    return st.session_state.get("lang", DEFAULT_LANG)


def t(key: str, **fmt) -> str:
    lang = get_lang()
    val = TRANSLATIONS.get(lang, {}).get(key)
    if val is None:
        val = TRANSLATIONS[DEFAULT_LANG].get(key, key)
    return val.format(**fmt) if fmt else val


def sector_display_html(name_en: str, name_cn: str) -> str:
    """Sector card title. English mode shows only English name; Chinese mode shows both."""
    if get_lang() == "zh":
        return f'{escape(name_cn)} <span style="opacity:.7;font-weight:500;font-size:13px;">{escape(name_en)}</span>'
    return escape(name_en)


def sector_page_title(code: str, name_en: str, name_cn: str) -> str:
    """Detail page H1."""
    if get_lang() == "zh":
        return f"{code} · {name_cn} {name_en}"
    return f"{code} · {name_en}"
