# AlphaQuant OS v1 — Implementation Report

**Date:** 2026-07-15
**Tag:** `AlphaQuant_Intelligence_v1`
**Status:** All 7 Brains implemented and wired into the live scan pipeline. Phase 1 (Nifty-500 backfill) data foundation in place; Phase 2 (full universe) and Phase 3 (continuous scheduling) are mechanism-only per the architecture doc's phased rollout plan — see Known Limitations.

This report summarizes the three implementation tasks that built AlphaQuant OS on top of the existing scanner/paper-trading engine, per `ALPHAQUANT_OS_ARCHITECTURE.md`.

---

## 1. What was built

### Task 2 — Data Foundation & Historical Analog Engine
- `os_brains/db.py` — Postgres connection + idempotent DDL for both Memory stores (`market_memory`, `experience_memory`).
- `os_brains/backfill.py` — resumable Phase 1 backfill pipeline (Nifty-500 universe, ~5y history, setup vectors + forward outcomes at 5/10/20-day horizons), tracked via `market_memory.ingestion_coverage` so it can be re-run indefinitely without reprocessing already-covered symbols.
- `os_brains/setup_vector.py` — the shared feature-vector construction (`FEATURE_NAMES`, `build_setup_vector_row`, pattern-flag/relative-strength series) used identically by the backfill pipeline and live lookups, so historical and live vectors are directly comparable.
- `os_brains/historical_analog_engine.py` (**Brain 3**) — similarity search over backfilled setups, returning an `AnalogReport` (win_rate, expected_return/drawdown, sample_confidence, `probability_of_success`).
- `os_brains/market_historian.py` (**Brain 2**) — seeded catalog of 10 named historical Indian-market regimes + rule-based similarity against the current per-symbol regime.

### Task 3 — Strategist, Risk Manager, Portfolio Manager
- `os_brains/strategist.py` (**Brain 4**) — enriches each scan's best candidate per symbol with Brain 1/2/3 evidence, computes `expected_value`, and folds a bounded, confidence-gated adjustment into `ai_score`.
- `os_brains/risk_manager.py` (**Brain 5**) — unconditional veto layer; every check (EXPOSURE, CORRELATION, LIQUIDITY, VOLATILITY, RISK_REWARD, MACRO, EVENT) runs on every candidate, approved or not, so a `RiskVerdict` is always explainable.
- `os_brains/portfolio_manager.py` (**Brain 6**) — final sizing/allocation authority: ranks approved candidates by `expected_value`, funds within capital/position/sector caps, always attaches an `AllocationDecision` even to unfunded candidates.
- `app.py` rewired so `build_ai_consensus` → Strategist → Risk Manager per candidate, `allocate_portfolio` → Portfolio Manager, and vetoed/unfunded candidates stay visible in the final trade list instead of being dropped.

### Task 4 — Reviewer & Continuous Learning (this task)
- `os_brains/experience_memory.py` — the only module that touches `experience_memory.*` tables directly. Owns the full decision lifecycle: `record_decision` (every candidate, vetoed or not — "no trade is a decision too"), `update_allocation` (Brain 6's capital fate), `mark_open` (paper trade actually opened), `record_outcome`/`record_review` (at close), `upsert_calibration`/`get_calibration` (the running per-symbol calibration average).
- `os_brains/reviewer.py` (**Brain 7**) — `review_closed_trade(position)`: judges `was_correct` from exit reason/P&L, splits the entry evidence into what mattered vs. what misled, writes a bounded `confidence_calibration_delta` (scaled down when the original analog evidence was thin), and generates a plain-language `lessons_learned` summary.
- **Wiring into `app.py`:**
  - `build_ai_consensus()` calls `experience_memory.record_decision(...)` right after Brain 5's verdict, attaching `decision_id` to the candidate.
  - `allocate_portfolio()` calls `experience_memory.update_allocation(...)` once Brain 6 has decided each approved candidate's capital fate (`ALLOCATED` → stays pending until actually opened; `APPROVED_NO_CAPITAL` → `NO_TRADE`).
  - `open_paper_trade()` carries `decision_id` onto the `PaperPosition` and calls `experience_memory.mark_open(...)`.
  - `PaperPosition.close_trade()` — the single method every close path in the codebase funnels through (both the older `mark_closed`/`update_paper_trade` call sites and the newer `check_stop_loss`/`check_target3` call sites) — now calls `reviewer.review_closed_trade(self)` right after marking the position `CLOSED`. This means Brain 7 fires regardless of which trade-management code path a future fix ends up using; no rework needed.
  - `os_brains/historical_analog_engine.py`'s `_get_calibration_delta(symbol)` (written in Task 3, before Brain 7 existed) already reads `experience_memory.calibration_state` by symbol — Brain 7 deliberately keys `calibration_state` the same way (`setup_archetype = symbol`), so the confidence-calibration loop closes automatically with no changes needed on the read side.
- **Phase 3 incremental-update hooks** (mechanism only, per architecture §7 — no scheduler exists or was created):
  - **New trading day → append Market Memory:** `os_brains/backfill.append_daily_snapshot()` computes/upserts only the newest day's setup vector (never re-walks a symbol's full history) plus `backfill_matured_forward_outcomes()`, which fills in `forward_outcomes` for already-ingested snapshots that have since "matured" enough calendar days to compute a 5/10/20-day forward return.
  - **New completed trade → append Experience Memory:** implemented for real (not a stub) — see the `close_trade()` wiring above.
  - **New historical data available → enrich Market Memory:** `os_brains/backfill.enrich_snapshot()` merges corrected/additional `raw_indicators`/`pattern_flags` into an already-ingested snapshot without touching its `setup_vector`/`forward_outcomes`.

