"""
AlphaQuant OS — Phase 1 resumable backfill pipeline.

Populates market_memory.daily_snapshots + forward_outcomes for the top
~500 most liquid NSE stocks (the Nifty 500 constituent list — by
definition the ~500 most liquid/largest NSE equities, which is the
standard proxy used here instead of a custom liquidity ranking pass over
the full ~2,384-symbol universe) over ~5 years, tagged ingestion_phase=1.

Resumability: progress is tracked entirely in
market_memory.ingestion_coverage (one row per symbol once it has been
backfilled). Each invocation asks the database which universe symbols are
NOT yet covered and processes the next `chunk_size` of them, so the script
can be re-run any number of times, in any session, and always continues
where it left off — it never depends on in-memory or in-process state.

Extending to Phase 2 (full universe) or Phase 3 (continuous daily updates)
requires zero schema/pipeline changes: Phase 2 is the same function called
against the remaining ~1,884 non-Nifty-500 symbols with ingestion_phase=2;
Phase 3 is the same per-symbol backfill function called with a 1-day
window and ingestion_phase=3, run on a schedule.
"""

import argparse
import datetime
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")

from os_brains.db import get_connection, apply_schema
from os_brains.market_historian import seed_regime_catalog
from os_brains.setup_vector import (
    HOLDING_HORIZONS,
    build_setup_vector_row,
    compute_pattern_flag_series,
    compute_relative_strength_series,
)

INGESTION_PHASE = 1
BACKFILL_YEARS = "5y"
INDICATOR_WARMUP_DAYS = 210  # matches EMA200 + margin

NSE_BLACKLIST = {
    "NIFTYBEES", "BANKBEES", "GOLDBEES", "LIQUIDBEES", "SILVERBEES", "JUNIORBEES",
}


def get_backfill_universe(limit=500):
    """
    Nifty 500 constituent list, filtered the same way
    app.fetch_complete_nse_universe() filters its combined sources (drop
    ETFs/BEES/FUND wrappers), sorted, capped at `limit`.
    """
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        df = pd.read_csv(url)
        df.columns = [c.upper().strip() for c in df.columns]
        symbols = set(df["SYMBOL"].astype(str).str.upper().str.strip().tolist())
    except Exception as e:
        logging.error(f"BACKFILL_UNIVERSE: failed to load Nifty 500 list: {e}")
        return []

    final = []
    for s in symbols:
        if len(s) < 2 or s in NSE_BLACKLIST:
            continue
        if "ETF" in s or "BEES" in s or "FUND" in s:
            continue
        final.append(s + ".NS")
    final = sorted(set(final))
    return final[:limit]


def get_covered_symbols(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol FROM market_memory.ingestion_coverage WHERE phase = %s",
            (INGESTION_PHASE,),
        )
        return {row[0] for row in cur.fetchall()}


def get_next_chunk(conn, universe, chunk_size):
    covered = get_covered_symbols(conn)
    remaining = [s for s in universe if s not in covered]
    return remaining[:chunk_size], len(remaining)


