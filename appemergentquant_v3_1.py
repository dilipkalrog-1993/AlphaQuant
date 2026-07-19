"""
=========================================================
AlphaQuant Professional
Version : 3.0.0
Status  : Production Build
Author  : Dilip + ChatGPT

Build Date : 2026

Current Phase
-------------
✓ Foundation
✓ Startup Engine
✓ Download Engine
✓ Indicator Engine
✓ AI Engine
✓ Portfolio Engine
✓ Paper Trading

Development Mode : TRUE
=========================================================
"""

# =====================================================
# IMPORTS
# =====================================================

import os
import sys
import time
import logging
import traceback
import warnings
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# Make the `os_brains` package importable regardless of the process's
# working directory. app.py uses absolute imports like
# `from os_brains import experience_memory` throughout, which only resolve
# automatically when Python's cwd/script-dir happens to be this file's own
# directory (e.g. `cd alphaquant && streamlit run app.py`). Explicitly
# putting this file's directory on sys.path makes those imports work no
# matter where the process is launched from -- the repo root, an extracted
# export run from any starting directory, etc. -- without changing any
# trading logic.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import requests
from io import StringIO

warnings.filterwarnings("ignore")

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AlphaQuant Professional",
    page_icon="📈",
    layout="wide"
)

# =====================================================
# APPEMERGENTQUANTFINAL - v1.0.0 (2026-07-18 13:32:14 UTC)
# Production build entry point.
#   * One-click end-to-end pipeline (RUN ALPHAQUANT primary button)
#   * Universe Engine v3.0.2 (nsearchives primary + fallbacks + disk cache)
#   * All existing engines preserved and reused
#   * Unified professional dark theme (CSS injected exactly once)
# =====================================================

# -------- Global professional dark theme (injected exactly once) --------
if not st.session_state.get("_theme_injected"):
    st.markdown(
        """
        <style>
        html, body, [class*="css"], .stApp {
            background: linear-gradient(180deg, #0b1020 0%, #101731 100%) !important;
            color: #e6e9f2 !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
        }
        section[data-testid="stSidebar"] {
            background: #0a0f1f !important;
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        section[data-testid="stSidebar"] * { color: #d7dbeb !important; }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 14px 16px;
        }
        div[data-testid="stMetricLabel"] { color: #96a0c4 !important; font-size: 12px; }
        div[data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 600; }
        div.stButton > button, div.stDownloadButton > button {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
            color: #ffffff !important;
            border: 0 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 10px 22px !important;
            transition: transform .08s ease, box-shadow .2s ease !important;
        }
        div.stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 22px rgba(79,70,229,0.35) !important;
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            font-size: 15px !important;
            padding: 12px 28px !important;
        }
        div[data-baseweb="tab-list"] {
            gap: 4px !important;
            background: rgba(255,255,255,0.03);
            padding: 6px !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.06);
        }
        button[data-baseweb="tab"] {
            background: transparent !important;
            color: #96a0c4 !important;
            border-radius: 8px !important;
            padding: 8px 18px !important;
            font-weight: 500 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
            color: #ffffff !important;
        }
        div[data-testid="stAlert"] {
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
        }
        div[data-testid="stDataFrame"] thead tr th {
            background: rgba(79,70,229,0.15) !important;
            color: #e6e9f2 !important;
            font-weight: 600 !important;
        }
        hr { border-color: rgba(255,255,255,0.08) !important; }
        h1, h2, h3 { color: #ffffff !important; letter-spacing: -0.01em; }
        div[data-testid="stExpander"] {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
        }
        div[role="progressbar"] > div {
            background: linear-gradient(90deg, #10b981 0%, #4f46e5 100%) !important;
        }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header[data-testid="stHeader"] { background: transparent; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_theme_injected"] = True

# -------- Top navigation banner --------
st.markdown(
    """
    <div style="
        display:flex; align-items:center; justify-content:space-between;
        background: linear-gradient(90deg, rgba(79,70,229,0.20) 0%, rgba(124,58,237,0.15) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px; padding: 14px 20px; margin: 4px 0 18px 0;
    ">
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="width:36px; height:36px; border-radius:9px;
             background: linear-gradient(135deg,#4f46e5,#7c3aed);
             display:flex; align-items:center; justify-content:center;
             font-weight:800; color:#fff; font-size:18px;">Q</div>
        <div>
          <div style="font-size:18px; font-weight:700; color:#fff; letter-spacing:-0.02em;">
             AlphaQuant Professional
          </div>
          <div style="font-size:11px; color:#96a0c4; letter-spacing:0.08em; text-transform:uppercase;">
             Autonomous NSE Trading Platform &middot; One-Click Pipeline &middot; v3.0.2
          </div>
        </div>
      </div>
      <div style="display:flex; gap:10px; font-size:12px; color:#96a0c4;">
        <span>&bull; Universe Engine: nsearchives</span>
        <span style="opacity:0.6;">&middot;</span>
        <span>&bull; Pipeline: One-Click</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =====================================================
# 6-TAB PAGE ROUTER
# =====================================================
# Sets st.session_state["_page"] via a top nav bar. Every major UI block
# further down the file is gated by _P("PageName") so only the currently
# active page renders. This gives the user the requested clean navigation
# (Dashboard / Scanner / AI / Portfolio / Paper Trading / Settings) while
# every engine still runs at import so the one-click pipeline behaviour
# is preserved.

_PAGE_LIST = ["Dashboard", "Scanner", "AI", "Portfolio", "Paper Trading", "Settings"]
_PAGE_ICONS = {"Dashboard": "🏠", "Scanner": "🔭", "AI": "🧠",
               "Portfolio": "💼", "Paper Trading": "📊", "Settings": "⚙️"}

if "_page" not in st.session_state:
    st.session_state["_page"] = "Dashboard"

_nav_cols = st.columns(len(_PAGE_LIST))
for _i, _pname in enumerate(_PAGE_LIST):
    _is_active = st.session_state["_page"] == _pname
    with _nav_cols[_i]:
        if st.button(
            f"{_PAGE_ICONS[_pname]}  {_pname}",
            key=f"_nav_btn_{_pname}",
            use_container_width=True,
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["_page"] = _pname
            st.rerun()

def _P(*pages) -> bool:
    """True when the current page matches any of the given page names."""
    return st.session_state.get("_page", "Dashboard") in pages

st.markdown("<div style='height: 6px'></div>", unsafe_allow_html=True)


# =====================================================
# APPLICATION CONFIGURATION
# =====================================================

CONFIG = {

    "VERSION": "3.0.0",

    "SCAN_MODE": "FULL_NSE",

    "LONG_ONLY": True,

    "MAX_WORKERS": 8,

    "DOWNLOAD_BATCH": 50,

    "DOWNLOAD_PERIOD": "1y",

    "DOWNLOAD_INTERVAL": "1d",

    "CACHE_MINUTES": 30,

    "MIN_PRICE": 20,

    "MIN_AVG_VOLUME": 100000,

    "MIN_AVG_TURNOVER": 10000000,

    "MAX_OPEN_POSITIONS": 10,

    "RISK_PER_TRADE": 1.0

}

# =====================================================
# SECTOR MAP
# =====================================================
# Defined here (ahead of both the sector-scoring engine further down and
# the Scan Manager's Sector filter) so any code that needs it - however
# early in the script - can rely on it already existing.

STOCK_SECTOR_MAP = {
    "HDFCBANK": "NIFTY BANK", "ICICIBANK": "NIFTY BANK", "SBIN": "NIFTY BANK",
    "KOTAKBANK": "NIFTY BANK", "AXISBANK": "NIFTY BANK", "INDUSINDBK": "NIFTY BANK",
    "BANKBARODA": "NIFTY BANK", "PNB": "NIFTY BANK", "IDFCFIRSTB": "NIFTY BANK",
    "FEDERALBNK": "NIFTY BANK", "AUBANK": "NIFTY BANK", "BANDHANBNK": "NIFTY BANK",

    "TCS": "NIFTY IT", "INFY": "NIFTY IT", "WIPRO": "NIFTY IT", "HCLTECH": "NIFTY IT",
    "TECHM": "NIFTY IT", "LTIM": "NIFTY IT", "MPHASIS": "NIFTY IT", "COFORGE": "NIFTY IT",
    "PERSISTENT": "NIFTY IT", "LTTS": "NIFTY IT",

    "MARUTI": "NIFTY AUTO", "TATAMOTORS": "NIFTY AUTO", "M&M": "NIFTY AUTO",
    "BAJAJ-AUTO": "NIFTY AUTO", "HEROMOTOCO": "NIFTY AUTO", "EICHERMOT": "NIFTY AUTO",
    "TVSMOTOR": "NIFTY AUTO", "ASHOKLEY": "NIFTY AUTO", "BALKRISIND": "NIFTY AUTO",
    "BOSCHLTD": "NIFTY AUTO", "MOTHERSON": "NIFTY AUTO",

    "HINDUNILVR": "NIFTY FMCG", "ITC": "NIFTY FMCG", "NESTLEIND": "NIFTY FMCG",
    "BRITANNIA": "NIFTY FMCG", "TATACONSUM": "NIFTY FMCG", "DABUR": "NIFTY FMCG",
    "MARICO": "NIFTY FMCG", "GODREJCP": "NIFTY FMCG", "COLPAL": "NIFTY FMCG",

    "SUNPHARMA": "NIFTY PHARMA", "DRREDDY": "NIFTY PHARMA", "CIPLA": "NIFTY PHARMA",
    "DIVISLAB": "NIFTY PHARMA", "AUROPHARMA": "NIFTY PHARMA", "LUPIN": "NIFTY PHARMA",
    "BIOCON": "NIFTY PHARMA", "TORNTPHARM": "NIFTY PHARMA", "ALKEM": "NIFTY PHARMA",

    "TATASTEEL": "NIFTY METAL", "JSWSTEEL": "NIFTY METAL", "HINDALCO": "NIFTY METAL",
    "VEDL": "NIFTY METAL", "SAIL": "NIFTY METAL", "JINDALSTEL": "NIFTY METAL",
    "NMDC": "NIFTY METAL", "NATIONALUM": "NIFTY METAL", "HINDCOPPER": "NIFTY METAL",

    "RELIANCE": "NIFTY ENERGY", "ONGC": "NIFTY ENERGY", "NTPC": "NIFTY ENERGY",
    "POWERGRID": "NIFTY ENERGY", "BPCL": "NIFTY ENERGY", "IOC": "NIFTY ENERGY",
    "GAIL": "NIFTY ENERGY", "TATAPOWER": "NIFTY ENERGY", "ADANIGREEN": "NIFTY ENERGY",
    "ADANIPOWER": "NIFTY ENERGY", "COALINDIA": "NIFTY ENERGY",
}


# =====================================================
# LOGGING
# =====================================================

LOG_FOLDER = os.path.join(_APP_DIR, "logs")

os.makedirs(LOG_FOLDER, exist_ok=True)

logging.basicConfig(

    filename=os.path.join(LOG_FOLDER, "alphaquant.log"),

    level=logging.INFO,

    format="%(asctime)s | %(levelname)s | %(message)s"

)

logging.info("AlphaQuant Started")

# =====================================================
# SESSION STATE
# =====================================================

if "portfolio" not in st.session_state:

    st.session_state.portfolio = []

if "watchlist" not in st.session_state:

    st.session_state.watchlist = []

if "audit_log" not in st.session_state:

    st.session_state.audit_log = []

if "selected_portfolio" not in st.session_state:

    st.session_state.selected_portfolio = []

if "market_data" not in st.session_state:

    st.session_state.market_data = {}


if "closed_positions" not in st.session_state:
    st.session_state.closed_positions = []

if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

if "run_complete_scan_requested" not in st.session_state:
    st.session_state.run_complete_scan_requested = False

if "last_cycle_time" not in st.session_state:
    st.session_state.last_cycle_time = None

if "last_cycle_trigger" not in st.session_state:
    st.session_state.last_cycle_trigger = None

if "last_cycle_message" not in st.session_state:
    st.session_state.last_cycle_message = ""

if "autonomous_active" not in st.session_state:
    st.session_state.autonomous_active = False

if "pipeline_events" not in st.session_state:
    st.session_state.pipeline_events = []

if "brain_status" not in st.session_state:
    st.session_state.brain_status = {}

if "decision_funnel" not in st.session_state:
    st.session_state.decision_funnel = []

if "no_trade_explanation" not in st.session_state:
    st.session_state.no_trade_explanation = []

if "startup_health" not in st.session_state:
    st.session_state.startup_health = []


# =====================================================
# HEADER
# =====================================================

st.title("📈 AlphaQuant Professional")

st.caption(
    "AI Assisted Long Only Trading Platform"
)

# =====================================================
# DASHBOARD
# =====================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Version",
    CONFIG["VERSION"]
)

c2.metric(
    "Scan Mode",
    "Entire NSE"
)

c3.metric(
    "Strategy",
    "Long Only"
)

c4.metric(
    "Status",
    "Ready"
)

st.divider()

st.info(
    "Phase 2.1 - Foundation Loaded Successfully"
)


# =====================================================
# STARTUP HEALTH CHECK
# =====================================================

def run_startup_health_check():
    checks = []

    def add(name, ok, message=""):
        checks.append({"Component": name, "Status": "OK" if ok else "MISSING/ERROR", "Message": message})

    add("Python", True, sys.version.split()[0])
    for module_name in ["streamlit", "pandas", "numpy", "psycopg2"]:
        try:
            __import__(module_name)
            add(module_name, True, "importable")
        except Exception as exc:
            add(module_name, False, str(exc))

    for module_name in [
        "os_brains.db", "os_brains.experience_memory", "os_brains.historical_analog_engine",
        "os_brains.strategist", "os_brains.risk_manager", "os_brains.portfolio_manager",
        "os_brains.reviewer", "os_brains.pipeline_manager",
    ]:
        try:
            __import__(module_name, fromlist=["*"])
            add(module_name, True, "importable")
        except Exception as exc:
            add(module_name, False, str(exc))

    try:
        from os_brains.db import apply_schema
        apply_schema()
        add("Database", True, "schema reachable")
    except Exception as exc:
        add("Database", False, str(exc))

    add("Configuration", bool(CONFIG), f"{len(CONFIG)} settings loaded")
    st.session_state.startup_health = checks
    return checks


def show_startup_health_check():
    if not st.session_state.startup_health:
        run_startup_health_check()
    unhealthy = [c for c in st.session_state.startup_health if c["Status"] != "OK"]
    with st.expander("Startup Health Check", expanded=bool(unhealthy)):
        st.dataframe(pd.DataFrame(st.session_state.startup_health), use_container_width=True)
        if unhealthy:
            st.error("AlphaQuant can start, but one or more services need attention before the full pipeline can complete.")
        else:
            st.success("All startup checks passed.")

show_startup_health_check()
# =====================================================
# UNIVERSE ENGINE
# VERSION 3.0.0 - Production Rebuild (Emergent)
# =====================================================
#
# The four brittle helpers that used to live here
# (fetch_complete_nse_universe, fetch_index_constituents,
# _clean_and_suffix_symbols, and their duplicated blacklist blocks)
# have been extracted into a single hardened module,
# `universe_engine.py`, which lives next to this file.
#
# The module exposes the SAME public signatures the rest of this app
# already imports/calls, so nothing else in the file needs to change:
#
#     NSE_INDEX_SOURCES                       - unchanged keys
#     fetch_complete_nse_universe() -> list   - '.NS'-suffixed uniques
#     fetch_index_constituents(url) -> set    - raw base symbols
#     _clean_and_suffix_symbols(iter) -> list - legacy alias
#
# The module handles: local disk cache (~/.alphaquant/universe_cache/*.csv,
# 24h TTL, stale-cache-wins), NSE archive fetch with cookie priming, public
# mirrors (nseindia.com/api + community GitHub CSVs), yfinance verification
# fallback for critical indices, urllib3 Retry with exponential backoff,
# rotating User-Agents, and a single canonical blacklist/suffix helper.
#
# @st.cache_data(ttl=86400, show_spinner=False) is re-applied inside the
# module, so the Streamlit-cache behaviour of this section is preserved.

# -------- BEGIN inlined universe_engine.py (v3.0.2, generated 2026-07-18 12:47:36 UTC) --------
# This block replaces the legacy Universe Engine (fetch_complete_nse_universe,
# fetch_index_constituents, and the duplicated blacklist code) with a hardened
# multi-tier fallback implementation:
#   Tier 1 - Local disk cache (~/.alphaquant/universe_cache/*.csv), 24h TTL
#   Tier 2 - nsearchives.nseindia.com (real NSE archives, primary)
#   Tier 3 - archives.nseindia.com + www.nseindia.com/api/... mirrors
#   Tier 4 - yfinance verification probe (Nifty50 seed fallback)
# Public API preserved: NSE_INDEX_SOURCES, fetch_complete_nse_universe(),
# fetch_index_constituents(url), _clean_and_suffix_symbols(iter).
# =========================================================
# IMPORTS
# =========================================================

import hashlib
import json
import logging
import os
import random
import tempfile
import time
from io import StringIO
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("alphaquant.universe")

# ---------------------------------------------------------
# Optional streamlit cache decorator (no-op when not on Streamlit)
# ---------------------------------------------------------
try:
    import streamlit as _st

    def _st_cache(func):
        return _st.cache_data(ttl=86400, show_spinner=False)(func)
except Exception:  # streamlit not installed / not running
    def _st_cache(func):
        return func

# ---------------------------------------------------------
# Optional yfinance import (only used by the tier-4 probe)
# ---------------------------------------------------------
try:
    import yfinance as yf
except Exception:  # yfinance is a project dep, but never let this file crash
    yf = None


# =========================================================
# CONSTANTS
# =========================================================

def _resolve_cache_dir() -> Path:
    """Prefer ~/.alphaquant/universe_cache, fall back to tempdir if not writable."""
    primary = Path.home() / ".alphaquant" / "universe_cache"
    try:
        primary.mkdir(parents=True, exist_ok=True)
        probe = primary / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return primary
    except Exception:
        fallback = Path(tempfile.gettempdir()) / "alphaquant_universe_cache"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


UNIVERSE_CACHE_DIR: Path = _resolve_cache_dir()
UNIVERSE_CACHE_META: Path = UNIVERSE_CACHE_DIR / "_meta.json"
UNIVERSE_CACHE_TTL_SEC: int = 86_400  # 24h

HTTP_TIMEOUT: tuple[int, int] = (5, 8)  # (connect, read) - fail fast on unreachable hosts
RETRY_TOTAL: int = 2
RETRY_BACKOFF: float = 0.3
RETRY_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})
# Note: 403 is INTENTIONALLY not in RETRY_STATUS. NSE returns 403 when the
# session cookies aren't primed - retrying without new cookies just wastes
# time. We handle 403 by cookie-priming once, then treating a second 403 as
# a hard failure and moving to the next URL/tier.
PER_URL_BUDGET_SEC: float = 25.0  # hard ceiling per URL incl. retries+backoff

USER_AGENTS: tuple[str, ...] = (
    # Realistic desktop browsers, rotated per session
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
)

# ---------------------------------------------------------
# NSE index sources (KEYS MUST NOT CHANGE - the rest of the app reads these)
#
# Primary uses `nsearchives.nseindia.com` (the newer NSE archive host that
# consistently returns 200 with browser-realistic UA + Referer). The legacy
# `archives.nseindia.com` host started returning 503/timeout in 2025 which
# is what triggered the "Universe Loading Failed" errors that motivated
# this rebuild.
# ---------------------------------------------------------
NSE_INDEX_SOURCES: dict[str, str] = {
    "Nifty50":        "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "Nifty Next 50":  "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv",
    "NSE500":         "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "Midcap":         "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    "Smallcap":       "https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
}

# Alternative hosts tried in order after the primary fails. Only real,
# publicly-reachable endpoints are listed - no placeholder GitHub URLs.
NSE_INDEX_MIRRORS: dict[str, tuple[str, ...]] = {
    "Nifty50": (
        "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050",
    ),
    "Nifty Next 50": (
        "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv",
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20NEXT%2050",
    ),
    "NSE500": (
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500",
    ),
    "Midcap": (
        "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20MIDCAP%20150",
    ),
    "Smallcap": (
        "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20SMALLCAP%20250",
    ),
    # LargeMidcap250 is merged into fetch_complete_nse_universe.
    "LargeMidcap250": (
        "https://nsearchives.nseindia.com/content/indices/ind_niftylargemidcap250list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftylargemidcap250list.csv",
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20LARGEMIDCAP%20250",
    ),
}

# The master equity list is the "everything on NSE" source.
EQUITY_MASTER_SOURCES: tuple[str, ...] = (
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
)

# Extra URLs merged into `fetch_complete_nse_universe` on top of the master.
_UNIVERSE_MERGE_KEYS: tuple[str, ...] = ("NSE500", "LargeMidcap250", "Smallcap")

# ---------------------------------------------------------
# Blacklists  (single source of truth - deduplicated from 3 places)
# ---------------------------------------------------------
SYMBOL_BLACKLIST: frozenset[str] = frozenset({
    "NIFTYBEES", "BANKBEES", "GOLDBEES", "LIQUIDBEES", "SILVERBEES",
    "JUNIORBEES", "CPSEETF", "PSUBNKBEES", "ITBEES",
})

SYMBOL_SUBSTRING_BLACKLIST: tuple[str, ...] = (
    "ETF", "BEES", "FUND", "GILT", "LIQUID", "NIFTY",
)


# =========================================================
# CACHE MANAGER
# =========================================================

def _cache_path(key: str) -> Path:
    """Deterministic per-key CSV cache file."""
    safe = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return UNIVERSE_CACHE_DIR / f"{safe}.csv"


def _meta_read() -> dict:
    try:
        return json.loads(UNIVERSE_CACHE_META.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _meta_write(meta: dict) -> None:
    try:
        UNIVERSE_CACHE_META.write_text(
            json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8"
        )
    except Exception as exc:
        log.warning("Universe: could not write cache meta: %s", exc)


def _cache_read(key: str) -> tuple[list[str] | None, float | None]:
    """Return (symbols, fetched_at_epoch) or (None, None) if no cache."""
    path = _cache_path(key)
    if not path.exists():
        return None, None
    try:
        symbols = [
            line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        meta = _meta_read().get(key, {})
        fetched_at = float(meta.get("fetched_at", path.stat().st_mtime))
        return symbols, fetched_at
    except Exception as exc:
        log.warning("Universe: cache read failed for %s: %s", key, exc)
        return None, None


def _cache_write(key: str, symbols: list[str]) -> None:
    if not symbols:
        return
    path = _cache_path(key)
    try:
        path.write_text("\n".join(symbols), encoding="utf-8")
        meta = _meta_read()
        meta[key] = {"fetched_at": time.time(), "count": len(symbols)}
        _meta_write(meta)
    except Exception as exc:
        log.warning("Universe: cache write failed for %s: %s", key, exc)


def _is_fresh(fetched_at: float | None) -> bool:
    if not fetched_at:
        return False
    return (time.time() - fetched_at) < UNIVERSE_CACHE_TTL_SEC


def _fmt_age(fetched_at: float) -> str:
    delta = int(max(0, time.time() - fetched_at))
    h, rem = divmod(delta, 3600)
    m, _ = divmod(rem, 60)
    return f"{h}h {m:02d}m"


# =========================================================
# HTTP LAYER
# =========================================================

def _build_session() -> requests.Session:
    """
    One reusable session with:
      * rotating browser-realistic UA
      * urllib3 Retry (exponential backoff, 403/429/5xx)
      * HTTPAdapter mounted on http:// and https://
    """
    s = requests.Session()

    retry = Retry(
        total=RETRY_TOTAL,
        connect=RETRY_TOTAL,
        read=RETRY_TOTAL,
        status=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=tuple(RETRY_STATUS),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=16)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/csv,application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.nseindia.com/",
        "Upgrade-Insecure-Requests": "1",
    })
    return s


def _prime_nse_cookies(session: requests.Session) -> None:
    """
    NSE returns 403 to any request that doesn't already carry its session
    cookies. Hitting the home page first can get us `nsit`/`nseappid`
    cookies which unlock the `www.nseindia.com` API endpoints.

    Best-effort: uses a plain requests call with NO retries so a hostile
    network can't stall this warm-up for tens of seconds. Note that the
    primary source `nsearchives.nseindia.com` does NOT require cookies -
    it serves 200 with just UA + Referer - so a failed prime here is
    non-fatal: the real fetches will still succeed.
    """
    for warmup in ("https://www.nseindia.com/",
                   "https://www.nseindia.com/market-data/live-equity-market"):
        try:
            # Bypass the retry-mounted adapters by using a bare request.
            r = requests.get(
                warmup,
                headers={
                    "User-Agent": session.headers.get("User-Agent", USER_AGENTS[0]),
                    "Accept": "text/html,application/xhtml+xml,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive",
                },
                timeout=(3, 4),
            )
            # Copy any cookies back into our session
            session.cookies.update(r.cookies)
        except Exception as exc:
            log.debug("Universe: NSE cookie prime hit %s failed: %s", warmup, exc)


def _fetch_csv(session: requests.Session, url: str) -> pd.DataFrame | None:
    """
    Best-effort CSV/JSON fetch. Returns a DataFrame with normalised
    (uppercased, stripped) column names, or None on failure. The
    `nseindia.com/api/...` mirrors return JSON, which is transparently
    reshaped into a DataFrame with a `SYMBOL` column.

    Has a hard PER_URL_BUDGET_SEC wall-clock ceiling to prevent unreachable
    hosts from stalling the whole universe load.
    """
    start = time.monotonic()
    try:
        resp = session.get(url, timeout=HTTP_TIMEOUT)
    except Exception as exc:
        log.warning("Universe: request error for %s: %s", url, exc)
        return None

    if time.monotonic() - start > PER_URL_BUDGET_SEC:
        log.warning("Universe: exceeded %ss budget on %s", PER_URL_BUDGET_SEC, url)
        return None

    if resp.status_code != 200 or not resp.content:
        log.warning("Universe: HTTP %s from %s", resp.status_code, url)
        return None

    ctype = (resp.headers.get("Content-Type") or "").lower()
    body = resp.text

    try:
        if "json" in ctype or body.lstrip().startswith("{"):
            payload = resp.json()
            rows = payload.get("data") if isinstance(payload, dict) else None
            if not rows:
                return None
            df = pd.DataFrame(rows)
        else:
            df = pd.read_csv(StringIO(body))
    except Exception as exc:
        log.warning("Universe: parse error for %s: %s", url, exc)
        return None

    if df is None or df.empty:
        return None

    df.columns = [str(c).upper().strip() for c in df.columns]
    return df


def _extract_symbol_column(df: pd.DataFrame) -> list[str]:
    """Pick the first plausible symbol column and return uppercased values."""
    for candidate in ("SYMBOL", "SYMBOL ", "TICKER", "SCRIP", "SCRIPCODE", "NSE_SYMBOL"):
        if candidate in df.columns:
            return (
                df[candidate]
                .astype(str)
                .str.upper()
                .str.strip()
                .replace({"NAN": ""})
                .tolist()
            )
    return []


# =========================================================
# NORMALISATION HELPER (single source of truth)
# =========================================================

def _normalize_symbols(raw: Iterable[str], suffix: bool = True) -> list[str]:
    """
    Uppercase + strip + dedupe + sort, apply blacklist, optionally append '.NS'.
    Empty/short/non-alnum entries are dropped. This is the ONE place blacklist
    rules live - any changes go here, nowhere else.
    """
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        s = str(item).upper().strip()
        # Strip any pre-existing '.NS' or '.BO' so blacklist matches the base.
        if s.endswith(".NS") or s.endswith(".BO"):
            s = s.rsplit(".", 1)[0]
        if len(s) < 2:
            continue
        if not s.replace("-", "").replace("&", "").isalnum():
            continue
        if s in SYMBOL_BLACKLIST:
            continue
        if any(bad in s for bad in SYMBOL_SUBSTRING_BLACKLIST):
            continue
        final = f"{s}.NS" if suffix else s
        if final in seen:
            continue
        seen.add(final)
        out.append(final)
    out.sort()
    return out


# =========================================================
# TIER-4  yfinance verification fallback
# =========================================================

# Small, hard-coded seed of Nifty50 constituents (Jan 2026 membership) used
# only when EVERY http tier and every mirror has failed for the critical
# Nifty50/NSE500 paths. yfinance is then used to VERIFY these tickers are
# alive on Yahoo - anything that fails to resolve is dropped. This is not
# meant to replace the primary source, only to keep the app usable when NSE
# and every mirror are simultaneously unreachable.
_NIFTY50_SEED: tuple[str, ...] = (
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BEL", "BHARTIARTL",
    "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB",
    "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK",
    "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK",
    "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK",
    "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND",
    "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE",
    "SBIN", "SHRIRAMFIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS",
    "TATASTEEL", "TCS", "TECHM", "TITAN", "TRENT",
    "ULTRACEMCO", "UPL", "WIPRO",
)


def _yfinance_probe(symbols: Iterable[str]) -> list[str]:
    """
    Return the subset of `symbols` (bare, no suffix) for which yfinance
    has non-empty history. Fast: uses a single batched download.
    """
    if yf is None:
        return []
    tickers = [f"{s}.NS" for s in symbols]
    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="5d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=False,
        )
    except Exception as exc:
        log.warning("Universe: yfinance probe failed: %s", exc)
        return []

    alive: list[str] = []
    if hasattr(data, "columns") and getattr(data.columns, "nlevels", 1) > 1:
        for t in tickers:
            try:
                sub = data[t]
                if not sub.dropna(how="all").empty:
                    alive.append(t.rsplit(".", 1)[0])
            except Exception:
                continue
    else:
        # single-ticker degenerate case
        if not data.dropna(how="all").empty and tickers:
            alive.append(tickers[0].rsplit(".", 1)[0])
    return alive


# =========================================================
# INTERNAL FETCH ORCHESTRATOR
# =========================================================

