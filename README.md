# Small-Cap Growth Trading System

## What This Tool Delivers
The Small-Cap Growth Trading System is a modular research and execution toolkit designed to help growth-oriented investors:

- Discover small-cap equities that meet liquidity, float, spread, and sector-quality filters.
- Generate and evaluate trading signals from four technical and fundamental strategies.
- Backtest single or multi-strategy portfolios with trade-by-trade simulation, configurable capital allocation, and risk limits.
- Produce attribution, performance, and combined equity reports suitable for investment memos or LP updates.
- Monitor live portfolios for drawdown and sector concentration breaches, triggering email alerts when risk limits are violated.
- Spin up analyst notebooks pre-wired to the latest reports for deeper dive analysis.

Every capability is orchestrated by `main.py`, which exposes a cohesive CLI while delegating actual analytics to the underlying modules (`universe`, `strategies`, `backtesting`, `reports`, `portfolio`, `automation`).

---

## Table of Contents
1. [Prerequisites & Installation](#prerequisites--installation)
2. [Configuration Basics](#configuration-basics)
3. [CLI Reference](#cli-reference)
4. [Investor Workflows & Methodologies](#investor-workflows--methodologies)
   - [Universe Screening](#universe-screening)
   - [Strategy Methodologies](#strategy-methodologies)
   - [Backtesting & Attribution](#backtesting--attribution)
   - [Portfolio Health Monitoring](#portfolio-health-monitoring)
   - [Notebook Generation](#notebook-generation)
5. [Architecture & Module Overview](#architecture--module-overview)
6. [Testing & Quality Assurance](#testing--quality-assurance)
7. [Troubleshooting & FAQ](#troubleshooting--faq)
8. [Next Steps](#next-steps)

---

## Prerequisites & Installation

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | Aligns with the virtual environment used in development.
| pip | Required to install dependencies.
| Optional: `yfinance`, SMTP credentials | Needed for Yahoo Finance downloads and email alerts if you use those features.

```bash
# 1. Create & activate a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install extra tooling for reports or notebooks if desired
pip install jupyter
```

> **Heads-up**: The CLI automatically raises informative errors if `yfinance` or other optional packages are missing when you attempt to use related features.

---

## Configuration Basics
The system centralizes settings through `trading_system.config_manager.ConfigManager`. Defaults live in `config/default_settings.json` and can be overridden by `config/settings.local.json` or alternative paths passed via CLI flags.

Key configuration sections:
- **email** – SMTP settings consumed by `automation/emailer.py`.
- **risk_management** – Maximum positions, individual/portfolio stops, and sector limits used by `portfolio.position_sizer.PositionSizer` and `portfolio.health.PortfolioHealthMonitor`.
- **strategy_weights** – Default allocations for combined backtests and reporting weights.
- **data_sources** – Caching controls for Yahoo downlinks.
  - Set `alpha_vantage_key` (or `TS_ALPHA_VANTAGE_KEY`) to enable on-demand Alpha Vantage fundamentals when cached files are missing.
- **universe_criteria** – Market-cap, volume, float, spread, and sector filters enforced by `universe/builder.py`.
- **storage** – Output directories for cached prices, signal archives, and portfolio snapshots.
- **fundamentals** - Optional CSV/JSON caches under `storage.universe_dir` that override enrichment metrics (earnings growth, relative strength).
- **automation** - Houses scan scheduling plus `fundamentals_refresh` options (frequency, time/day, Russell merge flags, validation thresholds) consumed by the automation CLI.

**Override hierarchy:** `defaults` ? `user settings` ? `environment variables` (prefixed with `TS_`). Use `--defaults` or `--settings` with any CLI command to swap configuration files on the fly.

---

## CLI Reference
All workflows route through `python main.py <command>`. Global flags available to every command:

| Flag | Description |
|------|-------------|
| `--settings PATH` | Use an alternate user settings JSON. |
| `--defaults PATH` | Use an alternate default settings JSON. |
| `--force-config-reload` | Bypass the cached config and reload from disk. |
| `--verbose` | Switch logging to DEBUG for deeper diagnostics. |

Commands:
- `scan` – Run the universe screening pipeline.
- `backtest` – Backtest one or more strategies.
- `report` – Inspect previously generated CSV reports.
- `health` – Evaluate drawdown and sector health of a portfolio snapshot.
- `notebook` – Copy the prebuilt analysis notebook to a destination workspace.
- `refresh-fundamentals` - Download and cache Alpha Vantage fundamentals for seed symbols.
- `schedule-fundamentals` - Run the fundamentals cache automation loop using configured schedules.
- `refresh-russell` - Download the latest Russell 2000 constituent list.

Example help:
```bash
python main.py scan --help
python main.py backtest --help
```

`schedule-fundamentals` reads the `automation.fundamentals_refresh` settings (frequency, day/time, Russell merge toggle, validation thresholds) and loops until interrupted. Add `--run-once` to execute a single cycle when external schedulers (cron, Task Scheduler) invoke the command.

---

## Investor Workflows & Methodologies

### Universe Screening
`python main.py scan` funnels candidate tickers through `universe.builder.UniverseBuilder`, enforcing liquidity and quality controls before investors spend time on detailed diligence.

**Methodology:**
1. **Seed list** – Start from `data/universe/seed_candidates.csv` or an explicit ticker list (`--symbols`).
2. **Fundamentals fetch** ? Pulls fresh fundamentals via Yahoo Finance (cached for configured TTL) and falls back to Alpha Vantage when an API key is provided.
3. **Filters** – Applies market cap, volume, bid/ask spread, float, sector, and exchange screens as defined in config.
4. **Russell 2000 merge** - Use `--include-russell` to append the bundled constituents from `data/universe/russell_2000.csv`.
4. **Persistence** – Saves accepted names to `storage.universe_dir` unless `--no-persist` is supplied.
5. **Diagnostics** – Reports skipped symbols for missing data or API errors.

**Example (Biotech tilt, top 25 symbols):**
```bash
python main.py scan --seed-candidates data/universe/biotech_watch.csv --limit 25 --output reports/universe/biotech_screen.csv
```
Sample console output:
```
Screened 150 candidates -> 28 passing filters

Preview:
   symbol sector      market_cap  dollar_volume
0   ARDX  biotech  1.92e+09      8.4e+07
1   KRYS  biotech  1.75e+09      5.1e+07
...
Skipped 6 symbols due to data issues: XYZ, ABC, ...
```
**Investor interpretation:** Focus diligence on names with rising dollar volume but still below the $2B cap, consistent with a small-cap breakout mandate. Save the generated CSV for coverage meetings or share via email from within the CLI using `--email`.

### Strategy Methodologies
Signals are generated by specialist modules, each returning `StrategySignal` dataclasses (see `strategies/base.py`).

| Strategy | Module | Style | Highlights |
|----------|--------|-------|------------|
| Dan Zanger Cup & Handle | `strategies/dan_zanger.py` | Technical breakout | Detects multi-month cup-handle formations, validates volume surge at breakout, enforces recovery ratios. |
| CAN SLIM | `strategies/canslim.py` | Fundamental growth | Scores equities on earnings acceleration, relative strength, proximity to 52-week highs, and volume confirmation. |
| Trend Following EMA | `strategies/trend_following.py` | Momentum | Uses fast/slow EMA crossovers with ATR-based stops and confidence weighting. |
| Livermore Breakout | `strategies/livermore.py` | Volatility contraction breakout | Seeks tight consolidation ranges with volume spikes on breakout above prior highs. |

**Strategy aggregation:** `strategies/aggregation.SignalAggregator` can blend signals with confidence/weight logic, and combined backtests default to config-defined weights (`strategy_weights`).

**Investor perspective:** Use strategy diversity to cover both technical (breakouts, trend continuation) and fundamental (earnings-driven) theses, enabling portfolios that balance conviction with risk-adjusted exposure.

### Backtesting & Attribution
`python main.py backtest` operationalizes historical evaluation via:
- `backtesting.engine.BacktestingEngine` – Runs each strategy over a price frame (CSV or Yahoo download via `--symbol`).
- `backtesting.runner.StrategyBacktestRunner` – Manages per-strategy runs with a shared position-sizer.
- `data_pipeline.enrichment.enrich_price_frame` - Adds relative strength, 52-week highs, and volume trends so strategies have all required fields before scoring.
- `portfolio.position_sizer.PositionSizer` – Respects risk config (max positions, sector caps, stop levels) when allocating capital to generated signals.
- `reports.performance.build_performance_report` – Calculates CAGR, Sharpe, drawdown metrics.
- `reports.attribution.compute_attribution` – Weights returns by strategy allocations for LP-style contributions.
- `backtesting.combiner.combine_equity_curves` – Produces a weighted composite equity curve.
The engine sizes positions using the configured risk limits, applies transaction costs on every fill, and records trade-level activity alongside equity curves.

**Example (compare trend vs. combo on AAPL):**
```bash
python main.py backtest --symbol AAPL --start 2020-01-01 --end 2024-01-01 \
  --strategies trend livermore --output-dir reports/backtests/aapl_combo
```
Console excerpt:
```
Performance metrics:
                     final_equity  total_return   cagr  max_drawdown  sharpe
trend_following          126543.0         0.265  0.06         -0.18    0.7
livermore_breakout       134210.0         0.342  0.08         -0.22    0.8

Attribution:
                     return  weight  contribution
trend_following        0.27     0.5          0.24
livermore_breakout     0.34     0.5          0.30
```
**Investor interpretation:** The Livermore sleeve outpaced the trend following leg over the chosen horizon, but both contributed meaningfully. Combine outputs with macro views to adjust weightings or capital allocation.

All CSV artifacts are saved under `reports/backtests/...` when `--output-dir` is provided:
- `performance/metrics.csv`
- `performance/attribution.csv`
- `combined/summary.csv`
- `combined/equity_curve.csv`

### Portfolio Health Monitoring
`python main.py health` provides a gut-check on live portfolios using stored CSVs.

Components:
- `portfolio.equity_curve.load_equity_curve` – Reads date-indexed equity history.
- `portfolio.health.PortfolioHealthMonitor` – Aggregates drawdown alerts (via `portfolio.alerts.DrawdownAlertManager`) and sector breaches (via `portfolio.sector_monitor.detect_sector_breaches`).

Example:
```bash
python main.py health --equity data/portfolio/equity_curve.csv --positions data/portfolio/positions.csv --email
```
Console sample:
```
Max drawdown: -12.4%

Alerts:
- Drawdown 0.15 from 2024-03-10 to 2024-04-22

Sector breaches:
- biotech: 0.42 (limit 0.35)
```
**Investor interpretation:** A 12% drawdown triggered alerts; biotech exposure exceeds configured limits, signaling the need to rebalance. With `--email`, an alert is dispatched to the configured inbox, keeping PMs informed even when away from the terminal.

### Notebook Generation
### Dashboard API & Frontend
1. Start the FastAPI service (uses existing config + strategy modules):
   ```bash
   uvicorn dashboard_api.app:app --reload
   ```
   The API listens on `http://localhost:8000` by default and exposes routes under `/api`.
2. Install web dependencies and run the React dev server:
   ```bash
   cd dashboard_web
   npm install
   npm run dev
   ```
   Set `VITE_API_BASE_URL` in `.env` (or via shell) if the API runs on a non-default host/port.

The dashboard supports symbol search, price/EMA charting, per-strategy confidence views, and aggregated signal summaries powered by the new backend endpoints.
For research workflows, clone the reporting notebook via `python main.py notebook`. The command copies `notebooks/backtest_analysis_template.ipynb` to a working location (default `notebooks/trading_dashboard.ipynb`). Set `--force` to overwrite existing dashboards.

Example:
```bash
python main.py notebook --dest notebooks/aapl_case_study.ipynb
```
Open the notebook in Jupyter to explore combined equity curves, attribution contributions, and sector exposures with interactive charts.

---

## Architecture & Module Overview

| Module | Responsibility | Notable Classes/Functions |
|--------|----------------|---------------------------|
| `trading_system/config_manager.py` | Load + validate application config, create storage directories. | `ConfigManager`, `TradingSystemConfig`, `EmailConfig`, etc. |
| `universe/builder.py` | Fetch fundamentals, apply screen, persist CSV snapshots. | `UniverseBuilder`, `SymbolSnapshot`. |
| `data_providers/yahoo.py` | Price history downloader with caching. | `YahooPriceProvider`. |
| `data_pipeline/enrichment.py` | Derive relative strength, 52-week highs, and volume features for strategies. | `enrich_price_frame`. |
| `data_pipeline/fundamentals.py` | Load cached fundamentals for enrichment overrides. | `load_fundamental_metrics`. |
| `strategies/*` | Implement domain-specific alpha signals. | `DanZangerCupHandleStrategy`, `CanSlimStrategy`, `TrendFollowingStrategy`, `LivermoreBreakoutStrategy`. |
| `portfolio/position_sizer.py` | Allocate capital across signals, enforces risk constraints. | `PositionSizer`. |
| `portfolio/health.py` | Aggregate drawdown and sector diagnostics. | `PortfolioHealthMonitor`. |
| `backtesting/*` | Execute and summarize historical strategy performance. | `BacktestingEngine`, `StrategyBacktestRunner`, `combine_equity_curves`. |
| `reports/*` | Build performance metrics, attribution, combined outputs. | `build_performance_report`, `generate_combined_report`, `compute_attribution`. |
| `automation/emailer.py` | SMTP-based alert dispatch. | `EmailDispatcher`. |

The CLI orchestrator (`main.py`) composes these modules, providing dependency hints and runtime safeguards (e.g., graceful error messaging when optional packages are absent).

---

## Testing & Quality Assurance

Unit tests are located under `tests/` and cover:
- Strategy logic, aggregation, portfolio analytics, data providers, and reporting utilities.
- CLI-specific regression tests (`tests/test_cli_main.py`) ensuring strategy instantiation, weight mappings, CSV normalization, and parser wiring remain stable.

Run the CLI-focused suite after making changes to `main.py`:
```bash
python -m pytest tests/test_cli_main.py
```
Or run the full project suite:
```bash
python -m pytest
```

`python -m compileall main.py` is used to ensure syntax validity before pushing changes.

---

## Troubleshooting & FAQ

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| `ModuleNotFoundError: No module named 'yfinance'` | Attempted Yahoo data fetch without dependency. | `pip install yfinance` |
| Email dispatch fails | Incorrect SMTP credentials or network policy. | Update `config/settings.local.json` with valid credentials; verify firewall rules. |
| Universe scan returning zero symbols | Filters too restrictive for current market batch. | Relax limits in config (e.g., raise `max_spread`, adjust `target_sectors`). |
| Backtest outputs empty reports | Strategies produced no BUY signals or enrichment inputs were missing. | Check data quality, confirm enriched columns exist (run `python main.py backtest --verbose`), broaden strategies, or extend lookback period. |

Logging with `--verbose` surfaces module-level context helpful for debugging.

---



### Automation Tips
- Use `python main.py schedule-fundamentals` to run the fundamentals cache loop defined in `automation.fundamentals_refresh`. Add `--force` if you need to override a disabled config toggle.
- For single-shot runs (CI, Task Scheduler, cron wrappers) append `--run-once` so the command exits after one refresh/validation cycle.
- Cron example (Linux/OS X):
  ```bash
  30 22 * * * /usr/bin/env bash -lc 'cd /path/to/trading_system && source .venv/bin/activate && python main.py schedule-fundamentals --force'
  ```
- Windows Task Scheduler example:
  ```powershell
  schtasks /Create /SC WEEKLY /D SUN /ST 22:30 /TN "TradingSystemFundamentals" /TR "cmd /c cd C:\projects\trading_system && .venv\Scripts\python.exe main.py schedule-fundamentals --force"
  ```
- Pair the scheduler with `python main.py refresh-russell --run-once` before each cycle if you want to pull fresh Russell constituents.
## Next Steps
## Next Steps
1. **Calibrate Parameters** – Tailor `strategy_weights` and risk controls to your mandate before running live capital.
2. **Integrate with Scheduling** – Use cron or Windows Task Scheduler to run `scan` and `health` commands weekly, leveraging the email alerts.
3. **Enrich Seed Universe** – Incorporate Russell 2000 constituents or custom watchlists for broader discovery.
4. **Extend Strategies** – Add new modules in `strategies/` and register them in `STRATEGY_FACTORIES` for inclusion in CLI workflows.
5. **Enhance Notebooks** – Build custom dashboards atop the generated CSV outputs for investment committee presentations.

The system is intentionally modular—adjust a single component (e.g., filters, risk limits, analytics) without rewriting the CLI. Combine automated reports with discretionary review to maintain a disciplined, repeatable small-cap growth process.









