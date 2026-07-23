# AlphaQuant v2.0 RC1 Engineering Audit

**Audit date:** 2026-07-16  
**Release decision:** **REJECT**

This is a forensic, read-only release-gate audit. No production source or
`os_brains/` file was changed as part of this audit.

## 1. Evidence and the reported 6,661-line deletion

The claimed `+353/-6661` change cannot be reproduced from this repository's
reachable Git history. The current branch contains one merged UI PR after the
mission-control merge:

| Range inspected | Additions | Deletions | Finding |
| --- | ---: | ---: | --- |
| `308e5b1..fcdbef7` (merge-base to current UI merge) | 190 | 20 | 114 additions/20 deletions in `app.py`; 76 documentation additions. |
| `308e5b1...fcdbef7` (three-dot PR comparison) | 190 | 20 | Same result; no hidden 6,661-line removal. |
| `e38bd30` (the UI-shell commit) | 190 | 20 | Same result. |

The repository does contain multiple tracked historical application variants,
including `apprelitfinal.py` (8,941 lines) and `app.py` (6,733 lines). Those
files were **not** deleted or renamed in the reviewed PR. Therefore a comparison
of one variant against another is not evidence that a line was deleted from the
current application; it is evidence that the repository has competing,
unconsolidated application entry points. The source PR/branch that produced the
reported `+353/-6661` statistic is required to make a literal section-by-section
mapping of that number.

### Current UI PR section mapping

| Old section | Status | New location | Functionality preserved | Risk |
| --- | --- | --- | --- | --- |
| Legacy page title/caption | Replaced | `app.py` platform hero (lines 189-200) | Branding only | Low |
| Unstyled app shell | Improved | `app.py` design tokens/CSS (lines 135-162) | Existing engines remain below shell | Low |
| Direct page rendering | Merged behind navigation | `app.py` page composition (lines 6682-6717) | Some views are routed; legacy UI still renders earlier | **High: duplicate rendering** |
| Download action label | Renamed | `Developer: Download Complete Universe` (lines 557-576) | Download remains callable | **High: shown outside Developer Mode** |
| Scan action | Renamed | `RUN ALPHAQUANT` (lines 2620-2636) | Scan starts only if data is already loaded | **High: manual pre-download required** |
| Application logic / strategy engines | Not deleted by UI PR | Existing `app.py` functions | Preserved in file | Medium: orchestration does not invoke all Brains |
| `os_brains/` | Unchanged | `os_brains/` | All Brain files remain tracked | Medium: no release-path integration proven |

## 2. Feature inventory: current executable entry point

Status meanings: **Preserved** means code remains callable in `app.py`;
**Moved** means the UI shell routes it; **Improved** means presentation changed;
**Temporarily disabled** means present but unreachable from the trader workflow;
**Removed from current entry point** means present in another tracked variant
but not in `app.py`.

| Feature | Current status | Release-gate observation |
| --- | --- | --- |
| Executive dashboard | Improved, but duplicated | Both the legacy dashboard and productized composition render. |
| Mission Control | Moved, incomplete | Navigation exists, but Dashboard and Mission Control call the same render functions. |
| One `RUN ALPHAQUANT` button | Preserved | Static count is one. |
| One execution pipeline | Preserved, incomplete | `execute_scan_pipeline()` exists, but does not build/download the universe. |
| Universe Builder | Preserved | Full NSE fetch exists. |
| Download missing market data | Temporarily disabled | Separate developer button; primary run explicitly refuses to download. |
| Market Observer | Temporarily disabled | Module exists but current pipeline does not call it. |
| Trade Candidate Engine | Preserved | Strategy registry and candidate creation remain. |
| Market Structure | Preserved | Called by current scan pipeline. |
| Historical Analog | Temporarily disabled | Brain module exists; current scan pipeline does not call it. |
| Strategist | Temporarily disabled | Brain module exists; current scan pipeline does not call it. |
| Risk Manager | Temporarily disabled | Brain module exists; current scan pipeline does not call it. |
| Portfolio Manager | Temporarily disabled | Brain module exists; legacy `allocate_portfolio()` is used instead. |
| AI Consensus | Preserved | `build_ai_consensus()` is called. |
| Paper Trading | Preserved, unsafe | Uses session state; restart durability is not implemented. |
| Paper trades survive restart | Removed from current entry point | No persistence/load call from `app.py`; `DATABASE_URL` is unset in this environment. |
| Reviewer | Temporarily disabled | Module exists; no current pipeline/reconciliation invocation found. |
| Experience Memory | Temporarily disabled | Module exists; no current pipeline/reconciliation invocation found. |
| PostgreSQL schema | Preserved as utility | `os_brains.db.apply_schema()` exists but is not called by `app.py`. |
| Portfolio / performance / reports | Moved, incomplete | Navigation branches exist; data originates in session state only. |
| Learning | Moved, placeholder | Metrics are display-only and do not prove Brain execution. |
| Universe selection | Reduced | Current UI only exposes whole NSE; advanced choices are absent from `app.py`. |
| Nifty50 / Nifty100 / Nifty200 / Nifty500 / F&O | Removed from current entry point | No corresponding active scan selector found. |
| Custom watchlist | Preserved as state only | `watchlist` is initialized, but no active scan-manager UI in `app.py`. |
| Market-cap / price / liquidity filters | Partially preserved | Global min price/volume settings exist; market-cap/turnover filters are absent. |
| Technical / pattern filters | Preserved internally, not selectable | Engines run through registered strategies, with no trader scan controls. |
| Sector filter | Removed from current entry point | Sector scoring exists; no active selector. |
| History / interval / batch size / workers | Preserved | Sidebar controls exist. |
| Developer/database utilities | Incorrectly exposed | Developer download and multiple diagnostics render before page routing. |
| Professional typography / palette | Improved | CSS shell is present, but duplicated legacy content prevents a finished layout. |