def _fetch_from_urls(
    session: requests.Session,
    urls: Iterable[str],
    label: str,
) -> list[str]:
    """
    Try each URL in order, return the first non-empty symbol list. Emits the
    exact log line style required ("Universe: NSE archives unavailable ...").
    """
    urls = list(urls)
    if not urls:
        return []

    for idx, url in enumerate(urls):
        tier = "NSE archives" if idx == 0 else f"mirror #{idx}"
        df = _fetch_csv(session, url)
        if df is None:
            log.warning(
                "Universe: %s unavailable for %s, trying %s",
                tier, label, f"mirror #{idx + 1}" if idx + 1 < len(urls) else "next tier",
            )
            continue
        symbols = _extract_symbol_column(df)
        if not symbols:
            log.warning("Universe: %s returned no SYMBOL column for %s", tier, label)
            continue
        log.info("Universe: %s served %s (%d rows)", tier, label, len(symbols))
        return symbols

    return []


# =========================================================
# PUBLIC API
# =========================================================

@_st_cache
def fetch_complete_nse_universe() -> list[str]:
    """
    Return the full NSE equity universe as sorted, unique, '.NS'-suffixed
    tickers. Implements the 4-tier fallback described in the module docstring.
    Never raises. Empty list is only returned if EVERY tier fails AND no
    cache has ever existed.
    """
    cache_key = "complete_nse_universe"
    cached, fetched_at = _cache_read(cache_key)

    if cached and _is_fresh(fetched_at):
        log.info(
            "Universe: loaded cache (%d symbols, age %s)",
            len(cached), _fmt_age(fetched_at),
        )
        return cached

    if cached:
        log.info("Universe: refreshing (cache expired)")
    else:
        log.info("Universe: no cache found, cold fetch")

    session = _build_session()
    _prime_nse_cookies(session)

    # --- Tier 2/3: master equity list + index constituent merges ---
    master = _fetch_from_urls(session, EQUITY_MASTER_SOURCES, "EQUITY_L")
    merged: set[str] = set(master)

    for key in _UNIVERSE_MERGE_KEYS:
        urls: list[str] = []
        primary = NSE_INDEX_SOURCES.get(key)
        if primary:
            urls.append(primary)
        urls.extend(NSE_INDEX_MIRRORS.get(key, ()))
        merged.update(_fetch_from_urls(session, urls, key))

    # --- Tier 4: yfinance probe as a last resort for the critical path ---
    if not merged:
        log.warning("Universe: all HTTP tiers failed, probing yfinance (Nifty50 seed)")
        probed = _yfinance_probe(_NIFTY50_SEED)
        merged.update(probed)

    final = _normalize_symbols(merged, suffix=True)

    if final:
        _cache_write(cache_key, final)
        log.info("Universe Loaded: %d symbols", len(final))
        return final

    # --- Stale-cache-wins ---
    if cached:
        log.warning("Universe: using cached universe (last refresh failed)")
        return cached

    log.error("Universe: every source failed and no cache exists - returning empty list")
    return []


@_st_cache
def fetch_index_constituents(url: str) -> set[str]:
    """
    Generic NSE index-constituent fetcher. Returns a set of RAW base symbols
    (no '.NS' suffix) - unchanged contract vs. the legacy implementation so
    the downstream `_clean_and_suffix_symbols` keeps working.

    Fallback chain per URL:
      1. Disk cache (< 24h)
      2. Primary URL (typically archives.nseindia.com)
      3. Mirrors mapped by the URL's index-key, if known
      4. Stale-cache-wins
    """
    if not url:
        return set()

    cache_key = f"index::{hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]}"
    cached, fetched_at = _cache_read(cache_key)

    if cached and _is_fresh(fetched_at):
        log.info(
            "Universe: loaded cache for %s (%d symbols, age %s)",
            url, len(cached), _fmt_age(fetched_at),
        )
        return set(cached)

    if cached:
        log.info("Universe: refreshing index %s (cache expired)", url)

    # Discover which named index this URL corresponds to, if any, so we can
    # append its known mirrors.
    index_key: str | None = None
    for key, src in NSE_INDEX_SOURCES.items():
        if src == url:
            index_key = key
            break

    session = _build_session()
    _prime_nse_cookies(session)

    urls: list[str] = [url]
    if index_key:
        urls.extend(NSE_INDEX_MIRRORS.get(index_key, ()))

    symbols = _fetch_from_urls(session, urls, index_key or url)

    # For the critical Nifty50 path, use yfinance as a last resort.
    if not symbols and index_key in {"Nifty50", "NSE500"}:
        log.warning("Universe: yfinance fallback for %s", index_key)
        symbols = _yfinance_probe(_NIFTY50_SEED)

    # Store the CLEANED (blacklist-applied) base symbols, but return an unsuffixed
    # set to preserve the legacy public contract.
    cleaned = _normalize_symbols(symbols, suffix=False)

    if cleaned:
        _cache_write(cache_key, cleaned)
        log.info("Universe Loaded: %d symbols for %s", len(cleaned), index_key or url)
        return set(cleaned)

    if cached:
        log.warning("Universe: using cached universe for %s (last refresh failed)", url)
        return set(cached)

    log.error("Universe: index %s exhausted every source and has no cache", url)
    return set()


# =========================================================
# BACKWARD-COMPAT SHIM
# =========================================================
# The legacy file defined `_clean_and_suffix_symbols` inline. Downstream
# call-sites (`get_named_universe`, `get_cap_bucket_symbols`) still use it,
# so we re-export a thin wrapper that delegates to `_normalize_symbols`.

def _clean_and_suffix_symbols(base_symbols: Iterable[str]) -> list[str]:
    """Legacy alias - kept so downstream call-sites keep working unchanged."""
    return _normalize_symbols(base_symbols, suffix=True)
# -------- END inlined universe_engine.py --------

# =====================================================
# LOAD UNIVERSE
# =====================================================

ALL_SYMBOLS = fetch_complete_nse_universe()

if len(ALL_SYMBOLS) == 0:
    st.error("Universe Loading Failed")
else:
    st.success(f"Universe Loaded : {len(ALL_SYMBOLS)} Stocks")

if _P("Scanner"):
    with st.expander("Universe Preview"):
        st.dataframe(
            pd.DataFrame({"Symbol": ALL_SYMBOLS}).head(100)
        )

# =====================================================
# SCAN MANAGER
# =====================================================
#
# Everything above this point (fetch_complete_nse_universe / ALL_SYMBOLS)
# is one raw data source: "the entire NSE, minus obvious ETFs". The Scan
# Manager below turns that - plus a few more NSE index-constituent
# sources - into the actual, final list of symbols a scan will run
# against, chosen and filtered by the user BEFORE any market data is
# downloaded or any strategy runs. This keeps a "RUN ALPHAQUANT" (or,
# later, an automated scan) from blindly crawling the whole exchange
# every time.
#
# It produces exactly one thing that matters downstream:
# `st.session_state.scan_universe` - the symbol list the Download/Scan
# buttons below now consume instead of the raw ALL_SYMBOLS. Nothing about
# how strategies, AI Consensus, Risk Manager, Portfolio Manager, or paper
# trading work is changed by this section.
#
# NSE_INDEX_SOURCES + fetch_index_constituents + _clean_and_suffix_symbols
# are re-exported from universe_engine (see block above), so the rest of
# this Scan Manager works unchanged.


SCAN_UNIVERSE_CHOICES = [
    "NSE All", "NSE500", "Nifty50", "Nifty Next 50",
    "Midcap", "Smallcap", "Watchlist",
]


def get_named_universe(choice):
    """
    Resolves one of the Scan Manager's universe choices to a final,
    ".NS"-suffixed, blacklist-cleaned symbol list.

    "NSE All" reuses fetch_complete_nse_universe()'s output as-is (already
    cleaned/suffixed). Every named index reuses the same NSE archive
    source pattern via fetch_index_constituents(). "Watchlist" reads the
    user's own session watchlist (managed in the Watchlist panel below).
    """

    if choice == "NSE All":
        return list(ALL_SYMBOLS)

    if choice == "Watchlist":
        return _clean_and_suffix_symbols(
            s.replace(".NS", "") for s in st.session_state.watchlist
        )

    url = NSE_INDEX_SOURCES.get(choice)

    if url is None:
        return []

    return _clean_and_suffix_symbols(fetch_index_constituents(url))


def get_cap_bucket_symbols(bucket):
    """
    "Market Cap" filter data source. There is no free, bulk market-cap
    number available without a per-symbol lookup across the whole
    exchange, so this reuses NSE's own index membership as the lightest
    reasonable proxy: Nifty50 + Nifty Next 50 = Large Cap, Nifty Midcap
    150 = Mid Cap, Nifty Smallcap 250 = Small Cap (NSE's own index
    methodology already buckets the exchange by free-float market cap).
    Returns None for "Any" (no filtering), or an empty set if every
    underlying source failed to fetch (degrades to "no cap filtering"
    rather than zeroing out the universe on a network hiccup).
    """

    if bucket == "Large Cap":
        base = (
            fetch_index_constituents(NSE_INDEX_SOURCES["Nifty50"])
            | fetch_index_constituents(NSE_INDEX_SOURCES["Nifty Next 50"])
        )
    elif bucket == "Mid Cap":
        base = fetch_index_constituents(NSE_INDEX_SOURCES["Midcap"])
    elif bucket == "Small Cap":
        base = fetch_index_constituents(NSE_INDEX_SOURCES["Smallcap"])
    else:
        return None

    return set(_clean_and_suffix_symbols(base))


SCAN_STYLE_STRATEGY_MAP = {

    "Breakout": {"BREAKOUT"},

    "Momentum": {"VCP", "PRICE SQUEEZE"},

    "Swing": {"DEMAND & SUPPLY", "MARKET REGIME"},

    "Intraday": {"ORDER BLOCK", "FVG"},

}


# =====================================================
# SCANNER FILTER PERSISTENCE
# =====================================================
# Streamlit widget keys are ephemeral: when the Scanner tab isn't rendered
# (user switched to Dashboard/AI/etc.), the `scan_manager_*` widget keys
# are garbage-collected from session_state. To keep filter selections
# stable across tab switches, we mirror every widget value into a
# `*_saved` shadow key that survives the widget's lifecycle. The pipeline
# and build_default_scan_universe_for_pipeline() read exclusively from
# the saved keys.

_SCAN_FILTER_DEFAULTS = {
    "scan_manager_universe_choice_saved": SCAN_UNIVERSE_CHOICES[0],
    "scan_manager_cap_filter_saved": "Any",
    "scan_manager_price_range_saved": (20, 20000),
    "scan_manager_min_volume_saved": CONFIG["MIN_AVG_VOLUME"],
    "scan_manager_min_turnover_saved": CONFIG["MIN_AVG_TURNOVER"],
    "scan_manager_sector_filter_saved": [],
    "scan_manager_style_filter_saved": [],
}
for _k, _v in _SCAN_FILTER_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v



def apply_style_selection_to_strategies(selected_styles):
    """
    Applies the Scan Manager's Style filter by enabling/disabling entries
    already sitting in st.session_state.strategy_registry - it does not
    change how the pipeline runs registered strategies (run_all_strategies
    is untouched). No style selected = no restriction, which is also the
    app's long-standing default (every registered strategy enabled).
    """

    if not selected_styles:

        for strategy in st.session_state.strategy_registry:
            strategy.enabled = True

        return

    active_names = set()

    for style in selected_styles:
        active_names |= SCAN_STYLE_STRATEGY_MAP.get(style, set())

    for strategy in st.session_state.strategy_registry:
        strategy.enabled = strategy.name in active_names


def fetch_quote_snapshot(symbols):
    """
    Cheap pre-scan snapshot used only to filter the universe by price /
    volume / liquidity before the real (period=1y+) download happens.
    Intentionally independent of download_batch/download_market_data:
    those are tuned for the full history download every stock needs once
    it's actually being scanned, while this only needs ~5 days of data
    per symbol to answer "is this even in range", so it stays a small,
    separate helper rather than overloading the main download path.
    """

    snapshot = {}

    def _fetch_one(symbol):

        try:

            df = yf.download(
                symbol,
                period="5d",
                interval="1d",
                progress=False,
                auto_adjust=True,
                threads=False,
            )

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df is None or len(df) == 0:
                return None

            closes = df["Close"].dropna()
            volumes = df["Volume"].dropna()

            if len(closes) == 0 or len(volumes) == 0:
                return None

            last_close = float(closes.iloc[-1])
            avg_volume = float(volumes.tail(5).mean())

            return symbol, {
                "price": last_close,
                "avg_volume": avg_volume,
                "avg_turnover": last_close * avg_volume,
            }

        except Exception as e:

            logging.warning(f"quote snapshot {symbol} : {e}")
            return None

    with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"]) as executor:

        for result in executor.map(_fetch_one, symbols):

            if result is not None:
                symbol, data = result
                snapshot[symbol] = data

    return snapshot


def build_scan_universe(
    universe_choice,
    cap_filter="Any",
    price_range=(0, 100000),
    min_volume=0,
    min_turnover=0,
    sectors=None,
    styles=None,
):
    """
    The Scan Manager's single public entry point: given a universe choice
    and the pre-scan filters, returns the final symbol list a scan should
    run against. Both the manual "Preview Scan List" button below and any
    future automated scan trigger call this same function, so there is
    exactly one place universe + filter logic lives.
    """

    symbols = get_named_universe(universe_choice)

    if cap_filter != "Any":
        cap_set = get_cap_bucket_symbols(cap_filter)
        if cap_set:
            symbols = [s for s in symbols if s in cap_set]

    if sectors:
        allowed = set(sectors)
        symbols = [
            s for s in symbols
            if STOCK_SECTOR_MAP.get(s.replace(".NS", ""), "UNKNOWN") in allowed
        ]

    price_min, price_max = price_range

    needs_quote_filter = (
        price_min > 0 or price_max < 100000 or min_volume > 0 or min_turnover > 0
    )

    if needs_quote_filter and symbols:

        snapshot = fetch_quote_snapshot(symbols)

        filtered = []

        for s in symbols:

            q = snapshot.get(s)

            if q is None:
                continue

            if not (price_min <= q["price"] <= price_max):
                continue

            if q["avg_volume"] < min_volume:
                continue

            if q["avg_turnover"] < min_turnover:
                continue

            filtered.append(s)

        symbols = filtered

    apply_style_selection_to_strategies(styles or [])

    return symbols


# =====================================================
# SCAN MANAGER UI
# =====================================================

if _P("Scanner"):

    st.divider()

    st.subheader("Scan Manager")

    st.caption(
        "Choose exactly what to scan before downloading any data or running "
        "any strategy - the Scan Manager builds the final symbol list once, "
        "up front."
    )

    if "scan_universe" not in st.session_state:
        st.session_state.scan_universe = []

    with st.expander("Watchlist"):

        watchlist_cols = st.columns([3, 1])

        new_watch_symbol = watchlist_cols[0].text_input(
            "Add symbol (e.g. RELIANCE)",
            key="watchlist_add_input",
        )

        if watchlist_cols[1].button("Add", key="watchlist_add_button"):

            cleaned = new_watch_symbol.strip().upper().replace(".NS", "")

            if cleaned and cleaned not in st.session_state.watchlist:
                st.session_state.watchlist.append(cleaned)

        if st.session_state.watchlist:

            st.write(", ".join(st.session_state.watchlist))

            remove_choice = st.selectbox(
                "Remove from watchlist",
                ["-"] + st.session_state.watchlist,
                key="watchlist_remove_select",
            )

            if remove_choice != "-" and st.button("Remove", key="watchlist_remove_button"):
                st.session_state.watchlist.remove(remove_choice)

        else:

            st.caption("Watchlist is empty.")

    scan_manager_cols = st.columns(2)

    scan_universe_choice = scan_manager_cols[0].selectbox(
        "Universe",
        SCAN_UNIVERSE_CHOICES,
        key="scan_manager_universe_choice",
    )
    st.session_state["scan_manager_universe_choice_saved"] = scan_universe_choice

    scan_cap_filter = scan_manager_cols[1].selectbox(
        "Market Cap",
        ["Any", "Large Cap", "Mid Cap", "Small Cap"],
        key="scan_manager_cap_filter",
    )
    st.session_state["scan_manager_cap_filter_saved"] = scan_cap_filter

    scan_price_range = st.slider(
        "Price Range (Rs)",
        min_value=0,
        max_value=20000,
        value=(20, 20000),
        key="scan_manager_price_range",
    )
    st.session_state["scan_manager_price_range_saved"] = scan_price_range

    scan_min_volume = st.number_input(
        "Minimum Average Volume (5-day)",
        min_value=0,
        value=CONFIG["MIN_AVG_VOLUME"],
        step=1000,
        key="scan_manager_min_volume",
    )
    st.session_state["scan_manager_min_volume_saved"] = scan_min_volume

    scan_min_turnover = st.number_input(
        "Liquidity - Minimum Average Turnover (Rs, 5-day)",
        min_value=0,
        value=CONFIG["MIN_AVG_TURNOVER"],
        step=1000000,
        key="scan_manager_min_turnover",
    )
    st.session_state["scan_manager_min_turnover_saved"] = scan_min_turnover

    scan_sector_filter = st.multiselect(
        "Sector (known-sector map only; leave empty for no sector restriction)",
        sorted(set(STOCK_SECTOR_MAP.values())),
        key="scan_manager_sector_filter",
    )
    st.session_state["scan_manager_sector_filter_saved"] = scan_sector_filter

    scan_style_filter = st.multiselect(
        "Style (which strategy types this scan should look for; leave empty for all)",
        sorted(SCAN_STYLE_STRATEGY_MAP.keys()),
        key="scan_manager_style_filter",
    )
    st.session_state["scan_manager_style_filter_saved"] = scan_style_filter

    st.checkbox(
        "Long Only",
        value=True,
        disabled=True,
        help="AlphaQuant is a long-only platform end-to-end -- there is no "
             "short-selling logic to disable.",
    )

    if st.button("Preview Scan List", key="scan_manager_build_button"):

        with st.spinner("Building scan universe..."):

            st.session_state.scan_universe = build_scan_universe(
                scan_universe_choice,
                cap_filter=scan_cap_filter,
                price_range=scan_price_range,
                min_volume=scan_min_volume,
                min_turnover=scan_min_turnover,
                sectors=scan_sector_filter,
                styles=scan_style_filter,
            )

            st.session_state.scan_manager_active_styles = scan_style_filter

    if st.session_state.scan_universe:

        st.success(
            f"Scan list ready: {len(st.session_state.scan_universe)} symbols "
            f"selected for the next scan."
        )

        with st.expander("Scan List Preview"):
            st.dataframe(
                pd.DataFrame(
                    {"Symbol": st.session_state.scan_universe}
                ).head(200)
            )

    else:

        st.info("Build a scan list above before downloading data or running a scan.")


# =====================================================
# PRODUCTION DOWNLOAD MANAGER
# VERSION 2.1C
# =====================================================

DOWNLOAD_STATUS = st.empty()

DOWNLOAD_PROGRESS = st.progress(0)


def split_into_batches(symbols, batch_size):

    return [

        symbols[i:i + batch_size]

        for i in range(

            0,

            len(symbols),

            batch_size

        )

    ]


def download_batch(batch):

    """
    Downloads one batch.

    Returns

    {
        symbol:dataframe
    }

    """

    results = {}

    for symbol in batch:

        try:

            df = yf.download(

                symbol,

                period=CONFIG["DOWNLOAD_PERIOD"],

                interval=CONFIG["DOWNLOAD_INTERVAL"],

                progress=False,

                auto_adjust=True,

                threads=False

            )

            # yfinance returns MultiIndex columns (Price, Ticker) even for a
            # single symbol. Flatten to plain OHLCV column names so every
            # downstream df["Close"]/df["High"]/etc access returns a Series,
            # not a nested DataFrame.
            if isinstance(df.columns, pd.MultiIndex):

                df.columns = df.columns.get_level_values(0)

            # Drop the most recent row if it is still an incomplete/unsettled
            # session (all price fields NaN), which yfinance can include for
            # the current trading day.
            if len(df) and df["Close"].isna().iloc[-1]:

                df = df.iloc[:-1]

            if len(df) > 50:

                results[symbol] = df

        except Exception as e:

            logging.warning(

                f"{symbol} : {e}"

            )

    return results


def download_market_data(symbols):

    logging.info(

        "Starting Production Download"

    )

    batches = split_into_batches(

        symbols,

        CONFIG["DOWNLOAD_BATCH"]

    )

    complete = {}

    total = len(batches)

    start = time.time()

    with ThreadPoolExecutor(

        max_workers=CONFIG["MAX_WORKERS"]

    ) as executor:

        futures = [

            executor.submit(

                download_batch,

                batch

            )

            for batch in batches

        ]

        for idx, future in enumerate(futures):

            data = future.result()

            complete.update(data)

            DOWNLOAD_PROGRESS.progress(

                (idx + 1) / total

            )

            DOWNLOAD_STATUS.write(

                f"Completed Batch {idx+1} / {total}"

            )

    elapsed = round(

        time.time() - start,

        2

    )

    logging.info(

        f"{len(complete)} datasets downloaded"

    )

    st.success(

        f"{len(complete)} symbols downloaded in {elapsed} sec"

    )

    return complete


# =====================================================
# MARKET DATA ENGINE STATUS
# =====================================================

st.divider()

st.subheader("Market Data Engine")

st.caption("Market data downloads automatically when RUN ALPHAQUANT is pressed.")

if st.session_state.market_data:

    st.success(f"{len(st.session_state.market_data)} symbol datasets are loaded for the latest run.")

else:

    st.info("No market data loaded yet. Press RUN ALPHAQUANT to build the universe and download data automatically.")
# =====================================================
# CONFIGURATION SIDEBAR
# VERSION 2.1D
# =====================================================

st.sidebar.title("⚙ AlphaQuant Settings")

CONFIG["DOWNLOAD_PERIOD"] = st.sidebar.selectbox(
    "History",
    ["6mo", "1y", "2y", "5y"],
    index=1
)

CONFIG["DOWNLOAD_INTERVAL"] = st.sidebar.selectbox(
    "Interval",
    ["1d", "1wk"],
    index=0
)

CONFIG["DOWNLOAD_BATCH"] = st.sidebar.slider(
    "Batch Size",
    min_value=10,
    max_value=100,
    value=CONFIG["DOWNLOAD_BATCH"],
    step=10
)

CONFIG["MAX_WORKERS"] = st.sidebar.slider(
    "Parallel Workers",
    min_value=2,
    max_value=16,
    value=CONFIG["MAX_WORKERS"]
)

CONFIG["MIN_PRICE"] = st.sidebar.number_input(
    "Minimum Stock Price (₹)",
    min_value=1,
    value=CONFIG["MIN_PRICE"]
)

CONFIG["MIN_AVG_VOLUME"] = st.sidebar.number_input(
    "Minimum Average Daily Volume",
    min_value=1000,
    value=CONFIG["MIN_AVG_VOLUME"],
    step=1000
)

CONFIG["MAX_OPEN_POSITIONS"] = st.sidebar.slider(
    "Maximum Open Positions",
    min_value=1,
    max_value=20,
    value=CONFIG["MAX_OPEN_POSITIONS"]
)

st.sidebar.markdown("---")

st.sidebar.success("Configuration Loaded")
# =====================================================
# INDICATOR ENGINE
# VERSION 2.2A
# =====================================================

try:
    import pandas_ta as ta
except Exception as e:
    logging.exception("pandas_ta failed to import")
    st.error(
        "pandas-ta failed to import:\n\n" + str(e)
    )
    st.code(traceback.format_exc())
    st.stop()


def calculate_indicators(df):
    """
    Calculates all core indicators once.

    Returns dataframe with indicators added.
    """

    # Default download period is "1y", which yfinance realistically
    # returns as ~249 rows (calendar year minus weekends/holidays), never
    # a full 250. The old ">= 250" bar was unreachable with the default
    # config, silently rejecting every stock. 200 rows is still enough
    # history for the longest lookback actually used below (EMA200).
    if len(df) < 200:
        return None

    try:

        # ==========================
        # EMA
        # ==========================

        df["EMA20"] = ta.ema(
            df["Close"],
            length=20
        )

        df["EMA50"] = ta.ema(
            df["Close"],
            length=50
        )

        df["EMA100"] = ta.ema(
            df["Close"],
            length=100
        )

        df["EMA200"] = ta.ema(
            df["Close"],
            length=200
        )

        # ==========================
        # RSI
        # ==========================

        df["RSI"] = ta.rsi(
            df["Close"],
            length=14
        )

        # ==========================
        # ATR
        # ==========================

        df["ATR"] = ta.atr(

            df["High"],

            df["Low"],

            df["Close"],

            length=14

        )

        # ==========================
        # ADX
        # ==========================

        adx = ta.adx(

            df["High"],

            df["Low"],

            df["Close"]

        )

        df["ADX"] = adx["ADX_14"]

        # ==========================
        # MACD
        # ==========================

        macd = ta.macd(

            df["Close"]

        )

        df["MACD"] = macd["MACD_12_26_9"]

        df["MACD_SIGNAL"] = macd["MACDs_12_26_9"]

        # ==========================
        # Bollinger
        # ==========================

        # length=20 must be explicit: this pandas_ta version defaults
        # bbands() to a 5-period window, not 20, when length is omitted.
        # Column names also vary by pandas_ta version (e.g. "BBU_20_2.0"
        # vs "BBU_20_2.0_2.0"), so select by prefix instead of an exact
        # hardcoded name.
        bb = ta.bbands(df["Close"], length=20)

        bb_upper_col = [c for c in bb.columns if c.startswith("BBU_20")][0]

        bb_middle_col = [c for c in bb.columns if c.startswith("BBM_20")][0]

        bb_lower_col = [c for c in bb.columns if c.startswith("BBL_20")][0]

        df["BB_UPPER"] = bb[bb_upper_col]

        df["BB_MIDDLE"] = bb[bb_middle_col]

        df["BB_LOWER"] = bb[bb_lower_col]

        # ==========================
        # VWAP
        # ==========================

        df["VWAP"] = ta.vwap(

            df["High"],

            df["Low"],

            df["Close"],

            df["Volume"]

        )

        # ==========================
        # Average Volume
        # ==========================

        df["AVG_VOLUME20"] = (

            df["Volume"]

            .rolling(20)

            .mean()

        )

        # ==========================
        # Relative Volume
        # ==========================

        df["RVOL"] = (

            df["Volume"]

            /

            df["AVG_VOLUME20"]

        )

        # ==========================
        # 52 Week High Low
        # ==========================

        df["HIGH52"] = (

            df["High"]

            .rolling(252)

            .max()

        )

        df["LOW52"] = (

            df["Low"]

            .rolling(252)

            .min()

        )

        return df

    except Exception as e:

        st.error("===================================")
        st.error("Indicator failed")
        st.error(str(e))
        st.code(traceback.format_exc())

        return None
# =====================================================
# STOCK INTELLIGENCE OBJECT
# VERSION 2.2B
# =====================================================

class StockObject:
    """
    Master object for every stock.

    Every engine writes into this object.

    Indicators

    Patterns

    Risk

    News

    Portfolio

    AI Decision

    """

    def __init__(self, symbol):

        self.symbol = symbol

        self.data = None

        self.indicators = {}

        self.patterns = {}

        self.risk = {}

        self.market = {}

        self.news = {}

        self.portfolio = {}

        self.decision = {}

        self.score = {

            "trend": 0,

            "momentum": 0,

            "volume": 0,

            "volatility": 0,

            "pattern": 0,

            "market": 0,

            "sector": 0,

            "news": 0,

            "risk": 0,

            "quality": 0

        }

        self.state = "DISCOVERED"

        self.reason = []

    def set_dataframe(self, df):

        self.data = df

    def add_indicator(self, name, value):

        self.indicators[name] = value

    def add_pattern(self, name, value):

        self.patterns[name] = value

    def add_news(self, name, value):

        self.news[name] = value

    def add_market(self, name, value):

        self.market[name] = value

    def add_risk(self, name, value):

        self.risk[name] = value

    def add_reason(self, text):

        self.reason.append(text)

    def set_state(self, state):

        self.state = state

    def add_score(self, category, points):

        if category in self.score:

            self.score[category] += points

    def calculate_trade_quality(self):

        total = 0

        for key in self.score:

            if key != "quality":

                total += self.score[key]

        self.score["quality"] = round(total, 2)

        return self.score["quality"]

    def summary(self):

        return {

            "Symbol": self.symbol,

            "State": self.state,

            "Trade Quality": self.score["quality"],

            "Reasons": self.reason

        }


# =====================================================
# STOCK OBJECT STORAGE
# =====================================================

if "stock_objects" not in st.session_state:

    st.session_state.stock_objects = {}


def get_stock(symbol):

    if symbol not in st.session_state.stock_objects:

        st.session_state.stock_objects[symbol] = StockObject(symbol)

    return st.session_state.stock_objects[symbol]


st.sidebar.success("Stock Intelligence Engine Loaded")
# =====================================================
# TRADE QUALITY ENGINE
# VERSION 2.2C
# =====================================================

MAX_SCORE = {

    "trend":20,

    "momentum":15,

    "volume":15,

    "volatility":10,

    "pattern":15,

    "market":5,

    "sector":5,

    "news":5,

    "risk":10

}


def score_trend(stock):

    df = stock.data

    if df is None:
        return

    last = df.iloc[-1]

    if last["EMA20"] > last["EMA50"]:

        stock.add_score("trend",5)

        stock.add_reason("EMA20 above EMA50")

    if last["EMA50"] > last["EMA100"]:

        stock.add_score("trend",5)

        stock.add_reason("EMA50 above EMA100")

    if last["EMA100"] > last["EMA200"]:

        stock.add_score("trend",5)

        stock.add_reason("EMA100 above EMA200")

    if last["Close"] > last["EMA20"]:

        stock.add_score("trend",5)

        stock.add_reason("Price above EMA20")


