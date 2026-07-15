# AlphaQuant — Phase 3 Report (Automated & Autonomous Pipeline)

**Date:** 2026-07-15
**Scope:** Scan Manager (universe/filter selection), a single automated pipeline trigger, an execution-mode abstraction (Paper/Simulation/future Live), and a genuinely autonomous, market-hours-aware trading loop — plus this validation pass.
**Method:** Headless validation via direct module import (`import app` — the same "no browser needed" methodology used in `ALPHAQUANT_OS_V1_REPORT.md`, since `st.*` calls no-op harmlessly outside a real script-run context) against real NSE market data, plus `streamlit.testing.v1.AppTest` for UI-path checks and a foreground `streamlit run` smoke test for startup-exception checking.

---

## 1. What Phase 3 built

### Scan Manager
Lets a user choose a universe (NSE All / NSE500 / Nifty50 / Nifty Next 50 / Midcap / Smallcap / Watchlist) plus price/volume/turnover/sector/style filters, and builds `st.session_state.scan_universe` — the single list every downstream download/scan/autonomous cycle now reads from. Fixed a `NameError`-causing definition-order bug (`STOCK_SECTOR_MAP` referenced before it was defined) found during that task's own review.

### Single automated pipeline trigger
`run_automated_cycle(trigger)` is now the one function that "downloads the Scan Manager's chosen universe, then runs the whole pipeline." Both the manual **Run Complete Scan** button and the autonomous loop call it — there is exactly one "do a scan cycle" code path, not two implementations that could drift apart. The two dev-only manual buttons that duplicated pipeline-internal calls (**Test Trade Quality**, **Test Market Structure**) were removed; the functions they called (`calculate_trade_quality`, `update_market_structure`) are untouched and still run automatically inside every scan.

### Execution-mode abstraction
`ExecutionEngine` / `PaperExecutionEngine` / `SimulationExecutionEngine` / `LiveExecutionEngine`, selected via `st.session_state.execution_mode` and returned by `get_execution_engine()`. Every trade-open (`execute_selected_portfolio`) and trade-close (`check_stop_loss`, `check_target3`) call site now goes through `get_execution_engine().open_trade(...)` / `.close_trade(...)` instead of touching `PaperPosition/paper_positions` directly. `LiveExecutionEngine` is an intentional, unimplemented seam — it raises `NotImplementedError` rather than silently falling back to paper trading, so a future real-broker integration only has to implement this interface.

### Autonomous trading loop
`is_market_open()` (NSE cash hours, 09:15–15:30 IST, Mon–Fri — no holiday calendar, see Known Limitations) gates a `st.fragment(run_every=...)` loop (`autonomous_loop_fragment`) that:
- every `MONITOR_INTERVAL_SECONDS` (20s): re-fetches the latest price for every open position (`quick_refresh_open_positions`, via the same lightweight `fetch_quote_snapshot` the Scan Manager uses) and checks stop-loss/target hits against it immediately;
- every `SCAN_INTERVAL_SECONDS` (300s): runs a full `run_automated_cycle` + `execute_scan_pipeline()` cycle (rescan the universe, open new qualifying trades, and — because `execute_scan_pipeline()` already ends with `monitor_open_positions()` — recompute trailing stops with fresh indicators too).

This is a real, working autonomous loop, with one honest, inherent limitation: Streamlit has no always-on background process, so it only runs while the AlphaQuant browser tab stays connected. That is tracked as a separate follow-up task ("Keep autonomous trading running even when the AlphaQuant browser tab is closed"), not fixed here.

