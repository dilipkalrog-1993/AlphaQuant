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
        ai_score=getattr(trade, "ai_score", 0)
    )

    if hasattr(position, "initialise"):

        position.initialise()

    st.session_state.paper_positions[trade.symbol] = position

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

    create_demand_supply_candidate(stock)
# =====================================================
# AI CONSENSUS ENGINE
# VERSION 3.4A
# =====================================================

if "final_trade_list" not in st.session_state:
    st.session_state.final_trade_list = []


def build_ai_consensus():

    grouped = {}

    for trade in st.session_state.trade_candidates.values():

        symbol = trade.symbol

        if symbol not in grouped:

            grouped[symbol] = []

        grouped[symbol].append(trade)

    final_list = []

    for symbol, trades in grouped.items():

        best = max(

            trades,

            key=lambda x: (
                x.confidence,
                x.risk_reward
            )

        )

        best.strategy_count = len(trades)

        best.ai_score = (

            best.confidence

            +

            (best.strategy_count * 5)

            +

            (best.risk_reward * 5)

        )

        final_list.append(best)

    final_list.sort(

        key=lambda x: x.ai_score,

        reverse=True

    )

    st.session_state.final_trade_list = final_list

    return final_list


def get_final_trade_dataframe():

    rows = []

    for trade in st.session_state.final_trade_list:

        rows.append({

            "Symbol": trade.symbol,

            "Best Strategy": trade.strategy,

            "AI Score": round(trade.ai_score, 2),

            "Confidence": trade.confidence,

            "RR": trade.risk_reward,

            "Entry": trade.entry,

            "Stop": trade.stop,

            "Target": trade.target1,

            "Signals": trade.strategy_count,

            "State": trade.state

        })

    if len(rows):

        return pd.DataFrame(rows)

    return pd.DataFrame()


def show_ai_consensus():

    build_ai_consensus()

    df = get_final_trade_dataframe()

    if len(df):

        st.subheader("AI Consensus Ranking")

        st.dataframe(

            df,

            use_container_width=True

        )
# =====================================================
# CAPITAL ALLOCATION ENGINE
# VERSION 3.4B
# =====================================================

def allocate_portfolio():

    if len(st.session_state.final_trade_list) == 0:
        return []

    capital = st.session_state.paper_capital

    max_positions = CONFIG["MAX_OPEN_POSITIONS"]

    selected = []

    remaining = capital

    trades = sorted(

        st.session_state.final_trade_list,

        key=lambda x: (

            x.ai_score,

            x.confidence,

            x.risk_reward

        ),

        reverse=True

    )

    for trade in trades:

        if len(selected) >= max_positions:
            break

        calculate_position_size(trade)

        if trade.position_size <= 0:
            continue

        if trade.capital_required > remaining:
            continue

        trade.portfolio_weight = round(

            (trade.capital_required / capital) * 100,

            2

        )

        remaining -= trade.capital_required

        selected.append(trade)

    st.session_state.selected_portfolio = selected

    return selected


def portfolio_dataframe():

    rows = []

    for trade in st.session_state.selected_portfolio:

        rows.append({

            "Symbol": trade.symbol,

            "Strategy": trade.strategy,

            "AI Score": round(trade.ai_score,2),

            "Confidence": trade.confidence,

            "Qty": trade.position_size,

            "Capital": round(trade.capital_required,2),

            "Weight %": trade.portfolio_weight,

            "Entry": trade.entry,

            "Stop": trade.stop,

            "Target": trade.target1,

            "RR": trade.risk_reward

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

    for trade in st.session_state.selected_portfolio:

        trade.state = "BUY"

        calculate_position_size(trade)

        open_paper_trade(trade)

def execute_scan_pipeline():

    st.session_state.trade_candidates = {}

    st.session_state.final_trade_list = []

    # Calculate sector rankings once
    calculate_sector_strength()

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

        run_all_strategies(stock)

        for trade in list(

            st.session_state.trade_candidates.values()

        ):

            if trade.symbol != symbol:

                continue

            validate_trade_candidate(

                stock,

                trade

            )

            calculate_position_size(

                trade

            )

    build_ai_consensus()

    allocate_portfolio()

    update_trade_position_sizes()

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

    # -----------------------------------------------------

    def total_pnl(self):

        return round(

            self.realized_pnl +

            self.unrealized_pnl,

            2

        )

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

                period="6mo"

            )

            if len(df) < 60:

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
show_market_dashboard()

show_ai_summary()

show_portfolio_summary()

show_live_positions()

show_portfolio_dashboard()

if st.session_state.run_complete_scan_requested:

    st.session_state.run_complete_scan_requested = False

    execute_scan_pipeline()

    if len(st.session_state.final_trade_list):

        show_ai_consensus()

        show_allocated_portfolio()

    else:

        st.info("No Trade Candidates Found")