def score_momentum(stock):

    df = stock.data

    if df is None:
        return

    last = df.iloc[-1]

    rsi = last["RSI"]

    if 55 <= rsi <= 70:

        stock.add_score("momentum",8)

        stock.add_reason(f"Healthy RSI {round(rsi,1)}")

    elif rsi > 70:

        stock.add_score("momentum",4)

        stock.add_reason("RSI Overbought")

    macd = last["MACD"]

    signal = last["MACD_SIGNAL"]

    if macd > signal:

        stock.add_score("momentum",7)

        stock.add_reason("MACD Bullish")


def score_volume(stock):

    df = stock.data

    if df is None:
        return

    last = df.iloc[-1]

    rvol = last["RVOL"]

    if rvol >= 2:

        stock.add_score("volume",15)

        stock.add_reason("Very High Relative Volume")

    elif rvol >= 1.5:

        stock.add_score("volume",10)

        stock.add_reason("High Relative Volume")

    elif rvol >= 1.2:

        stock.add_score("volume",5)

        stock.add_reason("Moderate Relative Volume")


def score_volatility(stock):

    df = stock.data

    if df is None:
        return

    last = df.iloc[-1]

    atr = last["ATR"]

    price = last["Close"]

    atr_percent = (atr / price) * 100

    stock.add_indicator(

        "ATR_PERCENT",

        round(atr_percent,2)

    )

    if 1 <= atr_percent <= 5:

        stock.add_score(

            "volatility",

            10

        )

        stock.add_reason(

            "Healthy ATR"

        )

    elif atr_percent < 1:

        stock.add_score(

            "volatility",

            5

        )


def score_risk(stock):

    df = stock.data

    if df is None:
        return

    last = df.iloc[-1]

    stop = last["Close"] - (2 * last["ATR"])

    stock.add_risk(

        "INITIAL_STOP",

        round(stop,2)

    )

    stock.add_score(

        "risk",

        10

    )

    stock.add_reason(

        "ATR Risk Calculated"

    )


def calculate_trade_quality(stock):

    stock.score = {

        "trend":0,

        "momentum":0,

        "volume":0,

        "volatility":0,

        "pattern":0,

        "market":0,

        "sector":0,

        "news":0,

        "risk":0,

        "quality":0

    }

    stock.reason = []

    score_trend(stock)

    score_momentum(stock)

    score_volume(stock)

    score_volatility(stock)

    score_risk(stock)

    quality = stock.calculate_trade_quality()

    if quality >= 90:

        stock.set_state("HIGH CONVICTION BUY")

    elif quality >= 80:

        stock.set_state("BUY")

    elif quality >= 70:

        stock.set_state("READY")

    elif quality >= 60:

        stock.set_state("WATCHLIST")

    else:

        stock.set_state("REJECT")

    stock.decision["QUALITY"] = quality

    stock.decision["STATE"] = stock.state

    return stock


# =====================================================
# QUALITY PREVIEW
# =====================================================
# The old "Test Trade Quality" manual dev button has been removed - this
# is not skipped work, calculate_trade_quality() already runs for every
# symbol inside execute_scan_pipeline() automatically, so a separate
# manual preview button was a dev-only leftover that duplicated the same
# call.

# =====================================================
# MARKET STRUCTURE ENGINE
# VERSION 2.2D
# =====================================================

STRUCTURE_LOOKBACK = 5


def detect_swings(df, lookback=STRUCTURE_LOOKBACK):

    df = df.copy()

    df["SWING_HIGH"] = False
    df["SWING_LOW"] = False

    for i in range(lookback, len(df)-lookback):

        high = df["High"].iloc[i]

        if high == max(
            df["High"].iloc[
                i-lookback:i+lookback+1
            ]
        ):
            df.loc[df.index[i], "SWING_HIGH"] = True

        low = df["Low"].iloc[i]

        if low == min(
            df["Low"].iloc[
                i-lookback:i+lookback+1
            ]
        ):
            df.loc[df.index[i], "SWING_LOW"] = True

    return df


def classify_market_structure(stock):

    df = stock.data

    if df is None:
        return

    df = detect_swings(df)

    stock.data = df

    highs = df[df["SWING_HIGH"]]

    lows = df[df["SWING_LOW"]]

    if len(highs) < 2 or len(lows) < 2:
        return

    last_high = highs["High"].iloc[-1]
    prev_high = highs["High"].iloc[-2]

    last_low = lows["Low"].iloc[-1]
    prev_low = lows["Low"].iloc[-2]

    trend = "SIDEWAYS"

    if last_high > prev_high and last_low > prev_low:

        trend = "UPTREND"

        stock.add_score("trend",5)

        stock.add_reason(
            "Higher High + Higher Low"
        )

    elif last_high < prev_high and last_low < prev_low:

        trend = "DOWNTREND"

        stock.add_reason(
            "Lower High + Lower Low"
        )

    elif last_high > prev_high:

        trend = "POSSIBLE_BREAKOUT"

        stock.add_reason(
            "Higher High Formed"
        )

    elif last_low < prev_low:

        trend = "WEAKNESS"

        stock.add_reason(
            "Lower Low Formed"
        )

    stock.market["TREND"] = trend

    stock.market["LAST_SWING_HIGH"] = round(
        last_high,
        2
    )

    stock.market["LAST_SWING_LOW"] = round(
        last_low,
        2
    )


def detect_break_of_structure(stock):

    df = stock.data

    if df is None:
        return

    last_close = df["Close"].iloc[-1]

    if "LAST_SWING_HIGH" in stock.market:

        if last_close > stock.market["LAST_SWING_HIGH"]:

            stock.add_pattern(
                "BOS",
                True
            )

            stock.add_score(
                "pattern",
                8
            )

            stock.add_reason(
                "Break of Structure"
            )

    if "LAST_SWING_LOW" in stock.market:

        if last_close < stock.market["LAST_SWING_LOW"]:

            stock.add_pattern(
                "BEARISH_BOS",
                True
            )


def detect_change_of_character(stock):

    trend = stock.market.get(
        "TREND",
        ""
    )

    if trend == "POSSIBLE_BREAKOUT":

        stock.add_pattern(
            "CHOCH",
            True
        )

        stock.add_score(
            "pattern",
            5
        )

        stock.add_reason(
            "Possible Change of Character"
        )


def update_market_structure(stock):

    classify_market_structure(stock)

    detect_break_of_structure(stock)

    detect_change_of_character(stock)

    return stock


# =====================================================
# MARKET STRUCTURE TEST
# =====================================================
# The old "Test Market Structure" manual dev button has been removed -
# update_market_structure() already runs for every symbol inside
# execute_scan_pipeline() automatically.

# =====================================================
# TRADE CANDIDATE ENGINE
# VERSION 2.2E
# =====================================================

class TradeCandidate:

    def __init__(self, symbol, strategy):

        self.symbol = symbol
        self.strategy = strategy

        self.state = "DISCOVERED"

        self.entry = None
        self.stop = None

        self.target1 = None
        self.target2 = None
        self.target3 = None

        self.risk = None
        self.reward = None
        self.risk_reward = 0

        self.confidence = 0

        self.position_size = 0
        self.capital_required = 0
        self.maximum_loss = 0
        self.maximum_profit = 0
        self.portfolio_weight = 0
        self.ai_score = 0
        self.strategy_count = 0
        self.direction = "LONG"

        self.reasons = []

        self.missing_triggers = []

        self.warnings = []

        self.timestamp = datetime.now()

    def add_reason(self, text):

        self.reasons.append(text)

    def add_trigger(self, text):

        self.missing_triggers.append(text)

    def add_warning(self, text):

        self.warnings.append(text)

    def set_entry(self, value):

        self.entry = round(value,2)

    def set_stop(self, value):

        self.stop = round(value,2)

    def set_target1(self, value):

        self.target1 = round(value,2)

    def set_target2(self, value):

        self.target2 = round(value,2)

    def set_target3(self, value):

        self.target3 = round(value,2)

    def calculate_rr(self):

        if self.entry is None:
            return

        if self.stop is None:
            return

        if self.target1 is None:
            return

        risk = self.entry-self.stop

        reward=self.target1-self.entry

        if risk<=0:

            return

        self.risk=risk

        self.reward=reward

        self.risk_reward=round(

            reward/risk,

            2

        )

    def summary(self):

        return {

            "Symbol":self.symbol,

            "Strategy":self.strategy,

            "State":self.state,

            "Entry":self.entry,

            "Stop":self.stop,

            "Target":self.target1,

            "RR":self.risk_reward,

            "Confidence":self.confidence,

            "Reasons":" | ".join(self.reasons),

            "Pending":" | ".join(self.missing_triggers)

        }


# =====================================================
# TRADE STORAGE
# =====================================================

if "trade_candidates" not in st.session_state:

    st.session_state.trade_candidates={}


def save_trade_candidate(candidate):

    key=f"{candidate.symbol}_{candidate.strategy}"

    st.session_state.trade_candidates[key]=candidate


def get_trade_candidates():

    rows=[]

    for trade in st.session_state.trade_candidates.values():

        rows.append(

            trade.summary()

        )

    return pd.DataFrame(rows)


# =====================================================
# PREVIEW PANEL
# =====================================================

if _P("AI"):

    st.divider()

    st.subheader("Trade Candidate Engine")

    if st.button("Show Trade Candidates"):

        df=get_trade_candidates()

        if len(df)==0:

            st.info(

                "No Trade Candidates Yet"

            )

        else:

            st.dataframe(

                df,

                use_container_width=True

            )
    # =====================================================
    # BATCH 1 - ADVANCED SIGNALS PANEL
    # =====================================================

    def get_batch1_signals_dataframe():

        rows = []

        for symbol, stock in st.session_state.stock_objects.items():

            if stock.data is None:
                continue

            rows.append({
                "Symbol": symbol,
                "Daily Trend": stock.indicators.get("MTF_DAILY_TREND"),
                "1H Trend": stock.indicators.get("MTF_1H_TREND"),
                "15M Trend": stock.indicators.get("MTF_15M_TREND"),
                "MTF Alignment": stock.score.get("mtf_alignment"),
                "RS vs NIFTY": stock.indicators.get("RS_SCORE"),
                "Sector": stock.indicators.get("SECTOR_NAME"),
                "Sector Score": stock.indicators.get("SECTOR_SCORE"),
                "Volume POC": stock.indicators.get("VOLUME_POC"),
                "Vol. Profile Position": stock.indicators.get("VOLUME_PROFILE_POSITION"),
                "Demand Zones": len(stock.patterns.get("FRESH_DEMAND", [])),
                "Supply Zones": len(stock.patterns.get("FRESH_SUPPLY", [])),
                "Batch1 Bonus": stock.score.get("batch1_bonus"),
                "Reasons": " | ".join(stock.reason[-4:]) if stock.reason else "",
            })

        return pd.DataFrame(rows)


    st.divider()

    st.subheader("Batch 1 - Advanced Signals")

    st.caption(
        "Multi-Timeframe Alignment, Relative Strength vs NIFTY, Sector Ranking, "
        "Volume Profile and Demand/Supply Zones - feeding into AI Consensus."
    )

    if st.button("Show Advanced Signals"):

        signals_df = get_batch1_signals_dataframe()

        if len(signals_df) == 0:

            st.info("No Signals Yet - Run a Scan First")

        else:

            st.dataframe(
                signals_df,
                use_container_width=True
            )


    def get_batch2_signals_dataframe():

        rows = []

        for symbol, stock in st.session_state.stock_objects.items():

            if stock.data is None:
                continue

            rows.append({
                "Symbol": symbol,
                "AI Confidence": stock.indicators.get("AI_CONFIDENCE"),
                "Batch2 Bonus": stock.indicators.get("BATCH2_CONFIDENCE_BONUS"),
                "False Breakout": stock.patterns.get("FALSE_BREAKOUT", False),
                "Exhaustion": stock.patterns.get("BREAKOUT_EXHAUSTION", False),
                "Smart Money Score": stock.indicators.get("SMART_MONEY_SCORE"),
                "BOS": stock.patterns.get("BOS", False),
                "CHOCH": stock.patterns.get("CHOCH", False),
                "Bullish OB": len(stock.patterns.get("BULLISH_ORDER_BLOCKS", [])),
                "Bullish FVG": len(stock.patterns.get("BULLISH_FVG", [])),
                "Liquidity Sweep": stock.patterns.get("BULLISH_SWEEP", False),
                "OBV Trend": stock.indicators.get("OBV_TREND"),
                "A/D Trend": stock.indicators.get("ADL_TREND"),
                "Volume Z-Score": stock.indicators.get("VOLUME_ZSCORE"),
                "Absorption Day": stock.indicators.get("ABSORPTION_DAY"),
                "Days To Earnings": stock.indicators.get("DAYS_TO_EARNINGS"),
                "Recent News": stock.indicators.get("RECENT_NEWS_COUNT"),
                "News Notes": " | ".join(list(stock.news.values())[-2:]) if stock.news else "",
                "Reasons": " | ".join(stock.reason[-4:]) if stock.reason else "",
            })

        return pd.DataFrame(rows)


    st.divider()

    st.subheader("Batch 2 - False Breakout, Smart Money, Institutional & News/Earnings")

    st.caption(
        "False Breakout Detection, Smart Money Concepts (BOS/CHOCH/Order Blocks/"
        "Liquidity Sweeps/FVG), Institutional Activity (volume-based proxy - "
        "NSE delivery % is not available from this data source), and the News/"
        "Earnings Filter - combined into the AI Confidence Engine feeding AI Consensus."
        )

    if st.button("Show Batch 2 Signals"):

        b2_df = get_batch2_signals_dataframe()

        if len(b2_df) == 0:

            st.info("No Signals Yet - Run a Scan First")

        else:

            st.dataframe(
                b2_df,
                use_container_width=True
            )

# =====================================================
# PRICE SQUEEZE ENGINE - PART 1
# VERSION 3.1A
# =====================================================

def calculate_price_squeeze(stock):

    """
    Detects volatility contraction.

    This is only the CORE engine.

    Trade generation happens later.
    """

    df = stock.data

    if df is None:

        return

    if len(df) < 50:

        return

    try:

        # -----------------------------
        # Bollinger Width
        # -----------------------------

        df["BB_WIDTH"] = (

            (df["BB_UPPER"] - df["BB_LOWER"])

            /

            df["BB_MIDDLE"]

        ) * 100

        # -----------------------------
        # Keltner Channel
        # -----------------------------

        ema20 = ta.ema(

            df["Close"],

            length=20

        )

        atr20 = ta.atr(

            df["High"],

            df["Low"],

            df["Close"],

            length=20

        )

        df["KC_UPPER"] = ema20 + (2 * atr20)

        df["KC_LOWER"] = ema20 - (2 * atr20)

        # -----------------------------
        # TTM Squeeze
        # -----------------------------

        df["TTM_SQUEEZE"] = (

            (df["BB_LOWER"] > df["KC_LOWER"])

            &

            (df["BB_UPPER"] < df["KC_UPPER"])

        )

        # -----------------------------
        # Width Percentile
        # -----------------------------

        width = df["BB_WIDTH"]

        current_width = width.iloc[-1]

        percentile = (

            width.rank(pct=True)

            .iloc[-1]

        )

        stock.add_indicator(

            "BB_WIDTH",

            round(current_width,2)

        )

        stock.add_indicator(

            "BB_PERCENTILE",

            round(percentile*100,2)

        )

        # -----------------------------
        # Core Squeeze Score
        # -----------------------------

        squeeze_score = 0

        if percentile <= 0.10:

            squeeze_score += 40

            stock.add_reason(

                "Extremely Tight Bollinger Width"

            )

        elif percentile <= 0.20:

            squeeze_score += 30

            stock.add_reason(

                "Very Tight Bollinger Width"

            )

        elif percentile <= 0.30:

            squeeze_score += 20

        elif percentile <= 0.40:

            squeeze_score += 10

        if df["TTM_SQUEEZE"].iloc[-1]:

            squeeze_score += 40

            stock.add_reason(

                "TTM Squeeze Active"

            )

        stock.patterns["PRICE_SQUEEZE"] = squeeze_score

        stock.add_score(

            "pattern",

            min(

                15,

                squeeze_score/5

            )

        )

        stock.data = df

        return

    except Exception as e:

        logging.exception(
            f"Price Squeeze Error: {stock.symbol}"
        )

        return

# =====================================================
# PRICE SQUEEZE ENGINE - PART 2
# VERSION 3.1B
# =====================================================

def detect_nr4(df):

    df["NR4"] = False

    ranges = df["High"] - df["Low"]

    for i in range(3, len(df)):

        current = ranges.iloc[i]

        previous = ranges.iloc[i-3:i]

        if current <= previous.min():

            df.loc[df.index[i], "NR4"] = True

    return df


def detect_nr7(df):

    df["NR7"] = False

    ranges = df["High"] - df["Low"]

    for i in range(6, len(df)):

        current = ranges.iloc[i]

        previous = ranges.iloc[i-6:i]

        if current <= previous.min():

            df.loc[df.index[i], "NR7"] = True

    return df


def detect_inside_bar(df):

    df["INSIDE_BAR"] = False

    for i in range(1, len(df)):

        if (

            df["High"].iloc[i] < df["High"].iloc[i-1]

            and

            df["Low"].iloc[i] > df["Low"].iloc[i-1]

        ):

            df.loc[df.index[i], "INSIDE_BAR"] = True

    return df


def detect_atr_contraction(stock):

    df = stock.data

    if df is None:

        return

    atr_avg = df["ATR"].rolling(20).mean()

    latest = df["ATR"].iloc[-1]

    average = atr_avg.iloc[-1]

    if pd.isna(average):

        return

    contraction = latest / average

    stock.add_indicator(

        "ATR_CONTRACTION",

        round(contraction,2)

    )

    if contraction < 0.80:

        stock.patterns["ATR_CONTRACTION"] = True

        stock.add_score("pattern",3)

        stock.add_reason("ATR Contracting")


def detect_volume_dryup(stock):

    df = stock.data

    if df is None:

        return

    latest = df["Volume"].iloc[-1]

    average = df["AVG_VOLUME20"].iloc[-1]

    if pd.isna(average):

        return

    ratio = latest / average

    stock.add_indicator(

        "VOLUME_RATIO",

        round(ratio,2)

    )

    if ratio < 0.70:

        stock.patterns["VOLUME_DRYUP"] = True

        stock.add_score("pattern",4)

        stock.add_reason("Volume Dry-Up")


def update_volatility_patterns(stock):

    df = stock.data

    if df is None:

        return

    df = detect_nr4(df)

    df = detect_nr7(df)

    df = detect_inside_bar(df)

    stock.data = df

    last = df.iloc[-1]

    if last["NR4"]:

        stock.patterns["NR4"] = True

        stock.add_score("pattern",2)

        stock.add_reason("NR4")

    if last["NR7"]:

        stock.patterns["NR7"] = True

        stock.add_score("pattern",3)

        stock.add_reason("NR7")

    if last["INSIDE_BAR"]:

        stock.patterns["INSIDE_BAR"] = True

        stock.add_score("pattern",3)

        stock.add_reason("Inside Bar")

    detect_atr_contraction(stock)

    detect_volume_dryup(stock)
# =====================================================
# PRICE SQUEEZE ENGINE - PART 3
# TRADE GENERATION
# VERSION 3.1C
# =====================================================

MIN_RISK_REWARD = 2.5
MIN_CONFIDENCE = 70


def create_price_squeeze_candidate(stock):

    df = stock.data

    if df is None:
        return None

    if len(df) < 60:
        return None

    last = df.iloc[-1]

    candidate = TradeCandidate(

        stock.symbol,

        "PRICE SQUEEZE"

    )

    confidence = 0

    # ==========================================
    # Trend Filter
    # ==========================================

    if stock.market.get("TREND") == "UPTREND":

        confidence += 20

        candidate.add_reason(

            "Strong Uptrend"

        )

    else:

        candidate.add_trigger(

            "Trend must become UPTREND"

        )

    # ==========================================
    # EMA Alignment
    # ==========================================

    if (

        last["EMA20"] >

        last["EMA50"] >

        last["EMA100"] >

        last["EMA200"]

    ):

        confidence += 20

        candidate.add_reason(

            "EMA Alignment"

        )

    else:

        candidate.add_trigger(

            "EMA Alignment Pending"

        )

    # ==========================================
    # Price Squeeze
    # ==========================================

    squeeze = stock.patterns.get(

        "PRICE_SQUEEZE",

        0

    )

    if squeeze >= 50:

        confidence += 20

        candidate.add_reason(

            "Strong Price Squeeze"

        )

    else:

        candidate.add_trigger(

            "Better Volatility Compression"

        )

    # ==========================================
    # Volume Dry-Up
    # ==========================================

    if stock.patterns.get(

        "VOLUME_DRYUP",

        False

    ):

        confidence += 10

        candidate.add_reason(

            "Volume Dry-Up"

        )

    # ==========================================
    # NR7
    # ==========================================

    if stock.patterns.get(

        "NR7",

        False

    ):

        confidence += 10

        candidate.add_reason(

            "NR7 Pattern"

        )

    # ==========================================
    # Inside Bar
    # ==========================================

    if stock.patterns.get(

        "INSIDE_BAR",

        False

    ):

        confidence += 10

        candidate.add_reason(

            "Inside Bar"

        )

    # ==========================================
    # ATR Contraction
    # ==========================================

    if stock.patterns.get(

        "ATR_CONTRACTION",

        False

    ):

        confidence += 10

        candidate.add_reason(

            "ATR Contracting"

        )

    candidate.confidence = confidence

    # ==========================================
    # Entry Trigger
    # ==========================================

    entry = round(

        last["High"] * 1.001,

        2

    )

    candidate.set_entry(entry)

    candidate.add_trigger(

        f"Close Above {entry}"

    )

    # ==========================================
    # Initial Stop
    # ==========================================

    stop = min(

        last["Low"],

        last["Close"] -

        (2 * last["ATR"])

    )

    candidate.set_stop(stop)

    # ==========================================
    # First Target
    # ==========================================

    risk = entry - stop

    target = entry + (risk * 3)

    candidate.set_target1(target)

    candidate.calculate_rr()

    # ==========================================
    # State
    # ==========================================

    if (

        candidate.risk_reward >= MIN_RISK_REWARD

        and

        confidence >= MIN_CONFIDENCE

    ):

        candidate.state = "READY"

    else:

        candidate.state = "WATCHLIST"

    save_trade_candidate(

        candidate

    )

    return candidate
# =====================================================
# PRICE SQUEEZE ENGINE - PART 4
# BREAKOUT CONFIRMATION ENGINE
# VERSION 3.1D
# =====================================================

MIN_BREAKOUT_RVOL = 1.80

def confirm_price_squeeze_breakout(stock):

    df = stock.data

    if df is None:
        return None

    key = f"{stock.symbol}_PRICE SQUEEZE"

    if key not in st.session_state.trade_candidates:
        return None

    trade = st.session_state.trade_candidates[key]

    last = df.iloc[-1]

    breakout = True

    # ----------------------------------
    # Price Breakout
    # ----------------------------------

    if last["Close"] < trade.entry:

        breakout = False

        trade.add_trigger(

            f"Close Above {trade.entry}"

        )

    else:

        trade.add_reason(

            "Breakout Confirmed"

        )

    # ----------------------------------
    # Relative Volume
    # ----------------------------------

    rvol = last["RVOL"]

    if rvol >= MIN_BREAKOUT_RVOL:

        trade.add_reason(

            f"RVOL {round(rvol,2)}"

        )

        trade.confidence += 10

    else:

        breakout = False

        trade.add_trigger(

            "RVOL >= 1.80"

        )

    # ----------------------------------
    # MACD
    # ----------------------------------

    if last["MACD"] > last["MACD_SIGNAL"]:

        trade.add_reason(

            "MACD Bullish"

        )

        trade.confidence += 5

    else:

        trade.add_trigger(

            "MACD Bullish Cross"

        )

    # ----------------------------------
    # RSI
    # ----------------------------------

    if 55 <= last["RSI"] <= 70:

        trade.add_reason(

            "Healthy RSI"

        )

        trade.confidence += 5

    else:

        trade.add_trigger(

            "RSI 55-70"

        )

    # ----------------------------------
    # Final Decision
    # ----------------------------------

    trade.calculate_rr()

    if (

        breakout

        and

        trade.risk_reward >= MIN_RISK_REWARD

        and

        trade.confidence >= MIN_CONFIDENCE

    ):

        trade.state = "BUY"

    elif trade.confidence >= 60:

        trade.state = "READY"

    else:

        trade.state = "WATCHLIST"

    save_trade_candidate(trade)

    return trade


# =====================================================
# RUN COMPLETE PRICE SQUEEZE STRATEGY
# =====================================================

def run_price_squeeze_strategy(stock):

    calculate_price_squeeze(stock)

    update_volatility_patterns(stock)

    create_price_squeeze_candidate(stock)

    confirm_price_squeeze_breakout(stock)


# =====================================================
# COMPLETE SCAN ENGINE
# =====================================================

def legacy_run_complete_scan():

    st.session_state.trade_candidates = {}

    total = len(st.session_state.market_data)

    progress = st.progress(0)

    status = st.empty()

    completed = 0

    for symbol, df in st.session_state.market_data.items():

        completed += 1

        progress.progress(completed / total)

        status.write(f"Scanning {symbol}")

        df = calculate_indicators(df)

        if df is None:
            continue

        stock = get_stock(symbol)

        stock.set_dataframe(df)

        calculate_trade_quality(stock)

        update_market_structure(stock)

        run_price_squeeze_strategy(stock)

    status.success("Scan Complete")


# =====================================================
# SCAN BUTTON
# =====================================================

st.divider()

st.subheader("AlphaQuant Scanner")


def _pipeline_event(event):
    st.session_state.pipeline_events.append({
        "Time": event.timestamp.strftime("%H:%M:%S"),
        "Stage": event.step,
        "Status": event.status,
        "Message": event.message,
    })
    st.session_state.brain_status[event.step] = event.status


def build_default_scan_universe_for_pipeline():
    # Reads filter values from persistent *_saved keys (see SCANNER FILTER
    # PERSISTENCE at top of file). Works regardless of which tab is
    # currently active, because those keys are initialised once at file
    # load and updated on every Scanner widget render.
    _ss = st.session_state
    st.session_state.scan_universe = build_scan_universe(
        _ss["scan_manager_universe_choice_saved"],
        cap_filter=_ss["scan_manager_cap_filter_saved"],
        price_range=_ss["scan_manager_price_range_saved"],
        min_volume=_ss["scan_manager_min_volume_saved"],
        min_turnover=_ss["scan_manager_min_turnover_saved"],
        sectors=_ss["scan_manager_sector_filter_saved"],
        styles=_ss["scan_manager_style_filter_saved"],
    )
    st.session_state.scan_manager_active_styles = _ss["scan_manager_style_filter_saved"]
    return f"{len(st.session_state.scan_universe)} symbols"


def run_alphaquant(trigger="MANUAL"):
    """One professional workflow entry point for the RUN ALPHAQUANT button."""
    from os_brains.pipeline_manager import PipelineManager, PipelineStep

    st.session_state.pipeline_events = []
    st.session_state.brain_status = {}
    st.session_state.decision_funnel = []
    st.session_state.no_trade_explanation = []

    manager = PipelineManager(on_event=_pipeline_event)

    def download_stage():
        if not st.session_state.scan_universe:
            return False
        st.session_state.market_data = download_market_data(st.session_state.scan_universe)
        return f"{len(st.session_state.market_data)} datasets" if st.session_state.market_data else False

    ok = manager.run([
        PipelineStep("Build Universe", build_default_scan_universe_for_pipeline, "Building selected universe"),
        PipelineStep("Download Data", download_stage, "Downloading OHLCV data"),
    ])

    if not ok:
        return False, "AlphaQuant stopped before scan execution. See Mission Control logs."

    st.session_state.run_complete_scan_requested = True
    st.session_state.last_cycle_time = datetime.now()
    st.session_state.last_cycle_trigger = trigger
    return True, f"RUN ALPHAQUANT queued: {len(st.session_state.market_data)} symbols."


def run_automated_cycle(trigger="AUTONOMOUS"):
    """Autonomous loop compatibility wrapper around the one-button workflow."""
    return run_alphaquant(trigger=trigger)


if st.button("RUN ALPHAQUANT", key="run_alphaquant_primary", type="primary"):

    ok, msg = run_alphaquant(trigger="MANUAL")

    if ok:
        st.success(msg)
    else:
        st.warning(msg)

# =====================================================
# TRADE VALIDATOR ENGINE
# =====================================================
# TRADE VALIDATOR ENGINE
# VERSION 3.2A
# =====================================================

MIN_TRADE_QUALITY = 70
MIN_RR = 2.5

def validate_trade_candidate(stock, trade):

    if trade is None:
        return None

    valid = True

    # -------------------------------
    # Trade Quality
    # -------------------------------

    tqi = stock.score.get("quality", 0)

    if tqi < MIN_TRADE_QUALITY:

        valid = False

        trade.add_trigger(
            f"TQI >= {MIN_TRADE_QUALITY}"
        )

    # -------------------------------
    # Risk Reward
    # -------------------------------

    trade.calculate_rr()

    if trade.risk_reward < MIN_RR:

        valid = False

        trade.add_trigger(
            f"RR >= {MIN_RR}"
        )

    # -------------------------------
    # Trend Filter
    # -------------------------------

    if stock.market.get("TREND") != "UPTREND":

        valid = False

        trade.add_trigger(
            "Primary Trend Up"
        )

    # -------------------------------
    # Price Filter
    # -------------------------------

    last = stock.data.iloc[-1]

    if last["Close"] < CONFIG["MIN_PRICE"]:

        valid = False

        trade.add_trigger(
            "Price Filter"
        )

    # -------------------------------
    # Volume Filter
    # -------------------------------

    if last["AVG_VOLUME20"] < CONFIG["MIN_AVG_VOLUME"]:

        valid = False

        trade.add_trigger(
            "Average Volume Filter"
        )

    # -------------------------------
    # Long Only
    # -------------------------------

    trade.direction = "LONG"

    if valid:

        trade.state = "READY"

    else:

        trade.state = "WATCHLIST"

    return trade
