# Project Plan: Small-Cap Growth Stock Trading System

## Guiding Objectives
- Deliver a modular Python system that discovers, backtests, and signals small-cap growth stocks using four defined strategies.
- Prioritize incremental delivery: working data access and filtering before advanced analytics.
- Maintain reliability through caching, error handling, and repeatable configuration.
- Validate each component with focused tests or dry-run scripts before integration.

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

## Phase 2: Universe Discovery & Screening (Initial Pass)
- [x] ~~Implement universe builder that screens tickers by market cap, volume, float, and sector (Deliverable: `universe/builder.py`; Completed: 2025-09-21; Notes: Yahoo fundamentals + cached snapshots).~~
  - [x] ~~Integrate fundamental data sources (Yahoo fundamentals baseline) (Deliverable: ingestion methods + caching; Result: yfinance fast_info with JSON cache).~~
  - [x] ~~Add liquidity and sector filtering logic (Deliverable: functions returning boolean masks; Result: dollar volume, float, spread, sector & exchange filters).~~
  - [x] ~~Persist resulting universe snapshot (Deliverable: CSV under `data/universe/`; Result: timestamped saves via `UniverseBuilder`).~~

## Phase 3: Strategy Modules (MVP Signals)
- [ ] Deliver Dan Zanger cup-and-handle detector (Deliverable: module + unit tests on synthetic data).
- [ ] Deliver CAN SLIM scorer with weighted criteria (Deliverable: scoring module + threshold logic).
- [ ] Deliver Trend Following EMA crossover strategy (Deliverable: indicator module + signal generator).
- [ ] Deliver Livermore breakout detector (Deliverable: pattern analysis module + signals).
- [ ] Implement signal aggregation logic with configurable weights (Deliverable: aggregator module + tests).

## Phase 4: Risk Management & Portfolio Tracking
- [ ] Build position sizing engine respecting risk and sector caps (Deliverable: portfolio module + tests).
- [ ] Implement drawdown monitoring and alerts (Deliverable: analytics module + logging/email hooks).
- [ ] Create paper trading ledger with entry/exit tracking (Deliverable: CSV-backed ledger + update routines).

## Phase 5: Backtesting & Reporting
- [ ] Implement backtesting engine with transaction costs (Deliverable: `backtesting/engine.py`; tests on synthetic data).
- [ ] Generate performance attribution reports (Deliverable: reporting module + sample output in `reports/`).
- [ ] Provide Jupyter notebook templates for analysis (Deliverable: notebooks demonstrating workflows).

## Ongoing Governance
- [ ] Update this plan after each completed task/sub-task with notes and new discoveries.
- [ ] Maintain logging, error handling, and documentation parity with implemented features.