## 3. AI Brain audit

`git diff --name-status 308e5b1..HEAD -- os_brains` returned no changed
files. **AI Brains preserved.**

The following Brain modules remain present: `market_observer`,
`market_historian`, `historical_analog_engine`, `strategist`, `risk_manager`,
`portfolio_manager`, `reviewer`, `experience_memory`, `db`, `backfill`,
`setup_vector`, and `pipeline_manager`.

## 4. Execution-pipeline comparison

| Expected RC1 stage | Current primary-button flow |
| --- | --- |
| Build Universe | **Not run** by `RUN ALPHAQUANT`. |
| Download Missing Market Data | **Not run**; button warns to use a separate download step. |
| Market Observer | **Not run**. |
| Trade Candidate Engine | Runs only after externally preloaded data. |
| Market Structure | Runs only after externally preloaded data. |
| Historical Analog | **Not run**. |
| Strategist | **Not run**. |
| Risk Manager | **Not run**. |
| Portfolio Manager | **Not run**; legacy allocation runs instead. |
| AI Consensus | Runs. |
| Paper Trading | Runs through the session-state path. |
| Reviewer | **Not run**. |
| Experience Memory | **Not run**. |
| Dashboard Refresh | Page has already rendered; selected outputs are then appended. |

The old and new verifiable primary flow is therefore the same in the critical
respect: **manual download -> `RUN ALPHAQUANT` -> legacy scan -> consensus ->
legacy allocation -> session-state paper trade.** It is not the requested RC1
flow and does not satisfy the no-manual-download requirement.

## 5. UI audit

| Requirement | Result | Evidence |
| --- | --- | --- |
| Exactly one dashboard | Fail | Legacy dashboard renders before productized page composition. |
| Exactly one Mission Control | Fail | Mission Control shares the dashboard render path and legacy content remains outside it. |
| Exactly one `RUN ALPHAQUANT` | Pass (static) | One literal occurrence. |
| No duplicate rendering | Fail | Productized composition is appended after pre-existing UI. |
| Developer tools only in Developer Mode | Fail | Developer download is rendered before routing. |
| Advanced Scan restored | Fail | Current entry point lacks required universes and filters. |
| Professional navigation / spacing / typography | Partial | Shell styling exists but does not isolate legacy views. |

## 6. Validation performed

* `python3 -m py_compile app.py os_brains/*.py` — passed.
* AST parsing for `app.py` and every `os_brains/*.py` — passed.
* Static control count — one `RUN ALPHAQUANT`, one visible developer download
  action, two `PaperPosition` classes, and two `monitor_open_positions`
  definitions.
* Runtime launch could not be performed because `streamlit` is not installed
  in the audit environment. PostgreSQL could not be exercised because
  `DATABASE_URL` is unset.

## 7. Required incremental stabilization plan

Do not merge or replace `app.py`. Before RC1 can be reconsidered:

1. Add one orchestration adapter that builds the selected universe, downloads
   data, and invokes the existing Brain modules in the required order.
2. Route all developer and database controls exclusively through Developer
   Mode, without removing their underlying functions.
3. Move legacy page render calls behind the existing navigation branches so
   exactly one selected page renders per rerun.
4. Restore the missing scan-manager filters using the existing tracked
   implementation as a reference, then add focused tests for filter outputs.
5. Use the existing database/experience-memory adapters to persist and restore
   paper positions, with a migration and a restart test against PostgreSQL.
6. Resolve duplicate `PaperPosition` and `monitor_open_positions` definitions
   by extracting the authoritative implementation without changing data shape.
7. Run a real Streamlit smoke test, PostgreSQL integration test, one-button
   pipeline test, filter test, paper-trade restart test, and visual regression
   check before changing this decision.