# =====================================================
# POSITION SIZING ENGINE
# VERSION 3.2B
# =====================================================

DEFAULT_CAPITAL = 100000
MAX_CAPITAL_PER_TRADE = 0.10

if "paper_capital" not in st.session_state:
    st.session_state.paper_capital = DEFAULT_CAPITAL


def calculate_position_size(trade):

    if trade is None:
        return None

    if trade.entry is None:
        return trade

    if trade.stop is None:
        return trade

    risk = trade.entry - trade.stop

    if risk <= 0:
        return trade

    capital = st.session_state.paper_capital

    risk_amount = capital * (CONFIG["RISK_PER_TRADE"] / 100)

    quantity = int(risk_amount / risk)

    max_quantity = int(
        (capital * MAX_CAPITAL_PER_TRADE) / trade.entry
    )

    quantity = min(quantity, max_quantity)

    quantity = max(quantity, 0)

    trade.position_size = quantity

    trade.capital_required = round(
        quantity * trade.entry,
        2
    )

    trade.maximum_loss = round(
        quantity * risk,
        2
    )

    if trade.target1 is not None:

        trade.maximum_profit = round(
            quantity *
            (trade.target1 - trade.entry),
            2
        )

    else:

        trade.maximum_profit = 0

    return trade


def update_trade_position_sizes():

    for trade in st.session_state.trade_candidates.values():

        calculate_position_size(trade)
# =====================================================
# PAPER TRADING ENGINE
# VERSION 3.2C
# =====================================================

if "paper_positions" not in st.session_state:
    st.session_state.paper_positions = {}

if "paper_history" not in st.session_state:
    st.session_state.paper_history = []


def open_paper_trade(trade):

    if trade.position_size <= 0:
        return

    if trade.state != "BUY":
        return

    if trade.symbol in st.session_state.paper_positions:
        return

    position = PaperPosition(
        symbol=trade.symbol,
        strategy=trade.strategy,
        qty=trade.position_size,
        entry=trade.entry or 0,
        stop=trade.stop or 0,
        target1=trade.target1 or 0,
        target2=trade.target2 or 0,
        target3=trade.target3 or 0,
        confidence=trade.confidence,
        ai_score=getattr(trade, "ai_score", 0),
        decision_id=getattr(trade, "decision_id", None)
    )

    if hasattr(position, "initialise"):

        position.initialise()

    st.session_state.paper_positions[trade.symbol] = position

    if position.decision_id is not None:
        try:
            from os_brains import experience_memory
            experience_memory.mark_open(position.decision_id)
        except Exception as e:
            logging.warning(f"OPEN_PAPER_TRADE experience_memory.mark_open failed symbol={trade.symbol}: {e}")

    logging.info(

        f"Paper BUY : {trade.symbol}"

    )


# =====================================================
# PAPER PORTFOLIO DASHBOARD
# VERSION 3.2D
# =====================================================

def paper_portfolio_summary():

    open_positions = len(st.session_state.paper_positions)
    closed_positions = len(st.session_state.paper_history)

    total_pnl = 0

    winners = 0
    losers = 0

    for trade in st.session_state.paper_history:

        total_pnl += trade.pnl

        if trade.pnl >= 0:
            winners += 1
        else:
            losers += 1

    if closed_positions > 0:
        win_rate = round(
            winners * 100 / closed_positions,
            2
        )
    else:
        win_rate = 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Open Positions",
        open_positions
    )

    c2.metric(
        "Closed Trades",
        closed_positions
    )

    c3.metric(
        "Net P&L",
        f"₹ {round(total_pnl,2)}"
    )

    c4.metric(
        "Win Rate",
        f"{win_rate}%"
    )


def show_open_positions():

    rows = []

    for position in st.session_state.paper_positions.values():

        rows.append({

            "Symbol": position.symbol,

            "Strategy": position.strategy,

            "Entry": position.entry,

            "Stop": position.stop,

            "Target": position.target1,

            "Qty": position.quantity,

            "Status": position.status

        })

    if len(rows):

        st.dataframe(

            pd.DataFrame(rows),

            use_container_width=True

        )

    else:

        st.info("No Open Paper Positions")


def show_trade_history():

    rows = []

    for trade in st.session_state.paper_history:

        rows.append({

            "Symbol": trade.symbol,

            "Strategy": trade.strategy,

            "Entry": trade.entry,

            "Exit": trade.exit_price,

            "Qty": trade.quantity,

            "PnL": trade.pnl,

            "Reason": trade.exit_reason

        })

    if len(rows):

        st.dataframe(

            pd.DataFrame(rows),

            use_container_width=True

        )

    else:

        st.info("No Closed Trades")


if _P("Paper Trading"):
    st.divider()

    st.subheader("Paper Trading Dashboard")

    paper_portfolio_summary()

    with st.expander("Open Positions", expanded=True):

        show_open_positions()

    with st.expander("Trade History"):

        show_trade_history()
# =====================================================
# STRATEGY REGISTRY
# VERSION 3.3A
# =====================================================

if "strategy_registry" not in st.session_state:

    st.session_state.strategy_registry = []


class Strategy:

    def __init__(

        self,

        name,

        function,

        enabled=True,

        priority=100

    ):

        self.name = name

        self.function = function

        self.enabled = enabled

        self.priority = priority


def register_strategy(

    name,

    function,

    priority=100,

    enabled=True

):

    for strategy in st.session_state.strategy_registry:

        if strategy.name == name:

            return

    st.session_state.strategy_registry.append(

        Strategy(

            name,

            function,

            enabled,

            priority

        )

    )

    st.session_state.strategy_registry.sort(

        key=lambda x: x.priority

    )


def run_all_strategies(stock):

    for strategy in st.session_state.strategy_registry:

        if strategy.enabled:

            try:

                strategy.function(stock)

            except Exception as e:

                logging.exception(

                    f"{strategy.name} : {stock.symbol}"

                )


def show_registered_strategies():

    rows = []

    for strategy in st.session_state.strategy_registry:

        rows.append({

            "Priority": strategy.priority,

            "Strategy": strategy.name,

            "Enabled": strategy.enabled

        })

    if len(rows):

        st.dataframe(

            pd.DataFrame(rows),

            use_container_width=True

        )


# ==========================================
# Strategy Dashboard
# ==========================================

if _P("Settings"):
    st.divider()

    st.subheader("Strategy Registry")

    show_registered_strategies()
# =====================================================
# DEMAND & SUPPLY ENGINE
# PART 1
# VERSION 3.3B
# =====================================================

BASE_LOOKBACK = 20
IMPULSE_MULTIPLIER = 2.0


def candle_body(candle):

    return abs(

        candle["Close"]

        - candle["Open"]

    )


def detect_impulse_candle(df, idx):

    candle = df.iloc[idx]

    avg_body = (

        abs(

            df["Close"]

            - df["Open"]

        )

        .rolling(20)

        .mean()

        .iloc[idx]

    )

    if pd.isna(avg_body):

        return False

    return candle_body(candle) >= (

        avg_body *

        IMPULSE_MULTIPLIER

    )


def detect_base(df, idx):

    if idx < 2:

        return False

    c1 = df.iloc[idx]

    c2 = df.iloc[idx-1]

    c3 = df.iloc[idx-2]

    avg_range = (

        (df["High"]-df["Low"])

        .rolling(20)

        .mean()

        .iloc[idx]

    )

    if pd.isna(avg_range):

        return False

    r1 = c1["High"]-c1["Low"]

    r2 = c2["High"]-c2["Low"]

    r3 = c3["High"]-c3["Low"]

    return (

        r1 < avg_range

        and

        r2 < avg_range

        and

        r3 < avg_range

    )


def detect_demand_supply(stock):

    df = stock.data

    if df is None:

        return

    demand = []

    supply = []

    for i in range(

        25,

        len(df)-3

    ):

        if detect_base(df, i):

            before = df.iloc[i-1]

            after = df.iloc[i+1]

            if detect_impulse_candle(df, i+1):

                if after["Close"] > before["Close"]:

                    demand.append({

                        "Low": round(

                            df.iloc[i]["Low"],

                            2

                        ),

                        "High": round(

                            df.iloc[i]["High"],

                            2

                        ),

                        "Index": i

                    })

                else:

                    supply.append({

                        "Low": round(

                            df.iloc[i]["Low"],

                            2

                        ),

                        "High": round(

                            df.iloc[i]["High"],

                            2

                        ),

                        "Index": i

                    })

    stock.patterns["DEMAND_ZONES"] = demand

    stock.patterns["SUPPLY_ZONES"] = supply

    stock.add_indicator(

        "DEMAND_COUNT",

        len(demand)

    )

    stock.add_indicator(

        "SUPPLY_COUNT",

        len(supply)

    )
# =====================================================
# DEMAND & SUPPLY ENGINE
# PART 2 - FRESH ZONES
# VERSION 3.3C
# =====================================================

def classify_fresh_zones(stock):

    df = stock.data

    if df is None:
        return

    demand = stock.patterns.get("DEMAND_ZONES", [])
    supply = stock.patterns.get("SUPPLY_ZONES", [])

    fresh_demand = []
    tested_demand = []

    for zone in demand:

        tested = False

        for j in range(zone["Index"] + 1, len(df)):

            low = df["Low"].iloc[j]

            if low <= zone["High"]:

                tested = True
                break

        if tested:

            tested_demand.append(zone)

        else:

            zone["Fresh"] = True
            fresh_demand.append(zone)

    fresh_supply = []
    tested_supply = []

    for zone in supply:

        tested = False

        for j in range(zone["Index"] + 1, len(df)):

            high = df["High"].iloc[j]

            if high >= zone["Low"]:

                tested = True
                break

        if tested:

            tested_supply.append(zone)

        else:

            zone["Fresh"] = True
            fresh_supply.append(zone)

    stock.patterns["FRESH_DEMAND"] = fresh_demand
    stock.patterns["TESTED_DEMAND"] = tested_demand

    stock.patterns["FRESH_SUPPLY"] = fresh_supply
    stock.patterns["TESTED_SUPPLY"] = tested_supply

    stock.add_indicator(
        "FRESH_DEMAND",
        len(fresh_demand)
    )

    stock.add_indicator(
        "FRESH_SUPPLY",
        len(fresh_supply)
    )

    if len(fresh_demand):

        stock.add_score(
            "pattern",
            min(
                len(fresh_demand) * 2,
                10
            )
        )

        stock.add_reason(
            f"{len(fresh_demand)} Fresh Demand Zones"
        )
# =====================================================
# DEMAND & SUPPLY ENGINE
# PART 3 - ZONE STRENGTH
# VERSION 3.3D
# =====================================================

def calculate_zone_strength(stock):

    demand = stock.patterns.get("FRESH_DEMAND", [])
    supply = stock.patterns.get("FRESH_SUPPLY", [])

    for zone in demand:

        score = 50

        width = zone["High"] - zone["Low"]

        if width > 0:
            score += 10

        score += 15

        zone["Strength"] = min(score, 100)

    for zone in supply:

        score = 50

        width = zone["High"] - zone["Low"]

        if width > 0:
            score += 10

        score += 15

        zone["Strength"] = min(score, 100)

    stock.patterns["FRESH_DEMAND"] = demand
    stock.patterns["FRESH_SUPPLY"] = supply


def get_best_demand_zone(stock):

    zones = stock.patterns.get("FRESH_DEMAND", [])

    if len(zones) == 0:
        return None

    return sorted(

        zones,

        key=lambda x: x["Strength"],

        reverse=True

    )[0]


def get_best_supply_zone(stock):

    zones = stock.patterns.get("FRESH_SUPPLY", [])

    if len(zones) == 0:
        return None

    return sorted(

        zones,

        key=lambda x: x["Strength"],

        reverse=True

    )[0]
# =====================================================
# DEMAND & SUPPLY ENGINE
# PART 4 - TRADE GENERATION
# VERSION 3.3E
# =====================================================

MIN_DS_CONFIDENCE = 70


def create_demand_supply_candidate(stock):

    calculate_zone_strength(stock)

    zone = get_best_demand_zone(stock)

    if zone is None:
        return

    df = stock.data

    last = df.iloc[-1]

    trade = TradeCandidate(

        stock.symbol,

        "DEMAND_SUPPLY"

    )

    entry = round(zone["High"], 2)

    stop = round(zone["Low"] - last["ATR"], 2)

    risk = entry - stop

    target = round(entry + (risk * 3), 2)

    trade.set_entry(entry)
    trade.set_stop(stop)
    trade.set_target1(target)

    confidence = 0

    if stock.market.get("TREND") == "UPTREND":

        confidence += 20

        trade.add_reason("Primary Uptrend")

    if stock.score["quality"] >= 70:

        confidence += 20

        trade.add_reason("High Trade Quality")

    if zone["Strength"] >= 70:

        confidence += 20

        trade.add_reason("Strong Institutional Demand")

    if len(stock.patterns.get("FRESH_DEMAND", [])):

        confidence += 20

        trade.add_reason("Fresh Demand Zone")

    if last["RVOL"] >= 1.2:

        confidence += 10

        trade.add_reason("Volume Confirmation")

    if last["MACD"] > last["MACD_SIGNAL"]:

        confidence += 10

        trade.add_reason("Bullish MACD")

    trade.confidence = confidence

    trade.calculate_rr()

    if (

        confidence >= MIN_DS_CONFIDENCE

        and

        trade.risk_reward >= 2.5

    ):

        trade.state = "READY"

    else:

        trade.state = "WATCHLIST"

    save_trade_candidate(trade)

    return trade


def run_demand_supply_strategy(stock):

    detect_demand_supply(stock)

    classify_fresh_zones(stock)

    calculate_zone_strength(stock)

    trade = create_demand_supply_candidate(stock)

    logging.info(
        f"DEMAND_SUPPLY symbol={stock.symbol} "
        f"fresh_demand={len(stock.patterns.get('FRESH_DEMAND', []))} "
        f"fresh_supply={len(stock.patterns.get('FRESH_SUPPLY', []))} "
        f"confidence={getattr(trade, 'confidence', None)} "
        f"state={getattr(trade, 'state', None)}"
    )
# =====================================================
# AI CONSENSUS ENGINE
# VERSION 3.4A
# =====================================================

if "final_trade_list" not in st.session_state:
    st.session_state.final_trade_list = []


def build_ai_consensus():
    """
    AI Decision Engine orchestrator: Brain 4 (Strategist) produces one
    candidate per symbol enriched with historical evidence, Brain 5 (Risk
    Manager) reviews every candidate and can veto it. Vetoed candidates
    stay in final_trade_list (with their RiskVerdict attached) instead of
    being dropped - "no trade" is a first-class, visible outcome, not a
    silent absence. Brain 6 (Portfolio Manager) runs later, in
    allocate_portfolio(), once every candidate has a verdict.
    """
    from os_brains.strategist import enrich_candidate
    from os_brains.risk_manager import evaluate as risk_evaluate, build_portfolio_state
    from os_brains import experience_memory

    app_module = sys.modules[__name__]

    grouped = {}

    for trade in st.session_state.trade_candidates.values():

        symbol = trade.symbol

        if symbol not in grouped:

            grouped[symbol] = []

        grouped[symbol].append(trade)

    portfolio_state = build_portfolio_state(app_module)

    final_list = []

    for symbol, trades in grouped.items():

        # ---- Brain 4 (Strategist): pick the best raw candidate for this
        # symbol from everything the strategy registry + Batch 1/2 signal
        # engines produced, then enrich it with historical evidence.
        best = max(

            trades,

            key=lambda x: (
                x.confidence,
                x.risk_reward
            )

        )

        best.strategy_count = len(trades)

        # Batch 1: fold Multi-Timeframe / Relative Strength / Sector /
        # Volume Profile signals into the AI Consensus score.
        signal_stock = get_stock(symbol)

        batch1_bonus = signal_stock.score.get("batch1_bonus", 0)

        batch2_bonus = signal_stock.score.get("batch2_bonus", 0)

        best.ai_score = (

            best.confidence

            +

            (best.strategy_count * 5)

            +

            (best.risk_reward * 5)

            +

            batch1_bonus

            +

            batch2_bonus

        )

        best.ai_confidence = signal_stock.score.get("ai_confidence", 50)

        best.add_reason(
            f"Batch1 signals bonus={batch1_bonus} "
            f"(MTF={signal_stock.score.get('mtf_alignment')}, "
            f"RS={signal_stock.score.get('relative_strength')}, "
            f"Sector={signal_stock.score.get('sector')}, "
            f"VolProfile={signal_stock.score.get('volume_profile')})"
        )

        best.add_reason(
            f"Batch2 signals bonus={batch2_bonus} ai_confidence={best.ai_confidence} "
            f"(SmartMoney={signal_stock.score.get('smart_money')}, "
            f"Institutional={signal_stock.score.get('institutional')}, "
            f"FalseBreakoutPenalty={signal_stock.score.get('false_breakout_penalty')}, "
            f"NewsEarningsPenalty={signal_stock.score.get('news_earnings')})"
        )

        try:
            enrich_candidate(signal_stock, best, app_module)
        except Exception as e:
            logging.warning(f"AI_CONSENSUS strategist enrichment failed symbol={symbol}: {e}")
            best.regime_context = None
            best.analog_report = None
            best.evidence_summary = []
            best.expected_value = 0.0

        # ---- Brain 5 (Risk Manager): unconditional veto layer. Runs on
        # every candidate, approved or not - the verdict is what makes
        # "no trade" visible instead of a candidate quietly vanishing.
        try:
            risk_verdict = risk_evaluate(
                best, signal_stock, best.regime_context, portfolio_state, app_module
            )
        except Exception as e:
            logging.warning(f"AI_CONSENSUS risk evaluation failed symbol={symbol}: {e}")
            risk_verdict = {
                "candidate_symbol": symbol, "verdict": "VETOED",
                "vetoed_by": ["RISK_MANAGER_ERROR"], "reason": str(e),
            }

        best.risk_verdict = risk_verdict

        if risk_verdict["verdict"] == "VETOED":
            best.state = "VETOED"
            best.add_reason(f"[RiskManager] VETOED - {risk_verdict['reason']}")
        else:
            best.add_reason(f"[RiskManager] APPROVED - {risk_verdict['reason']}")

        # ---- Brain 7 (Reviewer) support: record this decision in Experience
        # Memory now, vetoed or not, so a later close/review can be linked
        # back to exactly the evidence Brain 4/5 acted on. Never blocks the
        # pipeline - decision_id stays None on any DB failure.
        try:
            best.decision_id = experience_memory.record_decision(
                best, best.regime_context, best.analog_report, risk_verdict
            )
        except Exception as e:
            logging.warning(f"AI_CONSENSUS experience_memory.record_decision failed symbol={symbol}: {e}")
            best.decision_id = None

        final_list.append(best)

    # Approved candidates first (ranked by ai_score), then vetoed ones -
    # vetoes stay visible at the bottom rather than being filtered out.
    final_list.sort(

        key=lambda x: (x.risk_verdict["verdict"] == "APPROVED", x.ai_score),

        reverse=True

    )

    st.session_state.final_trade_list = final_list

    approved_count = sum(1 for t in final_list if t.risk_verdict["verdict"] == "APPROVED")
    vetoed_count = len(final_list) - approved_count

    logging.info(

        f"AI_CONSENSUS candidates_in={len(st.session_state.trade_candidates)} "

        f"symbols_grouped={len(grouped)} final_ranked={len(final_list)} "

        f"approved={approved_count} vetoed={vetoed_count} "

        f"symbols={[t.symbol for t in final_list]}"

    )

    return final_list


def get_final_trade_dataframe():

    rows = []

    for trade in st.session_state.final_trade_list:

        verdict = getattr(trade, "risk_verdict", None) or {}

        rows.append({

            "Symbol": trade.symbol,

            "Best Strategy": trade.strategy,

            "Verdict": verdict.get("verdict", "PENDING"),

            "AI Score": round(trade.ai_score, 2),

            "AI Confidence": getattr(trade, "ai_confidence", None),

            "Expected Value": getattr(trade, "expected_value", None),

            "Confidence": trade.confidence,

            "RR": trade.risk_reward,

            "Entry": trade.entry,

            "Stop": trade.stop,

            "Target": trade.target1,

            "Signals": trade.strategy_count,

            "State": trade.state,

            "Reason": verdict.get("reason", "")

        })

    if len(rows):

        return pd.DataFrame(rows)

    return pd.DataFrame()


def show_ai_consensus():
    # NOTE: DO NOT call build_ai_consensus() here. This is a DISPLAY function.
    # execute_scan_pipeline() already ran the full AI Consensus + Risk Manager
    # pass and populated st.session_state.final_trade_list. Calling it a second
    # time here re-runs the entire Risk Manager against paper_positions that
    # the pipeline just opened, so every candidate gets vetoed with
    # `EXPOSURE 10/10` and the original approvals are silently overwritten.
    # This function must ONLY read state, never re-run the pipeline.

    df = get_final_trade_dataframe()

    approved = [
        t for t in st.session_state.final_trade_list
        if getattr(t, "risk_verdict", {}).get("verdict") == "APPROVED"
    ]

    if len(df):

        st.subheader("AI Consensus Ranking")

        st.dataframe(

            df,

            use_container_width=True

        )

        if not approved:

            st.info(
                "No Trade - every candidate this scan was vetoed by the Risk "
                "Manager. See the Verdict/Reason columns above for why."
            )

    else:

        st.info("No Trade - no candidates were generated this scan.")
# =====================================================
# CAPITAL ALLOCATION ENGINE
# VERSION 3.4B
# =====================================================

def allocate_portfolio():
    """
    Brain 6 (Portfolio Manager): sizes and allocates capital across every
    candidate Brain 5 approved this scan - ranked by expected_value
    (Brain 4's historical-analog-informed estimate), respecting sector
    concentration caps and the portfolio's open-position limit. Vetoed
    candidates never reach this function; candidates that are approved
    but get no capital still get a state/rationale (APPROVED_NO_CAPITAL)
    so they stay visible rather than silently disappearing.
    """
    from os_brains.risk_manager import build_portfolio_state
    from os_brains.portfolio_manager import allocate as portfolio_allocate
    from os_brains import experience_memory

    if len(st.session_state.final_trade_list) == 0:
        st.session_state.selected_portfolio = []
        return []

    app_module = sys.modules[__name__]

    approved = [
        t for t in st.session_state.final_trade_list
        if getattr(t, "risk_verdict", {}).get("verdict") == "APPROVED"
    ]

    if not approved:
        st.session_state.selected_portfolio = []
        logging.info(
            f"PORTFOLIO_ALLOCATION final_trades_in={len(st.session_state.final_trade_list)} "
            f"approved=0 selected=[] - no trade this scan"
        )
        return []

    portfolio_state = build_portfolio_state(app_module)

    try:
        portfolio_allocate(approved, portfolio_state, app_module)
    except Exception as e:
        logging.warning(f"PORTFOLIO_ALLOCATION Brain 6 allocation failed: {e}")

    # Brain 7 support: every approved candidate now has a final capital
    # fate (ALLOCATED or APPROVED_NO_CAPITAL) - mirror it onto its
    # Experience Memory decision row so a trade that never actually opened
    # is recorded as NO_TRADE rather than sitting at PENDING forever.
    for candidate in approved:
        decision_id = getattr(candidate, "decision_id", None)
        if decision_id is None:
            continue
        allocation_decision = {
            "state": candidate.state,
            "position_size": getattr(candidate, "position_size", 0),
            "capital_required": getattr(candidate, "capital_required", 0),
            "portfolio_weight": getattr(candidate, "portfolio_weight", 0),
            "rationale": getattr(candidate, "allocation_rationale", ""),
        }
        outcome_state = "PENDING" if candidate.state == "ALLOCATED" else "NO_TRADE"
        try:
            experience_memory.update_allocation(decision_id, allocation_decision, outcome_state)
        except Exception as e:
            logging.warning(f"PORTFOLIO_ALLOCATION experience_memory.update_allocation failed symbol={candidate.symbol}: {e}")

    selected = [t for t in approved if t.state == "ALLOCATED"]

    st.session_state.selected_portfolio = selected

    logging.info(

        f"PORTFOLIO_ALLOCATION final_trades_in={len(st.session_state.final_trade_list)} "

        f"approved={len(approved)} selected={[t.symbol for t in selected]} "

        f"remaining_capital={selected[-1].cash_reserved if selected else portfolio_state['capital']}"

    )

    return selected


def portfolio_dataframe():

    rows = []

    for trade in st.session_state.selected_portfolio:

        rows.append({

            "Symbol": trade.symbol,

            "Strategy": trade.strategy,

            "AI Score": round(trade.ai_score,2),

            "AI Confidence": getattr(trade, "ai_confidence", None),

            "Expected Value": getattr(trade, "expected_value", None),

            "Confidence": trade.confidence,

            "Qty": trade.position_size,

            "Capital": round(trade.capital_required,2),

            "Weight %": trade.portfolio_weight,

            "Entry": trade.entry,

            "Stop": trade.stop,

            "Target": trade.target1,

            "RR": trade.risk_reward,

            "Rationale": getattr(trade, "allocation_rationale", "")

        })

    return pd.DataFrame(rows)


def show_allocated_portfolio():

    allocate_portfolio()

    df = portfolio_dataframe()

    if len(df):

        st.subheader("Allocated Portfolio")

        st.dataframe(

            df,

            use_container_width=True

        )
# =====================================================
# REAL TIME TRADE MONITOR
# VERSION 3.5A
# =====================================================

import time

if "live_monitor_running" not in st.session_state:
    st.session_state.live_monitor_running = False


# =====================================================
# EXECUTION PIPELINE
# VERSION 3.5B
# =====================================================
def execute_selected_portfolio():
    # Position size/capital here were already set by Brain 6
    # (portfolio_manager.allocate) - recalculating with the flat
    # per-trade sizer would silently overwrite its sector-cap trimming
    # and ranking, so this only flips state to BUY and opens the trade.

    for trade in st.session_state.selected_portfolio:

        trade.state = "BUY"

        get_execution_engine().open_trade(trade)

def _append_funnel(stage, entered, exited, rejected=0, reasons=None):
    reasons = reasons or []
    st.session_state.decision_funnel.append({
        "Stage": stage,
        "Entered": int(entered or 0),
        "Exited": int(exited or 0),
        "Rejected": int(rejected or 0),
        "Rejection Reasons": " | ".join(reasons),
    })


def _collect_no_trade_explanation():
    reasons = []
    veto_counts = {}
    for trade in st.session_state.final_trade_list:
        verdict = getattr(trade, "risk_verdict", {}) or {}
        if verdict.get("verdict") == "VETOED":
            labels = verdict.get("vetoed_by") or ["Risk Manager veto"]
            for label in labels:
                veto_counts[label] = veto_counts.get(label, 0) + 1
    for label, count in sorted(veto_counts.items()):
        reasons.append(f"Risk Manager rejected {count} candidate(s): {label}.")
    no_capital = [t for t in st.session_state.final_trade_list if getattr(t, "state", "") == "APPROVED_NO_CAPITAL"]
    if no_capital:
        reasons.append(f"Portfolio Exposure rejected {len(no_capital)} approved candidate(s).")
    weak_analog = [
        t for t in st.session_state.final_trade_list
        if (getattr(t, "analog_report", {}) or {}).get("sample_confidence") == "LOW"
    ]
    if weak_analog:
        reasons.append(f"Historical Analog evidence was weak for {len(weak_analog)} candidate(s).")
    negative_ev = [t for t in st.session_state.final_trade_list if (getattr(t, "expected_value", 0) or 0) < 0]
    if negative_ev:
        reasons.append(f"Expected Value was negative for {len(negative_ev)} candidate(s).")
    if not reasons:
        reasons.append("No stock satisfied the minimum evidence threshold across strategy, risk, portfolio and consensus stages.")
    st.session_state.no_trade_explanation = reasons
    return reasons