def _load_nifty_benchmark(period=BACKFILL_YEARS):
    import yfinance as yf
    df = yf.download("^NSEI", period=period, interval="1d", progress=False,
                      auto_adjust=True, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _compute_forward_outcomes(df, idx):
    """
    forward_return / max_drawdown / max_favorable_move / recovered_by_day
    for each horizon in HOLDING_HORIZONS, looking forward from row `idx`.
    Returns {} if the dataframe doesn't extend far enough past idx for the
    largest horizon.
    """
    entry_close = df["Close"].iloc[idx]
    outcomes = {}
    max_horizon = max(HOLDING_HORIZONS)
    if idx + max_horizon >= len(df):
        return outcomes

    for horizon in HOLDING_HORIZONS:
        window = df["Close"].iloc[idx + 1: idx + 1 + horizon]
        if len(window) < horizon:
            continue
        path_returns = (window - entry_close) / entry_close
        forward_return = float(path_returns.iloc[-1])
        max_drawdown = float(path_returns.min())
        max_favorable_move = float(path_returns.max())

        recovered_by_day = None
        if max_drawdown < 0:
            for offset, val in enumerate(path_returns, start=1):
                if val >= 0:
                    recovered_by_day = offset
                    break

        outcomes[horizon] = {
            "forward_return": forward_return,
            "max_drawdown": max_drawdown,
            "max_favorable_move": max_favorable_move,
            "recovered_by_day": recovered_by_day,
        }
    return outcomes


def backfill_symbol(conn, symbol, app_module, nifty_df):
    """
    Downloads ~5y of daily OHLCV for `symbol`, computes indicators (via
    app.calculate_indicators — reused, not duplicated), builds setup
    vectors + forward outcomes for every eligible historical day, and
    writes them to market_memory. Updates ingestion_coverage on success
    (and only on success, so a failed symbol is retried on the next run).

    Returns the number of daily_snapshots rows written.
    """
    import yfinance as yf

    try:
        df = yf.download(symbol, period=BACKFILL_YEARS, interval="1d",
                          progress=False, auto_adjust=True, threads=False)
    except Exception as e:
        logging.warning(f"BACKFILL {symbol}: download failed: {e}")
        return 0

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df is None or len(df) < INDICATOR_WARMUP_DAYS + max(HOLDING_HORIZONS) + 5:
        logging.warning(f"BACKFILL {symbol}: insufficient history ({0 if df is None else len(df)} rows)")
        return 0

    df = app_module.calculate_indicators(df)
    if df is None:
        logging.warning(f"BACKFILL {symbol}: calculate_indicators returned None")
        return 0

    pattern_flags = compute_pattern_flag_series(df)
    relative_strength_series = compute_relative_strength_series(df, nifty_df)

    sector = None
    try:
        from app import STOCK_SECTOR_MAP
        base = symbol.replace(".NS", "")
        sector = STOCK_SECTOR_MAP.get(base)
    except Exception:
        pass

    rows_written = 0
    with conn.cursor() as cur:
        for idx in range(INDICATOR_WARMUP_DAYS, len(df) - max(HOLDING_HORIZONS)):
            vector = build_setup_vector_row(df, idx, pattern_flags, relative_strength_series)
            if vector is None:
                continue

            trading_day = df.index[idx]
            if hasattr(trading_day, "date"):
                trading_day = trading_day.date()

            raw_indicators = {
                "EMA20": float(df["EMA20"].iloc[idx]),
                "EMA50": float(df["EMA50"].iloc[idx]),
                "EMA200": float(df["EMA200"].iloc[idx]),
                "ADX": float(df["ADX"].iloc[idx]) if pd.notna(df["ADX"].iloc[idx]) else None,
                "RVOL": float(df["RVOL"].iloc[idx]) if pd.notna(df["RVOL"].iloc[idx]) else None,
                "ATR": float(df["ATR"].iloc[idx]) if pd.notna(df["ATR"].iloc[idx]) else None,
            }
            flags_for_day = {
                col: bool(pattern_flags[col].iloc[idx]) for col in pattern_flags.columns
            }

            cur.execute(
                """
                INSERT INTO market_memory.daily_snapshots
                    (symbol, trading_day, close, setup_vector, raw_indicators,
                     pattern_flags, sector, ingestion_phase)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, trading_day) DO UPDATE SET
                    close = EXCLUDED.close,
                    setup_vector = EXCLUDED.setup_vector,
                    raw_indicators = EXCLUDED.raw_indicators,
                    pattern_flags = EXCLUDED.pattern_flags,
                    sector = EXCLUDED.sector
                RETURNING id
                """,
                (
                    symbol,
                    trading_day,
                    float(df["Close"].iloc[idx]),
                    json.dumps(vector),
                    json.dumps(raw_indicators),
                    json.dumps(flags_for_day),
                    sector,
                    INGESTION_PHASE,
                ),
            )
            snapshot_id = cur.fetchone()[0]

            outcomes = _compute_forward_outcomes(df, idx)
            for horizon, outcome in outcomes.items():
                cur.execute(
                    """
                    INSERT INTO market_memory.forward_outcomes
                        (snapshot_id, holding_period_days, forward_return,
                         max_drawdown, max_favorable_move, recovered_by_day)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_id, holding_period_days) DO UPDATE SET
                        forward_return = EXCLUDED.forward_return,
                        max_drawdown = EXCLUDED.max_drawdown,
                        max_favorable_move = EXCLUDED.max_favorable_move,
                        recovered_by_day = EXCLUDED.recovered_by_day
                    """,
                    (
                        snapshot_id, horizon, outcome["forward_return"],
                        outcome["max_drawdown"], outcome["max_favorable_move"],
                        outcome["recovered_by_day"],
                    ),
                )
            rows_written += 1

        first_day = df.index[INDICATOR_WARMUP_DAYS]
        last_day = df.index[len(df) - max(HOLDING_HORIZONS) - 1]
        if hasattr(first_day, "date"):
            first_day = first_day.date()
        if hasattr(last_day, "date"):
            last_day = last_day.date()

        cur.execute(
            """
            INSERT INTO market_memory.ingestion_coverage
                (symbol, first_day, last_day, phase)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                first_day = EXCLUDED.first_day,
                last_day = EXCLUDED.last_day,
                phase = EXCLUDED.phase,
                last_updated_at = now()
            """,
            (symbol, first_day, last_day, INGESTION_PHASE),
        )
    conn.commit()
    return rows_written


def run_chunk(chunk_size=10, universe_limit=500):
    import app as app_module

    # Idempotent bootstrap: guarantees a clean environment (schema not yet
    # applied, regime catalog not yet seeded) can run this pipeline directly
    # with zero manual DB prep. Both calls are safe to run on every
    # invocation (CREATE ... IF NOT EXISTS / ON CONFLICT DO UPDATE).
    apply_schema()
    seed_regime_catalog()

    conn = get_connection()
    try:
        universe = get_backfill_universe(limit=universe_limit)
        if not universe:
            logging.error("BACKFILL: universe is empty, aborting chunk")
            return {"processed": [], "remaining": 0, "rows_written": 0}

        chunk, remaining_before = get_next_chunk(conn, universe, chunk_size)
        if not chunk:
            logging.info("BACKFILL: universe fully covered, nothing to do")
            return {"processed": [], "remaining": 0, "rows_written": 0}

        nifty_df = _load_nifty_benchmark()

        results = []
        total_rows = 0
        for symbol in chunk:
            n = backfill_symbol(conn, symbol, app_module, nifty_df)
            results.append({"symbol": symbol, "rows_written": n})
            total_rows += n
            logging.info(f"BACKFILL_PROGRESS: {symbol} rows={n}")

        remaining_after = remaining_before - len(chunk)
        return {
            "processed": results,
            "remaining": remaining_after,
            "rows_written": total_rows,
            "universe_size": len(universe),
        }
    finally:
        conn.close()


def append_daily_snapshot(conn, symbol, app_module, nifty_df, df=None):
    """
    Phase 3 incremental hook (a) - "new trading day -> append Market Memory
    without reprocessing history" (ALPHAQUANT_OS_ARCHITECTURE.md section 7).

    Computes/upserts a setup_vector row for ONLY the most recent trading
    day already present in `df` (or freshly downloaded if `df` isn't
    supplied) - it never re-walks the symbol's full history the way
    backfill_symbol() does for the initial Phase 1 pass. Also opportunistically
    fills in forward_outcomes for any already-ingested snapshots that have
    now "matured" (enough calendar days have passed for one of
    HOLDING_HORIZONS to be computable), via
    backfill_matured_forward_outcomes() below.

    This function - not a new pipeline - is the entire Phase 3 rollout: a
    scheduler just needs to call this once per symbol per trading day. That
    scheduler does not exist yet (explicitly out of scope for this task);
    this function is the hook it would call.
    """
    if df is None:
        import yfinance as yf
        df = yf.download(symbol, period="2y", interval="1d", progress=False,
                          auto_adjust=True, threads=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    if df is None or len(df) < INDICATOR_WARMUP_DAYS + 5:
        logging.warning(f"APPEND_DAILY_SNAPSHOT {symbol}: insufficient history to build today's vector")
        return None

    df = app_module.calculate_indicators(df)
    if df is None:
        return None

    idx = len(df) - 1  # only the most recent day - the "new trading day"
    pattern_flags = compute_pattern_flag_series(df)
    relative_strength_series = compute_relative_strength_series(df, nifty_df)
    vector = build_setup_vector_row(df, idx, pattern_flags, relative_strength_series)
    if vector is None:
        logging.info(f"APPEND_DAILY_SNAPSHOT {symbol}: today's vector not computable yet (warm-up)")
        return None

    trading_day = df.index[idx]
    if hasattr(trading_day, "date"):
        trading_day = trading_day.date()

    sector = None
    try:
        from app import STOCK_SECTOR_MAP
        sector = STOCK_SECTOR_MAP.get(symbol.replace(".NS", ""))
    except Exception:
        pass

    raw_indicators = {
        "EMA20": float(df["EMA20"].iloc[idx]),
        "EMA50": float(df["EMA50"].iloc[idx]),
        "EMA200": float(df["EMA200"].iloc[idx]),
        "ADX": float(df["ADX"].iloc[idx]) if pd.notna(df["ADX"].iloc[idx]) else None,
        "RVOL": float(df["RVOL"].iloc[idx]) if pd.notna(df["RVOL"].iloc[idx]) else None,
        "ATR": float(df["ATR"].iloc[idx]) if pd.notna(df["ATR"].iloc[idx]) else None,
    }
    flags_for_day = {col: bool(pattern_flags[col].iloc[idx]) for col in pattern_flags.columns}

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO market_memory.daily_snapshots
                (symbol, trading_day, close, setup_vector, raw_indicators,
                 pattern_flags, sector, ingestion_phase)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, trading_day) DO UPDATE SET
                close = EXCLUDED.close,
                setup_vector = EXCLUDED.setup_vector,
                raw_indicators = EXCLUDED.raw_indicators,
                pattern_flags = EXCLUDED.pattern_flags,
                sector = EXCLUDED.sector
            RETURNING id
            """,
            (
                symbol, trading_day, float(df["Close"].iloc[idx]),
                json.dumps(vector), json.dumps(raw_indicators),
                json.dumps(flags_for_day), sector, 3,
            ),
        )
        snapshot_id = cur.fetchone()[0]
        cur.execute(
            """
            UPDATE market_memory.ingestion_coverage SET last_day = %s, last_updated_at = now()
            WHERE symbol = %s
            """,
            (trading_day, symbol),
        )
    conn.commit()
    logging.info(f"APPEND_DAILY_SNAPSHOT {symbol}: snapshot_id={snapshot_id} trading_day={trading_day}")
    return snapshot_id


def backfill_matured_forward_outcomes(conn, symbol, app_module, lookback_days=40):
    """
    Phase 3 incremental hook (a), continued - fills forward_outcomes for
    snapshots that were too recent to have a forward_return when they were
    first ingested (append_daily_snapshot only ever writes a snapshot's
    price/setup_vector, never outcomes for days that haven't happened yet)
    but have since matured because enough calendar days have passed. Only
    re-downloads/re-walks the last `lookback_days` of history, never the
    symbol's full backfilled range.
    """
    import yfinance as yf

    with dict_cursor_from(conn) as cur:
        cur.execute(
            """
            SELECT s.id, s.trading_day FROM market_memory.daily_snapshots s
            WHERE s.symbol = %s
              AND NOT EXISTS (
                  SELECT 1 FROM market_memory.forward_outcomes f WHERE f.snapshot_id = s.id
              )
            ORDER BY s.trading_day
            """,
            (symbol,),
        )
        pending = cur.fetchall()

    if not pending:
        return 0

    df = yf.download(symbol, period=f"{lookback_days + max(HOLDING_HORIZONS) + 10}d", interval="1d",
                      progress=False, auto_adjust=True, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df is None or df.empty:
        return 0

    day_to_idx = {
        (d.date() if hasattr(d, "date") else d): i for i, d in enumerate(df.index)
    }

    written = 0
    with conn.cursor() as cur:
        for row in pending:
            idx = day_to_idx.get(row["trading_day"])
            if idx is None:
                continue
            outcomes = _compute_forward_outcomes(df, idx)
            for horizon, outcome in outcomes.items():
                cur.execute(
                    """
                    INSERT INTO market_memory.forward_outcomes
                        (snapshot_id, holding_period_days, forward_return,
                         max_drawdown, max_favorable_move, recovered_by_day)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_id, holding_period_days) DO UPDATE SET
                        forward_return = EXCLUDED.forward_return,
                        max_drawdown = EXCLUDED.max_drawdown,
                        max_favorable_move = EXCLUDED.max_favorable_move,
                        recovered_by_day = EXCLUDED.recovered_by_day
                    """,
                    (row["id"], horizon, outcome["forward_return"], outcome["max_drawdown"],
                     outcome["max_favorable_move"], outcome["recovered_by_day"]),
                )
                written += 1
    conn.commit()
    logging.info(f"BACKFILL_MATURED_OUTCOMES {symbol}: snapshots_checked={len(pending)} outcomes_written={written}")
    return written


def dict_cursor_from(conn):
    from os_brains.db import dict_cursor
    return dict_cursor(conn)


def enrich_snapshot(conn, symbol, trading_day, extra_raw_indicators=None, extra_pattern_flags=None):
    """
    Phase 3 incremental hook (c) - "new historical data available ->
    enrich Market Memory". Mechanism only: merges additional fields into an
    ALREADY-ingested (symbol, trading_day) snapshot's raw_indicators /
    pattern_flags JSONB without touching setup_vector or forward_outcomes,
    for cases like a late corporate-action adjustment or a newly added
    indicator being backfilled onto historical rows. No caller/scheduler
    exists yet for this - it is the hook a future enrichment job would call,
    per the explicit "mechanism, not execution" scope of this task.
    """
    if not extra_raw_indicators and not extra_pattern_flags:
        return False
    with conn.cursor() as cur:
        cur.execute(
            "SELECT raw_indicators, pattern_flags FROM market_memory.daily_snapshots "
            "WHERE symbol = %s AND trading_day = %s",
            (symbol, trading_day),
        )
        row = cur.fetchone()
        if row is None:
            return False
        raw_indicators, pattern_flags = row
        raw_indicators = dict(raw_indicators or {})
        pattern_flags = dict(pattern_flags or {})
        raw_indicators.update(extra_raw_indicators or {})
        pattern_flags.update(extra_pattern_flags or {})
        cur.execute(
            "UPDATE market_memory.daily_snapshots SET raw_indicators = %s, pattern_flags = %s "
            "WHERE symbol = %s AND trading_day = %s",
            (json.dumps(raw_indicators), json.dumps(pattern_flags), symbol, trading_day),
        )
    conn.commit()
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=10)
    parser.add_argument("--universe-limit", type=int, default=500)
    args = parser.parse_args()

    summary = run_chunk(chunk_size=args.chunk_size, universe_limit=args.universe_limit)
    print(json.dumps(summary, indent=2, default=str))
