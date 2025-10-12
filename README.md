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
8. [Cloud Deployment](#cloud-deployment)
9. [Watchlist Persistence & Dashboard Integration](#watchlist-persistence--dashboard-integration)
10. [Strategy Weighting Overview](#strategy-weighting-overview)
11. [Russell 2000 Momentum Explorer](#russell-2000-momentum-explorer)
12. [Next Steps](#next-steps)
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
- `update-strategy-metrics` - Ingest reliability metrics from a JSON payload into the strategy weighting database.

Example help:
```bash
python main.py scan --help
python main.py backtest --help
```

`schedule-fundamentals` reads the `automation.fundamentals_refresh` settings (frequency, day/time, Russell merge toggle, validation thresholds) and loops until interrupted. Add `--run-once` to execute a single cycle when external schedulers (cron, Task Scheduler) invoke the command.

### Universe Refresh & Sector Metadata Pipeline
- Each fundamentals refresh cycle harvests sector metadata for both the small-cap universe (seed + optional Russell 2000 symbols) and, when enabled, the S&P 500 list. The snapshots are stored in `data/universe/sector_metadata.csv` with `symbol`, `name`, `sector`, `universe`, and `fetched_at` columns consumed by the dashboard's sector-average views.
- Run `python main.py schedule-fundamentals --run-once` to trigger an on-demand refresh; append `--include-sp500`/`--skip-sp500` or `--include-russell`/`--skip-russell` to override configuration flags for that invocation.
- Ensure `automation.fundamentals_refresh.include_sp500` is enabled if you want large-cap sector data preloaded alongside your small-cap research universe.


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

The dashboard supports symbol search, price/EMA charting, per-strategy confidence views, and aggregated signal summaries powered by the new backend endpoints. If the API returns HTTP 429, simply wait a few seconds before refreshing to respect Alpha Vantage throttling. Tailwind CSS powers the UI; tweak design tokens in dashboard_web/tailwind.config.ts as needed. Explore `/guides/signals` for interpretation walkthroughs and `/guides/glossary` for definitions with Investopedia links. A final score doughnut blends the latest strategy confidences into a single gauge for quick triage. Saved watchlist entries persist through the FastAPI backend with SQLModel over SQLite, so every reload pulls the latest status, score breakdown, and aggregated signal from the shared database.
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

## Watchlist Persistence & Dashboard Integration
The dashboard keeps every saved signal in a shared SQLite database managed by SQLModel. When you click **Save symbol snapshot** or land on the watchlist page, the workflow is:

1. The React app calls the FastAPI endpoint `/api/watchlist` with the symbol, its current status, score breakdown, and the latest aggregated signal.
2. FastAPI upserts the record into `data/watchlist.db`, preserving the timestamp so you know how fresh each snapshot is.
3. Reloading the dashboard or visiting `/watchlist` triggers a `fetchWatchlist` call; the hook converts database records into React state and keeps the list sorted by most recent save.
4. Opening a watchlist item routes you back to the dashboard, reloads the live chart data, and writes the refreshed snapshot back to the database so stale entries are automatically replaced.

Because persistence lives on the backend you can share the watchlist across browsers or team members; just keep the API running on a reachable host (set `VITE_API_BASE_URL` accordingly). If something looks off, check that the API process has write access to `data/watchlist.db` and watch the FastAPI logs for validation errors.

## Strategy Weighting Overview
As we move beyond equal-weighted averages, the "final score" will lean on measurable evidence instead of intuition. The goal is to favour strategies that are winning right now, in the current market regime, without letting any single playbook overwhelm the blend.

### Core Ingredients
- **Rolling reliability metrics:** For each strategy and regime we store win rate, average excess return, volatility, drawdown streaks, and sample size.
- **Exponential decay:** Recent trades count more than older history so the model reacts quickly when a strategy cools off.
- **Regime awareness:** Metrics are segmented by market backdrop (trending bull, choppy high-volatility, etc.) so we reuse the right weights at the right time.
- **Diversification guardrails:** We cap individual weights and penalise highly correlated strategies to avoid double-counting similar signals.

### Example Walkthrough
Imagine a week where the market is in a trending bull regime:
- CAN SLIM has a 62% win rate with +8% average alpha, so it earns a weight of 0.35.
- Dan Zanger cup-handle sits at 0.25 thanks to moderate hit rate but lower volatility.
- Trend-following has not kept up (45% win rate), so after decay it contributes 0.20.
- Livermore breakout is highly correlated with CAN SLIM this week; the diversification penalty nudges it down to 0.20.
The final score is the weighted sum of the latest confidences using those weights. If any strategy is missing data, we gracefully fall back to equal shares so the blend always resolves.

### Visual Guides & Upcoming Pages
We are planning a dedicated **Strategy Health** page under `/diagnostics/strategy-weights` that will include:
- Weight contribution bars and sparklines so you can see how influence shifts over time.
- Regime timelines that annotate when the system switches between trending and range-bound states.
- Correlation heatmaps and scatter plots comparing alpha versus drawdown, helping you spot redundant strategies.
- A walkthrough card explaining the weighting math with the same example above, so new teammates can follow along without digging into code.

These visuals will land alongside the database models for tracking regime-specific metrics. Until then, refer back to this section to understand how the upcoming weighting logic will behave and how to communicate it to stakeholders.

### Populating Metrics
Use the CLI helper to upsert fresh reliability metrics after each analytics run:

```bash
python main.py update-strategy-metrics --input data/strategy_metrics_sample.json
```

Add `--dry-run` to preview without writing to the database. Each JSON object should include the strategy/regime identifiers, sample size, wins, and any computed fields (excess return, reliability_weight, correlation_penalty, extras, etc.). The new `/diagnostics/strategy-weights` page reflects the latest snapshots you ingest.

## Momentum Explorer (Russell 2000 & S&P 500)

Use the `/api/russell/momentum` and `/api/sp500/momentum` endpoints - or the dashboard routes `/russell/momentum` and `/sp500/momentum` - to compare leadership across small-cap and large-cap universes. Timeframe toggles (day, week, month, YTD) adjust the lookback window, and the limit selector (50, 100, 150, 200) controls how many symbols appear per leaderboard. Each payload includes the relevant ETF baseline (IWM or SPY) so you can benchmark moves quickly.

- `Top Risers` lists the strongest percentage movers in descending order; `Underperformers` surfaces the weakest names.
- Click any column header (change %, final score, or individual strategy) to sort the table - strategy and aggregate scores are shown per row for fast triage.
- Stage a preferred watchlist status, push the symbol into the shared watchlist, or open the main dashboard with the selection pre-loaded via the quick actions column.
- Volume columns display the raw print plus relative volume to confirm participation.

Example API usage:

```bash
curl "http://localhost:8000/api/russell/momentum?timeframe=week&limit=50"
curl "http://localhost:8000/api/sp500/momentum?timeframe=week&limit=50"
```

## Next Steps
1. **Calibrate Parameters** - Tailor `strategy_weights` and risk controls to your mandate before running live capital.
2. **Integrate with Scheduling** - Use cron or Windows Task Scheduler to run `scan`, `health`, and `update-strategy-metrics` so diagnostics stay current.
3. **Enrich Seed Universe** - Incorporate Russell 2000 constituents or custom watchlists for broader discovery.
4. **Extend Strategies** - Add new modules in `strategies/` and register them in `STRATEGY_FACTORIES` for inclusion in CLI workflows.
5. **Enhance Notebooks** - Build custom dashboards atop the generated CSV outputs for investment committee presentations.
6. **Momentum Explorer** - Use the `/russell/momentum` and `/sp500/momentum` pages to compare leaders and laggards, sort by strategy or final scores, and push symbols to the dashboard or watchlist with one click.



The system is intentionally modular - adjust a single component (e.g., filters, risk limits, analytics) without rewriting the CLI. Combine automated reports with discretionary review to maintain a disciplined, repeatable small-cap growth process.











\n## Cloud Deployment\n- [Cloud deployment plan](docs/cloud_deployment_plan.md): containerisation, hosting, and configuration guidance.\n