def execute_scan_pipeline():
    from os_brains.pipeline_manager import PipelineManager, PipelineStep

    manager = PipelineManager(on_event=_pipeline_event)

    def initialize_stage():
        st.session_state.trade_candidates = {}
        st.session_state.final_trade_list = []
        st.session_state.selected_portfolio = []
        st.session_state.decision_funnel = []
        calculate_sector_strength()
        fetch_nifty_benchmark()
        prefetch_news_earnings(list(st.session_state.market_data.keys()))
        _append_funnel("Universe", len(st.session_state.market_data), len(st.session_state.market_data), 0, [])
        return f"{len(st.session_state.market_data)} symbols initialized"

    def scan_stage():
        total = len(st.session_state.market_data)
        progress = st.progress(0) if total else None
        status = st.empty()
        quality_pass = structure_pass = processed = 0
        candidate_reasons = []

        for index, (symbol, df) in enumerate(st.session_state.market_data.items(), start=1):
            if progress:
                progress.progress(index / total)
            status.write(f"Scanning : {symbol}")
            df = calculate_indicators(df)
            if df is None:
                candidate_reasons.append(f"{symbol}: indicator calculation failed")
                continue

            stock = get_stock(symbol)
            stock.set_dataframe(df)
            calculate_trade_quality(stock)
            processed += 1
            if (stock.score.get("quality") or 0) > 0:
                quality_pass += 1
            update_market_structure(stock)
            if stock.market.get("TREND") or stock.patterns.get("BOS") or stock.patterns.get("CHOCH"):
                structure_pass += 1

            run_batch1_signal_engines(stock)
            candidates_before = {k for k, v in st.session_state.trade_candidates.items() if v.symbol == symbol}
            run_all_strategies(stock)
            run_batch2_signal_engines(stock)
            candidates_after = {k for k, v in st.session_state.trade_candidates.items() if v.symbol == symbol}
            if not (candidates_after - candidates_before):
                candidate_reasons.append(f"{symbol}: no strategy setup triggered")

            for trade in list(st.session_state.trade_candidates.values()):
                if trade.symbol != symbol:
                    continue
                validate_trade_candidate(stock, trade)
                apply_sector_bonus(stock, trade)
                calculate_position_size(trade)

        _append_funnel("Trade Quality", total, quality_pass, total - quality_pass, ["insufficient indicator/quality score"] if total - quality_pass else [])
        _append_funnel("Market Structure", processed, structure_pass, processed - structure_pass, ["trend/BOS/CHOCH structure not strong enough"] if processed - structure_pass else [])
        raw_symbols = len({t.symbol for t in st.session_state.trade_candidates.values()})
        _append_funnel("Strategist", processed, raw_symbols, max(0, processed - raw_symbols), candidate_reasons[:25])
        return f"{len(st.session_state.trade_candidates)} raw candidates"

    def consensus_stage():
        before = len(st.session_state.trade_candidates)
        final_list = build_ai_consensus()
        analog_reject = [t.symbol for t in final_list if (getattr(t, "analog_report", {}) or {}).get("sample_confidence") == "LOW"]
        _append_funnel("Historical Analog", before, len(final_list) - len(analog_reject), len(analog_reject), [f"{s}: Historical Analog too weak" for s in analog_reject[:25]])
        approved = [t for t in final_list if getattr(t, "risk_verdict", {}).get("verdict") == "APPROVED"]
        risk_reasons = []
        for t in final_list:
            verdict = getattr(t, "risk_verdict", {}) or {}
            if verdict.get("verdict") == "VETOED":
                risk_reasons.append(f"{t.symbol}: {verdict.get('reason', 'Risk Manager veto')}")
        _append_funnel("Risk Manager", len(final_list), len(approved), len(final_list) - len(approved), risk_reasons[:25])
        _append_funnel("AI Consensus", before, len(final_list), max(0, before - len(final_list)), [])
        return f"{len(final_list)} consensus candidates; {len(approved)} approved"

    def portfolio_stage():
        approved = [t for t in st.session_state.final_trade_list if getattr(t, "risk_verdict", {}).get("verdict") == "APPROVED"]
        selected = allocate_portfolio()
        rejected = [t for t in approved if t.state != "ALLOCATED"]
        _append_funnel("Portfolio Manager", len(approved), len(selected), len(rejected), [f"{t.symbol}: {getattr(t, 'allocation_rationale', 'Portfolio correlation/exposure')}" for t in rejected[:25]])
        _append_funnel("Final Trades", len(st.session_state.final_trade_list), len(selected), len(st.session_state.final_trade_list) - len(selected), [])
        return f"{len(selected)} allocated trades"

    def paper_stage():
        execute_selected_portfolio()
        monitor_open_positions()
        return f"{len(st.session_state.paper_positions)} open paper positions"

    def reviewer_memory_stage():
        reviewed = len(st.session_state.get("closed_positions", []))
        _collect_no_trade_explanation()
        return f"Experience Memory updated; reviewer has {reviewed} closed position(s) available"

    ok = manager.run([
        PipelineStep("Market Observer", initialize_stage, "Preparing market context"),
        PipelineStep("Market Historian", lambda: "Regime catalog/context available", "Historian ready"),
        PipelineStep("Trade Candidate Engine", scan_stage, "Running indicators, Batch 1, Batch 2 and strategies"),
        PipelineStep("Historical Analog Engine", consensus_stage, "Strategist, analog evidence, risk and consensus"),
        PipelineStep("Strategist", lambda: "Strategist evidence included in consensus", "Completed"),
        PipelineStep("Risk Manager", lambda: "Risk verdicts captured", "Completed"),
        PipelineStep("Portfolio Manager", portfolio_stage, "Allocating approved trades"),
        PipelineStep("AI Consensus", lambda: "Consensus ranking refreshed", "Completed"),
        PipelineStep("Paper Trading Engine", paper_stage, "Opening/monitoring paper trades"),
        PipelineStep("Reviewer", reviewer_memory_stage, "Recording learning updates"),
        PipelineStep("Experience Memory", lambda: "Decision memory synchronized", "Completed"),
        PipelineStep("Dashboard Refresh", lambda: "Mission Control refreshed", "Completed"),
    ])

    if ok:
        st.success("Pipeline Completed Successfully")
    else:
        st.error("Pipeline stopped. See Mission Control logs.")
# =====================================================
# VCP ENGINE
# VERSION 3.6A
# =====================================================

def detect_vcp(stock):

    df = stock.data

    if df is None:
        return

    if len(df) < 120:
        return

    highs = df["High"].rolling(20).max()
    lows = df["Low"].rolling(20).min()

    swings = []

    for i in range(20, len(df), 10):

        high = highs.iloc[i]
        low = lows.iloc[i]

        contraction = ((high - low) / high) * 100

        swings.append(contraction)

    if len(swings) < 4:
        return

    last_four = swings[-4:]

    decreasing = all(
        last_four[i] > last_four[i + 1]
        for i in range(3)
    )

    if decreasing:

        stock.patterns["VCP"] = True

        stock.add_score("pattern", 15)

        stock.add_reason("Volatility Contraction Pattern")

        stock.add_indicator(
            "VCP_CONTRACTIONS",
            len(last_four)
        )
def create_vcp_candidate(stock):

    if not stock.patterns.get("VCP", False):
        return

    last = stock.data.iloc[-1]

    trade = TradeCandidate(
        stock.symbol,
        "VCP"
    )

    trade.set_entry(round(last["High"] * 1.002, 2))

    stop = min(
        last["Low"],
        last["EMA20"]
    )

    trade.set_stop(round(stop, 2))

    if trade.entry is None or trade.stop is None:
        return

    risk = trade.entry - trade.stop

    trade.set_target1(
        round(trade.entry + (risk * 3), 2)
    )

    confidence = 75

    if stock.market.get("TREND") == "UPTREND":
        confidence += 10

    if last["RVOL"] > 1.2:
        confidence += 10

    if last["MACD"] > last["MACD_SIGNAL"]:
        confidence += 5

    trade.confidence = min(confidence, 100)

    trade.calculate_rr()

    trade.state = "READY"

    save_trade_candidate(trade)
def run_vcp_strategy(stock):

    detect_vcp(stock)

    create_vcp_candidate(stock)


# ==========================================
# REGISTER STRATEGIES
# ==========================================

register_strategy(
    "PRICE SQUEEZE",
    run_price_squeeze_strategy,
    priority=10
)

register_strategy(
    "DEMAND & SUPPLY",
    run_demand_supply_strategy,
    priority=20
)

register_strategy(
    "VCP",
    run_vcp_strategy,
    priority=30
)


# =====================================================
# BREAKOUT ENGINE
# VERSION 3.7A
# =====================================================

BREAKOUT_LOOKBACK = 20
BREAKOUT_BUFFER = 0.002


def detect_breakout(stock):

    df = stock.data

    if df is None:
        return

    if len(df) < BREAKOUT_LOOKBACK + 5:
        return

    last = df.iloc[-1]

    resistance = df["High"].iloc[-BREAKOUT_LOOKBACK-1:-1].max()

    breakout_price = round(
        resistance * (1 + BREAKOUT_BUFFER),
        2
    )

    stock.add_indicator(
        "BREAKOUT_LEVEL",
        breakout_price
    )

    breakout = False

    if last["Close"] >= breakout_price:

        breakout = True

        stock.patterns["BREAKOUT"] = True

        stock.add_score(
            "pattern",
            12
        )

        stock.add_reason(
            "Resistance Breakout"
        )

    if last["RVOL"] >= 1.50:

        stock.add_score(
            "volume",
            5
        )

        stock.add_reason(
            "Volume Confirmation"
        )

    if last["MACD"] > last["MACD_SIGNAL"]:

        stock.add_score(
            "momentum",
            5
        )

        stock.add_reason(
            "Bullish MACD"
        )

    stock.patterns["BREAKOUT_READY"] = breakout
# =====================================================
# BREAKOUT ENGINE
# PART 2
# VERSION 3.7B
# =====================================================

def create_breakout_candidate(stock):

    if not stock.patterns.get(

        "BREAKOUT_READY",

        False

    ):

        return

    last = stock.data.iloc[-1]

    trade = TradeCandidate(

        stock.symbol,

        "BREAKOUT"

    )

    entry = stock.indicators["BREAKOUT_LEVEL"]

    stop = round(

        min(

            last["EMA20"],

            last["Low"]

        ),

        2

    )

    risk = entry - stop

    if risk <= 0:

        return

    trade.set_entry(entry)

    trade.set_stop(stop)

    trade.set_target1(

        round(

            entry + (risk * 3),

            2

        )

    )

    confidence = 70

    if stock.market.get("TREND") == "UPTREND":

        confidence += 10

        trade.add_reason(

            "Primary Uptrend"

        )

    if last["RVOL"] >= 1.5:

        confidence += 10

        trade.add_reason(

            "Volume Confirmation"

        )

    if last["MACD"] > last["MACD_SIGNAL"]:

        confidence += 10

        trade.add_reason(

            "Bullish MACD"

        )

    trade.confidence = min(

        confidence,

        100

    )

    trade.calculate_rr()

    if trade.risk_reward >= 2.5:

        trade.state = "READY"

    else:

        trade.state = "WATCHLIST"

    save_trade_candidate(trade)


def run_breakout_strategy(stock):

    detect_breakout(stock)

    create_breakout_candidate(stock)

register_strategy(
    "BREAKOUT",
    run_breakout_strategy,
    priority=40
)
# =====================================================
# ORDER BLOCK ENGINE
# VERSION 3.8A
# =====================================================

ORDER_BLOCK_LOOKBACK = 40


def detect_order_blocks(stock):

    df = stock.data

    if df is None:
        return

    if len(df) < ORDER_BLOCK_LOOKBACK:
        return

    bullish_blocks = []
    bearish_blocks = []

    for i in range(5, len(df)-3):

        candle = df.iloc[i]

        next1 = df.iloc[i+1]
        next2 = df.iloc[i+2]

        body = abs(
            candle["Close"] - candle["Open"]
        )

        rng = candle["High"] - candle["Low"]

        if rng == 0:
            continue

        body_percent = body / rng

        # Bullish Order Block

        if candle["Close"] < candle["Open"]:

            if (

                next1["Close"] > next1["Open"]

                and

                next2["Close"] > next2["Open"]

                and

                next2["Close"] > candle["High"]

            ):

                bullish_blocks.append({

                    "Low": candle["Low"],

                    "High": candle["High"],

                    "Index": i

                })

        # Bearish Order Block

        if candle["Close"] > candle["Open"]:

            if (

                next1["Close"] < next1["Open"]

                and

                next2["Close"] < next2["Open"]

                and

                next2["Close"] < candle["Low"]

            ):

                bearish_blocks.append({

                    "Low": candle["Low"],

                    "High": candle["High"],

                    "Index": i

                })

    stock.patterns["BULLISH_ORDER_BLOCKS"] = bullish_blocks

    stock.patterns["BEARISH_ORDER_BLOCKS"] = bearish_blocks

    stock.add_indicator(

        "ORDER_BLOCKS",

        len(bullish_blocks)

    )

    if len(bullish_blocks):

        stock.add_score(

            "pattern",

            min(len(bullish_blocks),5)

        )

        stock.add_reason(

            f"{len(bullish_blocks)} Bullish Order Blocks"

        )

def nearest_order_block(stock):

    zones = stock.patterns.get(
        "BULLISH_ORDER_BLOCKS",
        []
    )

    if not zones:
        return None

    price = stock.data.iloc[-1]["Close"]

    return min(
        zones,
        key=lambda z: abs(
            price - z["High"]
        )
    )


def create_order_block_candidate(stock):

    zone = nearest_order_block(stock)

    if zone is None:
        return

    last = stock.data.iloc[-1]

    trade = TradeCandidate(
        stock.symbol,
        "ORDER_BLOCK"
    )

    trade.set_entry(round(zone["High"], 2))
    trade.set_stop(round(zone["Low"], 2))

    if trade.entry is None or trade.stop is None:
        return

    risk = trade.entry - trade.stop

    if risk <= 0:
        return

    trade.set_target1(
        round(trade.entry + risk * 3, 2)
    )

    confidence = 70

    if stock.market.get("TREND") == "UPTREND":
        confidence += 10

    if last["RVOL"] >= 1.2:
        confidence += 10

    if stock.score["quality"] >= 80:
        confidence += 10

    trade.confidence = min(confidence, 100)

    trade.calculate_rr()

    trade.state = "READY"

    save_trade_candidate(trade)


def run_order_block_strategy(stock):

    detect_order_blocks(stock)

    create_order_block_candidate(stock)

register_strategy(
    "ORDER BLOCK",
    run_order_block_strategy,
    priority=50
)
# ==========================================================
# MODULE A - PART 1
# PROFESSIONAL POSITION OBJECT
# ==========================================================

from dataclasses import dataclass, field
from datetime import datetime


# ==========================================================
# EXECUTION ENGINE (Paper / Simulation / future Live)
# ==========================================================
# Owns "how a decision to open/close a trade becomes a recorded trade".
# Everything upstream (Brains, AI Consensus, Risk Manager, Portfolio
# Manager) only ever decides WHAT to trade - it hands a TradeCandidate or
# an open PaperPosition to get_execution_engine() and never touches
# st.session_state.paper_positions or PaperPosition.close_trade() itself.
# That means a future real broker only has to implement this interface;
# no decision-making code changes when the mode changes.

class ExecutionEngine:

    mode = "ABSTRACT"

    def open_trade(self, trade):
        raise NotImplementedError

    def close_trade(self, position, reason, price):
        raise NotImplementedError


class PaperExecutionEngine(ExecutionEngine):
    """
    Today's default and only fully "real" mode: records trades as
    PaperPosition objects in st.session_state, exactly as the app already
    did before this abstraction existed.
    """

    mode = "PAPER"

    def open_trade(self, trade):
        open_paper_trade(trade)
        return st.session_state.paper_positions.get(trade.symbol)

    def close_trade(self, position, reason, price):
        position.close_trade(reason, price)
        return position


class SimulationExecutionEngine(PaperExecutionEngine):
    """
    Identical mechanics to Paper mode - same PaperPosition bookkeeping,
    same Brain 7 / Experience Memory feedback on close. Kept as a
    distinct, explicitly-labelled mode so a run made against non-live or
    backfilled data is never confused with real-time paper trading in the
    trade journal / audit log, without needing a second trade-recording
    implementation.
    """

    mode = "SIMULATION"


class LiveExecutionEngine(ExecutionEngine):
    """
    Seam for a future real broker (e.g. Upstox). Intentionally not
    implemented in this phase - selecting this mode fails loudly instead
    of silently falling back to paper trading, so it can never be
    mistaken for a working live-execution path.
    """

    mode = "LIVE"

    def open_trade(self, trade):
        raise NotImplementedError(
            "Live execution is not implemented yet - use Paper or Simulation mode."
        )

    def close_trade(self, position, reason, price):
        raise NotImplementedError(
            "Live execution is not implemented yet - use Paper or Simulation mode."
        )


EXECUTION_ENGINES = {
    "PAPER": PaperExecutionEngine(),
    "SIMULATION": SimulationExecutionEngine(),
    "LIVE": LiveExecutionEngine(),
}

if "execution_mode" not in st.session_state:
    st.session_state.execution_mode = "PAPER"


def get_execution_engine():
    return EXECUTION_ENGINES.get(
        st.session_state.execution_mode,
        EXECUTION_ENGINES["PAPER"],
    )


@dataclass
class PaperPosition:

    symbol: str
    strategy: str

    qty: int = 0

    entry: float = 0.0

    stop: float = 0.0

    target1: float = 0.0
    target2: float = 0.0
    target3: float = 0.0

    current_price: float = 0.0

    highest_price: float = 0.0
    lowest_price: float = 0.0

    trailing_stop: float = 0.0

    invested: float = 0.0

    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    max_profit: float = 0.0
    max_drawdown: float = 0.0

    rr: float = 0.0

    confidence: int = 0

    ai_score: int = 0

    status: str = "OPEN"

    target1_hit: bool = False
    target2_hit: bool = False
    target3_hit: bool = False

    break_even: bool = False

    partial_exit_done: bool = False

    remaining_qty: int = 0

    entry_time: datetime = field(
        default_factory=datetime.now
    )

    exit_time: datetime | None = None

    exit_reason: str = ""

    history: list = field(default_factory=list)

    decision_id: int | None = None

    # -----------------------------------------------------

    def initialise(self):

        self.current_price = self.entry

        self.highest_price = self.entry

        self.lowest_price = self.entry

        self.trailing_stop = self.stop

        self.remaining_qty = self.qty

        self.invested = self.qty * self.entry

    # -----------------------------------------------------

    def update_price(self, price):

        self.current_price = float(price)

        if price > self.highest_price:
            self.highest_price = price

        if price < self.lowest_price:
            self.lowest_price = price

        self.unrealized_pnl = round(
            (price - self.entry) * self.remaining_qty,
            2
        )

        self.max_profit = max(
            self.max_profit,
            self.unrealized_pnl
        )

        self.max_drawdown = min(
            self.max_drawdown,
            self.unrealized_pnl
        )

    # -----------------------------------------------------

    def move_stop(self, new_stop):

        if new_stop > self.trailing_stop:

            self.trailing_stop = round(
                new_stop,
                2
            )

    # -----------------------------------------------------

    def activate_break_even(self):

        if self.break_even:
            return

        self.break_even = True

        self.trailing_stop = self.entry

    # -----------------------------------------------------

    def close_partial(self, qty, price):

        if qty <= 0:
            return

        qty = min(
            qty,
            self.remaining_qty
        )

        pnl = (
            price - self.entry
        ) * qty

        self.realized_pnl += pnl

        self.remaining_qty -= qty

        self.history.append({

            "time": datetime.now(),

            "type": "PARTIAL",

            "qty": qty,

            "price": price,

            "pnl": pnl

        })

    # -----------------------------------------------------

    def close_trade(self, reason, price):

        pnl = (
            price - self.entry
        ) * self.remaining_qty

        self.realized_pnl += pnl

        self.remaining_qty = 0

        self.status = "CLOSED"

        self.exit_reason = reason

        self.exit_time = datetime.now()

        self.history.append({

            "time": self.exit_time,

            "type": "EXIT",

            "price": price,

            "reason": reason,

            "pnl": pnl

        })

        # Brain 7 (Reviewer): every close path funnels through this method,
        # so this is the one place a completed trade can be reviewed and fed
        # back into Experience Memory regardless of which trade-management
        # path (legacy mark_closed or the newer check_stop_loss/
        # check_target3) actually triggered the close. Never raises - a
        # review failure must not prevent a trade from closing.
        try:
            from os_brains.reviewer import review_closed_trade
            review_closed_trade(self)
        except Exception as e:
            logging.warning(f"CLOSE_TRADE reviewer.review_closed_trade failed symbol={self.symbol}: {e}")

    # -----------------------------------------------------

    def total_pnl(self):

        return round(

            self.realized_pnl +

            self.unrealized_pnl,

            2

        )

    # -----------------------------------------------------
    # Backward-compatible aliases: earlier pipeline code (Trade History,
    # Open/Live Positions panels) reads .quantity / .pnl / .mark_closed(),
    # while this dataclass uses .qty / realized+unrealized pnl / close_trade().
    # These properties bridge the two without touching either call site.

    @property
    def quantity(self):
        return self.qty

    @property
    def pnl(self):
        return self.total_pnl()

    @property
    def exit_price(self):
        return self.current_price

    def mark_closed(self, price, reason):
        self.close_trade(reason, price)

    # -----------------------------------------------------

    def age_minutes(self):

        return int(

            (

                datetime.now()

                -

                self.entry_time

            ).total_seconds()

            / 60

        )
# ==========================================================
# MODULE A - PART 2
# POSITION MANAGER
# ==========================================================

def get_open_position(symbol):

    return st.session_state.paper_positions.get(symbol)


def add_open_position(position):

    st.session_state.paper_positions[position.symbol] = position


def remove_open_position(symbol):

    if symbol in st.session_state.paper_positions:

        del st.session_state.paper_positions[symbol]

       # ==========================================================
# MODULE A - PART 3
# TRADE MANAGEMENT ENGINE
# ==========================================================

TRAIL_ATR_MULTIPLIER = 1.5


def update_position_price(position, latest_price):

    position.update_price(latest_price)


def check_stop_loss(position):

    if position.status != "OPEN":
        return False

    if position.current_price <= position.trailing_stop:

        get_execution_engine().close_trade(
            position,
            "STOP LOSS",
            position.current_price
        )

        return True

    return False


def check_target1(position):

    if position.target1_hit:
        return

    if position.current_price >= position.target1:

        qty = max(
            1,
            int(position.qty * 0.25)
        )

        position.close_partial(
            qty,
            position.current_price
        )

        position.target1_hit = True

        position.activate_break_even()


def check_target2(position):

    if position.target2_hit:
        return

    if position.target2 == 0:
        return

    if position.current_price >= position.target2:

        qty = max(
            1,
            int(position.qty * 0.35)
        )

        position.close_partial(
            qty,
            position.current_price
        )

        position.target2_hit = True


def check_target3(position):

    if position.target3_hit:
        return

    if position.target3 == 0:
        return

    if position.current_price >= position.target3:

        position.target3_hit = True

        get_execution_engine().close_trade(
            position,
            "TARGET 3",
            position.current_price
        )


def update_trailing_stop(position, stock):

    df = stock.data

    if df is None:
        return

    if len(df) < 20:
        return

    ema20 = df.iloc[-1]["EMA20"]

    atr = df.iloc[-1]["ATR"]

    new_stop = max(

        ema20,

        position.current_price -
        (atr * TRAIL_ATR_MULTIPLIER)

    )

    position.move_stop(new_stop)


def manage_position(stock, position):

    last_price = stock.data.iloc[-1]["Close"]

    update_position_price(
        position,
        last_price
    )

    if check_stop_loss(position):

        return

    check_target1(position)

    check_target2(position)

    check_target3(position)

    update_trailing_stop(
        position,
        stock
    )
# ==========================================================
# MODULE A - PART 4
# LIVE POSITION MONITOR
# ==========================================================

def update_position_statistics(position):

    if position.unrealized_pnl > position.max_profit:

        position.max_profit = position.unrealized_pnl

    if position.unrealized_pnl < position.max_drawdown:

        position.max_drawdown = position.unrealized_pnl


def archive_closed_position(position):

    st.session_state.closed_positions.append(position)

    st.session_state.paper_history.append(position)

    st.session_state.trade_journal.append({

        "Symbol": position.symbol,

        "Strategy": position.strategy,

        "Entry": position.entry,

        "Exit": position.current_price,

        "PnL": round(position.realized_pnl,2),

        "Reason": position.exit_reason,

        "Minutes": position.age_minutes()

    })


def monitor_open_positions():

    if len(st.session_state.paper_positions) == 0:

        return

    remove_list = []

    for symbol, position in list(

        st.session_state.paper_positions.items()

    ):

        stock = get_stock(symbol)

        if stock is None:

            continue

        if stock.data is None:

            continue

        manage_position(

            stock,

            position

        )

        update_position_statistics(position)

        if position.status == "CLOSED":

            archive_closed_position(position)

            remove_list.append(symbol)

    for symbol in remove_list:

        del st.session_state.paper_positions[symbol]
# ==========================================================
# MODULE A - PART 5
# DASHBOARD & ANALYTICS
# ==========================================================

def portfolio_statistics():

    open_positions = list(
        st.session_state.paper_positions.values()
    )

    closed_positions = st.session_state.closed_positions

    open_pnl = round(
        sum(p.unrealized_pnl for p in open_positions),
        2
    )

    closed_pnl = round(
        sum(p.realized_pnl for p in closed_positions),
        2
    )

    invested = round(
        sum(p.invested for p in open_positions),
        2
    )

    wins = len(
        [
            p for p in closed_positions
            if p.realized_pnl > 0
        ]
    )

    losses = len(
        [
            p for p in closed_positions
            if p.realized_pnl <= 0
        ]
    )

    total = wins + losses

    if total == 0:

        win_rate = 0

    else:

        win_rate = round(
            wins * 100 / total,
            2
        )

    return {

        "OpenPnL": open_pnl,

        "ClosedPnL": closed_pnl,

        "Invested": invested,

        "Wins": wins,

        "Losses": losses,

        "WinRate": win_rate,

        "OpenTrades": len(open_positions),

        "ClosedTrades": len(closed_positions)

    }


# ----------------------------------------------------------


def show_portfolio_dashboard():

    stats = portfolio_statistics()

    st.markdown(
        "## 📊 Portfolio Monitor"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Open P&L",
        f"₹{stats['OpenPnL']:.2f}"
    )

    c2.metric(
        "Closed P&L",
        f"₹{stats['ClosedPnL']:.2f}"
    )

    c3.metric(
        "Win Rate",
        f"{stats['WinRate']}%"
    )

    c4.metric(
        "Open Trades",
        stats["OpenTrades"]
    )

    st.divider()

    st.subheader(
        "Open Positions"
    )

    rows = []

    for p in st.session_state.paper_positions.values():

        rows.append({

            "Symbol": p.symbol,

            "Strategy": p.strategy,

            "Qty": p.remaining_qty,

            "Entry": p.entry,

            "LTP": round(
                p.current_price,
                2
            ),

            "Stop": round(
                p.trailing_stop,
                2
            ),

            "PnL": round(
                p.unrealized_pnl,
                2
            ),

            "Age(Min)": p.age_minutes()

        })

    if len(rows):

        st.dataframe(
            rows,
            use_container_width=True
        )

    st.divider()

    st.subheader(
        "Closed Trades"
    )

    closed = []

    for p in st.session_state.closed_positions:

        closed.append({

            "Symbol": p.symbol,

            "Strategy": p.strategy,

            "PnL": round(
                p.realized_pnl,
                2
            ),

            "Reason": p.exit_reason

        })

    if len(closed):

        st.dataframe(

            closed,

            use_container_width=True

        )
# =====================================================
# FAIR VALUE GAP ENGINE
# MODULE B - PART 1
# =====================================================

FVG_MIN_GAP_PERCENT = 0.30


def detect_fair_value_gaps(stock):

    df = stock.data

    if df is None:
        return

    if len(df) < 10:
        return

    bullish = []
    bearish = []

    for i in range(2, len(df)):

        c1 = df.iloc[i-2]
        c2 = df.iloc[i-1]
        c3 = df.iloc[i]

        # Bullish FVG

        if c3["Low"] > c1["High"]:

            gap = (

                (c3["Low"] - c1["High"])

                / c1["High"]

            ) * 100

            if gap >= FVG_MIN_GAP_PERCENT:

                bullish.append({

                    "Low": round(c1["High"],2),

                    "High": round(c3["Low"],2),

                    "Gap": round(gap,2),

                    "Index": i

                })

        # Bearish FVG

        if c3["High"] < c1["Low"]:

            gap = (

                (c1["Low"] - c3["High"])

                / c1["Low"]

            ) * 100

            if gap >= FVG_MIN_GAP_PERCENT:

                bearish.append({

                    "Low": round(c3["High"],2),

                    "High": round(c1["Low"],2),

                    "Gap": round(gap,2),

                    "Index": i

                })

    stock.patterns["BULLISH_FVG"] = bullish
    stock.patterns["BEARISH_FVG"] = bearish

    if bullish:

        stock.add_score("pattern", 8)

        stock.add_reason(

            f"{len(bullish)} Bullish FVG"

        )


def nearest_fvg(stock):

    zones = stock.patterns.get(

        "BULLISH_FVG",

        []

    )

    if not zones:

        return None

    price = stock.data.iloc[-1]["Close"]

    return min(

        zones,

        key=lambda x: abs(

            price -

            x["High"]

        )

    )


def create_fvg_candidate(stock):

    zone = nearest_fvg(stock)

    if zone is None:
        return

    last = stock.data.iloc[-1]

    trade = TradeCandidate(

        stock.symbol,

        "FVG"

    )

    trade.set_entry(

        round(zone["High"],2)

    )

    trade.set_stop(

        round(

            zone["Low"] - last["ATR"],

            2

        )

    )

    if trade.entry is None or trade.stop is None:
        return

    risk = trade.entry - trade.stop

    if risk <= 0:
        return

    trade.set_target1(

        round(

            trade.entry + risk * 3,

            2

        )

    )

    confidence = 70

    if stock.market.get(

        "TREND"

    ) == "UPTREND":

        confidence += 10

    if last["RVOL"] >= 1.20:

        confidence += 10

    if last["MACD"] > last["MACD_SIGNAL"]:

        confidence += 10

    trade.confidence = min(

        confidence,

        100

    )

    trade.calculate_rr()

    trade.state = "READY"

    save_trade_candidate(trade)


def run_fvg_strategy(stock):

    detect_fair_value_gaps(stock)

    create_fvg_candidate(stock)

register_strategy(
    "FVG",
    run_fvg_strategy,
    priority=60
)
register_strategy(
    "FVG",
    run_fvg_strategy,
    priority=70
)
# =====================================================
# LIQUIDITY SWEEP ENGINE
# MODULE B - PART 2
# =====================================================

LIQUIDITY_LOOKBACK = 15


