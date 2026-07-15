# AlphaQuant OS Architecture Audit

This audit was produced before implementation changes.

## Brains
- Market Observer: `os_brains.market_observer.observe/observe_market`; enriches sector/relative-strength context.
- Market Historian: `os_brains.market_historian.seed_regime_catalog/get_regime_context`; maps live regime to historical regimes.
- Historical Analog Engine: `os_brains.historical_analog_engine.find_analogs`; compares setup vectors to historical snapshots.
- Strategist: `os_brains.strategist.enrich_candidate`; adds observer, historian, analog evidence and expected value to candidates.
- Risk Manager: `os_brains.risk_manager.evaluate`; vetoes candidates for exposure, correlation, liquidity, volatility, macro, risk/reward and events.
- Portfolio Manager: `os_brains.portfolio_manager.allocate`; sizes approved candidates under capital, slot and sector constraints.
- Reviewer: `os_brains.reviewer.review_closed_trade`; reviews closed trades and produces calibration lessons.
- Experience Memory: `os_brains.experience_memory`; records decisions, allocations, opens, outcomes, reviews and calibration.
- Database Layer: `os_brains.db`; owns PostgreSQL connection and schema bootstrap.
- Batch 1 engines in `apprelitfinal.py`: multi-timeframe, relative strength, sector, volume profile and demand/supply signals.
- Batch 2 engines in `apprelitfinal.py`: false breakout, smart money, institutional activity and news/earnings filters.
- Trade Candidate Engine in `apprelitfinal.py`: strategy registry plus VCP, breakout, order block, FVG, liquidity, price squeeze and demand/supply candidate creators.
- Paper Trading Engine in `apprelitfinal.py`: paper execution, open position monitoring and trade archiving.

## UI buttons and controls
- Watchlist Add/Remove.
- Build Scan List.
- Download Scan Universe.
- Show Trade Candidates.
- Show Advanced Signals.
- Show Batch 2 Signals.
- Run Complete Scan.
- Start/Stop Autonomous Mode.

## Execution paths and entry points
- Manual developer workflow: Build Scan List -> Download Scan Universe -> Run Complete Scan -> deferred `execute_scan_pipeline()` on rerun.
- Autonomous workflow: Start Autonomous Mode -> fragment calls `run_automated_cycle()` while market is open -> deferred `execute_scan_pipeline()`.
- Legacy path: `legacy_run_complete_scan()` is defined but not called by current UI.
- Display-only path: `show_alphaquant_os_panel()` manually displays OS context for one selected symbol after data exists.

## Pipeline stops and visibility gaps
- Manual intervention is required between universe building, data download, scan execution and dashboard inspection.
- `run_automated_cycle()` queues execution instead of running all stages immediately, hiding failures until a later rerun.
- No single professional mission-control surface exists for progress, brain status, logs, funnel counts, learning updates and reviewer output.
- Rejections are stored in candidate reasons/risk verdicts but not aggregated into a decision funnel.
- No-trade output can still appear as generic empty-state text instead of explaining where candidates were rejected.

## Dead or duplicate functions/modules
- `legacy_run_complete_scan()` is dead relative to the current UI.
- `app.py`, `app1.py`, `apprelit.py`, packaged source copies and zip files duplicate app/module history but are not the active root `apprelitfinal.py` entry point.
- `os_brains.backfill` and `os_brains.setup_vector` are support modules; they are not directly user-triggered in the active UI except through Strategist/Historical Analog code.

## Windows/Replit risks
- Relative `logs` path is safe if launched from repo root but should be anchored to the app directory for arbitrary Windows working directories.
- PostgreSQL configuration relies on environment variables and can fail noisily without a clear health check.
- `psycopg2` may be missing on Windows unless listed/installed; startup should report this clearly.
- Absolute import assumptions are partly mitigated by inserting the app directory into `sys.path`.
