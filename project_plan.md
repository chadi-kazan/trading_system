# Project Plan: Small-Cap Growth Stock Trading System

## System Reconstruction Blueprint\n### Business Objective\nDeliver a weekly-use research assistant for novice-to-intermediate small-cap investors. The system ingests Yahoo Finance price data and Alpha Vantage fundamentals, applies curated growth strategies (CAN SLIM, Dan Zanger cup-handle, EMA trend following, Livermore breakout), scores opportunities, simulates backtests, and presents actionable dashboards plus education so users understand each signal. Saved watchlist entries track conviction level, status, and score breakdown for ongoing monitoring.\n\n### Implementation Steps
1. Establish Python 3.11 environment with FastAPI, Uvicorn, pandas, yfinance, requests, numpy, and pytest per `requirements.txt`. Ensure storage directories align with `config/default_settings.json` (price cache, universe snapshots, signals, portfolio).
2. Implement FastAPI backend (`dashboard_api/`):
   - `app.py` creates the app, enables CORS for the React host, and registers the `/api` router.
   - `routes/meta.py` exposes `/api/health` and `/api/strategies`; `routes/symbols.py` handles `/api/search` and `/api/symbols/{symbol}` with validation and 429 responses.
   - `services.py` loads config via `ConfigManager`, fetches price history using `YahooPriceProvider`, enriches frames with `enrich_price_frame`, executes all strategies (`strategies/*`), aggregates signals with `SignalAggregator`, applies in-memory caching and Alpha Vantage throttling, and normalises metadata for the API schemas.
3. Retain CLI entry (`main.py`) with subcommands for scans, backtests, reporting, health checks, dataset refresh, Russell downloads, and scheduled fundamentals refresh orchestrated by `automation.fundamentals_refresh`.
4. Provide automated tests under `tests/` covering CLI handlers, strategy logic, indicators, enrichment, and data providers. Use temporary directories and config helpers to isolate side effects.
5. Build React 19 + TypeScript dashboard (`dashboard_web/`) using Vite, Tailwind CSS, Recharts, and `react-router-dom`:
   - App routes: `/` dashboard, `/guides/signals`, `/guides/glossary`, `/watchlist`, `*` 404 fallback.
   - Dashboard renders search panel, scenario callouts, final score doughnut, price chart overlays, aggregated signals, strategy cards, and watchlist controls with status taxonomy.
   - Guides provide interpretation tips, glossary entries with Investopedia links, and watchlist page lists saved signals with search, miniature doughnuts, and deep links back to the dashboard.
6. Run backend with `python -m uvicorn dashboard_api.app:app --reload` and frontend with `npm run dev` (set `VITE_API_BASE_URL`). Build frontend via `npm run build` for static hosting.
7. Document setup, API/SPA usage, and deployment guidance in README and `docs/cloud_deployment_plan.md`; update `project_plan.md` after each milestone with tests and next actions.


## Guiding Objectives
- Deliver a modular Python system that discovers, backtests, and signals small-cap growth stocks using four defined strategies.
- Prioritize incremental delivery: working data access and filtering before advanced analytics.
- Maintain reliability through caching, error handling, and repeatable configuration.
- Validate each component with focused tests or dry-run scripts before integration.
- After every feature implementation suggest a git commit command that i can copy to commit the files you changed.
- Update the README.md file if necessary to document new patterns/usage after every implementation.
- constantly review and update the project plan to add new tasks to it and refine the requirements as i give you instructions. add any instructions i give you here as well when required.

## Phase 0: Planning & Baseline
- [x] ~~Review instructions and capture key constraints (Deliverable: notes in this plan; Completed: 2025-09-21).~~
- [x] ~~Document initial architecture outline covering modules, data flow, and integrations (Deliverable: architecture section in plan; Completed: 2025-09-21).~~

### Architecture Outline
- `config`: `ConfigManager` loads defaults from JSON, overlays env/user overrides, exposes typed views used across modules.
- `data_providers`: Yahoo price fetcher with caching + Alpha Vantage earnings fetcher sharing retry/logging utilities.
- `universe`: Screens fundamentals/liquidity using provider outputs, persists dated universe snapshots.
- `strategies`: One module per strategy returning signal frames; shared indicator helpers in `indicators/`.
- `portfolio`: Risk rules (position sizing, sector caps, drawdown monitor) and paper-trade ledger stored in CSV/SQLite-ready adapters.
- `backtesting`: Engine that replays signals with transaction costs; produces performance metrics consumed by reporting.
- `automation`: Scheduling, email alerts, and reporting pipelines orchestrating scans/backtests weekly.
- `notebooks`: Analyst-facing Jupyter templates referencing the modules above for ad-hoc analysis.