def detect_liquidity_sweep(stock):

    df = stock.data

    if df is None:
        return

    if len(df) < LIQUIDITY_LOOKBACK + 5:
        return

    last = df.iloc[-1]

    previous_low = (

        df["Low"]

        .iloc[-LIQUIDITY_LOOKBACK-1:-1]

        .min()

    )

    previous_high = (

        df["High"]

        .iloc[-LIQUIDITY_LOOKBACK-1:-1]

        .max()

    )

    bullish = False

    bearish = False

    # ==========================================
    # Bullish Liquidity Sweep
    # ==========================================

    if (

        last["Low"] < previous_low

        and

        last["Close"] > previous_low

    ):

        bullish = True

        stock.patterns["BULLISH_SWEEP"] = True

        stock.add_score(

            "pattern",

            12

        )

        stock.add_reason(

            "Bullish Liquidity Sweep"

        )

    # ==========================================
    # Bearish Liquidity Sweep
    # ==========================================

    if (

        last["High"] > previous_high

        and

        last["Close"] < previous_high

    ):

        bearish = True

        stock.patterns["BEARISH_SWEEP"] = True

    stock.add_indicator(

        "LIQUIDITY_SWEEP",

        bullish

    )


def create_liquidity_candidate(stock):

    if not stock.patterns.get(

        "BULLISH_SWEEP",

        False

    ):

        return

    last = stock.data.iloc[-1]

    trade = TradeCandidate(

        stock.symbol,

        "LIQUIDITY_SWEEP"

    )

    entry = round(

        last["High"] * 1.001,

        2

    )

    stop = round(

        last["Low"],

        2

    )

    risk = entry - stop

    if risk <= 0:

        return

    trade.set_entry(entry)

    trade.set_stop(stop)

    trade.set_target1(

        round(

            entry + (risk * 3),

            2

        )

    )

    confidence = 75

    # ==========================================
    # Volume Confirmation
    # ==========================================

    if last["RVOL"] >= 1.5:

        confidence += 10

        trade.add_reason(

            "High Relative Volume"

        )

    # ==========================================
    # MACD
    # ==========================================

    if last["MACD"] > last["MACD_SIGNAL"]:

        confidence += 5

        trade.add_reason(

            "Bullish MACD"

        )

    # ==========================================
    # Trend
    # ==========================================

    if stock.market.get(

        "TREND"

    ) == "UPTREND":

        confidence += 10

        trade.add_reason(

            "Primary Uptrend"

        )

    trade.confidence = min(

        confidence,

        100

    )

    trade.calculate_rr()

    trade.state = "READY"

    save_trade_candidate(

        trade

    )


def run_liquidity_strategy(stock):

    detect_liquidity_sweep(stock)

    create_liquidity_candidate(stock)
# =====================================================
# ==========================================================
# MARKET REGIME ENGINE
# MODULE B - PART 3 (FINAL)
# ==========================================================

ADX_TREND = 25
RVOL_HIGH = 1.50


def detect_market_regime(stock):

    df = stock.data

    if df is None:
        return

    if len(df) < 60:
        return

    last = df.iloc[-1]
    prev = df.iloc[-2]

    regime = "SIDEWAYS"
    strength = 50

    # ------------------------------------------------------
    # Trend Detection
    # ------------------------------------------------------

    if (

        last["EMA20"] >

        last["EMA50"] >

        last["EMA200"]

    ):

        regime = "TRENDING_BULL"

        strength += 20

    elif (

        last["EMA20"] <

        last["EMA50"] <

        last["EMA200"]

    ):

        regime = "TRENDING_BEAR"

        strength += 20

    # ------------------------------------------------------
    # ADX
    # ------------------------------------------------------

    if "ADX" in df.columns:

        if last["ADX"] >= ADX_TREND:

            strength += 10

    # ------------------------------------------------------
    # Relative Volume
    # ------------------------------------------------------

    if "RVOL" in df.columns:

        if last["RVOL"] >= RVOL_HIGH:

            strength += 10

    # ------------------------------------------------------
    # ATR Expansion
    # ------------------------------------------------------

    if "ATR" in df.columns:

        atr_avg = df["ATR"].tail(20).mean()

        if last["ATR"] > atr_avg:

            strength += 10

    # ------------------------------------------------------
    # Gap Detection
    # ------------------------------------------------------

    gap_up = False
    gap_down = False

    if last["Open"] > prev["High"]:

        gap_up = True

        strength += 5

    elif last["Open"] < prev["Low"]:

        gap_down = True

        strength += 5

    # ------------------------------------------------------
    # EMA Slope
    # ------------------------------------------------------

    ema20_prev = df.iloc[-5]["EMA20"]

    if last["EMA20"] > ema20_prev:

        strength += 5

    # ------------------------------------------------------
    # Save Results
    # ------------------------------------------------------

    strength = min(

        strength,

        100

    )

    stock.market["REGIME"] = regime

    stock.market["MARKET_STRENGTH"] = strength

    stock.market["GAP_UP"] = gap_up

    stock.market["GAP_DOWN"] = gap_down

    stock.add_indicator(

        "MARKET_REGIME",

        regime

    )

    stock.add_indicator(

        "MARKET_STRENGTH",

        strength

    )

    stock.patterns["TRENDING_BULL"] = regime == "TRENDING_BULL"

    stock.patterns["TRENDING_BEAR"] = regime == "TRENDING_BEAR"

    if regime == "TRENDING_BULL":

        stock.add_score(

            "trend",

            10

        )

        stock.add_reason(

            "Bull Market"

        )

    elif regime == "TRENDING_BEAR":

        stock.add_reason(

            "Bear Market"

        )

    else:

        stock.add_reason(

            "Sideways Market"

        )


# ==========================================================
# MARKET REGIME AI BONUS
# ==========================================================

def apply_market_regime_bonus(stock, trade):

    regime = stock.market.get(

        "REGIME",

        "SIDEWAYS"

    )

    strength = stock.market.get(

        "MARKET_STRENGTH",

        50

    )

    if regime == "TRENDING_BULL":

        trade.confidence += 10

        trade.add_reason(

            "Bull Market"

        )

    elif regime == "TRENDING_BEAR":

        trade.confidence -= 15

        trade.add_reason(

            "Bear Market"

        )

    else:

        trade.confidence -= 5

        trade.add_reason(

            "Sideways Market"

        )

    if strength >= 80:

        trade.confidence += 5

        trade.add_reason(

            "Strong Trend"

        )

    trade.confidence = max(

        0,

        min(

            trade.confidence,

            100

        )

    )


# ==========================================================
# RUNNER
# ==========================================================

def run_market_regime(stock):

    detect_market_regime(stock)

register_strategy(

    "MARKET REGIME",

    run_market_regime,

    priority=5

)


# =====================================================
# BREAK OF STRUCTURE (BOS)
# CHANGE OF CHARACTER (CHOCH)
# MODULE B - PART 4
# =====================================================

BOS_LOOKBACK = 20


def detect_market_structure_shift(stock):

    df = stock.data

    if df is None:
        return

    if len(df) < BOS_LOOKBACK + 10:
        return

    last = df.iloc[-1]

    previous_high = df["High"].iloc[
        -BOS_LOOKBACK-1:-1
    ].max()

    previous_low = df["Low"].iloc[
        -BOS_LOOKBACK-1:-1
    ].min()

    bos = False

    choch = False

    direction = "NONE"

    # ===========================
    # Bullish BOS
    # ===========================

    if last["Close"] > previous_high:

        bos = True

        direction = "UP"

        stock.add_reason(
            "Bullish BOS"
        )

        stock.add_score(
            "pattern",
            15
        )

    # ===========================
    # Bearish BOS
    # ===========================

    elif last["Close"] < previous_low:

        direction = "DOWN"

    # ===========================
    # CHOCH
    # ===========================

    ema20 = last["EMA20"]

    ema50 = last["EMA50"]

    if (

        ema20 > ema50

        and

        direction == "UP"

    ):

        choch = True

        stock.add_reason(
            "CHOCH"
        )

        stock.add_score(
            "pattern",
            8
        )

    stock.patterns["BOS"] = bos

    stock.patterns["CHOCH"] = choch

    stock.market["STRUCTURE"] = direction

    stock.add_indicator(
        "BOS",
        bos
    )

    stock.add_indicator(
        "CHOCH",
        choch
    )
# =====================================================
# MULTI TIMEFRAME ENGINE
# MODULE B - PART 5
# =====================================================

TIMEFRAME_SCORE = {

    "MONTHLY":20,

    "WEEKLY":20,

    "DAILY":20

}


def evaluate_timeframe(df):

    if len(df) < 200:

        return None

    last = df.iloc[-1]

    if (

        last["EMA20"] >

        last["EMA50"] >

        last["EMA200"]

    ):

        return "UP"

    elif (

        last["EMA20"] <

        last["EMA50"] <

        last["EMA200"]

    ):

        return "DOWN"

    return "SIDEWAYS"


def detect_multi_timeframe(stock):

    if stock.data is None:

        return

    daily = stock.data.copy()

    weekly = (

        daily

        .resample("W-FRI")

        .agg({

            "Open":"first",

            "High":"max",

            "Low":"min",

            "Close":"last",

            "Volume":"sum"

        })

        .dropna()

    )

    monthly = (

        daily

        .resample("ME")

        .agg({

            "Open":"first",

            "High":"max",

            "Low":"min",

            "Close":"last",

            "Volume":"sum"

        })

        .dropna()

    )

    weekly = calculate_indicators(weekly)

    monthly = calculate_indicators(monthly)

    if weekly is None or monthly is None:

        return

    daily_trend = evaluate_timeframe(daily)

    weekly_trend = evaluate_timeframe(weekly)

    monthly_trend = evaluate_timeframe(monthly)

    stock.market["DAILY_TREND"] = daily_trend
    stock.market["WEEKLY_TREND"] = weekly_trend
    stock.market["MONTHLY_TREND"] = monthly_trend

    alignment = 0

    if daily_trend == "UP":

        alignment += 20

    if weekly_trend == "UP":

        alignment += 20

    if monthly_trend == "UP":

        alignment += 20

    stock.market["MTF_SCORE"] = alignment

    stock.add_indicator(

        "MTF_SCORE",

        alignment

    )

    if alignment >= 60:

        stock.add_reason(

            "Multi Timeframe Bullish"

        )

        stock.add_score(

            "trend",

            10

        )
# ==========================================================
# SECTOR STRENGTH ENGINE
# MODULE B - PART 6
# ==========================================================

SECTOR_ETFS = {

    "NIFTY BANK":"^NSEBANK",

    "NIFTY IT":"^CNXIT",

    "NIFTY AUTO":"^CNXAUTO",

    "NIFTY FMCG":"^CNXFMCG",

    "NIFTY PHARMA":"^CNXPHARMA",

    "NIFTY METAL":"^CNXMETAL",

    "NIFTY ENERGY":"^CNXENERGY"

}

sector_strength = {}


def calculate_sector_strength():

    global sector_strength

    sector_strength = {}

    for sector in SECTOR_ETFS:

        try:

            ticker = yf.Ticker(

                SECTOR_ETFS[sector]

            )

            df = ticker.history(

                period="2y"

            )

            if len(df) < 200:

                continue

            df = calculate_indicators(df)

            if df is None:

                continue

            last = df.iloc[-1]

            score = 0

            if last["EMA20"] > last["EMA50"]:

                score += 30

            if last["EMA50"] > last["EMA200"]:

                score += 30

            if last["MACD"] > last["MACD_SIGNAL"]:

                score += 20

            if last["RSI"] > 55:

                score += 20

            sector_strength[sector] = score

        except Exception as e:

            logging.warning(f"calculate_sector_strength failed for {sector}: {e}")

            continue


def get_sector_score(sector):

    return sector_strength.get(

        sector,

        50

    )
def apply_sector_bonus(

    stock,

    trade

):

    sector = getattr(

        stock,

        "sector",

        None

    )

    if sector is None:

        return

    score = get_sector_score(

        sector

    )

    if score >= 80:

        trade.confidence += 10

        trade.add_reason(

            "Strong Sector"

        )

    elif score >= 60:

        trade.confidence += 5

        trade.add_reason(

            "Positive Sector"

        )

    elif score <= 40:

        trade.confidence -= 5

        trade.add_reason(

            "Weak Sector"

        )

    trade.confidence = min(

        trade.confidence,

        100

    )
# ==========================================================
# BATCH 1 - ADVANCED SIGNAL ENGINES
# MULTI-TIMEFRAME / RELATIVE STRENGTH / SECTOR / VOLUME PROFILE
# ==========================================================

NIFTY_INDEX_SYMBOL = "^NSEI"

nifty_benchmark_df = None

def assign_sector(stock):
    """
    Maps a stock to a known NSE sector bucket using STOCK_SECTOR_MAP.
    Falls back to a neutral "UNKNOWN" sector when no mapping exists,
    which get_sector_score() treats as a neutral 50 score.
    """
    base = stock.symbol.replace(".NS", "")
    sector = STOCK_SECTOR_MAP.get(base, "UNKNOWN")
    stock.sector = sector
    score = get_sector_score(sector) if sector != "UNKNOWN" else 50
    stock.score["sector"] = score
    stock.add_indicator("SECTOR_NAME", sector)
    stock.add_indicator("SECTOR_SCORE", score)
    if score >= 80:
        stock.add_reason(f"Sector {sector} strong ({score}/100)")
    elif score <= 40:
        stock.add_reason(f"Sector {sector} weak ({score}/100)")
    logging.info(
        f"SECTOR symbol={stock.symbol} sector={sector} score={score}"
    )
    return sector, score


