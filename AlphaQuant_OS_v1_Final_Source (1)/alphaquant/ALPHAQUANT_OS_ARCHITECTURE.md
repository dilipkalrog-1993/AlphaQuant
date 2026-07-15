# AlphaQuant OS — Architecture

**Status:** Design specification. No code in this repository implements this document yet — it is the contract that the AlphaQuant OS implementation tasks (Data Foundation → Decision Layer → Reviewer/Continuous Learning) must build against.

**Supersedes framing:** AlphaQuant is no longer "a stock scanner with an AI Consensus Engine bolted on." It is an AI capital-allocation operating system made of independent, cooperating modules ("Brains") that observe, remember, decide, and learn. The scanner, Batch 1, and Batch 2 signal engines already built are not thrown away — they become the sensory inputs of Brain 1 and Brain 4 below.

---

## 1. Philosophy

AlphaQuant exists for one purpose: **to allocate capital only when the available evidence justifies risking capital.**

Operating principles, in priority order:

1. **Capital preservation before capital appreciation.** A drawdown that is avoided is worth more than a gain that is captured. Every Brain that can say "don't," should be free to say it without needing to justify inaction.
2. **The objective is not to maximize the number of trades.** Trade count is not a KPI. Risk-adjusted, compounded wealth is.
3. **"No trade" is a successful decision, not a null result.** When the system declines to allocate capital, that decision is logged, explained, and counted as a first-class outcome next to "trade taken" — never rendered as an empty table or silence.
4. **The question is never "should I buy?"** It is **"should I allocate capital, and if so, how much, why, and what is the expected value given historical evidence?"**
5. **Every decision must be explainable after the fact**, using the same evidence structure whether the outcome was a win, a loss, or a pass.

This philosophy is enforced structurally, not just in prose: Brain 5 (Risk Manager) has unconditional veto power over every other Brain, and the AI Decision Engine's output type always includes a valid "no allocation" state (see §6).

---

## 2. The Seven Brains

Each Brain is a single-responsibility module. It receives a defined input, returns a defined structured output, and never reaches into another Brain's internal state — only into its published output and the two Memory stores (§3). This section is the contract; implementation tasks fill in the concrete logic.

### Brain 1 — Market Observer

**Responsibility:** Observe current conditions. Never decide, never score toward a trade, never veto.

**Inputs:** Live/recent OHLCV data, sector membership, relative strength inputs, breadth data (advance/decline across the scanned universe), news headlines, earnings calendar, macro/index data, futures & open interest where available.

**Output contract** (`MarketObservation`, one per symbol per scan + one per market-wide scan):
```
{
  symbol: str | None,          # None for market-wide observations
  timestamp: datetime,
  price: {last, ohlc, atr, rvol},
  volume: {value, zscore, obv_trend, adl_trend},
  breadth: {advancers, decliners, unchanged} | None,   # market-wide only
  sector: {name, relative_rank},
  relative_strength: float,     # 0-100, vs universe
  news: {days_to_earnings, recent_headlines: [...]},
  macro: {index_regime, index_trend} | None,            # market-wide only
  futures_oi: {...} | None                              # only if a source is available
}
```

**Absorbs existing code:** `run_batch1_signal_engines` (Multi-Timeframe, Relative Strength, Sector, Volume Profile), `analyze_institutional_activity` (OBV/ADL/volume-zscore proxy), `prefetch_news_earnings` / `check_news_earnings_filter`, `detect_market_regime`'s raw trend/ADX/RVOL/gap measurements. These functions are not rewritten from scratch — Brain 1 is the module that calls them and assembles their raw outputs into one `MarketObservation`, rather than each caller reaching into `stock.score`/`stock.indicators` directly.

**Never does:** score a trade, apply a bonus/penalty, decide anything actionable.

### Brain 2 — Market Historian