## Phase 1: Core Infrastructure Setup
- [x] ~~Create configuration management module that loads defaults from `config/` and supports user overrides (Deliverable: `trading_system/config_manager.py`; Completed: 2025-09-21; Notes: dataclass-backed loader with validation and env overrides).~~
  - [x] ~~Define configuration schema and defaults aligned with risk/strategy settings (Deliverable: JSON/YAML + dataclasses; Result: dataclasses plus `config/default_settings.json`).~~
  - [x] ~~Implement loader with validation/errors and environment override hooks (Deliverable: callable returning typed config object; Result: `ConfigManager.load` with validation and directory creation).~~
  - [x] ~~Add smoke test or script to verify config load (Deliverable: CLI or pytest covering happy path & missing file; Result: module `__main__` preview and missing-file assertion).~~
- [x] ~~Establish data provider interface with Yahoo Finance price retrieval & CSV caching (Deliverable: `data_providers/yahoo.py`; Completed: 2025-09-21; Notes: Yahoo provider with caching + retry).~~
  - [x] ~~Design provider abstraction & caching policy (Deliverable: interface description + docstring; Result: `data_providers/base.py` protocol & dataclasses).~~
  - [x] ~~Implement daily OHLCV fetch with retry/backoff (Deliverable: function/class method with pandas output; Result: `YahooPriceProvider.get_price_history`).~~
  - [x] ~~Validate performance by retrieving 2 tickers via test script (Deliverable: reproducible test case; Result: `tests/smoke_yahoo_provider.py`).~~
  - [x] ~~Add automated tests for Yahoo provider caching (Deliverable: `tests/test_yahoo_provider.py`; Result: cache validation & refresh cases).~~

## Phase 2: Universe Discovery & Screening (Initial Pass)
- [x] ~~Implement universe builder that screens tickers by market cap, volume, float, and sector (Deliverable: `universe/builder.py`; Completed: 2025-09-21; Notes: Yahoo fundamentals + cached snapshots).~~
  - [x] ~~Integrate fundamental data sources (Yahoo fundamentals baseline) (Deliverable: ingestion methods + caching; Result: yfinance fast_info with JSON cache).~~
  - [x] ~~Add liquidity and sector filtering logic (Deliverable: functions returning boolean masks; Result: dollar volume, float, spread, sector & exchange filters).~~
  - [x] ~~Persist resulting universe snapshot (Deliverable: CSV under `data/universe/`; Result: timestamped saves via `UniverseBuilder`).~~
  - [x] ~~Introduce seed candidate loader and smoke integration (Deliverable: `universe/candidates.py`; Notes: fallback list + optional CSV override).~~
  - [x] ~~Add unit tests for seed candidate loader (Deliverable: `tests/test_candidates.py`; Result: CSV parsing & fallback coverage).~~
  - [x] ~~Add automated unit tests for universe filters (Deliverable: `tests/test_universe_builder.py`; Result: mock ticker injections).~~
  - [x] ~~Capture skipped tickers and relax float/spread handling (Deliverable: `universe/builder.py`; Notes: diagnostics for missing fundamentals).~~

## Phase 3: Strategy Modules (MVP Signals)
- [x] ~~Deliver Dan Zanger cup-and-handle detector (Deliverable: module + unit tests on synthetic data; Completed: 2025-09-21; Notes: `strategies/dan_zanger.py` with configurable params and pytest coverage).~~
  - [x] ~~Establish strategy scaffolding and indicator helpers (Deliverable: `strategies/base.py`, `indicators/moving_average.py`; Notes: shared signal dataclasses).~~

- [x] ~~Deliver CAN SLIM scorer with weighted criteria (Deliverable: scoring module + threshold logic; Completed: 2025-09-21; Notes: `strategies/canslim.py` with pytest coverage).~~
- [x] ~~Deliver Trend Following EMA crossover strategy (Deliverable: indicator module + signal generator; Completed: 2025-09-21; Notes: `strategies/trend_following.py` with EMA/ATR logic and tests).~~
- [x] ~~Deliver Livermore breakout detector (Deliverable: pattern analysis module + signals; Completed: 2025-09-21; Notes: `strategies/livermore.py` with breakout tests).~~
- [x] ~~Implement signal aggregation logic with configurable weights (Deliverable: aggregator module + tests; Completed: 2025-09-21; Notes: `strategies/aggregation.py` with pytest coverage).~~

## Phase 4: Risk Management & Portfolio Tracking
- [x] ~~Build position sizing engine respecting risk and sector caps (Deliverable: portfolio module + tests; Completed: 2025-09-21; Notes: `portfolio/position_sizer.py` with pytest coverage).~~
- [x] ~~Implement drawdown monitoring and alerts (Deliverable: analytics module + logging/email hooks; Completed: 2025-09-21; Notes: `portfolio/drawdown_monitor.py` and `portfolio/alerts.py` with pytest coverage).~~
- [x] ~~Create paper trading ledger with entry/exit tracking (Deliverable: CSV-backed ledger + update routines; Completed: 2025-09-21; Notes: `portfolio/ledger.py` with pytest coverage).~~
- [x] ~~Add equity curve utilities for monitoring (Deliverable: `portfolio/equity_curve.py` + tests).~~
- [x] ~~Integrate portfolio health monitoring (Deliverable: `portfolio/health.py` with alerts/sector checks).~~