def fetch_nifty_benchmark():
    """
    Downloads the NIFTY 50 index once per scan and caches it globally,
    so per-symbol relative strength calculations don't re-download it.
    """
    global nifty_benchmark_df
    try:
        df = yf.download(
            NIFTY_INDEX_SYMBOL,
            period=CONFIG["DOWNLOAD_PERIOD"],
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df is None or len(df) < 30:
            logging.warning("NIFTY benchmark download returned insufficient data")
            nifty_benchmark_df = None
            return None
        nifty_benchmark_df = df
        logging.info(f"NIFTY_BENCHMARK loaded rows={len(df)}")
        return df
    except Exception as e:
        logging.exception(f"fetch_nifty_benchmark failed: {e}")
        nifty_benchmark_df = None
        return None


def calculate_relative_strength(stock, lookback=63):
    """
    Relative Strength vs NIFTY: compares the stock's trailing return over
    `lookback` trading days (default ~3 months) against the index's return
    over the same window. Score is centered at 50 (in-line with the index),
    above 50 = outperforming, below 50 = underperforming.
    """
    df = stock.data
    if df is None or len(df) <= lookback:
        return None
    if nifty_benchmark_df is None or len(nifty_benchmark_df) <= lookback:
        return None
    try:
        stock_return = (
            df["Close"].iloc[-1] / df["Close"].iloc[-lookback] - 1
        ) * 100
        nifty_return = (
            nifty_benchmark_df["Close"].iloc[-1]
            / nifty_benchmark_df["Close"].iloc[-lookback]
            - 1
        ) * 100
        rs_delta = stock_return - nifty_return
        rs_score = max(0, min(100, 50 + (rs_delta * 2)))
        stock.add_indicator("RS_STOCK_RETURN_PCT", round(stock_return, 2))
        stock.add_indicator("RS_NIFTY_RETURN_PCT", round(nifty_return, 2))
        stock.add_indicator("RS_SCORE", round(rs_score, 2))
        stock.score["relative_strength"] = round(rs_score, 2)
        if rs_delta > 0:
            stock.add_reason(
                f"Outperforming NIFTY by {round(rs_delta, 2)}% over {lookback}d"
            )
        else:
            stock.add_reason(
                f"Underperforming NIFTY by {round(abs(rs_delta), 2)}% over {lookback}d"
            )
        logging.info(
            f"RELATIVE_STRENGTH symbol={stock.symbol} stock_return={round(stock_return,2)} "
            f"nifty_return={round(nifty_return,2)} rs_score={round(rs_score,2)}"
        )
        return rs_score
    except Exception as e:
        logging.exception(f"calculate_relative_strength failed for {stock.symbol}: {e}")
        return None


def _mtf_trend_label(df):
    """Shared trend classifier used for 1H / 15M timeframes."""
    if df is None or len(df) < 25:
        return "UNKNOWN"
    close = df["Close"]
    ema_fast = close.ewm(span=9).mean().iloc[-1]
    ema_slow = close.ewm(span=21).mean().iloc[-1]
    if ema_fast > ema_slow * 1.001:
        return "UPTREND"
    if ema_fast < ema_slow * 0.999:
        return "DOWNTREND"
    return "SIDEWAYS"


def analyze_multi_timeframe(stock):
    """
    Multi-Timeframe Analysis: pulls intraday 1H and 15M data for the symbol
    and classifies trend on each timeframe, then measures alignment against
    the already-computed Daily trend (stock.market["TREND"]).

    yfinance intraday limits (60m ~730d, 15m ~60d) are respected via the
    request periods below; failures are logged, never swallowed silently,
    and simply leave that timeframe as UNKNOWN rather than crashing the scan.
    """
    daily_trend = stock.market.get("TREND", "UNKNOWN")

    trend_1h = "UNKNOWN"
    trend_15m = "UNKNOWN"

    try:
        df_1h = yf.download(
            stock.symbol,
            period="60d",
            interval="60m",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        if isinstance(df_1h.columns, pd.MultiIndex):
            df_1h.columns = df_1h.columns.get_level_values(0)
        trend_1h = _mtf_trend_label(df_1h)
    except Exception as e:
        logging.warning(f"analyze_multi_timeframe 1H failed for {stock.symbol}: {e}")

    try:
        df_15m = yf.download(
            stock.symbol,
            period="5d",
            interval="15m",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        if isinstance(df_15m.columns, pd.MultiIndex):
            df_15m.columns = df_15m.columns.get_level_values(0)
        trend_15m = _mtf_trend_label(df_15m)
    except Exception as e:
        logging.warning(f"analyze_multi_timeframe 15M failed for {stock.symbol}: {e}")

    trends = [daily_trend, trend_1h, trend_15m]
    known = [t for t in trends if t != "UNKNOWN"]
    agree = len(known) > 0 and len(set(known)) == 1
    alignment_score = 100 if agree and len(known) == 3 else (
        60 if agree else 30
    )

    stock.add_indicator("MTF_DAILY_TREND", daily_trend)
    stock.add_indicator("MTF_1H_TREND", trend_1h)
    stock.add_indicator("MTF_15M_TREND", trend_15m)
    stock.score["mtf_alignment"] = alignment_score

    if agree and len(known) == 3:
        stock.add_reason("All timeframes aligned (Daily/1H/15M)")
    elif not agree:
        stock.add_reason("Timeframes conflicting (Daily/1H/15M)")

    logging.info(
        f"MULTI_TIMEFRAME symbol={stock.symbol} daily={daily_trend} "
        f"1h={trend_1h} 15m={trend_15m} alignment={alignment_score}"
    )

    return alignment_score


def calculate_volume_profile(stock, lookback=120, bins=20):
    """
    Volume Profile Analysis: bins Close price over the lookback window and
    sums traded Volume per bin to find the Point of Control (POC) - the
    price level with the heaviest traded volume - plus any other
    High Volume Nodes (HVN, >=70% of the POC's volume).
    """
    df = stock.data
    if df is None or len(df) < 30:
        return None
    try:
        window = df.tail(lookback)
        price_min = window["Low"].min()
        price_max = window["High"].max()
        if price_max <= price_min:
            return None

        bin_edges = np.linspace(price_min, price_max, bins + 1)
        bin_volume = np.zeros(bins)

        for _, row in window.iterrows():
            mid_price = (row["High"] + row["Low"]) / 2
            idx = np.searchsorted(bin_edges, mid_price) - 1
            idx = max(0, min(bins - 1, idx))
            bin_volume[idx] += row["Volume"]

        poc_idx = int(np.argmax(bin_volume))
        poc_price = round((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2, 2)
        poc_volume = bin_volume[poc_idx]

        hvn_threshold = poc_volume * 0.7
        hvn_count = int(np.sum(bin_volume >= hvn_threshold))

        last_close = df["Close"].iloc[-1]
        position = "ABOVE_POC" if last_close > poc_price else (
            "BELOW_POC" if last_close < poc_price else "AT_POC"
        )

        stock.add_indicator("VOLUME_POC", poc_price)
        stock.add_indicator("VOLUME_HVN_COUNT", hvn_count)
        stock.add_indicator("VOLUME_PROFILE_POSITION", position)
        stock.score["volume_profile"] = 70 if position == "ABOVE_POC" else (
            50 if position == "AT_POC" else 30
        )

        if position == "ABOVE_POC":
            stock.add_reason(f"Price trading above Volume POC ({poc_price})")
        elif position == "BELOW_POC":
            stock.add_reason(f"Price trading below Volume POC ({poc_price})")

        logging.info(
            f"VOLUME_PROFILE symbol={stock.symbol} poc={poc_price} "
            f"hvn_count={hvn_count} position={position}"
        )

        return {
            "poc": poc_price,
            "hvn_count": hvn_count,
            "position": position,
        }
    except Exception as e:
        logging.exception(f"calculate_volume_profile failed for {stock.symbol}: {e}")
        return None


def run_batch1_signal_engines(stock):
    """
    Runs all five Batch 1 signal engines for a single stock and returns a
    combined confidence bonus (0-25) intended to be added on top of a trade
    candidate's existing confidence score inside build_ai_consensus().
    Demand & Supply zones already run as part of the strategy registry
    (run_demand_supply_strategy); this function only adds the sector bonus
    for that engine via apply_sector_bonus, called per-candidate below.
    """
    assign_sector(stock)
    analyze_multi_timeframe(stock)
    calculate_relative_strength(stock)
    calculate_volume_profile(stock)

    bonus = 0
    if stock.score.get("mtf_alignment", 0) >= 100:
        bonus += 8
    elif stock.score.get("mtf_alignment", 0) >= 60:
        bonus += 4

    rs = stock.score.get("relative_strength", 50)
    if rs >= 70:
        bonus += 6
    elif rs <= 30:
        bonus -= 4

    sector_score = stock.score.get("sector", 50)
    if sector_score >= 80:
        bonus += 5
    elif sector_score <= 40:
        bonus -= 3

    vp_score = stock.score.get("volume_profile", 50)
    if vp_score >= 70:
        bonus += 4

    bonus = max(-10, min(25, bonus))
    stock.add_indicator("BATCH1_CONFIDENCE_BONUS", bonus)
    stock.score["batch1_bonus"] = bonus
    return bonus


# =====================================================
# PHASE 2 - BATCH 2
# False Breakout Detection / Smart Money Concepts /
# Institutional Activity / News & Earnings Filter /
# AI Confidence Engine
# =====================================================

# Configurable weights: how much each Batch 2 engine moves the final
# AI Confidence score. Tune these without touching engine logic.
BATCH2_WEIGHTS = {
    "smart_money": 1.0,
    "institutional": 0.4,
    "false_breakout": 1.0,
    "news_earnings": 1.0,
}

NEWS_EARNINGS_WARNING_DAYS = 5

# Populated once per scan by prefetch_news_earnings(); avoids one
# network round-trip per symbol inside the hot per-symbol loop.
news_earnings_cache = {}

# ----------------------------------------------------------------
# News/Earnings prefetch throttling layer
# ----------------------------------------------------------------
# Yahoo Finance rate-limits aggressively at scale (observed during the
# 800-symbol Batch 2 stress test). This layer adds a disk-backed TTL
# cache (so a rescan within the TTL window makes zero network calls),
# a global request-pacing gate shared across worker threads (so we
# never exceed a fixed requests/second ceiling regardless of
# MAX_WORKERS), and per-request exponential backoff with jitter on
# failure/rate-limit. Every outcome (cache hit, retry, rate-limit,
# permanent failure) is counted and logged; nothing here is allowed to
# raise back into the scan pipeline - on total failure a symbol simply
# gets a neutral {"days_to_earnings": None, "recent_headlines": []}.

import json
import random
import threading

NEWS_EARNINGS_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".cache", "news_earnings_cache.json"
)

NEWS_EARNINGS_CACHE_TTL_SECONDS = 3600  # 1 hour - balances freshness vs. request volume

NEWS_EARNINGS_MAX_REQUESTS_PER_SECOND = 4  # global ceiling, independent of MAX_WORKERS

NEWS_EARNINGS_MAX_RETRIES = 3

NEWS_EARNINGS_BACKOFF_BASE_SECONDS = 1.0

_news_earnings_rate_lock = threading.Lock()
_news_earnings_last_request_time = [0.0]

_news_earnings_stats_lock = threading.Lock()


def _news_earnings_rate_gate():
    # Global pacing gate: blocks the calling thread until issuing another
    # request would not exceed NEWS_EARNINGS_MAX_REQUESTS_PER_SECOND,
    # regardless of how many worker threads are running concurrently.
    min_interval = 1.0 / NEWS_EARNINGS_MAX_REQUESTS_PER_SECOND

    with _news_earnings_rate_lock:

        now = time.time()

        elapsed = now - _news_earnings_last_request_time[0]

        wait = min_interval - elapsed

        if wait > 0:
            time.sleep(wait)

        _news_earnings_last_request_time[0] = time.time()


def _news_earnings_is_rate_limit_error(exc):

    msg = str(exc).lower()

    return "429" in msg or "too many requests" in msg or "rate limit" in msg


def _news_earnings_load_disk_cache():

    try:
        if os.path.exists(NEWS_EARNINGS_CACHE_FILE):

            with open(NEWS_EARNINGS_CACHE_FILE, "r") as f:
                return json.load(f)

    except Exception as e:
        logging.warning(f"NEWS_EARNINGS_CACHE load failed err={e}")

    return {}


def _news_earnings_save_disk_cache(cache):

    try:
        os.makedirs(os.path.dirname(NEWS_EARNINGS_CACHE_FILE), exist_ok=True)

        with open(NEWS_EARNINGS_CACHE_FILE, "w") as f:
            json.dump(cache, f)

    except Exception as e:
        logging.warning(f"NEWS_EARNINGS_CACHE save failed err={e}")


def detect_false_breakout(stock, check_window=5):
    """
    Flags breakouts that already failed (price broke the resistance
    level in the recent past, then closed back below it), plus
    exhaustion on the CURRENT breakout candle (weak close, low volume).
    Returns a confidence penalty (<= 0).
    """
    df = stock.data

    if df is None or len(df) < BREAKOUT_LOOKBACK + check_window + 5:
        stock.patterns["FALSE_BREAKOUT"] = False
        return 0

    false_breakout = False

    n = len(df)

    start = max(BREAKOUT_LOOKBACK + 1, n - check_window - 5)

    for idx in range(start, n):

        resistance = df["High"].iloc[idx - BREAKOUT_LOOKBACK:idx].max()

        breakout_price = resistance * (1 + BREAKOUT_BUFFER)

        candle = df.iloc[idx]

        if candle["Close"] >= breakout_price:

            after = df.iloc[idx + 1: idx + 1 + check_window]

            if len(after) and (after["Close"] < resistance).any():
                false_breakout = True
                break

    last = df.iloc[-1]

    exhaustion = False

    if stock.patterns.get("BREAKOUT_READY"):

        candle_range = last["High"] - last["Low"]

        if candle_range > 0:

            close_position = (last["Close"] - last["Low"]) / candle_range

            if close_position <= 0.3 and last.get("RVOL", 1) < 1.2:
                exhaustion = True

    penalty = 0

    if false_breakout:
        penalty -= 15
        stock.add_reason(
            "[FalseBreakout] Prior breakout failed - price reclaimed below resistance"
        )

    if exhaustion:
        penalty -= 8
        stock.add_reason(
            "[FalseBreakout] Exhaustion candle on breakout - weak close, low volume"
        )

    stock.patterns["FALSE_BREAKOUT"] = false_breakout
    stock.patterns["BREAKOUT_EXHAUSTION"] = exhaustion
    stock.score["false_breakout_penalty"] = penalty

    logging.info(
        f"FALSE_BREAKOUT symbol={stock.symbol} false_breakout={false_breakout} "
        f"exhaustion={exhaustion} penalty={penalty}"
    )

    return penalty


def analyze_smart_money_concepts(stock):
    """
    Aggregates the Smart Money Concept patterns that already run earlier
    in the pipeline (BOS/CHOCH via update_market_structure(), Order
    Blocks / Liquidity Sweeps / Fair Value Gaps via their strategy
    registry entries) into a single explainable score. Must be called
    AFTER run_all_strategies(stock) so those patterns are populated.
    """
    score = 0

    if stock.patterns.get("BOS"):
        score += 15
        stock.add_reason("[SmartMoney] Break of Structure (bullish)")

    if stock.patterns.get("BEARISH_BOS"):
        score -= 10
        stock.add_reason("[SmartMoney] Bearish Break of Structure")

    if stock.patterns.get("CHOCH"):
        score += 8
        stock.add_reason("[SmartMoney] Change of Character (possible trend shift)")

    bullish_ob = len(stock.patterns.get("BULLISH_ORDER_BLOCKS", []))
    bearish_ob = len(stock.patterns.get("BEARISH_ORDER_BLOCKS", []))

    if bullish_ob:
        score += min(bullish_ob * 3, 9)
        stock.add_reason(
            f"[SmartMoney] {bullish_ob} Bullish Order Block(s) identified"
        )

    if bearish_ob > bullish_ob:
        score -= 5
        stock.add_reason("[SmartMoney] Bearish Order Blocks dominate")

    if stock.patterns.get("BULLISH_SWEEP"):
        score += 10
        stock.add_reason("[SmartMoney] Bullish Liquidity Sweep (stop hunt reversal)")

    if stock.patterns.get("BEARISH_SWEEP"):
        score -= 6
        stock.add_reason("[SmartMoney] Bearish Liquidity Sweep")

    bullish_fvg = len(stock.patterns.get("BULLISH_FVG", []))
    bearish_fvg = len(stock.patterns.get("BEARISH_FVG", []))

    if bullish_fvg:
        score += min(bullish_fvg * 2, 6)
        stock.add_reason(
            f"[SmartMoney] {bullish_fvg} Bullish Fair Value Gap(s) unfilled"
        )

    if bearish_fvg > bullish_fvg:
        score -= 3

    score = max(-15, min(30, score))

    stock.add_indicator("SMART_MONEY_SCORE", score)
    stock.score["smart_money"] = score

    logging.info(
        f"SMART_MONEY symbol={stock.symbol} score={score} "
        f"bos={stock.patterns.get('BOS', False)} choch={stock.patterns.get('CHOCH', False)} "
        f"bullish_ob={bullish_ob} bearish_ob={bearish_ob} "
        f"bullish_sweep={stock.patterns.get('BULLISH_SWEEP', False)} "
        f"bearish_sweep={stock.patterns.get('BEARISH_SWEEP', False)} "
        f"bullish_fvg={bullish_fvg} bearish_fvg={bearish_fvg}"
    )

    return score


def analyze_institutional_activity(stock, lookback=20):
    """
    NSE delivery-percentage / bulk-and-block-deal data is not available
    through the yfinance data source this app uses, so institutional
    activity is approximated from price/volume behaviour instead:
    On-Balance Volume trend, a Chaikin-style Accumulation/Distribution
    Line, volume Z-score anomalies, and high-volume narrow-range
    'absorption' candles. This is a documented proxy, not delivery %.
    """
    df = stock.data

    if df is None or len(df) < lookback + 5:
        stock.score["institutional"] = 50
        return 50

    recent = df.iloc[-(lookback + 1):]

    close = recent["Close"]
    volume = recent["Volume"]
    high = recent["High"]
    low = recent["Low"]

    obv = [0.0]

    for i in range(1, len(recent)):

        if close.iloc[i] > close.iloc[i - 1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i - 1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])

    obv_rising = (obv[-1] - obv[0]) > 0

    price_range = (high - low).replace(0, np.nan)

    mfm = ((close - low) - (high - close)) / price_range
    mfm = mfm.fillna(0)

    adl = (mfm * volume).cumsum()

    adl_trend = float(adl.iloc[-1] - adl.iloc[0])

    vol_mean = volume.iloc[:-1].mean()
    vol_std = volume.iloc[:-1].std()

    if vol_std and vol_std > 0:
        vol_z = float((volume.iloc[-1] - vol_mean) / vol_std)
    else:
        vol_z = 0.0

    last_range = float(high.iloc[-1] - low.iloc[-1])
    avg_range = float((high - low).iloc[:-1].mean())

    absorption = False

    if vol_z >= 2 and avg_range > 0 and last_range <= avg_range * 0.7:

        close_pos = (
            (close.iloc[-1] - low.iloc[-1]) / last_range
            if last_range > 0 else 0.5
        )

        if close_pos >= 0.6:
            absorption = True

    score = 50

    if obv_rising and adl_trend > 0:
        score += 15
        stock.add_reason(
            "[Institutional] OBV and Accumulation/Distribution both rising (buying pressure)"
        )
    elif (not obv_rising) and adl_trend < 0:
        score -= 15
        stock.add_reason(
            "[Institutional] OBV and Accumulation/Distribution both falling (distribution pressure)"
        )
    elif obv_rising or adl_trend > 0:
        score += 6
    else:
        score -= 6

    if vol_z >= 2:
        score += 8
        stock.add_reason(
            f"[Institutional] Unusual volume spike (z={round(vol_z, 1)}) - possible institutional activity"
        )

    if absorption:
        score += 10
        stock.add_reason(
            "[Institutional] High-volume narrow-range absorption candle detected"
        )

    score = max(0, min(100, score))

    stock.add_indicator("OBV_TREND", "RISING" if obv_rising else "FALLING")
    stock.add_indicator("ADL_TREND", round(adl_trend, 2))
    stock.add_indicator("VOLUME_ZSCORE", round(vol_z, 2))
    stock.add_indicator("ABSORPTION_DAY", absorption)
    stock.score["institutional"] = score

    logging.info(
        f"INSTITUTIONAL_ACTIVITY symbol={stock.symbol} score={score} "
        f"obv_trend={'RISING' if obv_rising else 'FALLING'} "
        f"adl_trend={round(adl_trend, 2)} vol_z={round(vol_z, 2)} absorption={absorption}"
    )

    return score


def prefetch_news_earnings(symbols):
    """
    Fetches earnings-calendar and recent-news data for every symbol in
    the scan ONCE, concurrently, before the per-symbol loop runs -
    exactly like fetch_nifty_benchmark() does for the RS benchmark.
    check_news_earnings_filter() then reads from this cache instead of
    making a network call per symbol inside the hot loop.

    Throttling layer (Batch 2 completion):
      - Disk-backed TTL cache: a symbol fetched within the last
        NEWS_EARNINGS_CACHE_TTL_SECONDS is served from disk with ZERO
        network calls.
      - Global rate gate: all worker threads share one pacing gate
        capping requests to NEWS_EARNINGS_MAX_REQUESTS_PER_SECOND,
        independent of CONFIG["MAX_WORKERS"].
      - Exponential backoff with jitter: on failure (rate-limit or
        transient error) a request is retried up to
        NEWS_EARNINGS_MAX_RETRIES times with delay
        base * 2**attempt + random jitter.
      - Total failure after retries never raises - the symbol gets a
        neutral entry ({"days_to_earnings": None, "recent_headlines": []})
        and the pipeline continues.
    """
    global news_earnings_cache

    disk_cache = _news_earnings_load_disk_cache()

    now_ts = time.time()

    stats = {
        "cache_hits": 0,
        "cache_misses": 0,
        "requests_attempted": 0,
        "retries": 0,
        "rate_limited": 0,
        "permanent_failures": 0,
    }

    fresh_cache = {}
    to_fetch = []

    for symbol in symbols:

        entry = disk_cache.get(symbol)

        if entry and (now_ts - entry.get("fetched_at", 0)) < NEWS_EARNINGS_CACHE_TTL_SECONDS:
            fresh_cache[symbol] = entry["data"]
            stats["cache_hits"] += 1
        else:
            to_fetch.append(symbol)
            stats["cache_misses"] += 1

    def _fetch_one(symbol):

        from datetime import date

        last_exc = None

        for attempt in range(NEWS_EARNINGS_MAX_RETRIES + 1):

            try:
                _news_earnings_rate_gate()

                with _news_earnings_stats_lock:
                    stats["requests_attempted"] += 1

                ticker = yf.Ticker(symbol)

                days_to_earnings = None

                try:
                    cal = ticker.calendar

                    earnings_dates = cal.get("Earnings Date") if isinstance(cal, dict) else None

                    if earnings_dates:

                        if not isinstance(earnings_dates, list):
                            earnings_dates = [earnings_dates]

                        today = date.today()

                        upcoming = [d for d in earnings_dates if d >= today]

                        if upcoming:
                            days_to_earnings = (min(upcoming) - today).days

                except Exception as e:
                    logging.warning(f"NEWS_EARNINGS calendar fetch failed symbol={symbol} err={e}")

                recent_headlines = []

                try:
                    from datetime import datetime as dt, timedelta, timezone

                    news_items = ticker.news or []

                    cutoff = dt.now(timezone.utc) - timedelta(hours=48)

                    for item in news_items[:10]:

                        content = item.get('content', item)

                        pub = content.get('pubDate')
                        title = content.get('title')

                        if not pub or not title:
                            continue

                        try:
                            pub_dt = dt.fromisoformat(pub.replace('Z', '+00:00'))
                        except Exception:
                            continue

                        if pub_dt >= cutoff:
                            recent_headlines.append(title)

                except Exception as e:
                    logging.warning(f"NEWS_EARNINGS news fetch failed symbol={symbol} err={e}")

                return symbol, {
                    "days_to_earnings": days_to_earnings,
                    "recent_headlines": recent_headlines,
                }

            except Exception as e:

                last_exc = e

                is_rate_limit = _news_earnings_is_rate_limit_error(e)

                with _news_earnings_stats_lock:
                    if is_rate_limit:
                        stats["rate_limited"] += 1

                if attempt < NEWS_EARNINGS_MAX_RETRIES:

                    with _news_earnings_stats_lock:
                        stats["retries"] += 1

                    delay = NEWS_EARNINGS_BACKOFF_BASE_SECONDS * (2 ** attempt) + random.uniform(0, 0.5)

                    logging.warning(
                        f"NEWS_EARNINGS retry symbol={symbol} attempt={attempt + 1} "
                        f"rate_limited={is_rate_limit} delay={round(delay, 2)}s err={e}"
                    )

                    time.sleep(delay)

                    continue

        with _news_earnings_stats_lock:
            stats["permanent_failures"] += 1

        logging.warning(
            f"NEWS_EARNINGS prefetch permanently failed symbol={symbol} "
            f"after {NEWS_EARNINGS_MAX_RETRIES} retries err={last_exc}"
        )

        return symbol, {"days_to_earnings": None, "recent_headlines": []}

    fetched_results = {}

    if to_fetch:

        fetch_workers = min(CONFIG["MAX_WORKERS"], NEWS_EARNINGS_MAX_REQUESTS_PER_SECOND * 2, len(to_fetch))
        fetch_workers = max(fetch_workers, 1)

        with ThreadPoolExecutor(max_workers=fetch_workers) as executor:

            for symbol, result in executor.map(_fetch_one, to_fetch):
                fetched_results[symbol] = result

    news_earnings_cache = {}
    news_earnings_cache.update(fresh_cache)
    news_earnings_cache.update(fetched_results)

    fetched_at = time.time()

    for symbol, result in fetched_results.items():
        disk_cache[symbol] = {"fetched_at": fetched_at, "data": result}

    stale_cutoff = fetched_at - (NEWS_EARNINGS_CACHE_TTL_SECONDS * 24)

    disk_cache = {
        sym: entry for sym, entry in disk_cache.items()
        if entry.get("fetched_at", 0) >= stale_cutoff
    }

    _news_earnings_save_disk_cache(disk_cache)

    cache_hit_ratio = (
        round(stats["cache_hits"] / len(symbols) * 100, 1) if symbols else 0.0
    )

    logging.info(
        f"NEWS_EARNINGS_PREFETCH symbols={len(symbols)} "
        f"cached={len(news_earnings_cache)} "
        f"cache_hits={stats['cache_hits']} cache_misses={stats['cache_misses']} "
        f"cache_hit_ratio={cache_hit_ratio}% "
        f"requests_attempted={stats['requests_attempted']} "
        f"retries={stats['retries']} rate_limited={stats['rate_limited']} "
        f"permanent_failures={stats['permanent_failures']}"
    )

    return stats
def check_news_earnings_filter(stock):
    """
    Reads the pre-fetched earnings/news cache for this symbol and turns
    it into a confidence penalty: heavy penalty for entries right before
    an earnings release, a lighter caution penalty for an unusually
    busy news cycle (higher volatility risk).
    """
    cached = news_earnings_cache.get(stock.symbol, {})

    days_to_earnings = cached.get("days_to_earnings")
    recent_headlines = cached.get("recent_headlines", [])

    stock.add_indicator("DAYS_TO_EARNINGS", days_to_earnings)
    stock.add_indicator("RECENT_NEWS_COUNT", len(recent_headlines))

    penalty = 0

    if days_to_earnings is not None and days_to_earnings <= NEWS_EARNINGS_WARNING_DAYS:
        penalty -= 15
        stock.add_news(
            "EARNINGS_WARNING",
            f"Earnings in {days_to_earnings} day(s) - avoid new entry"
        )
        stock.add_reason(
            f"[News/Earnings] Earnings in {days_to_earnings}d - confidence reduced, avoid fresh entries"
        )

    if len(recent_headlines) >= 3:
        penalty -= 3
        stock.add_news(
            "NEWS_VOLUME_WARNING",
            f"{len(recent_headlines)} news items in last 48h - elevated volatility risk"
        )
        stock.add_reason(
            f"[News/Earnings] {len(recent_headlines)} recent headlines - caution advised"
        )

    for i, headline in enumerate(recent_headlines[:3]):
        stock.add_news(f"HEADLINE_{i}", headline)

    penalty = max(-20, penalty)

    stock.score["news_earnings"] = penalty

    logging.info(
        f"NEWS_EARNINGS symbol={stock.symbol} days_to_earnings={days_to_earnings} "
        f"recent_news={len(recent_headlines)} penalty={penalty}"
    )

    return penalty


def run_batch2_signal_engines(stock):
    """
    Runs False Breakout Detection, Smart Money Concepts aggregation,
    Institutional Activity Analysis and the News/Earnings Filter for a
    single stock, combines them with BATCH2_WEIGHTS into one AI
    Confidence score (0-100) and a matching bonus/penalty intended to
    be added onto a trade candidate's ai_score inside
    build_ai_consensus() - exactly like run_batch1_signal_engines().
    Must be called AFTER run_all_strategies(stock) so BOS/CHOCH/Order
    Block/Liquidity Sweep/FVG patterns are already populated.
    """
    fb_penalty = detect_false_breakout(stock)
    sm_score = analyze_smart_money_concepts(stock)
    inst_score = analyze_institutional_activity(stock)
    news_penalty = check_news_earnings_filter(stock)

    bonus = 0.0

    bonus += sm_score * BATCH2_WEIGHTS["smart_money"]
    bonus += (inst_score - 50) * BATCH2_WEIGHTS["institutional"]
    bonus += fb_penalty * BATCH2_WEIGHTS["false_breakout"]
    bonus += news_penalty * BATCH2_WEIGHTS["news_earnings"]

    bonus = max(-30, min(30, round(bonus, 1)))

    ai_confidence = max(0, min(100, round(50 + bonus, 1)))

    stock.add_indicator("BATCH2_CONFIDENCE_BONUS", bonus)
    stock.add_indicator("AI_CONFIDENCE", ai_confidence)
    stock.score["batch2_bonus"] = bonus
    stock.score["ai_confidence"] = ai_confidence

    stock.add_reason(
        f"[AI Confidence Engine] {ai_confidence}/100 "
        f"(SmartMoney={sm_score}, Institutional={inst_score}, "
        f"FalseBreakout={fb_penalty}, News/Earnings={news_penalty})"
    )

    logging.info(
        f"AI_CONFIDENCE symbol={stock.symbol} ai_confidence={ai_confidence} "
        f"bonus={bonus} smart_money={sm_score} institutional={inst_score} "
        f"false_breakout_penalty={fb_penalty} news_earnings_penalty={news_penalty}"
    )

    return bonus


# ==========================================================
# EXECUTIVE MARKET DASHBOARD
# MODULE C - PART 1
# ==========================================================

def show_market_dashboard():

    st.divider()

    st.header("📊 AlphaQuant Executive Dashboard")

    total_scanned = len(st.session_state.market_data)

    qualified = len(st.session_state.trade_candidates)

    selected = len(st.session_state.selected_portfolio)

    open_positions = len(st.session_state.paper_positions)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Stocks Scanned",
        total_scanned
    )

    c2.metric(
        "Trade Candidates",
        qualified
    )

    c3.metric(
        "Portfolio",
        selected
    )

    c4.metric(
        "Live Positions",
        open_positions
    )

    st.divider()
def show_ai_summary():

    if len(st.session_state.final_trade_list)==0:

        return

    st.subheader("Top AI Opportunities")

    rows=[]

    for trade in st.session_state.final_trade_list[:10]:

        rows.append({

            "Rank":len(rows)+1,

            "Stock":trade.symbol,

            "Strategy":trade.strategy,

            "AI Score":round(trade.ai_score,2),

            "Confidence":trade.confidence,

            "RR":trade.risk_reward,

            "State":trade.state

        })

    st.dataframe(

        pd.DataFrame(rows),

        use_container_width=True,

        hide_index=True

    )
def show_portfolio_summary():

    st.subheader("Portfolio Allocation")

    if len(st.session_state.selected_portfolio)==0:

        st.info("No Portfolio")

        return

    rows=[]

    for trade in st.session_state.selected_portfolio:

        rows.append({

            "Stock":trade.symbol,

            "Weight %":trade.portfolio_weight,

            "Capital":trade.capital_required,

            "Entry":trade.entry,

            "Target":trade.target1,

            "RR":trade.risk_reward

        })

    st.dataframe(

        pd.DataFrame(rows),

        use_container_width=True,

        hide_index=True

    )
def show_live_positions():

    st.subheader("Live Positions")

    rows=[]

    for p in st.session_state.paper_positions.values():

        rows.append({

            "Stock":p.symbol,

            "Strategy":p.strategy,

            "Entry":p.entry,

            "Qty":p.quantity,

            "Status":p.status

        })

    if len(rows):

        st.dataframe(

            pd.DataFrame(rows),

            use_container_width=True,

            hide_index=True

        )

    else:

        st.info(

            "No Open Positions"

        )
# =====================================================
# ALPHAQUANT OS - PHASE 1 (READ-ONLY)
# =====================================================
# Brains 1-3 (Market Observer, Market Historian, Historical Analog Engine)
# are surfaced here purely as read-only context for a human to inspect.
# This panel never calls build_ai_consensus, never mutates scoring/ranking,
# and never gates or auto-vetoes a trade candidate - it only reports what
# AlphaQuant OS already knows. Any failure here is caught and shown as a
# warning so it can never break the existing scan/consensus workflow above.


def show_alphaquant_os_panel():

    with st.expander("AlphaQuant OS - Historical Context (Phase 1, read-only)"):

        try:
            from os_brains.db import apply_schema
            from os_brains.market_historian import get_regime_context, seed_regime_catalog
            from os_brains.market_observer import observe
            from os_brains.historical_analog_engine import find_analogs
            from os_brains.setup_vector import (
                build_setup_vector_row,
                compute_pattern_flag_series,
                compute_relative_strength_series,
            )
        except Exception as e:
            st.info(f"AlphaQuant OS modules unavailable: {e}")
            return

        # Idempotent bootstrap so this panel works on a clean environment
        # with zero manual DB prep - safe to call every render
        # (CREATE ... IF NOT EXISTS / ON CONFLICT DO UPDATE), gated on a
        # session flag so it only actually runs once per session.
        if not st.session_state.get("alphaquant_os_bootstrapped", False):
            try:
                apply_schema()
                seed_regime_catalog()
                st.session_state["alphaquant_os_bootstrapped"] = True
            except Exception as e:
                st.warning(f"AlphaQuant OS database bootstrap failed: {e}")
                return

        stocks = st.session_state.get("stock_objects", {})
        symbols_with_data = [
            s for s, obj in stocks.items() if obj.data is not None and len(obj.data)
        ]

        if not symbols_with_data:
            st.caption(
                "Run a scan first, then pick a scanned symbol here to see its "
                "regime context and closest historical analogs."
            )
            return

        symbol = st.selectbox(
            "Symbol",
            sorted(symbols_with_data),
            key="alphaquant_os_symbol_select",
        )

        stock = stocks[symbol]

        try:
            if "REGIME" not in stock.market:
                detect_market_regime(stock)

            regime_ctx = get_regime_context(stock)

            st.markdown(f"**Current regime:** {regime_ctx['current_regime']} "
                        f"(strength {regime_ctx['current_regime_strength']})")

            for entry in regime_ctx["nearest_historical_regimes"]:
                st.write(
                    f"- {entry['regime_name']} ({entry['date_range']}) - "
                    f"similarity {entry['similarity_score']} - {entry['how_it_resolved']}"
                )
        except Exception as e:
            st.warning(f"Market Historian unavailable: {e}")

        try:
            observation = observe(stock, sys.modules[__name__])
            st.caption(
                f"Sector: {observation['sector']['name']} | "
                f"Relative strength vs NIFTY: {observation['relative_strength']}"
            )
        except Exception as e:
            st.warning(f"Market Observer unavailable: {e}")

        try:
            nifty_df = nifty_benchmark_df
            if nifty_df is None:
                fetch_nifty_benchmark()
                nifty_df = nifty_benchmark_df

            if nifty_df is not None:
                flags = compute_pattern_flag_series(stock.data)
                rs_series = compute_relative_strength_series(stock.data, nifty_df)
                vector = build_setup_vector_row(
                    stock.data, len(stock.data) - 1, flags, rs_series
                )
                if vector is not None:
                    report = find_analogs(
                        symbol, vector, as_of_date=stock.data.index[-1].date()
                    )
                    if report["matched_analogs_count"] > 0:
                        st.markdown(
                            f"**Closest historical analogs:** "
                            f"{report['matched_analogs_count']} matches "
                            f"({report['sample_confidence']} confidence)"
                        )
                        st.write(
                            f"- Typical holding period: {report['typical_holding_period_days']}d | "
                            f"Win rate: {round(report['win_rate'] * 100, 1)}% | "
                            f"Expected return: {round(report['expected_return'] * 100, 2)}% | "
                            f"Expected drawdown: {round(report['expected_drawdown'] * 100, 2)}%"
                        )
                        st.caption(
                            "For context only - Phase 1 does not feed this into "
                            "trade scoring, ranking, or vetoes."
                        )
                    else:
                        st.caption(
                            "No sufficiently similar historical setups found yet "
                            "(backfilled dataset is still small in Phase 1)."
                        )
        except Exception as e:
            st.warning(f"Historical Analog Engine unavailable: {e}")


def show_mission_control():
    st.divider()
    st.header("Mission Control")

    if st.session_state.get("last_cycle_time"):
        st.caption(
            f"Last run: {st.session_state.last_cycle_time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"({st.session_state.get('last_cycle_trigger', 'UNKNOWN')})"
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Universe", len(st.session_state.get("scan_universe", [])))
    c2.metric("Downloaded", len(st.session_state.get("market_data", {})))
    c3.metric("Candidates", len(st.session_state.get("trade_candidates", {})))
    c4.metric("Final Trades", len(st.session_state.get("selected_portfolio", [])))

    tab_progress, tab_funnel, tab_trades, tab_learning, tab_portfolio = st.tabs([
        "Live Progress", "Decision Funnel", "Final Trades", "Learning & Reviewer", "Portfolio"
    ])

    with tab_progress:
        if st.session_state.get("brain_status"):
            st.dataframe(
                pd.DataFrame([
                    {"Brain/Stage": k, "Status": v}
                    for k, v in st.session_state.brain_status.items()
                ]),
                use_container_width=True,
            )
        if st.session_state.get("pipeline_events"):
            st.dataframe(pd.DataFrame(st.session_state.pipeline_events), use_container_width=True)
        else:
            st.info("Press RUN ALPHAQUANT to start the complete workflow.")

    with tab_funnel:
        if st.session_state.get("decision_funnel"):
            st.dataframe(pd.DataFrame(st.session_state.decision_funnel), use_container_width=True)
        else:
            st.info("Decision funnel will populate after RUN ALPHAQUANT.")
        if not st.session_state.get("selected_portfolio") and st.session_state.get("no_trade_explanation"):
            st.warning("No trade today.")
            for reason in st.session_state.no_trade_explanation:
                st.write(f"- {reason}")

    with tab_trades:
        final_df = get_final_trade_dataframe()
        if len(final_df):
            st.dataframe(final_df, use_container_width=True)
        elif st.session_state.get("no_trade_explanation"):
            st.warning("No trade today.")
            for reason in st.session_state.no_trade_explanation:
                st.write(f"- {reason}")
        else:
            st.info("Final trades will appear after the pipeline completes.")

    with tab_learning:
        st.subheader("Learning Updates")
        if st.session_state.get("no_trade_explanation"):
            for reason in st.session_state.no_trade_explanation:
                st.write(f"- {reason}")
        st.subheader("Reviewer Output")
        if st.session_state.get("closed_positions"):
            st.write(f"Closed positions available for reviewer: {len(st.session_state.closed_positions)}")
        else:
            st.caption("No closed paper trades have reached reviewer yet.")

    with tab_portfolio:
        pdf = portfolio_dataframe()
        if len(pdf):
            st.dataframe(pdf, use_container_width=True)
        else:
            st.caption("No allocated portfolio positions from the latest run.")


show_mission_control()

# =====================================================
# 6-TAB CONTENT ROUTER (final render area)
# =====================================================
# Each show_* function below already renders a self-contained section.
# We route them to the six tabs the user selected via the top nav bar.
# Everything ABOVE this line ran unconditionally (engines + Scan Manager
# filters + RUN button + pipeline) so the one-click behaviour is preserved.

if _P("Dashboard"):
    show_market_dashboard()
    show_portfolio_summary()
    show_ai_summary()

elif _P("Scanner"):
    st.subheader("🔭 Scanner")
    st.caption(
        "The Scan Manager filters (Universe / Cap / Price / Volume / Turnover / "
        "Sector / Style) are rendered above at the top of the app. Adjust them "
        "and click 🚀 RUN ALPHAQUANT on the Dashboard tab to execute the full "
        "pipeline."
    )
    with st.expander("Current Scan Universe", expanded=True):
        _current = st.session_state.get("scan_universe", []) or []
        if _current:
            st.metric("Symbols in scan list", f"{len(_current):,}")
            st.dataframe(
                pd.DataFrame({"Symbol": _current[:500]}),
                use_container_width=True,
                hide_index=True,
            )
            if len(_current) > 500:
                st.caption(f"Showing first 500 of {len(_current):,} symbols.")
        else:
            st.info("No scan list built yet. Click 🚀 RUN ALPHAQUANT on the Dashboard tab.")

elif _P("AI"):
    show_ai_summary()
    st.divider()
    if st.session_state.get("final_trade_list"):
        show_ai_consensus()
    else:
        st.info("AI Consensus results appear here after the pipeline runs.")

elif _P("Portfolio"):
    show_portfolio_summary()
    st.divider()
    show_portfolio_dashboard()

elif _P("Paper Trading"):
    show_live_positions()

elif _P("Settings"):
    show_alphaquant_os_panel()

if st.session_state.run_complete_scan_requested:

    st.session_state.run_complete_scan_requested = False

    execute_scan_pipeline()

    st.session_state.last_cycle_message = (
        f"{len(st.session_state.final_trade_list)} trade candidate(s), "
        f"{len(st.session_state.paper_positions)} open position(s)."
    )

    if len(st.session_state.final_trade_list):

        # After a pipeline run, always show the ranked results and the
        # allocation, regardless of which tab the user is on - this is
        # the "here's what just happened" summary the user expects to
        # see right after pressing RUN.
        show_ai_consensus()

        show_allocated_portfolio()

    else:

        st.warning("No trade today.")
        for reason in _collect_no_trade_explanation():
            st.write(f"- {reason}")

# =====================================================
# AUTONOMOUS TRADING LOOP
# =====================================================
# Streamlit has no always-on background process - a script only runs
# while a session is connected, so "autonomous" here means "keeps
# scanning/monitoring on its own for as long as this AlphaQuant tab
# stays open", using st.fragment(run_every=...) (the Streamlit-native
# replacement for a manual while/sleep loop) rather than a blocking
# while True loop or an OS-level background process. That is an inherent
# constraint of Streamlit's request/response execution model, not a bug
# in this feature.

MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)

MONITOR_INTERVAL_SECONDS = 20
SCAN_INTERVAL_SECONDS = 300

IST = ZoneInfo("Asia/Kolkata")


def is_market_open(now=None):
    """
    NSE cash market hours: 09:15-15:30 IST, Monday-Friday. No holiday
    calendar is consulted (out of scope) - a market holiday will still
    read as "open" here, same limitation the rest of the app already has
    since nothing else checks holidays either.
    """

    now = now or datetime.now(IST)

    if now.weekday() >= 5:
        return False

    open_time = now.replace(
        hour=MARKET_OPEN[0], minute=MARKET_OPEN[1], second=0, microsecond=0
    )

    close_time = now.replace(
        hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1], second=0, microsecond=0
    )

    return open_time <= now <= close_time


def quick_refresh_open_positions():
    """
    Lightweight per-tick check, independent of a full rescan: pulls just
    the latest price for every symbol with an open paper position (via
    the same cheap fetch_quote_snapshot() the Scan Manager uses) and
    checks stop-loss/target hits against it immediately, instead of
    waiting for the next full pipeline cycle. Trailing-stop
    recalculation needs EMA20/ATR from a full indicator recompute, so
    that still only happens inside the full pipeline cycle via
    monitor_open_positions() - this only re-checks the existing
    stop/target levels against a fresh price so a hit is never missed
    for SCAN_INTERVAL_SECONDS at a time.
    """

    positions = st.session_state.paper_positions

    if not positions:
        return

    quotes = fetch_quote_snapshot(list(positions.keys()))

    for symbol, position in list(positions.items()):

        quote = quotes.get(symbol)

        if not quote or quote.get("price") is None:
            continue

        update_position_price(position, quote["price"])

        closed = check_stop_loss(position)

        if not closed:
            check_target1(position)
            check_target2(position)
            check_target3(position)

        update_position_statistics(position)

        if position.status == "CLOSED":
            archive_closed_position(position)
            remove_open_position(symbol)


st.divider()

st.subheader("Autonomous Trading Loop")

st.caption(
    "Runs the Scan Manager's chosen universe through the full pipeline "
    "and monitors open positions on its own while the market is open and "
    "this tab stays connected. It reuses run_automated_cycle() - the same "
    "code path 'RUN ALPHAQUANT' uses - so there is one pipeline, "
    "triggered manually or automatically."
)

col_auto_a, col_auto_b = st.columns(2)

with col_auto_a:

    if not st.session_state.autonomous_active:

        if st.button("Start Autonomous Mode"):

            if not st.session_state.scan_universe:
                st.warning(
                    "Build a scan list in Scan Manager above before "
                    "starting autonomous mode."
                )
            else:
                st.session_state.autonomous_active = True
                st.rerun()

    else:

        if st.button("Stop Autonomous Mode"):

            st.session_state.autonomous_active = False
            st.rerun()

with col_auto_b:

    st.metric(
        "Autonomous Mode",
        "RUNNING" if st.session_state.autonomous_active else "STOPPED",
    )


