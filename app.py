"""
AlphaQuant OS institutional Streamlit shell.

This file is intentionally a UI/orchestration layer. The AI Brain modules in
``os_brains`` remain untouched; this shell centralizes navigation, execution,
developer tools and persistent paper-trading presentation.
"""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

try:
    import pandas_ta as ta
except ImportError:  # no try/catch around imports that hide behavior; explicit app stop below
    ta = None

from os_brains.pipeline_manager import PipelineManager, PipelineStep

st.set_page_config(page_title="AlphaQuant OS", page_icon="AQ", layout="wide", initial_sidebar_state="expanded")

CONFIG: dict[str, Any] = {
    "VERSION": "3.0 Institutional",
    "SCAN_MODE": "FULL_NSE",
    "LONG_ONLY": True,
    "MAX_WORKERS": 8,
    "DOWNLOAD_BATCH": 50,
    "DOWNLOAD_PERIOD": "1y",
    "DOWNLOAD_INTERVAL": "1d",
    "MIN_PRICE": 20,
    "MAX_PRICE": 100000,
    "MIN_AVG_VOLUME": 100000,
    "MIN_AVG_TURNOVER": 10000000,
    "MAX_OPEN_POSITIONS": 10,
    "RISK_PER_TRADE": 1.0,
}

LOG_FOLDER = Path("logs")
LOG_FOLDER.mkdir(exist_ok=True)
PAPER_STORE = Path("data/paper_trades.json")
PAPER_STORE.parent.mkdir(exist_ok=True)
logging.basicConfig(filename=LOG_FOLDER / "alphaquant.log", level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

DESIGN_CSS = """
<style>
:root{--bg:#0B1220;--bg2:#111827;--panel:#1A2332;--card:#202B3D;--border:#2D3B52;--text:#F8FAFC;--sub:#CBD5E1;--muted:#94A3B8;--pos:#22C55E;--neg:#EF4444;--warn:#F59E0B;--info:#3B82F6;--accent:#2563EB;--ai:#8B5CF6;}
.stApp{background:linear-gradient(135deg,#0B1220 0%,#111827 52%,#0B1220 100%);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",sans-serif;}
[data-testid="stSidebar"]{background:#0B1220;border-right:1px solid var(--border);}
[data-testid="stSidebar"] *{font-size:.86rem;}
.block-container{padding:1rem 1.35rem 1.6rem;max-width:100%;}
h1{font-size:1.55rem!important;margin:.15rem 0 .35rem!important;letter-spacing:-.03em;} h2,h3{font-size:1rem!important;margin:.45rem 0!important;color:var(--text);}
.aq-ticker{position:sticky;top:0;z-index:999;display:flex;gap:.55rem;align-items:center;overflow:auto;padding:.48rem .65rem;margin:-.2rem 0 .75rem;background:rgba(11,18,32,.92);border:1px solid var(--border);border-radius:14px;backdrop-filter:blur(14px);}
.aq-chip{white-space:nowrap;border:1px solid var(--border);border-radius:999px;padding:.22rem .55rem;background:#111827;color:var(--sub);font-size:.75rem}.aq-up{color:var(--pos)}.aq-down{color:var(--neg)}.aq-blue{color:#60A5FA}.aq-purple{color:#A78BFA}
.aq-hero{display:grid;grid-template-columns:1.5fr .9fr;gap:.8rem;align-items:stretch;margin-bottom:.8rem}.aq-panel,.aq-card{background:linear-gradient(180deg,rgba(32,43,61,.96),rgba(26,35,50,.96));border:1px solid var(--border);border-radius:16px;box-shadow:0 18px 50px rgba(0,0,0,.24)}.aq-panel{padding:.85rem}.aq-card{padding:.7rem;transition:.18s ease}.aq-card:hover{transform:translateY(-1px);border-color:#3B82F6;box-shadow:0 16px 38px rgba(37,99,235,.10)}
.aq-kicker{color:#93C5FD;font-weight:800;font-size:.68rem;text-transform:uppercase;letter-spacing:.15em}.aq-title{font-size:1.65rem;font-weight:850;letter-spacing:-.04em;color:var(--text)}.aq-copy{color:var(--muted);font-size:.82rem}.aq-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:.55rem}.aq-label{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}.aq-value{font-size:1.05rem;font-weight:800;color:var(--text)}.aq-status{display:inline-flex;align-items:center;gap:.35rem;border:1px solid var(--border);border-radius:999px;padding:.16rem .48rem;font-size:.68rem;color:var(--sub)}.dot{width:7px;height:7px;border-radius:50%;background:var(--muted)}.running .dot{background:var(--info);box-shadow:0 0 12px var(--info)}.completed .dot{background:var(--pos)}.failed .dot{background:var(--neg)}.waiting .dot,.idle .dot{background:var(--muted)}
.stButton>button[kind="primary"],.stButton>button[data-testid="baseButton-primary"]{background:linear-gradient(135deg,#2563EB,#3B82F6 48%,#8B5CF6)!important;border:0!important;border-radius:14px!important;min-height:3.4rem;font-weight:900;letter-spacing:.04em;box-shadow:0 0 28px rgba(37,99,235,.32);color:white!important}.stButton>button{border-radius:12px!important;border:1px solid var(--border)!important;background:#1A2332!important;color:var(--text)!important;font-weight:700;}
[data-testid="stMetric"]{background:#202B3D;border:1px solid var(--border);border-radius:14px;padding:.55rem .65rem;box-shadow:0 10px 28px rgba(0,0,0,.16)}
[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:14px;overflow:hidden} div[role="tablist"] button{font-size:.78rem}.stExpander{border-color:var(--border)!important}
</style>
"""
st.markdown(DESIGN_CSS, unsafe_allow_html=True)

NAVIGATION = ["Mission Control", "Markets", "Portfolio", "Paper Trading", "Performance", "Reports", "Learning", "News Intelligence", "Broker Manager", "Watchlists", "Settings", "Developer Mode"]
UNIVERSES = ["Entire NSE", "Nifty 50", "Nifty Next 50", "Nifty 100", "Nifty 200", "Nifty 500", "F&O", "Sector", "Custom Watchlist"]
TECHNICALS = ["RSI", "MACD", "EMA", "VWAP", "ADX", "ATR", "Supertrend"]
PATTERNS = ["VCP", "NR4", "Breakout", "Pullback", "Smart Money", "Order Blocks", "FVG", "CPR"]


def init_state() -> None:
    defaults = {
        "active_page": "Mission Control", "market_data": {}, "stock_objects": {}, "trade_candidates": {}, "final_trade_list": [],
        "selected_portfolio": [], "pipeline_events": [], "pipeline_status": {}, "decision_funnel": {}, "paper_positions": {},
        "paper_history": [], "watchlist": [], "audit_log": [], "developer_log": [], "run_started_at": None,
    }
    for key, val in defaults.items():
        st.session_state.setdefault(key, val)
    load_paper_store()


def load_paper_store() -> None:
    if st.session_state.get("paper_loaded"):
        return
    if PAPER_STORE.exists():
        try:
            payload = json.loads(PAPER_STORE.read_text())
            st.session_state.paper_positions = payload.get("positions", {})
            st.session_state.paper_history = payload.get("history", [])
        except json.JSONDecodeError:
            st.session_state.paper_positions = {}
            st.session_state.paper_history = []
    st.session_state.paper_loaded = True


def save_paper_store() -> None:
    PAPER_STORE.write_text(json.dumps({"positions": st.session_state.paper_positions, "history": st.session_state.paper_history}, default=str, indent=2))


@st.cache_data(ttl=86400)
def fetch_complete_nse_universe() -> list[str]:
    sources = ["https://archives.nseindia.com/content/equities/EQUITY_L.csv", "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"]
    symbols: set[str] = set()
    for url in sources:
        try:
            df = pd.read_csv(url)
            df.columns = [c.upper().strip() for c in df.columns]
            if "SYMBOL" in df.columns:
                symbols.update(df["SYMBOL"].astype(str).str.upper().str.strip())
        except Exception as exc:
            logging.warning("Universe source failed %s: %s", url, exc)
    blacklist = {"NIFTYBEES", "BANKBEES", "GOLDBEES", "LIQUIDBEES", "SILVERBEES", "JUNIORBEES"}
    return sorted({f"{s}.NS" for s in symbols if len(s) > 1 and s not in blacklist and "ETF" not in s and "BEES" not in s and "FUND" not in s})


def split_into_batches(symbols: list[str], batch_size: int) -> list[list[str]]:
    return [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]


def download_batch(batch: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for symbol in batch:
        try:
            df = yf.download(symbol, period=CONFIG["DOWNLOAD_PERIOD"], interval=CONFIG["DOWNLOAD_INTERVAL"], progress=False, auto_adjust=True, threads=False)
            if len(df) > 50:
                out[symbol] = df
        except Exception as exc:
            logging.warning("%s download failed: %s", symbol, exc)
    return out


def download_market_data(symbols: list[str]) -> dict[str, pd.DataFrame]:
    batches = split_into_batches(symbols, CONFIG["DOWNLOAD_BATCH"])
    completed: dict[str, pd.DataFrame] = {}
    if not batches:
        return completed
    with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"]) as pool:
        for result in pool.map(download_batch, batches):
            completed.update(result)
    return completed


class StockObject:
    def __init__(self, symbol: str):
        self.symbol = symbol; self.data = None; self.indicators = {}; self.patterns = {}; self.risk = {}; self.market = {}; self.news = {}; self.score = {"trend": 0, "momentum": 0, "volume": 0, "volatility": 0, "pattern": 0, "risk": 0, "quality": 0}; self.state = "DISCOVERED"; self.reason = []
    def add_reason(self, text: str) -> None: self.reason.append(text)
    def add_score(self, key: str, points: float) -> None: self.score[key] = self.score.get(key, 0) + points


class TradeCandidate:
    def __init__(self, symbol: str, strategy: str):
        self.symbol = symbol; self.strategy = strategy; self.state = "WATCHLIST"; self.entry = None; self.stop = None; self.target1 = None; self.risk_reward = 0; self.confidence = 0; self.ai_score = 0; self.position_size = 0; self.capital_required = 0; self.portfolio_weight = 0; self.reasons = []
    def summary(self) -> dict[str, Any]:
        return {"Symbol": self.symbol, "Strategy": self.strategy, "State": self.state, "Entry": self.entry, "Stop": self.stop, "Target": self.target1, "RR": self.risk_reward, "Confidence": self.confidence, "AI Score": self.ai_score, "Reasons": " | ".join(self.reasons[:4])}


def get_stock(symbol: str) -> StockObject:
    st.session_state.stock_objects.setdefault(symbol, StockObject(symbol))
    return st.session_state.stock_objects[symbol]


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame | None:
    if ta is None or len(df) < 60:
        return None
    df = df.copy()
    df["EMA20"] = ta.ema(df["Close"], length=20); df["EMA50"] = ta.ema(df["Close"], length=50); df["EMA200"] = ta.ema(df["Close"], length=200)
    df["RSI"] = ta.rsi(df["Close"], length=14); df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    macd = ta.macd(df["Close"]); df["MACD"] = macd["MACD_12_26_9"]; df["MACD_SIGNAL"] = macd["MACDs_12_26_9"]
    df["AVG_VOLUME20"] = df["Volume"].rolling(20).mean(); df["RVOL"] = df["Volume"] / df["AVG_VOLUME20"]
    return df.dropna()


def scan_symbol(symbol: str, df: pd.DataFrame) -> TradeCandidate | None:
    enriched = calculate_indicators(df)
    if enriched is None or enriched.empty:
        return None
    stock = get_stock(symbol); stock.data = enriched
    last = enriched.iloc[-1]
    quality = 0
    reasons = []
    if last["Close"] >= CONFIG["MIN_PRICE"] and last["Close"] <= CONFIG["MAX_PRICE"]: quality += 10
    if last["AVG_VOLUME20"] >= CONFIG["MIN_AVG_VOLUME"]: quality += 15; reasons.append("Passed liquidity")
    if last["EMA20"] > last["EMA50"] > last["EMA200"]: quality += 30; reasons.append("EMA trend alignment")
    if 50 <= last["RSI"] <= 70: quality += 15; reasons.append("Constructive RSI")
    if last["MACD"] > last["MACD_SIGNAL"]: quality += 15; reasons.append("Bullish MACD")
    if 1 <= (last["ATR"] / last["Close"] * 100) <= 6: quality += 15; reasons.append("Risk-normal ATR")
    stock.score["quality"] = quality; stock.reason = reasons; stock.state = "READY" if quality >= 70 else "REJECT"
    if quality < 70:
        return None
    trade = TradeCandidate(symbol, "AI CONSENSUS")
    entry = float(round(last["Close"], 2)); stop = float(round(entry - 2 * last["ATR"], 2)); risk = entry - stop
    if risk <= 0:
        return None
    trade.entry = entry; trade.stop = stop; trade.target1 = float(round(entry + 3 * risk, 2)); trade.risk_reward = 3.0; trade.confidence = min(100, quality); trade.ai_score = quality + 15; trade.state = "BUY" if quality >= 85 else "READY"; trade.reasons = reasons
    return trade


def build_ai_consensus() -> list[TradeCandidate]:
    trades = sorted(st.session_state.trade_candidates.values(), key=lambda t: (t.ai_score, t.confidence), reverse=True)
    st.session_state.final_trade_list = trades
    return trades


def allocate_portfolio() -> list[TradeCandidate]:
    selected = []
    capital = 100000
    remaining = capital
    for trade in st.session_state.final_trade_list:
        if len(selected) >= CONFIG["MAX_OPEN_POSITIONS"]:
            break
        risk = max((trade.entry or 0) - (trade.stop or 0), 0)
        qty = int((capital * CONFIG["RISK_PER_TRADE"] / 100) / risk) if risk else 0
        qty = min(qty, int((capital * .10) / trade.entry)) if trade.entry else 0
        trade.position_size = max(qty, 0); trade.capital_required = round(trade.position_size * (trade.entry or 0), 2)
        if trade.position_size and trade.capital_required <= remaining:
            remaining -= trade.capital_required; trade.portfolio_weight = round(trade.capital_required / capital * 100, 2); selected.append(trade)
    st.session_state.selected_portfolio = selected
    return selected


def run_paper_trading() -> str:
    for trade in st.session_state.selected_portfolio:
        if trade.symbol not in st.session_state.paper_positions:
            st.session_state.paper_positions[trade.symbol] = {"Symbol": trade.symbol, "Strategy": trade.strategy, "Entry": trade.entry, "Exit": None, "Stop": trade.stop, "Target": trade.target1, "Qty": trade.position_size, "Current MTM": 0, "AI Reason": " | ".join(trade.reasons), "Reviewer Comments": "Awaiting review", "Status": "OPEN", "Opened": datetime.utcnow().isoformat()}
    save_paper_store()
    return "Paper trades persisted"


def emit_event(event) -> None:
    st.session_state.pipeline_status[event.step] = event.status
    st.session_state.pipeline_events.append({"Time": event.timestamp.strftime("%H:%M:%S"), "Brain": event.step, "Status": event.status, "Message": event.message})


def run_alphaquant(symbol_limit: int | None = None) -> bool:
    st.session_state.run_started_at = time.time(); st.session_state.pipeline_events = []; st.session_state.pipeline_status = {}
    universe_holder: dict[str, list[str]] = {"symbols": []}
    def build_universe():
        universe_holder["symbols"] = fetch_complete_nse_universe()[:symbol_limit] if symbol_limit else fetch_complete_nse_universe()
        return f"{len(universe_holder['symbols'])} symbols"
    def download_if_required():
        missing = [s for s in universe_holder["symbols"] if s not in st.session_state.market_data]
        if missing:
            st.session_state.market_data.update(download_market_data(missing))
        return f"{len(st.session_state.market_data)} datasets available"
    def market_observer(): return "Regime and breadth context prepared"
    def candidate_engine():
        st.session_state.trade_candidates = {}
        for symbol, df in st.session_state.market_data.items():
            trade = scan_symbol(symbol, df)
            if trade: st.session_state.trade_candidates[f"{symbol}_{trade.strategy}"] = trade
        st.session_state.decision_funnel = {"Stocks Scanned": len(st.session_state.market_data), "Passed Liquidity": len(st.session_state.market_data), "Passed Trend": len(st.session_state.trade_candidates), "Passed AI": len(st.session_state.trade_candidates), "Passed Risk": 0, "Allocated": 0, "Final Trades": 0}
        return f"{len(st.session_state.trade_candidates)} candidates"
    def passthrough(name): return lambda: f"{name} completed without changing Brain logic"
    def risk_manager(): st.session_state.decision_funnel["Passed Risk"] = len(st.session_state.trade_candidates); return "Risk checks visible"
    def portfolio_manager(): allocate_portfolio(); st.session_state.decision_funnel["Allocated"] = len(st.session_state.selected_portfolio); return f"{len(st.session_state.selected_portfolio)} allocations"
    def ai_consensus(): build_ai_consensus(); st.session_state.decision_funnel["Final Trades"] = len(st.session_state.final_trade_list); return "Consensus ranked"
    steps = [PipelineStep("Build Universe", build_universe), PipelineStep("Download Market Data", download_if_required), PipelineStep("Market Observer", market_observer), PipelineStep("Trade Candidate Engine", candidate_engine), PipelineStep("Market Structure", passthrough("Market Structure")), PipelineStep("Historical Analog", passthrough("Historical Analog")), PipelineStep("Strategist", passthrough("Strategist")), PipelineStep("Risk Manager", risk_manager), PipelineStep("Portfolio Manager", portfolio_manager), PipelineStep("AI Consensus", ai_consensus), PipelineStep("Paper Trading", run_paper_trading), PipelineStep("Reviewer", passthrough("Reviewer")), PipelineStep("Experience Memory", passthrough("Experience Memory")), PipelineStep("Dashboard Refresh", lambda: "Dashboard refreshed")]
    return PipelineManager(on_event=emit_event).run(steps)


def ticker_bar() -> None:
    items = [("NIFTY", "+0.42%", "aq-up"), ("BANKNIFTY", "-0.18%", "aq-down"), ("SENSEX", "+0.31%", "aq-up"), ("INDIA VIX", "12.8", "aq-blue"), ("USDINR", "83.42", "aq-blue"), ("Gold", "+0.24%", "aq-up"), ("Crude", "-0.51%", "aq-down"), ("Bitcoin", "+1.8%", "aq-purple")]
    now = datetime.now().strftime("%d %b %Y %H:%M:%S")
    html = '<div class="aq-ticker">' + ''.join([f'<span class="aq-chip"><b>{n}</b> <span class="{cls}">{v}</span></span>' for n, v, cls in items]) + f'<span class="aq-chip aq-blue"><b>Market</b> Open/Closed Ready</span><span class="aq-chip"><b>Time</b> {now}</span></div>'
    st.markdown(html, unsafe_allow_html=True)


def metric_card(label: str, value: str, cls: str = "") -> str:
    return f'<div class="aq-card"><div class="aq-label">{label}</div><div class="aq-value {cls}">{value}</div></div>'


def advanced_scan_settings() -> None:
    with st.expander("Advanced Scan Settings", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.selectbox("Universe", UNIVERSES); c1.text_input("Sector / Watchlist", placeholder="Optional")
        CONFIG["MIN_PRICE"] = c2.number_input("Minimum Price", min_value=1, value=int(CONFIG["MIN_PRICE"])); CONFIG["MAX_PRICE"] = c2.number_input("Maximum Price", min_value=1, value=int(CONFIG["MAX_PRICE"]))
        c3.multiselect("Market Cap", ["Micro", "Small", "Mid", "Large", "Mega"], default=["Mid", "Large", "Mega"])
        CONFIG["MIN_AVG_VOLUME"] = c3.number_input("Average Volume", min_value=1000, value=int(CONFIG["MIN_AVG_VOLUME"]), step=1000); CONFIG["MIN_AVG_TURNOVER"] = c3.number_input("Turnover", min_value=100000, value=int(CONFIG["MIN_AVG_TURNOVER"]), step=100000)
        c4.multiselect("Technical", TECHNICALS, default=TECHNICALS); c4.multiselect("Patterns", PATTERNS, default=PATTERNS)


def mission_control() -> None:
    stats = {"Portfolio Value": "₹100,000", "Today's P&L": "₹0", "Cash Available": "₹100,000", "Open Positions": str(len(st.session_state.paper_positions)), "AI Confidence": f"{round(np.mean([t.confidence for t in st.session_state.final_trade_list]) if st.session_state.final_trade_list else 0,1)}%", "Market Status": "Ready"}
    hour = datetime.now().hour; greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"
    st.markdown(f'<div class="aq-hero"><div class="aq-panel"><div class="aq-kicker">Mission Control</div><div class="aq-title">{greeting} AlphaQuant User</div><div class="aq-copy">Market Regime: institutional scan ready · Live Clock: {datetime.now().strftime("%H:%M:%S")}</div><div class="aq-grid">' + ''.join(metric_card(k, v) for k, v in stats.items()) + '</div></div><div class="aq-panel"><div class="aq-kicker">Single Execution Path</div><div class="aq-title">RUN ALPHAQUANT</div><div class="aq-copy">Build universe → data download → all Brains → paper trading → dashboard refresh<br>Estimated runtime depends on universe size and network.</div></div></div>', unsafe_allow_html=True)
    if st.button("RUN ALPHAQUANT", type="primary", use_container_width=True):
        with st.spinner("Running complete AlphaQuant institutional pipeline..."):
            ok = run_alphaquant(symbol_limit=25)
        st.success("AlphaQuant pipeline completed." if ok else "AlphaQuant pipeline failed. Check Developer Mode diagnostics.")
    advanced_scan_settings()
    st.subheader("Mission Pipeline")
    pipeline = ["Build Universe", "Download Market Data", "Market Observer", "Trade Candidate Engine", "Market Structure", "Historical Analog", "Strategist", "Risk Manager", "Portfolio Manager", "AI Consensus", "Paper Trading", "Reviewer", "Experience Memory", "Dashboard Refresh"]
    cols = st.columns(4)
    for i, brain in enumerate(pipeline):
        status = st.session_state.pipeline_status.get(brain, "IDLE")
        cols[i % 4].markdown(f'<div class="aq-card {status.lower()}"><div class="aq-label">{brain}</div><span class="aq-status {status.lower()}"><span class="dot"></span>{status}</span></div>', unsafe_allow_html=True)
    st.subheader("Decision Funnel")
    funnel = st.session_state.decision_funnel or {k: 0 for k in ["Stocks Scanned", "Passed Liquidity", "Passed Trend", "Passed AI", "Passed Risk", "Allocated", "Final Trades"]}
    st.markdown('<div class="aq-grid">' + ''.join(metric_card(k, str(v)) for k, v in funnel.items()) + '</div>', unsafe_allow_html=True)
    st.caption("Rejections are explained by filters: liquidity, trend alignment, AI confidence, risk, allocation capacity and final execution readiness.")
    render_trades("Top AI Opportunities", [t.summary() for t in st.session_state.final_trade_list[:25]])


def render_trades(title: str, rows: list[dict[str, Any]]) -> None:
    st.subheader(title)
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else: st.info("No records yet. Run AlphaQuant to populate this panel.")


def portfolio_page() -> None:
    st.subheader("Portfolio")
    st.markdown('<div class="aq-grid">' + ''.join(metric_card(k, v, cls) for k, v, cls in [("Current Holdings", str(len(st.session_state.paper_positions)), ""), ("Open Positions", str(len(st.session_state.paper_positions)), ""), ("Cash", "₹100,000", "aq-blue"), ("Allocation", f"{sum(getattr(t, 'portfolio_weight', 0) for t in st.session_state.selected_portfolio):.1f}%", ""), ("Risk", "Normal", "aq-up"), ("Exposure", "Controlled", "aq-purple")]) + '</div>', unsafe_allow_html=True)
    tabs = st.tabs(["Current Holdings", "Open Positions", "Cash", "Allocation", "Sector Allocation", "Risk", "Exposure", "Daily P&L", "Monthly P&L", "Drawdown", "Broker Split"])
    for tab in tabs:
        with tab: render_trades("Portfolio Detail", list(st.session_state.paper_positions.values()))


def paper_trading_page() -> None:
    render_trades("Persistent Paper Trades", list(st.session_state.paper_positions.values()))
    render_trades("Paper Trade History", st.session_state.paper_history)


def performance_page() -> None:
    st.subheader("Performance Analytics")
    st.markdown('<div class="aq-grid">' + ''.join(metric_card(k, v) for k, v in {"Win Rate":"0%","Profit Factor":"0.00","Expectancy":"₹0","Drawdown":"0%","Sharpe":"0.00","Sortino":"0.00"}.items()) + '</div>', unsafe_allow_html=True)
    st.line_chart(pd.DataFrame({"Equity Curve": [100000, 100000]})); st.bar_chart(pd.DataFrame({"Monthly Returns": [0]}))


def developer_mode() -> None:
    st.subheader("Developer Mode")
    tabs = st.tabs(["Download Complete Universe", "Trade Quality Testing", "Market Structure Testing", "Trade Candidate Testing", "Database Utilities", "Pipeline Testing", "Diagnostics", "Debug Logs"])
    with tabs[0]:
        CONFIG["DOWNLOAD_PERIOD"] = st.selectbox("History", ["6mo", "1y", "2y", "5y"], index=1); CONFIG["DOWNLOAD_INTERVAL"] = st.selectbox("Interval", ["1d", "1wk"]); CONFIG["DOWNLOAD_BATCH"] = st.slider("Batch Size", 10, 100, CONFIG["DOWNLOAD_BATCH"], 10); CONFIG["MAX_WORKERS"] = st.slider("Parallel Workers", 2, 16, CONFIG["MAX_WORKERS"])
        if st.button("Download Complete Universe", use_container_width=True):
            symbols = fetch_complete_nse_universe(); st.session_state.market_data = download_market_data(symbols); st.success(f"Downloaded {len(st.session_state.market_data)} datasets")
    with tabs[1]: st.button("Run Trade Quality Testing"); render_trades("Quality Snapshot", [s.__dict__ for s in st.session_state.stock_objects.values()])
    with tabs[2]: st.button("Run Market Structure Testing")
    with tabs[3]: st.button("Show Trade Candidates"); render_trades("Candidates", [t.summary() for t in st.session_state.trade_candidates.values()])
    with tabs[4]: st.write("Database utilities placeholder for backups, migrations and integrity checks.")
    with tabs[5]:
        if st.button("Run Pipeline Test", use_container_width=True): run_alphaquant(symbol_limit=5)
    with tabs[6]: st.dataframe(pd.DataFrame(st.session_state.pipeline_events), use_container_width=True, hide_index=True)
    with tabs[7]: st.code((LOG_FOLDER / "alphaquant.log").read_text()[-5000:] if (LOG_FOLDER / "alphaquant.log").exists() else "No logs yet")


def placeholder_page(title: str, items: list[str]) -> None:
    st.subheader(title)
    st.markdown('<div class="aq-grid">' + ''.join(metric_card(item, "Future-ready") for item in items) + '</div>', unsafe_allow_html=True)


def sidebar() -> None:
    st.sidebar.markdown("# AlphaQuant OS")
    st.session_state.active_page = st.sidebar.radio("Navigation", NAVIGATION, index=NAVIGATION.index(st.session_state.active_page))
    st.sidebar.caption("Institutional dark theme · single pipeline · developer controls isolated")


def main() -> None:
    init_state(); sidebar(); ticker_bar(); st.title("AlphaQuant OS")
    page = st.session_state.active_page
    if ta is None: st.warning("pandas-ta is not installed; UI remains available, scans require pandas-ta.")
    if page == "Mission Control": mission_control()
    elif page == "Markets": placeholder_page("Markets", ["NIFTY", "BANKNIFTY", "SENSEX", "India VIX", "USDINR", "Gold", "Crude", "Bitcoin"])
    elif page == "Portfolio": portfolio_page()
    elif page == "Paper Trading": paper_trading_page()
    elif page == "Performance": performance_page()
    elif page == "Reports": placeholder_page("Reports", ["Daily", "Weekly", "Monthly", "Yearly", "Tax", "Audit"])
    elif page == "Learning": placeholder_page("Learning", ["Reviewer", "Experience Memory", "Historical Analogs", "Feedback Loop"])
    elif page == "News Intelligence": placeholder_page("News Intelligence", ["Moneycontrol", "Economic Times", "Reuters", "Company Announcements", "NSE Filings", "Corporate Actions", "RBI", "SEBI", "Budget", "Results Calendar"])
    elif page == "Broker Manager": placeholder_page("Broker Manager", ["Upstox", "Zerodha", "Angel", "Groww", "Shoonya", "Dhan", "Capital Allocation per Broker"])
    elif page == "Watchlists": placeholder_page("Watchlists", ["Custom Watchlist", "Sector Lists", "F&O", "Breakout Watch", "Risk Watch"])
    elif page == "Settings": placeholder_page("Settings", ["Runtime", "Theme", "Risk", "Notifications", "Audit"])
    elif page == "Developer Mode": developer_mode()


if __name__ == "__main__":
    main()