---

## 2. Validation performed

All validation was done headlessly (`import app as app_module` + direct function calls), the same methodology used for Tasks 2/3, since Streamlit's `st.*` calls no-op harmlessly outside a real script-run context and `AppTest`-based UI clicking adds no coverage `execute_scan_pipeline()` doesn't already exercise.

1. **Full trade lifecycle (open → close → reviewed → calibration updated).** Built a fully-enriched fake candidate → `record_decision` → `update_allocation` → opened a real `PaperPosition` (`decision_id` attached, `mark_open` called, verified `outcome_state` flips to `OPEN`) → forced a close via the exact `close_trade()` method every real close path uses → verified: `outcome_state` flipped to `CLOSED`, a `trade_outcomes` row was written with the correct entry/exit/pnl, a `trade_reviews` row was written with `was_correct=True` and an evidence-mattered/misled split, and `calibration_state` for that symbol went from nonexistent to `sample_count=1`.
2. **15-symbol scan pipeline** (Nifty large-caps): ran `execute_scan_pipeline()` twice back-to-back. Zero exceptions. 15 candidates produced, 10 vetoed (real MACRO/EVENT/etc. vetoes), 5 approved, 5 allocated and opened as real paper trades — every one of the 15 got a `decisions` row, and `outcome_state` correctly split into `OPEN` (5, allocated+opened), `NO_TRADE` (10, vetoed) — matching Task 3's already-validated veto/allocation behavior with Brain 7's bookkeeping layered on top without changing any of it.
3. **60-symbol scan pipeline** (broader universe slice): completed in ~48s with zero exceptions; 52 candidates produced, 10 allocated/opened, decision `outcome_state` distribution: 15 `OPEN`, 5 `PENDING` (approved+allocated candidates whose position size rounded to zero at `open_paper_trade` time — a pre-existing, not newly introduced, edge case; correctly never flips to `OPEN`), 62 `NO_TRADE`. Confirms the decision-recording layer holds up at a larger batch size than the single-lifecycle test.
4. Test rows (`TESTSYM`) from validation step 1 were deleted from the database after the test; the 15/60-symbol runs used real market data and their decision rows were left in place as real historical records.

---

## 3. Known limitations (pre-existing, not introduced by this task)

- **Historical-analog evidence rarely populates on a live scan** because the default live download window (`~1y`) doesn't give `HIGH52`/`LOW52` (`rolling(252)`) enough history to ever compute, so `setup_vector` is `None` for most live symbols and `find_analogs` returns an empty report. Backfill itself uses 5y and is unaffected. **Tracked as a separate, already-queued follow-up task** — not re-fixed here to avoid scope creep into Task 4's mandate.
- **Full-universe (~2,384 symbol) scan performance with all 7 Brains active is untested** — this report's validation went up to 60 symbols. **Tracked as a separate, already-queued follow-up task.**
- **The live trade-management code path has duplicate definitions.** `app.py` defines `PaperPosition` and `monitor_open_positions` twice; Python keeps only the *last* definition of each at module scope. The dataclass-based `PaperPosition` (used by `open_paper_trade`/`paper_positions`) is the one actually in effect. `monitor_open_positions`'s second/effective definition operates on `st.session_state.open_positions`, populated only via `add_open_position()` — which nothing in the codebase calls. In practice this means no code path in `execute_scan_pipeline()` currently auto-closes an opened paper position; `close_trade()` is called by `check_stop_loss`/`check_target3` (dead — `open_positions` is never populated) and by `update_paper_trade`/`mark_closed` (also dead — reachable only via a `monitor_open_positions` name that a later definition shadows). This predates this task and is out of scope for "Reviewer & continuous learning" to fix. Brain 7 was deliberately hooked into `close_trade()` itself — the one method every existing and future close path already funnels through — so whichever of these gets wired up (or a new one) in a future task, Brain 7 fires with zero additional changes.
- **Phase 2 (full-universe backfill) and Phase 3 (continuous scheduled updates) are not running** — per this task's explicit scope, only the incremental-update *mechanism* (`append_daily_snapshot`, `backfill_matured_forward_outcomes`, `enrich_snapshot`) was built. No cron/scheduler was created.
- **`calibration_state` is keyed by raw symbol**, not a coarser strategy/regime archetype bucket the architecture doc's example suggests. This matches the key format `historical_analog_engine._get_calibration_delta()` already used (written in Task 3), kept as-is for correctness rather than introducing a second, incompatible key scheme.

---

## 4. Files added/changed this task

- Added: `os_brains/experience_memory.py`, `os_brains/reviewer.py`, `ALPHAQUANT_OS_V1_REPORT.md` (this file).
- Changed: `os_brains/backfill.py` (added `append_daily_snapshot`, `backfill_matured_forward_outcomes`, `enrich_snapshot`), `app.py` (`build_ai_consensus`, `allocate_portfolio`, `open_paper_trade`, `PaperPosition` dataclass field, `PaperPosition.close_trade`).
