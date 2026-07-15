# AlphaQuant OS Institutional UI Migration Report

## What was removed
- Removed duplicate top-level Streamlit rendering from the previous mixed dashboard flow. The application now renders through a single `main()` router and one active page at a time.
- Removed the primary-workflow dependency that required users to manually download market data before running AlphaQuant. The unified pipeline downloads missing data automatically.
- Removed dashboard-surface developer buttons from the trader-facing experience. Developer controls no longer render on Mission Control, Portfolio, Paper Trading, Performance, Markets, Reports, Learning, News Intelligence, Broker Manager, Watchlists, or Settings.

## What was relocated
- Runtime download settings, batch size, parallel workers, diagnostics, debug logs, trade-quality testing, market-structure testing, candidate inspection, database utilities, and pipeline testing are now consolidated under **Developer Mode**.
- Advanced scan settings are available on Mission Control in a collapsed-by-default panel, preserving universe, price, market-cap, liquidity, technical, and pattern controls without cluttering the institutional home view.

## What execution paths were unified
- The app now exposes exactly one trader-facing execution action: **RUN ALPHAQUANT**.
- That one action executes the complete orchestration path: Build Universe → Download Market Data → Market Observer → Trade Candidate Engine → Market Structure → Historical Analog → Strategist → Risk Manager → Portfolio Manager → AI Consensus → Paper Trading → Reviewer → Experience Memory → Dashboard Refresh.

## What developer tools were moved
Developer Mode now contains dedicated tabs for:
- Download Complete Universe
- Trade Quality Testing
- Market Structure Testing
- Trade Candidate Testing
- Database Utilities
- Pipeline Testing
- Diagnostics
- Debug Logs

## What UI sections were created
- Mission Control homepage with live ticker bar, institutional metrics, premium RUN ALPHAQUANT execution block, Mission Pipeline status grid, Decision Funnel, and Top AI Opportunities.
- Markets page placeholder for live macro/index coverage.
- Professional Portfolio page with holdings, cash, allocation, sector allocation, risk, exposure, P&L, drawdown, and broker split tabs.
- Persistent Paper Trading page backed by `data/paper_trades.json`.
- Performance analytics page with equity curve, monthly returns, win rate, profit factor, expectancy, drawdown, Sharpe, and Sortino cards.
- Future-ready News Intelligence page for Moneycontrol, Economic Times, Reuters, company announcements, NSE filings, corporate actions, RBI, SEBI, Budget, and results calendar.
- Future-ready Broker Manager page for Upstox, Zerodha, Angel, Groww, Shoonya, Dhan, and per-broker capital allocation.

## How backward compatibility was preserved
- The AI Brain modules under `os_brains/` were not modified.
- The new app remains Streamlit-based and keeps familiar AlphaQuant state objects, market data storage, trade candidate storage, portfolio selection, and paper-trading concepts.
- Existing core configuration concepts remain available: universe selection, market-cap filters, price filters, liquidity filters, sector/watchlist input, batch size, parallel workers, Trade Quality testing, Market Structure testing, Trade Candidate testing, database utilities, pipeline testing, diagnostics, and debug logs.
- Paper trades are now persisted to disk so restart survival is improved instead of reduced.
