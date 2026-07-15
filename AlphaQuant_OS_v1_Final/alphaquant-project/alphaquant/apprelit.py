"""
=========================================================
 AlphaQuant Professional
 Version : 2.1
 Author  : Dilip + ChatGPT

 Long Only AI Trading Platform

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
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

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
# APPLICATION CONFIGURATION
# =====================================================

CONFIG = {

    "VERSION": "2.1",

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
# LOGGING
# =====================================================

LOG_FOLDER = "logs"

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

if "open_positions" not in st.session_state:
    st.session_state.open_positions = {}

if "closed_positions" not in st.session_state:
    st.session_state.closed_positions = []

if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

if "run_complete_scan_requested" not in st.session_state:
    st.session_state.run_complete_scan_requested = False


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
# UNIVERSE ENGINE
# VERSION 2.1B
# =====================================================

@st.cache_data(ttl=86400)
def fetch_complete_nse_universe():

    """
    Downloads the NSE equity universe.

    This function intentionally keeps almost every listed
    equity.

    Liquidity filtering is performed later.
    """

    logging.info("Loading NSE Universe")

    sources = [

        "https://archives.nseindia.com/content/equities/EQUITY_L.csv",

        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",

        "https://archives.nseindia.com/content/indices/ind_niftylargemidcap250list.csv",

        "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv"

    ]

    symbols = set()

    for url in sources:

        try:

            df = pd.read_csv(url)

            df.columns = [

                x.upper().strip()

                for x in df.columns

            ]

            if "SYMBOL" in df.columns:

                values = (

                    df["SYMBOL"]

                    .astype(str)

                    .str.upper()

                    .str.strip()

                    .tolist()

                )

                symbols.update(values)

        except Exception as e:

            logging.warning(f"{url} : {e}")

    blacklist = {

        "NIFTYBEES",

        "BANKBEES",

        "GOLDBEES",

        "LIQUIDBEES",

        "SILVERBEES",

        "JUNIORBEES"

    }

    final_list = []

    for s in symbols:

        if len(s) < 2:

            continue

        if s in blacklist:

            continue

        if "ETF" in s:

            continue

        if "BEES" in s:

            continue

        if "FUND" in s:

            continue

        final_list.append(

            s + ".NS"

        )

    final_list = sorted(

        list(set(final_list))

    )

    logging.info(

        f"Universe Loaded : {len(final_list)} Stocks"

    )

    return final_list


# =====================================================
# LOAD UNIVERSE
# =====================================================

ALL_SYMBOLS = fetch_complete_nse_universe()

st.success(

    f"Universe Loaded : {len(ALL_SYMBOLS)} Stocks"

)

with st.expander("Universe Preview"):

    st.dataframe(

        pd.DataFrame(

            {

                "Symbol": ALL_SYMBOLS

            }

        ).head(100)

    )
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
# DOWNLOAD BUTTON
# =====================================================

st.divider()

st.subheader("Market Data Engine")

if st.button("Download Complete Universe"):

    st.session_state.market_data = download_market_data(

        ALL_SYMBOLS

    )

    st.success(

        "Download Finished"

    )
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

st.divider()

st.subheader("Trade Quality Engine")

if st.button("Test Trade Quality"):

    if len(st.session_state.market_data) == 0:

        st.warning("Please download market data first.")

    else:

        preview = []

        for symbol, df in st.session_state.market_data.items():

            try:

                df = calculate_indicators(df)

                if df is None:
                    st.error(f"{symbol} -> calculate_indicators returned None")
                    continue

                stock = get_stock(symbol)

                stock.set_dataframe(df)

                calculate_trade_quality(stock)

                preview.append({
                    "Symbol": symbol,
                    "State": stock.state,
                    "TQI": stock.score["quality"],
                    "Reasons": " | ".join(stock.reason[:4])
                })

            except Exception as e:

                st.error(f"{symbol}: {e}")

        if len(preview):

            preview = pd.DataFrame(preview)

            preview = preview.sort_values(
                "TQI",
                ascending=False
            )

            st.dataframe(
                preview,
                use_container_width=True
            )

        else:

            st.warning("No stocks processed successfully.")
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

st.divider()

st.subheader("Market Structure Engine")

if st.button("Test Market Structure"):

    if len(st.session_state.market_data) == 0:

        st.warning(
            "Download market data first."
        )

    else:

        rows = []

        for symbol, df in st.session_state.market_data.items():

            df = calculate_indicators(df)

            if df is None:
                continue

            stock = get_stock(symbol)

            stock.set_dataframe(df)

            update_market_structure(stock)

            rows.append({

                "Symbol": symbol,

                "Trend": stock.market.get(
                    "TREND",
                    ""
                ),

                "Swing High": stock.market.get(
                    "LAST_SWING_HIGH",
                    ""
                ),

                "Swing Low": stock.market.get(
                    "LAST_SWING_LOW",
                    ""
                ),

                "Patterns": ", ".join(
                    stock.patterns.keys()
                )

            })

        if len(rows):

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True
            )
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

if st.button("Run Complete Scan"):

    if len(st.session_state.market_data) == 0:

        st.warning("Download market data first.")

    else:

        st.session_state.run_complete_scan_requested = True
        st.info("Scan queued. Initializing all strategy modules before execution.")

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


class PaperPosition:

    def __init__(self, trade):

        self.symbol = trade.symbol
        self.strategy = trade.strategy

        self.entry = trade.entry
        self.stop = trade.stop

        self.target1 = trade.target1
        self.target2 = trade.target2
        self.target3 = trade.target3

        self.quantity = trade.position_size

        self.entry_time = datetime.now()

        self.exit_time = None

        self.exit_price = None

        self.status = "OPEN"

        self.pnl = 0

        self.exit_reason = ""

    def mark_closed(self, price, reason):

        self.exit_price = round(price, 2)

        self.exit_reason = reason

        self.exit_time = datetime.now()

        self.status = "CLOSED"

        self.pnl = round(

            (self.exit_price - self.entry)

            * self.quantity,

            2

        )


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


def update_paper_trade(symbol, last_price):

    if symbol not in st.session_state.paper_positions:
        return

    position = st.session_state.paper_positions[symbol]

    if position.status != "OPEN":
        return

    if last_price <= position.stop:

        if hasattr(position, "mark_closed"):

            position.mark_closed(

                position.stop,

                "STOP LOSS"

            )

        else:

            position.close_trade("STOP LOSS", position.stop)

    elif last_price >= position.target1:

        if hasattr(position, "mark_closed"):

            position.mark_closed(

                position.target1,

                "TARGET"

            )

        else:

            position.close_trade("TARGET", position.target1)

    if position.status == "CLOSED":

        st.session_state.paper_history.append(position)

        del st.session_state.paper_positions[symbol]


def run_paper_trading():

    for trade in st.session_state.trade_candidates.values():

        calculate_position_size(trade)

        open_paper_trade(trade)

    for symbol, position in list(

        st.session_state.paper_positions.items()

    ):

        stock = get_stock(symbol)

        if stock.data is None:
            continue

        last_price = stock.data["Close"].iloc[-1]

        update_paper_trade(

            symbol,

            last_price

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

    build_ai_consensus()

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


def update_live_trade(stock):

    symbol = stock.symbol

    if symbol not in st.session_state.paper_positions:
        return

    position = st.session_state.paper_positions[symbol]

    last = stock.data.iloc[-1]

    last_price = float(last["Close"])

    update_paper_trade(
        symbol,
        last_price
    )


def monitor_open_positions():

    for symbol in list(st.session_state.paper_positions.keys()):

        stock = get_stock(symbol)

        if stock.data is None:
            continue

        update_live_trade(stock)


def start_live_monitor():

    st.session_state.live_monitor_running = True

    while st.session_state.live_monitor_running:

        monitor_open_positions()

        time.sleep(5)


def stop_live_monitor():

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

        open_paper_trade(trade)

def execute_scan_pipeline():

    st.session_state.trade_candidates = {}

    st.session_state.final_trade_list = []

    # Calculate sector rankings once
    calculate_sector_strength()

    # Batch 1: load NIFTY benchmark once for Relative Strength calculations
    fetch_nifty_benchmark()

    # Batch 2: prefetch earnings/news for every symbol once, concurrently,
    # instead of hitting the network per symbol inside the loop below.
    prefetch_news_earnings(list(st.session_state.market_data.keys()))

    total = len(st.session_state.market_data)

    progress = st.progress(0)

    status = st.empty()

    for index, (symbol, df) in enumerate(


        st.session_state.market_data.items(),

        start=1

    ):

        progress.progress(index / total)

        status.write(f"Scanning : {symbol}")

        df = calculate_indicators(df)

        if df is None:

            continue

        stock = get_stock(symbol)

        stock.set_dataframe(df)

        calculate_trade_quality(stock)

        update_market_structure(stock)

        # Batch 1: Multi-Timeframe / Relative Strength / Sector / Volume Profile
        run_batch1_signal_engines(stock)

        registered_names = [s.name for s in st.session_state.strategy_registry if s.enabled]

        candidates_before = {k for k, v in st.session_state.trade_candidates.items() if v.symbol == symbol}

        run_all_strategies(stock)

        # Batch 2: False Breakout / Smart Money / Institutional Activity /
        # News & Earnings - must run after strategies so BOS/CHOCH/Order
        # Block/Liquidity Sweep/FVG patterns are already populated.
        run_batch2_signal_engines(stock)

        candidates_after = {k for k, v in st.session_state.trade_candidates.items() if v.symbol == symbol}

        new_candidate_keys = candidates_after - candidates_before

        logging.info(

            f"SCAN symbol={symbol} tqi={stock.score.get('quality')} "

            f"trend={stock.market.get('TREND')} "

            f"registered_strategies={registered_names} "

            f"candidates_created={sorted(new_candidate_keys)}"

        )

        for trade in list(

            st.session_state.trade_candidates.values()

        ):

            if trade.symbol != symbol:

                continue

            validate_trade_candidate(

                stock,

                trade

            )

            # Batch 1: fold sector strength into per-trade confidence
            apply_sector_bonus(stock, trade)

            calculate_position_size(

                trade

            )

            logging.info(

                f"VALIDATE symbol={symbol} strategy={trade.strategy} "

                f"state={trade.state} rr={getattr(trade, 'risk_reward', None)} "

                f"missing_triggers={getattr(trade, 'missing_triggers', None)}"

            )

    build_ai_consensus()

    allocate_portfolio()

    # Brain 6 (portfolio_manager) is the final authority on sizing for
    # allocated trades - update_trade_position_sizes() used to run here
    # and would silently overwrite that sizing with flat per-trade risk
    # sizing, so it has been removed from this pipeline.

    execute_selected_portfolio()

    monitor_open_positions()

    status.success(

        "Pipeline Completed Successfully"

    )
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

    return st.session_state.open_positions.get(symbol)


def add_open_position(position):

    st.session_state.open_positions[position.symbol] = position


def remove_open_position(symbol):

    if symbol in st.session_state.open_positions:

        del st.session_state.open_positions[symbol]

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

        position.close_trade(
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

        position.close_trade(
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

    if len(st.session_state.open_positions) == 0:

        return

    remove_list = []

    for symbol, position in list(

        st.session_state.open_positions.items()

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

        del st.session_state.open_positions[symbol]
# ==========================================================
# MODULE A - PART 5
# DASHBOARD & ANALYTICS
# ==========================================================

def portfolio_statistics():

    open_positions = list(
        st.session_state.open_positions.values()
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

    for p in st.session_state.open_positions.values():

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


show_market_dashboard()

show_ai_summary()

show_portfolio_summary()

show_live_positions()

show_portfolio_dashboard()

show_alphaquant_os_panel()

if st.session_state.run_complete_scan_requested:

    st.session_state.run_complete_scan_requested = False

    execute_scan_pipeline()

    if len(st.session_state.final_trade_list):

        show_ai_consensus()

        show_allocated_portfolio()

    else:

        st.info("No Trade Candidates Found")