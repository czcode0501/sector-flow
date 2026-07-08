# Sector Flow — US Stock Sector Money-Flow Dashboard

A real-time dashboard for tracking money flow across the 11 SPDR Select Sector ETFs and their top holdings. Built with Streamlit + Finnhub + yfinance.

<p align="center">
  <em>Dark-mode dashboard · 9 indicators × 3 time windows (1D / 5D / 20D) · Silent auto-refresh · Click-through drill-down · Ticker search</em>
</p>

---

## Features

- **11 sector ETFs at a glance** — Cards sorted live by 1D CMF (strongest inflow first)
- **Drill into any sector** — Top 10 by market cap, most extreme net-dollar-flow, largest movers
- **Ticker search** — Any US stock, full metrics table
- **9 indicators, 3 time windows each**:

| Indicator | Meaning |
|---|---|
| **涨跌幅 / Price Change** | Close vs. N-day prior close, in % |
| **CMF** | Chaikin Money Flow — buy/sell pressure by close location × volume |
| **Net $Flow** | Net directional dollar volume (approx. buy − sell) |
| **Flow %** | Net flow ÷ total dollar volume |
| **Up/Dn Vol** | Up-day volume ÷ down-day volume |
| **RVOL** | Today's volume ÷ N-day average volume |
| **Close Loc** | Close position within day range (0 = low, 1 = high) |
| **MFI** | Money Flow Index — volume-weighted RSI |
| **OBV Δ%** | On-Balance Volume change over N periods |

- **Zero-flicker refresh** — Uses Streamlit `@st.fragment(run_every=...)`, only the data area re-renders. No page flash.
- **Flip-in animations** — Numbers "flip" like a rolodex when new data arrives.
- **Desktop shortcut** — Optional one-click launcher on Windows.

## Tech stack

- **UI**: [Streamlit](https://streamlit.io/) 1.32+
- **Real-time quotes**: [Finnhub](https://finnhub.io/) (free tier — 60 req/min)
- **Historical OHLCV**: [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance)
- **Compute**: pandas + numpy

## Setup

```bash
git clone https://github.com/czcode0501/sector-flow.git
cd sector-flow
pip install -r requirements.txt
```

Get a free Finnhub API key at https://finnhub.io/register, then:

```bash
cp .env.example .env
# open .env and paste your key after FINNHUB_API_KEY=
```

Run:

```bash
python -m streamlit run app.py
```

Open http://localhost:8501 in your browser.

### Optional: Windows desktop shortcut

Double-click `launch.bat` — or create a Desktop shortcut pointing to it. Includes a Python launcher (`launch.py`) that reuses an existing Streamlit instance if one is already running.

## Configuration

| File | Purpose |
|---|---|
| `.env` | Your `FINNHUB_API_KEY` (never committed) |
| `sectors.py` | Sector ETF list + top-30 constituent stocks per sector |
| `data.py` | Data fetchers + indicator computations |
| `app.py` | Streamlit UI + routing |

To customize the constituent lists, edit `SECTOR_STOCKS` in `sectors.py`. To change the sector sort key or refresh interval, edit `app.py`.

## Rate limit note

Finnhub free tier is **60 calls/minute**. The main dashboard hits ~44/min, safely under. Sector detail pages hit ~120/min when refreshing every 15s across 30 stocks — you may see occasional 429s that self-recover within a minute. If this bothers you, either raise the refresh interval or thin the constituent lists.

## Screenshots

_Add your own screenshots here._

## Roadmap ideas

- [ ] Historical trend charts (CMF over time)
- [ ] Compare mode (side-by-side sector or stock)
- [ ] Alerting (Slack/email when CMF crosses threshold)
- [ ] Configurable indicator thresholds
- [ ] Extended-hours data
- [ ] Broker/exchange filter beyond SPDR sectors (e.g. Vanguard, iShares)

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

For educational and personal research use only. Not financial advice. Data may be delayed, incomplete, or wrong. Do not trade solely on what this app shows you.

---

# 中文说明

一个实时追踪**美股 11 大板块 ETF 及其成分股资金流**的仪表盘。基于 Streamlit + Finnhub + yfinance 搭建。

## 功能

- **11 个板块一屏总览** —— 按当日 CMF 资金流入实时降序排列
- **点击板块下钻** —— 查看该板块市值 Top 10、净流入最剧烈 Top 10、涨跌幅最大 Top 10
- **代码搜索** —— 输入任意美股代码,查看完整指标表
- **9 个指标 × 3 个时间窗口(1D / 5D / 20D)**:

| 指标 | 含义 |
|---|---|
| **涨跌幅** | 相对 N 日前收盘价的涨跌 % |
| **CMF** | 蔡金资金流量 — 用收盘位置 × 成交量衡量买卖压力 |
| **Net $Flow** | 净主动买入金额(近似) |
| **Flow %** | 净流入 ÷ 总成交金额 |
| **Up/Dn Vol** | 上涨日成交量 ÷ 下跌日成交量 |
| **RVOL** | 当日成交量 ÷ N 日均量 |
| **Close Loc** | 当日收盘位置(0 = 最低,1 = 最高) |
| **MFI** | 资金流量指标 — 量能加权 RSI |
| **OBV Δ%** | OBV 累计变化 % |

- **零闪烁静默刷新** —— 使用 Streamlit `@st.fragment`,只有数据区局部刷新,页面不闪
- **数字翻页动画** —— 新数据到达时数字像翻日历一样翻转
- **一键桌面快捷方式**(Windows)

## 安装

```bash
git clone https://github.com/czcode0501/sector-flow.git
cd sector-flow
pip install -r requirements.txt
```

到 https://finnhub.io/register 免费注册拿 API key,然后:

```bash
cp .env.example .env
# 打开 .env,把你的 key 填在 FINNHUB_API_KEY= 后面
```

启动:

```bash
python -m streamlit run app.py
```

浏览器打开 http://localhost:8501

## API 限速提示

Finnhub 免费档 **每分钟 60 次调用**。主页大约 44 次/分钟,安全;板块详情页 15 秒刷新 × 30 只股票 ≈ 120 次/分钟,偶尔会返回 429(1 分钟自动恢复)。想彻底避免可以在侧栏把详情页刷新间隔调到 30 秒。

## 授权

MIT — 见 [LICENSE](LICENSE)。

## 免责声明

本项目仅供学习与个人研究,不构成任何投资建议。数据可能延迟、缺失或错误。请勿单纯依据本应用做出交易决策。
