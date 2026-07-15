# AlphaQuant — Phase 2, Batch 1 Report

Date: 2026-07-14
Baseline commit verified before starting: `Phase1_Production` tag (7a2f8ff) — re-ran RELIANCE.NS end-to-end, 0 exceptions, before touching any code.

## Features built (all 5, as scoped)

Each feature was added as its own function, wired into `execute_scan_pipeline()`, feeds `build_ai_consensus()`, and is exposed through indicators, reasoning strings, a score/confidence contribution, a dedicated UI panel, and a dedicated `logging.info` line per symbol per scan.

1. **Multi-Timeframe Analysis** (`analyze_multi_timeframe`) — pulls live 1H and 15M intraday data per symbol, classifies trend on each timeframe (EMA9/EMA21 cross), and scores alignment against the existing Daily trend (100 = all three agree, 60 = partial agreement, 30 = conflicting). Log line: `MULTI_TIMEFRAME`.
2. **Relative Strength vs NIFTY** (`calculate_relative_strength`) — downloads `^NSEI` once per scan (`fetch_nifty_benchmark`), compares each stock's trailing ~63-day return against the index's, and converts the spread into a 0–100 RS score. Log line: `RELATIVE_STRENGTH`.
3. **Sector Strength Ranking** (`assign_sector` + fix to `calculate_sector_strength`) — maps ~90 well-known NSE symbols to one of 7 sector buckets and reads the sector's technical score. **Root cause fixed along the way:** `calculate_sector_strength()` was already in the codebase but was silently producing an empty result for every sector, because it downloaded only 6 months of ETF history and then fed that into `calculate_indicators()`, which requires ≥200 rows — so every sector was always skipped and the feature was dead code. Fixed by using the same 2-year window the rest of the app uses. Also wired the previously-unused `apply_sector_bonus()` (it existed but was never called) into the per-candidate validation loop. Log line: `SECTOR`.
4. **Volume Profile Analysis** (`calculate_volume_profile`) — bins the last 120 days of price into 20 levels weighted by traded volume, finds the Point of Control (POC) and High Volume Nodes, and flags whether price is trading above/at/below POC. Log line: `VOLUME_PROFILE`.
5. **Demand & Supply Zones** — this engine already existed and was already fully wired into the strategy registry and candidate generation (confidence, entry/stop/target, `add_reason`); it did not need new detection logic. Added the missing sector bonus hookup and a dedicated `DEMAND_SUPPLY` log line so it now reports fresh zone counts, confidence, and state per symbol per scan, matching the other four engines' visibility.

All five roll into a single `run_batch1_signal_engines(stock)` bonus (range -10 to +25) that is added directly onto `best.ai_score` inside `build_ai_consensus()`, with a reasoning string recorded on the winning trade showing each sub-score that contributed.

**New UI panel:** "Batch 1 — Advanced Signals" (below Trade Candidate Engine) — a `Show Advanced Signals` button rendering a table of Daily/1H/15M trend, MTF alignment, RS score, sector + sector score, volume POC + position, demand/supply zone counts, the consensus bonus, and the latest reasoning per scanned symbol.

## Bug fixed along the way (pre-existing, not introduced by Batch 1)

Found while validating Portfolio/Trade History rendering after a scan: the file defined **two conflicting `PaperPosition` classes** (an old plain class using `.quantity`/`.pnl`/`.mark_closed()`, and a newer `@dataclass` using `.qty`/`.realized_pnl`+`.unrealized_pnl`/`.close_trade()`). Because the dataclass is defined later in the file, it silently wins at runtime, and Trade History / Live Positions rendering code that still used `.quantity` / `.pnl` / `.mark_closed()` crashed with `AttributeError` — but only on the rerun *after* a position had actually been opened, which is why it hadn't shown up in the original Phase 1 validation (that test never re-rendered after opening a position). Fixed by adding `.quantity`, `.pnl`, and `.mark_closed()` as compatibility properties/method on the live dataclass — no call sites changed, no behavior removed, both naming conventions now resolve correctly.

## Validation

Baseline (Phase 1) re-verified first, then full pipeline re-tested end-to-end with Batch 1 active, including a second rerun (Show Advanced Signals) to force the Portfolio/Trade History code paths to render with open positions.

| Metric | RELIANCE.NS | 100 NSE symbols |
|---|---|---|
| Runtime exceptions | 0 | 0 |
| Signal engine coverage (Sector/MTF/RS/Volume Profile/Demand-Supply logged) | 100% | 100% (87/87 scanned) |
| Trade candidates | 4 | 288 |
| AI Consensus final ranked trades | 1 | 87 |
| Portfolio positions opened | 1 | 10 |
| Regression check (candidate/final-trade counts vs. pre-Batch1 baseline) | match | match (288 / 87, identical to pre-Batch1 run) |

No regressions: candidate counts, final trade counts, and portfolio selection on the same 100-symbol universe are identical to the pre-Batch-1 baseline numbers. The only behavior change is the new Batch 1 bonus added on top of `ai_score`, and the sector-strength/PaperPosition bugs described above are now fixed rather than silently broken.

## Files changed
- `alphaquant/app.py` only.

## Git
- Commit: "Phase2 Batch1: Multi-Timeframe, Relative Strength, Sector Ranking, Volume Profile, Demand/Supply integration"