@st.fragment(run_every=MONITOR_INTERVAL_SECONDS)
def autonomous_loop_fragment():

    if not st.session_state.autonomous_active:
        st.caption("Autonomous mode is stopped.")
        return

    now_ist = datetime.now(IST)

    if not is_market_open(now_ist):
        st.caption(
            f"Market closed ({now_ist.strftime('%H:%M:%S')} IST) - "
            "autonomous mode is armed but idle."
        )
        return

    quick_refresh_open_positions()

    due_for_full_cycle = (
        st.session_state.last_cycle_time is None
        or (datetime.now() - st.session_state.last_cycle_time).total_seconds()
        >= SCAN_INTERVAL_SECONDS
    )

    if due_for_full_cycle:

        ok, msg = run_automated_cycle(trigger="AUTONOMOUS")

        # run_automated_cycle() only sets run_complete_scan_requested so the
        # manual button (defined earlier in the script, before
        # execute_scan_pipeline itself exists yet) can defer to the bottom
        # of the file. A fragment rerun only re-executes this function's own
        # body, not that bottom block, so the pipeline has to be triggered
        # directly here - and the flag must be cleared right after, or it
        # would linger and cause a second, redundant execute_scan_pipeline()
        # call on the next full-page rerun.
        st.session_state.run_complete_scan_requested = False

        if ok:
            execute_scan_pipeline()

            st.session_state.last_cycle_message = (
                f"{len(st.session_state.final_trade_list)} trade candidate(s), "
                f"{len(st.session_state.paper_positions)} open position(s)."
            )
        else:
            st.session_state.last_cycle_message = msg

    if st.session_state.last_cycle_time:

        st.caption(
            f"Last full cycle: "
            f"{st.session_state.last_cycle_time.strftime('%H:%M:%S')} "
            f"({st.session_state.last_cycle_trigger}) - "
            f"{len(st.session_state.paper_positions)} open position(s) "
            f"monitored every {MONITOR_INTERVAL_SECONDS}s. "
            f"{st.session_state.last_cycle_message}"
        )

    else:

        st.caption("Waiting for the first autonomous cycle...")


autonomous_loop_fragment()

# =====================================================
# LIVE MARKET ENGINE
# VERSION 1.0.0
# =====================================================
# Turns AlphaQuant from a one-shot scanner into a continuous market
# monitor. Downloads history ONCE per session, then polls only the
# newest completed candle for the selected interval and re-runs the
# existing pipeline (strategies -> AI -> Risk -> Portfolio -> Paper
# Trades) on the updated cache. All existing engines are reused
# unchanged; nothing about strategy, AI, risk, portfolio or paper
# trading logic is duplicated here.
#
# Provider abstraction: MarketDataProvider is an ABC so the yfinance
# implementation can later be swapped for a broker WebSocket feed
# (Upstox, Zerodha, etc.) without touching any downstream engine.

from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    """
    Contract every market-data source must implement. yfinance today,
    Upstox/Zerodha/etc. tomorrow - the LiveMarketEngine only knows this
    interface.
    """

    @abstractmethod
    def download_history(self, symbols, interval, period):
        """Return {symbol: DataFrame} - full history for each symbol."""

    @abstractmethod
    def fetch_latest_batch(self, symbols, interval):
        """Return {symbol: DataFrame} with just the last few candles."""

    @abstractmethod
    def is_market_open(self, now=None):
        """Return True iff the market is currently open."""


class YFinanceProvider(MarketDataProvider):
    """yfinance-backed provider. Wraps the existing download plumbing."""

    _PERIOD_FOR_INTERVAL = {
        "1m": "5d", "5m": "1mo", "15m": "1mo",
        "30m": "1mo", "1h": "3mo", "1d": "1y",
    }

    def download_history(self, symbols, interval, period=None):
        period = period or self._PERIOD_FOR_INTERVAL.get(interval, "1y")
        try:
            data = yf.download(
                tickers=" ".join(symbols) if len(symbols) > 1 else symbols[0],
                period=period,
                interval=interval,
                group_by="ticker",
                progress=False,
                threads=True,
                auto_adjust=False,
            )
        except Exception as exc:
            logging.warning("LIVE download_history failed: %s", exc)
            return {}
        out = {}
        if len(symbols) == 1:
            df = data.dropna(how="all")
            if not df.empty:
                out[symbols[0]] = df
            return out
        for sym in symbols:
            try:
                sub = data[sym].dropna(how="all")
                if not sub.empty:
                    out[sym] = sub
            except Exception:
                continue
        return out

    def fetch_latest_batch(self, symbols, interval):
        # Short-period pull is enough to grab the last N candles for each
        # symbol; we then slice to just the newest candle per symbol in
        # LiveMarketCache.append_from_batch.
        short_period = "1d" if interval in ("1m", "5m", "15m", "30m", "1h") else "5d"
        return self.download_history(symbols, interval, short_period)

    def is_market_open(self, now=None):
        return is_market_open(now)


class LiveMarketCache:
    """
    Per-symbol OHLCV cache. `initialize()` fills it once from a
    provider.download_history(); subsequent `append_from_batch()` calls
    only add new candles (no duplicate rows, no re-download of history).
    """

    def __init__(self):
        self.data = {}
        self.last_updated = {}
        self.new_candle_symbols = set()

    def initialize(self, provider, symbols, interval, period=None):
        history = provider.download_history(symbols, interval, period)
        self.data = history
        now = datetime.now()
        self.last_updated = {sym: now for sym in history}
        self.new_candle_symbols = set(history.keys())
        return len(history)

    def append_from_batch(self, batch):
        """
        Merge new-candle rows in-place. Returns the set of symbols that
        received a truly new candle (i.e. a bar not already in cache).
        """
        self.new_candle_symbols = set()
        for sym, incoming in batch.items():
            if incoming is None or incoming.empty:
                continue
            cached = self.data.get(sym)
            if cached is None or cached.empty:
                self.data[sym] = incoming
                self.new_candle_symbols.add(sym)
                self.last_updated[sym] = datetime.now()
                continue
            last_ts = cached.index[-1]
            new_rows = incoming[incoming.index > last_ts]
            if new_rows.empty:
                continue
            self.data[sym] = pd.concat([cached, new_rows])
            self.new_candle_symbols.add(sym)
            self.last_updated[sym] = datetime.now()
        return self.new_candle_symbols

    def snapshot(self):
        return dict(self.data)


class LiveMarketEngine:
    """
    Orchestrator. `initialize_session()` downloads history once; every
    `tick()` fetches only the latest candle and re-executes the
    downstream pipeline on symbols whose cache actually advanced.
    """

    _INTERVAL_SECONDS = {
        "1m": 60, "5m": 300, "15m": 900,
        "30m": 1800, "1h": 3600, "1d": 24 * 3600,
    }

    def __init__(self, provider):
        self.provider = provider
        self.cache = LiveMarketCache()
        self.symbols = []
        self.interval = "5m"
        self.session_id = None
        self.last_tick_time = None
        self.last_tick_stats = {}
        self.total_ticks = 0

    def is_initialized(self):
        return bool(self.symbols) and bool(self.cache.data)

    def initialize_session(self, symbols, interval):
        self.symbols = list(symbols)
        self.interval = interval
        n = self.cache.initialize(self.provider, self.symbols, interval)
        # Hand the initialised cache to the rest of the app so the
        # existing pipeline (which reads st.session_state.market_data)
        # sees the same DataFrames.
        st.session_state.market_data = self.cache.snapshot()
        self.session_id = datetime.now().isoformat()
        return n

    def next_candle_seconds(self):
        """Approximate seconds until the next candle boundary."""
        sec = self._INTERVAL_SECONDS.get(self.interval, 300)
        if not self.last_tick_time:
            return sec
        elapsed = (datetime.now() - self.last_tick_time).total_seconds()
        return max(0, int(sec - elapsed))

    def tick(self):
        """
        One monitoring iteration: fetch newest candles, update cache,
        re-run the existing pipeline (execute_scan_pipeline) on the
        refreshed data so all downstream engines (strategies, AI, risk,
        portfolio, paper) run against the new bar.
        """
        if not self.is_initialized():
            return {"status": "not_initialized"}

        if not self.provider.is_market_open():
            return {"status": "market_closed"}

        batch = self.provider.fetch_latest_batch(self.symbols, self.interval)
        changed = self.cache.append_from_batch(batch)

        stats = {
            "status": "ok",
            "polled": len(batch),
            "new_candle_symbols": sorted(list(changed)),
            "candles_added": len(changed),
            "tick_time": datetime.now(),
        }

        if changed:
            # Hand the refreshed cache to the pipeline
            st.session_state.market_data = self.cache.snapshot()
            try:
                execute_scan_pipeline()
                stats["pipeline"] = "executed"
                stats["open_positions"] = len(st.session_state.paper_positions)
                stats["closed_positions"] = len(
                    st.session_state.get("paper_history", [])
                )
            except Exception as exc:
                stats["pipeline"] = f"error: {exc}"
                logging.warning("LIVE pipeline execution failed: %s", exc)
        else:
            # Even with no new candles we still trail-stop / monitor exits
            try:
                monitor_open_positions()
                stats["monitored_only"] = True
            except Exception as exc:
                logging.warning("LIVE monitor_only failed: %s", exc)

        self.last_tick_time = stats["tick_time"]
        self.total_ticks += 1
        self.last_tick_stats = stats
        return stats

    def status(self):
        realised_pnl = sum(
            (t.pnl or 0) for t in st.session_state.get("paper_history", [])
            if getattr(t, "closed_at", None)
            and getattr(t, "closed_at").date() == datetime.now().date()
        )
        unrealised_pnl = sum(
            ((p.last_price or p.entry or 0) - (p.entry or 0)) * (p.quantity or 0)
            for p in st.session_state.paper_positions.values()
        )
        return {
            "initialized": self.is_initialized(),
            "interval": self.interval,
            "symbols_monitored": len(self.symbols),
            "market_open": self.provider.is_market_open(),
            "last_tick": self.last_tick_time,
            "total_ticks": self.total_ticks,
            "next_candle_seconds": self.next_candle_seconds(),
            "open_positions": len(st.session_state.paper_positions),
            "closed_positions_today": sum(
                1 for t in st.session_state.get("paper_history", [])
                if getattr(t, "closed_at", None)
                and getattr(t, "closed_at").date() == datetime.now().date()
            ),
            "realised_pnl_today": realised_pnl,
            "unrealised_pnl": unrealised_pnl,
        }


# ------------------------ Live engine session bootstrap ------------------
if "live_engine" not in st.session_state:
    st.session_state.live_engine = LiveMarketEngine(YFinanceProvider())

if "live_enabled" not in st.session_state:
    st.session_state.live_enabled = False

if "live_interval" not in st.session_state:
    st.session_state.live_interval = "5m"

# ------------------------ Live Market UI (rendered on Dashboard tab) ------
if _P("Dashboard"):
    st.divider()
    st.subheader("Live Market Engine")

    _engine = st.session_state.live_engine
    _status = _engine.status()

    _cfg_cols = st.columns([1, 1, 1, 2])

    _cfg_cols[0].selectbox(
        "Interval",
        options=["1m", "5m", "15m", "30m", "1h", "1d"],
        key="live_interval",
    )

    _cfg_cols[1].toggle(
        "Live monitoring",
        key="live_enabled",
        help="When ON, fetches only the newest candle for the current scan "
             "universe on every tick and re-runs the full pipeline "
             "(strategies -> AI -> Risk -> Portfolio -> Paper Trades). "
             "History is downloaded ONCE per session, not on every tick.",
    )

    if _cfg_cols[2].button("Initialize session", key="live_init_btn"):
        _syms = st.session_state.get("scan_universe") or []
        if not _syms:
            st.warning(
                "Live Market Engine needs a scan list first. Build one on the "
                "Scanner tab (Preview Scan List) or run any RUN ALPHAQUANT "
                "cycle to populate the universe."
            )
        else:
            with st.spinner(f"Downloading history for {len(_syms)} symbols..."):
                _n = _engine.initialize_session(_syms, st.session_state.live_interval)
            st.success(
                f"Live session initialised: {_n} symbols on {st.session_state.live_interval} "
                f"interval. History cached; only newest candle will be fetched from here on."
            )

    _next_secs = _status["next_candle_seconds"] if _status["initialized"] else 0
    _cfg_cols[3].metric(
        "Next candle in",
        f"{_next_secs // 60:02d}:{_next_secs % 60:02d}" if _status["initialized"] else "--:--",
    )

    _st_cols = st.columns(6)
    _st_cols[0].metric(
        "Live status",
        "🟢 RUNNING" if (st.session_state.live_enabled and _status["market_open"] and _status["initialized"])
        else ("🟡 ARMED" if st.session_state.live_enabled else "⚪ OFF"),
    )
    _st_cols[1].metric("Monitored", _status["symbols_monitored"])
    _st_cols[2].metric(
        "Last candle",
        _status["last_tick"].strftime("%H:%M:%S") if _status["last_tick"] else "-",
    )
    _st_cols[3].metric("Open positions", _status["open_positions"])
    _st_cols[4].metric(
        "Realised P&L (today)",
        f"₹{_status['realised_pnl_today']:,.0f}",
    )
    _st_cols[5].metric(
        "Unrealised P&L",
        f"₹{_status['unrealised_pnl']:,.0f}",
    )

    if _engine.last_tick_stats:
        with st.expander("Last tick details"):
            _lt = _engine.last_tick_stats
            st.write(f"**Status:** `{_lt.get('status')}`")
            st.write(f"**Time:** {_lt.get('tick_time')}")
            st.write(f"**Candles added:** {_lt.get('candles_added', 0)}")
            if _lt.get("new_candle_symbols"):
                st.write(f"**New candle for:** {', '.join(_lt['new_candle_symbols'][:20])}"
                         + ("..." if len(_lt['new_candle_symbols']) > 20 else ""))
            st.write(f"**Pipeline:** {_lt.get('pipeline', '-')}")


# ------------------------ Live tick fragment ------------------------------
# Runs at the finest supported cadence (30s) but the tick() itself is a
# no-op unless the market is open, the engine is initialised, and live
# monitoring is enabled. We keep the fragment cadence FIXED and let the
# engine internally decide whether to actually do work; this is cheaper
# than re-mounting the fragment on every interval change.

_LIVE_TICK_SECONDS = 30

@st.fragment(run_every=_LIVE_TICK_SECONDS)
def live_market_tick_fragment():
    if not st.session_state.get("live_enabled"):
        return
    _engine = st.session_state.get("live_engine")
    if _engine is None or not _engine.is_initialized():
        return
    if not _engine.provider.is_market_open():
        return
    # Only tick if at least one candle-interval has elapsed since last tick
    interval_sec = LiveMarketEngine._INTERVAL_SECONDS.get(_engine.interval, 300)
    if _engine.last_tick_time:
        elapsed = (datetime.now() - _engine.last_tick_time).total_seconds()
        if elapsed < interval_sec:
            return
    _engine.tick()


live_market_tick_fragment()


# =====================================================
# BROKER PROVIDERS (Multi-broker WebSocket integration)
# VERSION 1.0.0
# =====================================================
# Concrete MarketDataProvider implementations for real Indian brokers.
# Each wraps the broker's official SDK/REST + WebSocket. Ticks are
# aggregated into candles matching the app's interval selection so ALL
# downstream engines (strategies, AI, risk, portfolio, paper) see the
# same DataFrame shape regardless of upstream provider.
#
# CREDENTIALS: no secrets are hard-coded. Users paste api_key / access_token
# on the Settings tab. Tokens live only in st.session_state for that session.
# =====================================================

INTERVAL_MINUTES_MAP = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "1d": 1440}


class CandleAggregator:
    """Rolls raw ticks into interval-bucketed OHLCV candles."""

    def __init__(self, interval: str):
        self.interval = interval
        self.current_start = None
        self.row = None
        self.prev_cum_volume = None

    def _floor_bucket(self, ts):
        mins = INTERVAL_MINUTES_MAP[self.interval]
        ts = ts if getattr(ts, "tzinfo", None) else ts.replace(tzinfo=IST)
        ts = ts.astimezone(IST)
        if mins == 1440:
            return datetime(ts.year, ts.month, ts.day, tzinfo=IST)
        bucket_min = (ts.minute // mins) * mins
        return ts.replace(minute=bucket_min, second=0, microsecond=0)

    def push(self, ts, price, qty=None, cum_volume=None):
        start = self._floor_bucket(ts)
        completed = None
        if self.current_start is None:
            self.current_start = start
            self.row = {"timestamp": start, "Open": price, "High": price,
                        "Low": price, "Close": price, "Volume": 0}
        elif start != self.current_start:
            completed = self.row
            self.current_start = start
            self.row = {"timestamp": start, "Open": price, "High": price,
                        "Low": price, "Close": price, "Volume": 0}
            self.prev_cum_volume = None
        self.row["High"] = max(self.row["High"], price)
        self.row["Low"] = min(self.row["Low"], price)
        self.row["Close"] = price
        if cum_volume is not None:
            delta = cum_volume if self.prev_cum_volume is None else max(cum_volume - self.prev_cum_volume, 0)
            self.prev_cum_volume = cum_volume
            self.row["Volume"] += delta
        elif qty is not None:
            self.row["Volume"] += int(qty)
        return completed

    def snapshot(self):
        return dict(self.row) if self.row else None


def _period_to_start(period: str, now=None):
    now = (now or datetime.now(IST)).astimezone(IST)
    n = int(''.join(c for c in period if c.isdigit()) or "1")
    unit = ''.join(c for c in period if c.isalpha()).lower()
    if unit.startswith("d"): return now - timedelta(days=n)
    if unit.startswith("mo"): return now - timedelta(days=30 * n)
    if unit in ("y", "yr", "year"): return now - timedelta(days=365 * n)
    return now - timedelta(days=n)


class UpstoxProvider(MarketDataProvider):
    """
    Upstox Uplink v3 provider. Historical via REST; live ticks via
    upstox-python-sdk MarketDataStreamerV3.
    Requires: pip install upstox-python-sdk requests
    Docs: https://upstox.com/developer/api-documentation/
    """

    UPSTOX_HIST = {"1m": ("minutes", 1), "5m": ("minutes", 5), "15m": ("minutes", 15),
                   "30m": ("minutes", 30), "1h": ("hours", 1), "1d": ("days", 1)}

    def __init__(self, api_key: str, access_token: str, symbol_map: dict):
        self.api_key = api_key
        self.access_token = access_token
        self.symbol_map = symbol_map
        self.aggregators = {sym: CandleAggregator("1m") for sym in symbol_map}
        self._streamer = None

    def is_market_open(self, now=None):
        return is_market_open(now)

    def download_history(self, symbols, interval, period="1y"):
        import requests as _rq
        unit, step = self.UPSTOX_HIST.get(interval, ("days", 1))
        end = datetime.now(IST).date()
        start = _period_to_start(period).date()
        headers = {"Accept": "application/json", "Authorization": "Bearer " + self.access_token}
        out = {}
        for sym in symbols:
            instrument_key = self.symbol_map.get(sym)
            if not instrument_key:
                continue
            url = ("https://api.upstox.com/v3/historical-candle/"
                   + instrument_key + "/" + unit + "/" + str(step)
                   + "/" + str(end) + "/" + str(start))
            try:
                r = _rq.get(url, headers=headers, timeout=20)
                r.raise_for_status()
                candles = r.json().get("data", {}).get("candles", [])
                if not candles:
                    continue
                cols = ["timestamp", "Open", "High", "Low", "Close", "Volume", "OI"][:len(candles[0])]
                df = pd.DataFrame(candles, columns=cols)
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(IST)
                df = df.set_index("timestamp").sort_index()
                out[sym] = df
            except Exception as exc:
                logging.warning("Upstox history failed for %s: %s", sym, exc)
        return out

    def fetch_latest_batch(self, symbols, interval):
        out = {}
        for sym in symbols:
            agg = self.aggregators.get(sym) or CandleAggregator(interval)
            snap = agg.snapshot()
            if snap:
                idx = pd.DatetimeIndex([snap.pop("timestamp")], name="timestamp")
                out[sym] = pd.DataFrame([snap], index=idx)
        return out

    def start_stream(self, symbols):
        import upstox_client
        conf = upstox_client.Configuration()
        conf.access_token = self.access_token
        api_client = upstox_client.ApiClient(conf)
        instrument_keys = [self.symbol_map[s] for s in symbols if s in self.symbol_map]
        self._streamer = upstox_client.MarketDataStreamerV3(
            api_client, instrumentKeys=instrument_keys, mode="ltpc",
        )
        self._streamer.on("message", self._on_message)
        self._streamer.connect()

    def _on_message(self, msg):
        for instrument_key, feed in (msg or {}).get("feeds", {}).items():
            ltpc = feed.get("ltpc") or feed.get("ff", {}).get("marketFF", {}).get("ltpc")
            if not ltpc:
                continue
            price, ts_raw = ltpc.get("ltp"), ltpc.get("ltt")
            if price is None or ts_raw is None:
                continue
            ts = pd.to_datetime(int(ts_raw), unit="ms", utc=True).tz_convert(IST).to_pydatetime()
            cum_vol = feed.get("vtt") or ltpc.get("vtt")
            for sym, key in self.symbol_map.items():
                if key == instrument_key:
                    self.aggregators[sym].push(ts, float(price),
                                               cum_volume=int(cum_vol) if cum_vol is not None else None)
                    break


class ZerodhaProvider(MarketDataProvider):
    """
    Zerodha Kite Connect provider. Historical via kiteconnect REST; live
    ticks via KiteTicker WebSocket.
    Requires: pip install kiteconnect
    Docs: https://kite.trade/docs/connect/v3/
    """

    KITE_HIST = {"1m": "minute", "5m": "5minute", "15m": "15minute",
                 "30m": "30minute", "1h": "60minute", "1d": "day"}

    def __init__(self, api_key: str, access_token: str, symbol_map: dict):
        self.api_key = api_key
        self.access_token = access_token
        self.symbol_map = symbol_map
        self.token_to_symbol = {int(v): k for k, v in symbol_map.items()}
        self.aggregators = {sym: CandleAggregator("1m") for sym in symbol_map}
        self._ticker = None
        self._kite = None

    def is_market_open(self, now=None):
        return is_market_open(now)

    def _kite_client(self):
        if self._kite is None:
            from kiteconnect import KiteConnect
            self._kite = KiteConnect(api_key=self.api_key)
            self._kite.set_access_token(self.access_token)
        return self._kite

    def download_history(self, symbols, interval, period="1y"):
        kite = self._kite_client()
        end = datetime.now(IST)
        start = _period_to_start(period, end)
        kite_interval = self.KITE_HIST.get(interval, "day")
        out = {}
        for sym in symbols:
            token = self.symbol_map.get(sym)
            if not token:
                continue
            try:
                rows = kite.historical_data(int(token), start, end, kite_interval, continuous=False, oi=False)
                if not rows:
                    continue
                df = pd.DataFrame(rows).rename(columns={
                    "date": "timestamp", "open": "Open", "high": "High",
                    "low": "Low", "close": "Close", "volume": "Volume",
                })
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(IST)
                df = df.set_index("timestamp").sort_index()
                out[sym] = df
            except Exception as exc:
                logging.warning("Zerodha history failed for %s: %s", sym, exc)
        return out

    def fetch_latest_batch(self, symbols, interval):
        out = {}
        for sym in symbols:
            agg = self.aggregators.get(sym) or CandleAggregator(interval)
            snap = agg.snapshot()
            if snap:
                idx = pd.DatetimeIndex([snap.pop("timestamp")], name="timestamp")
                out[sym] = pd.DataFrame([snap], index=idx)
        return out

    def start_stream(self, symbols):
        from kiteconnect import KiteTicker
        tokens = [int(self.symbol_map[s]) for s in symbols if s in self.symbol_map]
        self._ticker = KiteTicker(self.api_key, self.access_token)
        self._ticker.on_connect = lambda ws, resp: (
            self._ticker.subscribe(tokens),
            self._ticker.set_mode(self._ticker.MODE_FULL, tokens),
        )
        self._ticker.on_ticks = self._on_ticks
        self._ticker.auto_reconnect(True, 5, 10)
        self._ticker.connect(threaded=True)

    def _on_ticks(self, ws, ticks):
        for t in ticks or []:
            sym = self.token_to_symbol.get(int(t.get("instrument_token", 0)))
            if not sym:
                continue
            price = float(t.get("last_price") or 0)
            ts = t.get("exchange_timestamp") or t.get("last_trade_time") or datetime.now(IST)
            if isinstance(ts, str):
                ts = pd.to_datetime(ts, utc=True).tz_convert(IST).to_pydatetime()
            cum_vol = t.get("volume_traded")
            qty = t.get("last_traded_quantity") or t.get("last_quantity")
            self.aggregators[sym].push(ts, price, qty=qty, cum_volume=cum_vol)


# ------------------------ Stub providers -----------------------------
class _StubBrokerProvider(MarketDataProvider):
    BROKER_NAME = "Stub"
    DOCS_URL = ""
    def __init__(self, api_key: str = "", access_token: str = "", symbol_map=None):
        self.api_key = api_key
        self.access_token = access_token
        self.symbol_map = symbol_map or {}
    def is_market_open(self, now=None): return is_market_open(now)
    def download_history(self, symbols, interval, period="1y"):
        raise NotImplementedError(self.BROKER_NAME + " provider not implemented. Docs: " + self.DOCS_URL)
    def fetch_latest_batch(self, symbols, interval):
        raise NotImplementedError(self.BROKER_NAME + " provider not implemented. Docs: " + self.DOCS_URL)


class AngelOneProvider(_StubBrokerProvider):
    BROKER_NAME = "AngelOne SmartAPI"
    DOCS_URL = "https://smartapi.angelbroking.com/docs"

class DhanProvider(_StubBrokerProvider):
    BROKER_NAME = "Dhan HQ"
    DOCS_URL = "https://dhanhq.co/docs"

class FyersProvider(_StubBrokerProvider):
    BROKER_NAME = "Fyers"
    DOCS_URL = "https://myapi.fyers.in/docsv3"

class FivePaisaProvider(_StubBrokerProvider):
    BROKER_NAME = "5paisa"
    DOCS_URL = "https://www.5paisa.com/developerapi/overview"

class IIFLProvider(_StubBrokerProvider):
    BROKER_NAME = "IIFL Markets"
    DOCS_URL = "https://www.iiflsecurities.com/traderterminal/apidocs"


BROKER_REGISTRY = {
    "YFinance (default, no login)": YFinanceProvider,
    "Upstox": UpstoxProvider,
    "Zerodha Kite": ZerodhaProvider,
    "AngelOne SmartAPI (coming soon)": AngelOneProvider,
    "Dhan HQ (coming soon)": DhanProvider,
    "Fyers (coming soon)": FyersProvider,
    "5paisa (coming soon)": FivePaisaProvider,
    "IIFL Markets (coming soon)": IIFLProvider,
}


# ------------------------ Broker picker UI (Settings tab) ---------------
if _P("Settings"):
    st.divider()
    st.subheader("Market Data Provider")

    st.caption(
        "Choose the market-data source used by the Live Market Engine. "
        "YFinance (default) needs no credentials. Broker providers use their "
        "official WebSocket feed and require an API key + access token you "
        "generate in the broker developer console. Tokens live only in this "
        "session; they are never persisted."
    )

    _broker_choice = st.selectbox(
        "Broker",
        options=list(BROKER_REGISTRY.keys()),
        key="broker_choice",
    )

    _needs_creds = _broker_choice != "YFinance (default, no login)"

    if _needs_creds:
        _cred_cols = st.columns(2)
        _api_key = _cred_cols[0].text_input(
            "API key",
            value=st.session_state.get("broker_api_key", ""),
            type="password",
            key="broker_api_key_input",
        )
        _access_token = _cred_cols[1].text_input(
            "Access token",
            value=st.session_state.get("broker_access_token", ""),
            type="password",
            key="broker_access_token_input",
        )
        st.session_state["broker_api_key"] = _api_key
        st.session_state["broker_access_token"] = _access_token

        with st.expander("Symbol to instrument mapping (required for broker feeds)"):
            st.caption(
                "Upstox needs NSE_EQ instrument keys (e.g. NSE_EQ|INE002A01018). "
                "Zerodha needs numeric instrument_token integers. "
                "Paste as JSON, e.g. {'RELIANCE.NS': 'NSE_EQ|INE002A01018', ...} or "
                "{'RELIANCE.NS': 408065, ...}"
            )
            _mapping_raw = st.text_area(
                "Instrument map JSON",
                value=st.session_state.get("broker_symbol_map_raw", "{}"),
                height=140,
                key="broker_symbol_map_input",
            )
            st.session_state["broker_symbol_map_raw"] = _mapping_raw

    if st.button("Activate this provider", key="broker_activate_btn"):
        provider_cls = BROKER_REGISTRY[_broker_choice]
        try:
            if _needs_creds:
                import json as _json
                symbol_map = _json.loads(
                    st.session_state.get("broker_symbol_map_raw", "{}") or "{}"
                )
                provider = provider_cls(
                    api_key=st.session_state.get("broker_api_key", ""),
                    access_token=st.session_state.get("broker_access_token", ""),
                    symbol_map=symbol_map,
                )
            else:
                provider = provider_cls()
            _old = st.session_state.get("live_engine")
            new_engine = LiveMarketEngine(provider)
            if _old is not None:
                new_engine.cache = _old.cache
                new_engine.symbols = _old.symbols
                new_engine.interval = _old.interval
                new_engine.last_tick_time = _old.last_tick_time
                new_engine.total_ticks = _old.total_ticks
            st.session_state["live_engine"] = new_engine
            st.session_state["active_broker"] = _broker_choice
            st.success("Provider activated: " + _broker_choice)
            if "coming soon" in _broker_choice.lower():
                st.warning(
                    "This provider is a stub - the interface is wired but "
                    "download_history / fetch_latest_batch will raise "
                    "NotImplementedError. Implement the class to enable it."
                )
        except Exception as exc:
            st.error("Provider activation failed: " + str(exc))

    st.caption(
        "Active provider: "
        + st.session_state.get("active_broker", "YFinance (default, no login)")
    )