**Responsibility:** Remember historical market behavior at the *regime* level — not individual stock patterns (that is Brain 3's job), but named periods of market-wide behavior.

**Inputs:** A seeded catalog of known historical regimes (2008 Financial Crisis, COVID Crash, post-COVID recovery, rate-hike cycles, election periods, Union Budget days, identified bull/bear/liquidity-crisis windows), each tagged with date ranges and market-wide characteristics (index drawdown, volatility regime, breadth behavior). Also ingests `detect_market_regime`'s existing per-symbol regime classification (`TRENDING_BULL` / `TRENDING_BEAR` / `SIDEWAYS`) as the *current* state to compare against history.

**Output contract** (`RegimeContext`):
```
{
  as_of: datetime,
  current_regime: "TRENDING_BULL" | "TRENDING_BEAR" | "SIDEWAYS",
  current_regime_strength: int,           # 0-100, from detect_market_regime
  nearest_historical_regimes: [
    { regime_name, date_range, similarity_score, characteristics, how_it_resolved }
  ]
}
```

**Absorbs existing code:** `detect_market_regime`, `apply_market_regime_bonus` supplies the *current* half of the comparison; the historical catalog and similarity-to-catalog matching is new. `apply_market_regime_bonus`'s confidence adjustment logic is retired from being applied directly to a trade — its knowledge (bull market → favorable, bear/sideways → unfavorable) becomes an input Brain 4 consumes from Brain 2's output instead of a side effect buried in trade scoring.

**Never does:** evaluate a specific stock's setup (Brain 3) or produce a trade candidate (Brain 4).

### Brain 3 — Historical Analog Engine

**Responsibility:** Given a specific stock's current setup, find statistically similar historical setups (any stock, any time, within the backfilled dataset) and report what happened after them.

**Market-state representation:** each historical trading day for a backfilled symbol is reduced to a fixed-length, normalized numeric vector ("setup vector") capturing: trend state (EMA20/50/200 ordering as ordinal), ADX, RVOL, ATR relative to its 20-day average, distance from 52-week high/low, sector relative strength percentile, volume z-score, and the Batch 1/2 pattern flags active that day (BOS/CHOCH, order block presence, sweep presence, FVG presence) encoded as booleans. All continuous fields are z-score normalized against the full backfilled dataset (not per-symbol) so setups are comparable across stocks.

**Similarity method:** cosine similarity over the normalized setup vector, restricted first to the top-N nearest neighbors (e.g. N=50) by vector distance, then filtered to a minimum similarity threshold. This is a design-level choice, not a locked implementation — the Data Foundation task may substitute a comparably-simple metric (e.g. weighted Euclidean distance) if it measures better in practice, as long as the output contract below is unchanged.

**Output contract** (`AnalogReport`):
```
{
  symbol: str,
  as_of: date,
  setup_vector: [...],
  matched_analogs_count: int,
  win_rate: float,                 # % of analogs where forward return over the holding window was positive
  expected_return: float,          # mean forward return over the holding window
  expected_drawdown: float,        # mean max adverse excursion before resolution
  recovery_time_days: float | None,
  typical_holding_period_days: float,
  probability_of_success: float,   # calibrated, not identical to win_rate — see Brain 7
  sample_confidence: "LOW" | "MEDIUM" | "HIGH"   # based on matched_analogs_count
}
```

`sample_confidence` exists so downstream Brains can discount a result built on 4 historical analogs versus one built on 400 — this is the mechanism that keeps Phase 1's smaller dataset honest rather than overconfident.

**Never does:** decide whether to trade — it only reports historical evidence for Brain 4 to weigh.

### Brain 4 — Strategist

**Responsibility:** Produce candidate trades. The only Brain allowed to say "this looks like an opportunity."

**Inputs:** Brain 1's `MarketObservation`, Brain 2's `RegimeContext`, Brain 3's `AnalogReport`, plus the existing technical/structural signal stack (trend, momentum, volume, Smart Money Concepts via `analyze_smart_money_concepts`, existing strategy registry entries — Order Blocks, Liquidity Sweeps, FVGs, Demand & Supply, False Breakout Detection).

**Output contract** (`TradeCandidate` — extends the existing trade-candidate object, does not replace it):
```
{
  ...existing fields (symbol, strategy, entry, stop, target1-3, confidence, risk_reward)...
  analog_report: AnalogReport,
  regime_context: RegimeContext,
  evidence_summary: [ {factor, direction, weight, note}, ... ],   # feeds Brain 7 explainability later
  expected_value: float          # win_rate * expected_return - (1 - win_rate) * expected_drawdown, at minimum
}
```

**Absorbs existing code:** `run_all_strategies`, `run_batch1_signal_engines`, `run_batch2_signal_engines`'s trade-scoring parts (Smart Money, False Breakout, News/Earnings penalty — Institutional Activity moves to Brain 1 as an observation, but its *scoring interpretation* stays here). Brain 4 is where `build_ai_consensus`'s current per-symbol scoring logic lives going forward, extended with `analog_report` and `expected_value`.

**Never does:** check portfolio-level risk, size a position, or have the final word — Brains 5 and 6 sit downstream of every candidate Brain 4 produces.

### Brain 5 — Risk Manager

**Responsibility:** Veto. The only Brain with unconditional authority to reject a `TradeCandidate` before it can be acted on.

**Checks:** portfolio exposure (current `MAX_OPEN_POSITIONS`, existing sector concentration), correlation across currently open positions, liquidity (existing `MIN_AVG_VOLUME`/`MIN_AVG_TURNOVER` filters plus position-size-vs-average-volume), volatility (ATR relative to normal range), risk/reward ratio floor, macro risk (Brain 2's current regime — e.g. auto-tighten or veto in `TRENDING_BEAR`/high-volatility regimes), event risk (Brain 1's `days_to_earnings` proximity).

**Output contract** (`RiskVerdict`):
```
{
  candidate_symbol: str,
  verdict: "APPROVED" | "VETOED",
  vetoed_by: [ "EXPOSURE" | "CORRELATION" | "LIQUIDITY" | "VOLATILITY" | "RISK_REWARD" | "MACRO" | "EVENT" ],
  reason: str    # human-readable, always populated even when approved (e.g. "within all limits")
}
```

A vetoed candidate is never silently dropped — it must remain visible (UI/log) as "considered, not taken" with its reason, consistent with the philosophy that "no trade" is a visible outcome.

### Brain 6 — Portfolio Manager

**Responsibility:** For every `RiskVerdict: APPROVED` candidate, decide position size and portfolio-level allocation.

**Inputs:** Approved candidates ranked by `expected_value`, current open positions, available capital, sector allocation state, `CONFIG["RISK_PER_TRADE"]` and related sizing config.

**Output contract** (`AllocationDecision`):
```
{
  symbol: str,
  position_size: int,
  capital_required: float,
  sector_allocation_after: {sector: pct, ...},
  cash_reserved: float,
  rationale: str
}
```

**Absorbs existing code:** `calculate_position_size`, `update_trade_position_sizes` — extended to consider sector-level and portfolio-level caps rather than a single trade's risk in isolation.

### Brain 7 — Reviewer

**Responsibility:** Review every completed trade (and, longer-term, notable "no trade" decisions) after the fact.

**Inputs:** A closed `PaperPosition` (existing `mark_closed` lifecycle) plus the `TradeCandidate`, `RiskVerdict`, and `AllocationDecision` that produced it (read from Experience Memory, §3).

**Output contract** (`TradeReview`):
```
{
  symbol: str,
  closed_at: datetime,
  was_correct: bool,              # did the trade thesis play out
  evidence_that_mattered: [str],
  evidence_that_misled: [str],
  confidence_calibration_delta: float,   # adjustment applied to future confidence for similar setups
  lessons_learned: str
}
```

`confidence_calibration_delta` is the mechanism by which Brain 3's `probability_of_success` diverges from raw `win_rate` over time — repeated misleading evidence for a given setup type or symbol systematically discounts future confidence for that pattern, without needing to retrain a model.

---

## 3. The Two-Memory Model

Market Memory and Experience Memory are deliberately separate stores with different owners, different write patterns, and different lifecycles. Neither Brain reads or writes the other's tables directly — access goes through each store's own interface module (§5).

### Market Memory

**Owns:** facts about the market that are true independent of anything AlphaQuant itself has ever done. Historical regimes, historical analog setups and their outcomes, support/resistance levels, demand/supply zones, volume profile nodes, institutional-activity proxy history.

**Write pattern:** append-mostly. New trading days append new rows; the historical regime catalog and backfilled analog dataset are populated by the Data Foundation task and grow via the Phase 1 → 2 → 3 rollout (§7), never rewritten wholesale.

**Proposed schema (Postgres):**

```sql
-- One row per (symbol, trading_day): the raw material for Brain 3's setup vectors.
CREATE TABLE market_memory.daily_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    symbol          TEXT NOT NULL,
    trading_day     DATE NOT NULL,
    close           NUMERIC,
    setup_vector    JSONB NOT NULL,      -- normalized feature vector, see Brain 3
    raw_indicators  JSONB,               -- EMA20/50/200, ADX, RVOL, ATR, etc. for debugging/re-derivation
    pattern_flags   JSONB,               -- BOS/CHOCH/order-block/sweep/FVG booleans for that day
    sector          TEXT,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    ingestion_phase SMALLINT NOT NULL,   -- 1 = top-500/5yr backfill, 2 = full universe, 3 = continuous daily
    UNIQUE (symbol, trading_day)
);
CREATE INDEX ON market_memory.daily_snapshots (trading_day);
CREATE INDEX ON market_memory.daily_snapshots USING GIN (setup_vector);

-- Forward outcomes for each snapshot, at one or more holding horizons.
CREATE TABLE market_memory.forward_outcomes (
    id                  BIGSERIAL PRIMARY KEY,
    snapshot_id         BIGINT NOT NULL REFERENCES market_memory.daily_snapshots(id),
    holding_period_days INT NOT NULL,
    forward_return      NUMERIC,
    max_drawdown        NUMERIC,
    max_favorable_move  NUMERIC,
    recovered_by_day    INT,             -- NULL if never recovered within the holding window
    UNIQUE (snapshot_id, holding_period_days)
);

-- Named historical market regimes (Brain 2's catalog). Seeded once, rarely rewritten.
CREATE TABLE market_memory.historical_regimes (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,       -- "2008 Financial Crisis", "COVID Crash", etc.
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    characteristics JSONB NOT NULL,      -- index drawdown, volatility regime, breadth behavior
    notes           TEXT
);

-- Market-wide structural levels (support/resistance, demand/supply, volume-profile nodes,
-- institutional-activity proxy zones) kept separate from per-day snapshots since they persist
-- across many days until invalidated.
CREATE TABLE market_memory.structural_levels (
    id           BIGSERIAL PRIMARY KEY,
    symbol       TEXT NOT NULL,
    level_type   TEXT NOT NULL,          -- SUPPORT | RESISTANCE | DEMAND_ZONE | SUPPLY_ZONE | VOLUME_NODE | INSTITUTIONAL_ZONE
    price_low    NUMERIC NOT NULL,
    price_high   NUMERIC NOT NULL,
    first_seen   DATE NOT NULL,
    last_valid   DATE,                   -- NULL while still considered active
    strength     INT,
    metadata     JSONB
);
CREATE INDEX ON market_memory.structural_levels (symbol, level_type);

-- Tracks ingestion coverage explicitly, so Phase 2/3 expansion knows what is already done
-- without scanning the whole daily_snapshots table.
CREATE TABLE market_memory.ingestion_coverage (
    symbol          TEXT PRIMARY KEY,
    first_day       DATE NOT NULL,
    last_day        DATE NOT NULL,
    phase           SMALLINT NOT NULL,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

This schema is sized for growth: `ingestion_phase` and `ingestion_coverage` mean Phase 2 (remaining universe) and Phase 3 (continuous daily append) are just more rows with `phase = 2/3` and later `last_day` values — no column additions, no migration, no backfill-in-place rewrite.

### Experience Memory

**Owns:** facts about what AlphaQuant itself decided and how it turned out. This is the store Brain 7 writes to and reads from, and the one that makes "continuous learning" possible without retraining a model — it is a growing, queryable ledger of decisions and outcomes.

**Write pattern:** append-on-decision, append-on-close, occasional calibration-summary updates. Never rewrites history — a `TradeReview` is a new row referencing the trade it reviews, not an edit to the original decision record.

**Proposed schema (Postgres):**

```sql
-- One row per candidate AlphaQuant's Strategist produced, whether or not it was ever taken.
CREATE TABLE experience_memory.decisions (
    id                  BIGSERIAL PRIMARY KEY,
    symbol              TEXT NOT NULL,
    decided_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    trade_candidate     JSONB NOT NULL,   -- full TradeCandidate incl. evidence_summary, expected_value
    regime_context      JSONB NOT NULL,
    analog_report       JSONB NOT NULL,
    risk_verdict        JSONB NOT NULL,   -- includes veto reason when applicable
    allocation_decision JSONB,            -- NULL when vetoed / not allocated
    outcome_state       TEXT NOT NULL DEFAULT 'PENDING'  -- PENDING | NO_TRADE | OPEN | CLOSED
);
CREATE INDEX ON experience_memory.decisions (symbol, decided_at);
CREATE INDEX ON experience_memory.decisions (outcome_state);

-- One row per closed paper position, linked back to the decision that opened it.
CREATE TABLE experience_memory.trade_outcomes (
    id              BIGSERIAL PRIMARY KEY,
    decision_id     BIGINT NOT NULL REFERENCES experience_memory.decisions(id),
    opened_at       TIMESTAMPTZ NOT NULL,
    closed_at       TIMESTAMPTZ NOT NULL,
    entry           NUMERIC NOT NULL,
    exit_price      NUMERIC NOT NULL,
    exit_reason     TEXT NOT NULL,        -- STOP LOSS | TARGET | manual, etc.
    pnl             NUMERIC NOT NULL,
    max_drawdown    NUMERIC,
    max_profit      NUMERIC
);

-- Brain 7's review of each closed trade outcome (and, later, notable no-trade decisions).
CREATE TABLE experience_memory.trade_reviews (
    id                            BIGSERIAL PRIMARY KEY,
    decision_id                   BIGINT NOT NULL REFERENCES experience_memory.decisions(id),
    reviewed_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    was_correct                   BOOLEAN NOT NULL,
    evidence_that_mattered        JSONB,
    evidence_that_misled          JSONB,
    confidence_calibration_delta  NUMERIC NOT NULL,
    lessons_learned               TEXT
);

-- Running calibration state per setup archetype, updated as trade_reviews accumulate. This is
-- what Brain 3 reads to turn win_rate into probability_of_success.
CREATE TABLE experience_memory.calibration_state (
    setup_archetype   TEXT PRIMARY KEY,   -- e.g. a coarse bucket derived from the setup_vector / strategy name
    sample_count      INT NOT NULL DEFAULT 0,
    avg_calibration_delta NUMERIC NOT NULL DEFAULT 0,
    last_updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Portfolio-level performance over time, independent of individual trades.
CREATE TABLE experience_memory.portfolio_snapshots (
    id            BIGSERIAL PRIMARY KEY,
    snapshot_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    open_positions INT NOT NULL,
    closed_trades  INT NOT NULL,
    net_pnl        NUMERIC NOT NULL,
    win_rate       NUMERIC,
    metadata       JSONB
);
```

Storing full `TradeCandidate`/`RegimeContext`/`AnalogReport`/`RiskVerdict` as JSONB on `decisions` (rather than normalizing every field into columns) is a deliberate choice: these structures will evolve as Brains 3-6 are refined, and JSONB avoids a migration on every field addition while still being queryable (Postgres JSONB supports indexing and containment queries when needed).

---

## 4. Historical Analog Engine — Design Detail

(Elaborates Brain 3's contract in §2 with the specifics implementation will need.)

- **Setup vector construction:** built once per `(symbol, trading_day)` at backfill time and stored in `daily_snapshots.setup_vector`; built on-demand for the *current* day during a live scan using the same feature function, so historical and live vectors are guaranteed comparable.
- **Normalization:** z-score every continuous feature against the full `daily_snapshots` population (recomputed periodically, not per-query, to keep lookups fast) — not per-symbol, so a setup on a small-cap and a setup on a large-cap are directly comparable when their *shape* is similar.
- **Similarity:** cosine similarity, top-N (default 50) nearest neighbors, then a minimum-similarity cutoff before computing aggregate stats. If fewer than a practical minimum (e.g. 10) analogs clear the cutoff, `sample_confidence` is `LOW` and Brain 4 must discount `expected_value` accordingly rather than treating it as equally reliable.
- **Holding period:** stats are computed at a small fixed set of holding horizons (e.g. 5, 10, 20 trading days) stored in `forward_outcomes`; `AnalogReport.typical_holding_period_days` reports whichever horizon has the strongest historical edge for that specific setup, not a single hardcoded value for all setups.
- **Excludes same-symbol lookahead:** when searching analogs for `symbol` on `trading_day`, matches from that same symbol within the trade's own likely holding window are excluded to avoid a setup "matching itself."

---

## 5. Module Interfaces

Each Brain and each Memory store is a separate module exposing a narrow function-level interface. No Brain queries another Brain's internals or another Memory store's tables directly.

```
market_observer.observe(symbol) -> MarketObservation
market_observer.observe_market() -> MarketObservation   # market-wide, symbol=None

market_historian.get_regime_context() -> RegimeContext

historical_analog_engine.find_analogs(symbol, setup_vector) -> AnalogReport

strategist.generate_candidates(observation, regime_context, analog_report) -> list[TradeCandidate]

risk_manager.evaluate(candidate, portfolio_state) -> RiskVerdict

portfolio_manager.allocate(approved_candidates, portfolio_state) -> list[AllocationDecision]

reviewer.review(decision_id) -> TradeReview

market_memory.record_snapshot(...) / market_memory.query_analogs(...) / market_memory.get_regimes(...)
experience_memory.record_decision(...) / experience_memory.record_outcome(...) / experience_memory.record_review(...) / experience_memory.get_calibration(setup_archetype)
```

The AI Decision Engine (what `build_ai_consensus`/`show_ai_consensus` becomes) is the orchestrator that calls Brains 1 → 2 → 3 → 4 → 5 → 6 in sequence for each scan, persists the result via `experience_memory.record_decision`, and renders both taken trades and vetoed/no-trade candidates as equally first-class outcomes.

---

## 6. Mapping Existing Code to Brains

| Existing code | Becomes part of |
|---|---|
| `run_batch1_signal_engines` (MTF, Relative Strength, Sector, Volume Profile) | Brain 1 (Market Observer) — raw observation |
| `analyze_institutional_activity` | Brain 1 (Market Observer) — raw observation |
| `prefetch_news_earnings` / `check_news_earnings_filter` | Brain 1 (Market Observer) — raw observation |
| `detect_market_regime` (current-state half) | Brain 2 (Market Historian) input |
| `apply_market_regime_bonus` | Retired as a direct trade-confidence mutator; its knowledge becomes a `RegimeContext` input Brain 4 weighs explicitly |
| `analyze_smart_money_concepts`, `detect_false_breakout`, strategy registry (Order Blocks, Sweeps, FVG, Demand & Supply) | Brain 4 (Strategist) — candidate generation |
| `build_ai_consensus` scoring logic | Brain 4 (Strategist) output + AI Decision Engine orchestration |
| `calculate_position_size`, `update_trade_position_sizes` | Brain 6 (Portfolio Manager), extended with sector/portfolio-level caps |
| `MAX_OPEN_POSITIONS`, `MIN_AVG_VOLUME`, `MIN_AVG_TURNOVER` checks | Brain 5 (Risk Manager) checks |
| `PaperPosition` lifecycle (`mark_closed`, `paper_history`) | Trigger for Brain 7 (Reviewer) + `experience_memory.record_outcome` |

No existing Batch 1/2 engine is deleted or duplicated — each is relocated to the Brain whose responsibility matches what it already does.

---

## 7. Phased Rollout Plan

**Phase 1 — Data Foundation.** Provision Postgres; create the Market Memory and Experience Memory schemas above. Implement Brain 1 and Brain 2 as thin structuring layers over existing code. Backfill `daily_snapshots` + `forward_outcomes` for the ~500 most liquid NSE stocks over ~5 years, run as a resumable, chunked pipeline (not a single long-running job), tagging every row `ingestion_phase = 1`. Implement Brain 3 (Historical Analog Engine) against that backfilled data. No trading decisions change yet.

**Phase 2 — Decision Layer.** Implement Brain 4 (Strategist), Brain 5 (Risk Manager), Brain 6 (Portfolio Manager). Reframe the AI Decision Engine around allocate/no-allocate outcomes, both rendered as first-class results. Fully replaces the current flat weighted-sum `ai_score` with the Brain 1→6 pipeline.

**Phase 3 — Reviewer & Continuous Learning.** Implement Brain 7. Wire `experience_memory.record_decision/outcome/review` into the paper-trading lifecycle. Implement the three incremental-update hooks:
- *New trading day* → append that day's `daily_snapshots`/`forward_outcomes` rows (does not reprocess history).
- *New completed trade* → append to `experience_memory` and trigger a Brain 7 review.
- *New historical data becomes available* → enrich `market_memory` incrementally (used by the later full-universe backfill and continuous-update phases below, without requiring this phase's code to change).

**Phase 4 (future, not yet scheduled as a task) — Full NSE Universe.** Extend the same backfill pipeline to the remaining NSE symbols, tagging new rows `ingestion_phase = 2`. No schema change required; `market_memory.ingestion_coverage` tracks what remains.

**Phase 5 (future, not yet scheduled as a task) — Continuous Daily Updates.** A scheduled job appends each new trading day's snapshots/outcomes automatically (`ingestion_phase = 3`), keeping the Historical Analog Engine's dataset current without manual re-runs.

This document does not schedule Phases 4-5 as project tasks — they are named here so the schema and pipeline design in Phases 1-3 are held accountable to supporting them without a rewrite, per the incremental-learning requirement.