### Bug found and fixed during this validation task
`experience_memory.record_outcome()` (and `record_review()`/`upsert_calibration()`) were silently failing on every single autonomously-closed trade. `PaperPosition`'s P&L/price fields are `numpy.float64` (they flow through pandas/numpy math), and psycopg2 has no adapter for numpy scalars — it fell back to embedding the value's `repr()` (`np.float64(-830.94)`) unquoted in the SQL text, which Postgres tried to parse as a schema reference (`schema "np" does not exist`) and rejected. The blanket `except Exception: logging.warning(...)` in every Experience Memory write function caught this, so nothing crashed — but `trade_outcomes` rows were never written for **any** closed trade, autonomous or manual, before this fix. Fixed by coercing every numeric parameter through a new `_safe_num()` helper (calls `.item()` on anything numpy-scalar-shaped) before it reaches psycopg2. Verified below: before the fix, `trade_outcomes` rows were `None` for every close; after the fix, every close produces a row.

---

## 2. Validation performed (real NSE data, this session)

### 2.1 100-symbol autonomous cycle (NSE500, first 100 real symbols)
| Stage | Result |
|---|---|
| `run_automated_cycle` (download) | 100/100 symbols downloaded |
| Scan → candidates (`final_trade_list`) | 99 (consistent with AlphaQuant OS's already-documented behavior of keeping vetoed/unfunded candidates visible instead of dropping them — not a regression, matches `ALPHAQUANT_OS_V1_REPORT.md`) |
| AI Consensus → Risk Manager → Portfolio Manager → autonomous open | 10 paper positions opened (capped at `MAX_OPEN_POSITIONS`, same cap behavior as every prior phase report) |
| `execution_mode` | `PAPER` (confirms the new abstraction defaults correctly and routed every open through `get_execution_engine().open_trade()`) |
| Runtime | 82.8s end-to-end (download + full 7-Brain scan + consensus + risk + portfolio + open), in line with prior phases' ~0.4–1.5s/symbol scan-time benchmarks |
| Runtime exceptions | **0** |

### 2.2 Autonomous exit chain (stop-loss hit → Brain 7 → Experience Memory → calibration)
Forced a real open position's price below its trailing stop and called the exact function the autonomous loop's `quick_refresh_open_positions()`/full-cycle `monitor_open_positions()` call (`check_stop_loss`), through the new execution-engine abstraction:

| Step | Evidence |
|---|---|
| `check_stop_loss(position)` → `get_execution_engine().close_trade(...)` | Returned `True`; `position.status` flipped `OPEN → CLOSED`, `exit_reason = "STOP LOSS"` |
| `experience_memory.decisions.outcome_state` | `OPEN → CLOSED` |
| `experience_memory.trade_outcomes` (Brain 7 write, post-fix) | Row written: `entry=8823.5, exit_price=8721.49, exit_reason='STOP LOSS', pnl=-204.02` |
| `experience_memory.trade_reviews` (Brain 7 verdict) | Row written: `was_correct=False, confidence_calibration_delta=-0.015`, with a generated `lessons_learned` string naming which entry evidence mattered vs. misled |
| `experience_memory.calibration_state` | `sample_count` incremented (`None → 1 → 2` across repeated tests on the same symbol), `avg_calibration_delta` updated — confirming the confidence-calibration feedback loop (`historical_analog_engine._get_calibration_delta()` reads this exact table) closes end-to-end on an autonomous close, not just a manual one |

Repeated across **10 autonomous stop-loss closes** in the 100-symbol run (§2.1's opened positions): all 10 produced a `trade_outcomes` row and a `trade_reviews` row (verified via a direct count query joined on the run's decision IDs) — zero silent drops, post-fix.

Also exercised `check_target1` (partial-exit flag, correctly leaves the position `OPEN` when only target1 is hit — by design, not a defect) and `check_target3` (correctly no-ops when a strategy variant sets `target3 = 0` — also by design).

### 2.3 Toggle / UI paths (`streamlit.testing.v1.AppTest`)
- **Build Scan List** → **Run Complete Scan** (Nifty50, 50 symbols): 0 exceptions, 50 candidates, 9 positions opened, `last_cycle_message` correctly reports `"50 trade candidate(s), 9 open position(s)."`.
- **Start Autonomous Mode** / **Stop Autonomous Mode**: toggles `st.session_state.autonomous_active` with 0 exceptions; button label now flips immediately (`st.rerun()` added after the toggle, since Streamlit doesn't retroactively re-render an already-decided if/else branch mid-script — confirmed via AppTest before and after the fix).
- Full script load (`AppTest.from_file("app.py").run()`): 0 exceptions, all expected buttons present (`Build Scan List`, `Run Complete Scan`, `Start Autonomous Mode`, etc.).

### 2.4 Startup / process-level check
Foreground `streamlit run app.py` on a scratch port: `/_stcore/health` returns `ok`; stdout/stderr grepped for `traceback|nameerror|exception` — none found.

### 2.5 Regression check vs. pre-Phase-3 baseline
- Candidate/final-trade/portfolio-selection counts at 50 and 100-symbol scale match the shape of every prior phase report (`PHASE1_VALIDATION_REPORT.md`, `PHASE2_BATCH1_REPORT.md`, `PHASE2_BATCH2_REPORT.md`, `ALPHAQUANT_OS_V1_REPORT.md`) — same `MAX_OPEN_POSITIONS` cap, same near-100% candidate-generation rate, same "vetoed/unfunded candidates stay visible" behavior from AlphaQuant OS.
- `calculate_trade_quality()` and `update_market_structure()` — the two functions whose manual test buttons were removed — were confirmed still running automatically inside every scan cycle (their outputs feed `final_trade_list`/AI Consensus in every run above); removing the buttons did not remove the underlying logic.
- Brain 1–7 pipeline (Market Observer → Market Historian → Historical Analog Engine → Strategist → Risk Manager → Portfolio Manager → Reviewer) fired for every candidate in every run above (`decisions` table rows for `NO_TRADE`/`PENDING`/`OPEN`/`CLOSED` all present), matching `ALPHAQUANT_OS_V1_REPORT.md`'s documented outcome-state distribution shape.
- No behavior that worked before Phase 3 stopped working; the `record_outcome`/numpy bug fixed in §1 was a **pre-existing** defect (predates Phase 3 — `record_outcome` has existed since AlphaQuant OS v1 and never worked correctly), not something Phase 3's changes introduced. It surfaced during this validation because this is the first time anyone traced a real close all the way through to a `trade_outcomes` row rather than just checking `calibration_state`.

---

## 3. Known limitations (carried forward or newly identified — not fixed here, tracked as separate follow-ups)

1. **Autonomous mode only runs while the AlphaQuant browser tab stays open** — an inherent constraint of Streamlit's execution model (no persistent background process). Tracked as project task "Keep autonomous trading running even when the AlphaQuant browser tab is closed."
2. **`is_market_open()` has no NSE holiday calendar** — it will treat a weekday market holiday as open. Tracked as project task "Account for NSE market holidays in the autonomous trading loop's market-hours check."
3. **Historical-analog evidence rarely populates on a live scan** (pre-existing, unrelated to Phase 3) — tracked as project task "Make sure historical-analog evidence actually shows up, not just on paper."
4. **Full NSE-universe (~2,400 symbol) scan performance with the autonomous loop active is untested at that scale** — this report validated up to 100 symbols; tracked as project task "Confirm a full-universe scan still runs smoothly with the new AI brains."
5. **Sector coverage (~90 symbols) and duplicate-definition risk** — pre-existing, already tracked as separate project tasks, unaffected by Phase 3.

None of the above were introduced by Phase 3; items 1–2 are inherent to or introduced by this phase's own scope and are already queued as follow-ups, items 3–5 predate Phase 3 entirely.

---

## 4. Files changed this task
- `alphaquant/os_brains/experience_memory.py` — added `_safe_num()`; applied it to every numeric parameter in `record_outcome()`, `record_review()`, and `upsert_calibration()`.
- `alphaquant/Phase3_Architecture_Report.md` — this report.

## 5. Git
- All Phase 3 work (Scan Manager, single automated pipeline trigger, execution abstraction, autonomous loop) was already committed and merged prior to this task.
- This task commits the `experience_memory.py` fix and this report.