## Phase 5: Backtesting & Reporting
- [x] ~~Implement backtesting engine with transaction costs (Deliverable: `backtesting/engine.py`; tests on synthetic data).~~
- [x] ~~Implement individual strategy backtesting harness (Deliverable: `backtesting/runner.py`; tests on synthetic data).~~
- [x] ~~Implement combined strategy backtesting aggregation (Deliverable: `backtesting/combiner.py` + tests).~~
- [x] ~~Generate performance attribution reports (Deliverable: reporting module + sample output in `reports/`; Notes: `reports/performance.py`, `reports/attribution.py`, and `reports/combined.py`).~~
- [x] ~~Provide Jupyter notebook templates for analysis (Deliverable: notebooks demonstrating workflows; Notes: `notebooks/backtest_analysis_template.ipynb`).~~
## Recent Updates (2025-09-24)
- [x] Enhanced dashboard visuals with inline overlays, tooltips, and scenario callouts (Completed: 2025-10-04).\n- [x] Added dashboard education pages (signal guide + glossary with external resources) (Completed: 2025-10-04).
- [x] Added dashboard API caching/throttling guards and surfaced rate-limit responses (Completed: 2025-10-04).
- [x] Expanded scheduler CLI validation tests (limits, throttle, conflict handling) (Completed: 2025-10-04).
- [x] Implemented FastAPI dashboard API endpoints for symbol analysis and search (Completed: 2025-10-04).
- [x] Implemented scheduled fundamentals refresh CLI with validation, configuration extensions, and docs/tests (Completed: 2025-10-04).
- [x] Added rate-limit aware Alpha Vantage retries with enhanced logging (Completed: 2025-10-04).
- [x] Upgraded the backtesting engine to simulate trades with transaction costs and added regression coverage.
- [x] Introduced price-data enrichment to backfill CAN SLIM inputs from OHLCV series and wired it into the CLI backtest flow.
- [x] Added fundamentals loader and enrichment overrides sourced from universe caches.
- [x] Added Russell 2000 seeding support and CLI flag to merge constituents into scans.
- [x] Integrated Alpha Vantage fallback when cached fundamentals are missing.
- [x] Added CLI task to refresh Russell 2000 constituents from an external feed.

## Phase 6: Web Dashboard Delivery (Planned)
- [x] ~~Build watchlist persistence with status taxonomy and saved final score snapshots.~~
- [x] ~~Add watchlist browsing UI with search, per-item donuts, and dashboard deep links.~~
- [x] Final score doughnut visualisation rolling up strategy confidences. (Completed: 2025-10-04).
- [x] ~~Scaffold dedicated FastAPI service layer exposing REST endpoints for strategy summaries, signal breakdowns, and price overlays. (Completed: 2025-10-04; Notes: FastAPI app with search + analysis endpoints and service orchestration.)~~
- [x] ~~Build React SPA (Vite + TypeScript) consuming the API and rendering Recharts-based visualisations for key strategies. (Completed: 2025-10-04; Notes: Vite shell with search, price chart, strategy cards, aggregated signals.)~~
- [x] ~~Implement shared data contracts, caching/throttling guards for live symbol lookups, and graceful error/loading states. (Completed: 2025-10-04; Notes: in-memory caches, Alpha Vantage throttle guard, 429 surfacing.)~~
- [x] ~~Polish UI with an Alpaca-inspired card layout, search-driven workflows, and manual refresh controls. (Completed: 2025-10-04; Notes: Tailwind CSS upgrade with React 19 visuals.)~~
- [x] ~~Update README with backend/frontend setup steps and capture follow-up task for eventual cloud deployment. (Completed: 2025-10-04; Notes: README sections + Cloud deployment doc).~~

## Next Actions
1. Monitor the first scheduled fundamentals run and review validation logs for anomalies.
2. Evaluate automated tests/Cypress smoke checks for the Tailwind React dashboard.
3. Draft Docker Compose + deployment artifacts for repo (build scripts, env samples).

## Ongoing Governance
- [ ] Update this plan after each completed task/sub-task with notes and new discoveries. (Last refreshed 2025-10-04)
- [ ] Maintain logging, error handling, and documentation parity with implemented features. (Docs refresh pending for new backtest pipeline)
- [ ] Integrate broader candidate feed (e.g., Russell 2000 constituents) for richer universe seeds.
## Weighing Strategies Initiative
- [ ] Document the reliability-weighted scoring methodology in README with novice-friendly diagrams and examples.
- [ ] Design SQLModel extensions (Strategy, MarketRegime, StrategyRegimeSnapshot, StrategyMetricHistory) and plan migrations for storing rolling metrics.
- [ ] Implement FastAPI models and endpoints for reading/updating strategy performance metrics and reliability weights.
- [ ] Build analytics job or CLI workflow to refresh rolling stats, regime detection, and exponential decay parameters.
- [ ] Create frontend diagnostics pages and visualisations (weight trends, regime timelines, correlation heatmaps) backed by the new endpoints.
- [ ] Integrate dynamic weights into dashboard scoring and expose per-strategy contributions across watchlist saves.
- [ ] Add automated tests plus documentation updates covering the weighting pipeline and diagnostics UI.

