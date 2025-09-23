# Refactoring Plan

## Overview
Refactor `main.py` to leverage the modular strategy, backtesting, reporting, and alert infrastructure built across the project. The goal is to replace the monolithic implementation with a clean CLI that orchestrates scanning, backtesting, and reporting using the dedicated modules.

## Tasks

### 1. Extract Configuration Loading
- Identify duplicated configuration logic in `main.py` and replace it with `ConfigManager` usage.
- Ensure CLI commands share a single configuration loading helper.

### 2. Replace Strategy Implementations
- Remove inline strategy classes from `main.py`.
- Wire in modular strategies (`DanZangerCupHandleStrategy`, `CanSlimStrategy`, etc.).

### 3. Integrate Backtesting Pipeline
- Hook CLI backtest command to `BacktestingEngine` and `StrategyBacktestRunner`.
- Ensure outputs are saved via `reports/performance` och `reports/combined` modules.

### 4. Hook Portfolio Monitoring
- Replace manual risk/drawdown calculations with `PortfolioHealthMonitor` and alert manager.
- Update CLI commands for health checks.

### 5. Wire Email Alerts
- Replace inline SMTP usage with `EmailDispatcher`.

### 6. Introduce Notebook & Reporting Commands
- Add CLI option for generating notebooks or reports using the new modules.

### 7. Clean Up Legacy Code
- Remove unused imports, constants, and helper functions from `main.py`.
- Ensure CLI help text is updated.

### 8. Regression Testing
- Add CLI integration tests (if feasible) covering scan/backtest/report commands with sample data.

### 9. Documentation Update
- Update `README` or add new doc describing CLI usage after refactor.
