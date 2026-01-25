# Claude Instructions for Trading System

## Project Overview

This is a **Small-Cap Growth Trading System** - a modular research and execution toolkit for growth-oriented investors. It provides universe screening, strategy backtesting, portfolio monitoring, and risk management with both CLI and web dashboard interfaces.

**Key Capabilities:**
- Screen small-cap equities by liquidity, float, spread, and sector filters
- Generate trading signals from 4 technical and fundamental strategies
- Backtest single or multi-strategy portfolios with risk limits
- Monitor live portfolios for drawdown and sector concentration breaches
- Web dashboard for interactive symbol analysis and watchlist management

---

## Codebase Architecture

### Directory Structure

```
trading_system/
├── main.py                          # CLI entry point (8 commands)
├── trading_system/                  # Core configuration management
│   └── config_manager.py           # ConfigManager, TradingSystemConfig
├── universe/                        # Universe screening module
│   ├── builder.py                  # UniverseBuilder - filters small-cap stocks
│   ├── candidates.py               # Load seed candidates
│   └── russell.py                  # Russell 2000 constituent handling
├── strategies/                      # Trading strategy implementations
│   ├── base.py                     # Strategy base class
│   ├── canslim.py                  # CAN SLIM fundamental growth
│   ├── dan_zanger.py               # Cup-and-handle breakout
│   ├── trend_following.py          # EMA crossover momentum
│   ├── livermore.py                # Volatility contraction breakout
│   └── aggregation.py              # Multi-strategy signal blending
├── backtesting/                     # Historical simulation engine
│   ├── engine.py                   # BacktestingEngine - trade simulation
│   ├── runner.py                   # StrategyBacktestRunner
│   └── combiner.py                 # Equity curve merging
├── portfolio/                       # Position sizing & risk management
│   ├── position_sizer.py           # Capital allocation with risk limits
│   ├── health.py                   # PortfolioHealthMonitor
│   ├── alerts.py                   # DrawdownAlertManager
│   └── sector_monitor.py           # Sector concentration tracking
├── data_pipeline/                   # Data enrichment
│   ├── enrichment.py               # Add volume ratios, relative strength
│   └── fundamentals.py             # Load Alpha Vantage fundamentals cache
├── data_providers/                  # External data sources
│   └── yahoo.py                    # YahooPriceProvider with caching
├── indicators/                      # Technical indicators
│   └── technical.py                # EMA, ATR, volume indicators
├── analytics/                       # Market overlays
│   ├── regime.py                   # MarketRegimeAnalyzer (VIX/HYG/SPY)
│   └── earnings.py                 # EarningsSignal quality scoring
├── reports/                         # Performance reporting
│   ├── performance.py              # Metrics (CAGR, Sharpe, drawdown)
│   ├── attribution.py              # Strategy contribution analysis
│   └── combined.py                 # Combined reports
├── automation/                      # Scheduled tasks
│   ├── emailer.py                  # EmailDispatcher for alerts
│   ├── fundamentals_refresh.py     # Scheduled cache refresh
│   └── strategy_metrics_refresh.py # Strategy reliability updates
├── dashboard_api/                   # FastAPI backend
│   ├── app.py                      # API entry point
│   ├── services.py                 # SignalService orchestrator
│   └── routes/                     # API endpoints
│       ├── symbols.py              # Symbol analysis
│       ├── watchlist.py            # Watchlist CRUD
│       ├── momentum.py             # Momentum leaderboards
│       └── russell.py, sp500.py    # Index-specific endpoints
├── dashboard_web/                   # React + Vite frontend
│   ├── src/
│   │   ├── pages/                  # Symbol, watchlist, momentum pages
│   │   ├── components/             # Reusable UI components
│   │   └── hooks/                  # API hooks
│   └── tailwind.config.ts          # Tailwind styling
├── config/                          # Configuration files
│   ├── default_settings.json       # System defaults
│   └── settings.local.json         # User overrides (gitignored)
├── data/                            # Runtime data (gitignored)
│   ├── cache/                      # Price cache (7-day TTL)
│   ├── universe/                   # Screened symbols, fundamentals
│   ├── watchlist.db                # SQLite watchlist persistence
│   └── reports/                    # Backtest outputs
└── tests/                           # Unit and integration tests
    └── test_cli_main.py            # CLI regression tests
```

---

## Core Concepts

### 1. Configuration Management

**Location:** `trading_system/config_manager.py`

**Key Class:** `ConfigManager`
- Loads hierarchical config: `default_settings.json` → `settings.local.json` → environment variables (prefix `TS_`)
- Validates risk limits, strategy weights (must sum to 1.0)
- Creates storage directories on load
- Cached in memory with `--force-config-reload` option

**Config Structure:**
```python
TradingSystemConfig
├── EmailConfig                     # SMTP settings
├── RiskManagementConfig            # Max positions, stops, sector limits
├── StrategyWeightsConfig           # Weights for aggregation (sum=1.0)
├── DataSourcesConfig               # API keys, cache TTL
├── UniverseCriteriaConfig          # Market cap, volume, spread filters
├── StorageConfig                   # Cache directories
└── AutomationConfig                # Scheduling, refresh rules
```

**When modifying config:**
- Always validate strategy weights sum to 1.0
- Update both defaults and document in README
- Test with `--force-config-reload` flag

### 2. Strategy Pattern

**Base Class:** `strategies/base.py:Strategy`

**Required Methods:**
```python
def generate_signals(self, symbol: str, prices: pd.DataFrame) -> Iterable[StrategySignal]:
    """Generate BUY/SELL/HOLD signals from enriched price data."""

def required_columns(self) -> List[str]:
    """Return list of required DataFrame columns."""
```

**Four Implementations:**

1. **CAN SLIM** (`canslim.py`) - Fundamental growth scoring
   - Earnings acceleration (≥25% YoY)
   - Relative strength (52-week normalized)
   - Price near 52-week high (within 15%)
   - Volume surge (≥20% above 20-day avg)

2. **Dan Zanger Cup-and-Handle** (`dan_zanger.py`) - Technical breakout
   - Cup: 12-35% drawdown from left/right peaks
   - Handle: 5-15 bar consolidation, 5-15% pullback
   - Breakout: Close above handle high + 2% with volume >1.5x

3. **Trend Following EMA** (`trend_following.py`) - Momentum
   - Fast EMA (12) crosses above slow EMA (26)
   - ATR-based stops, volume confirmation

4. **Livermore Breakout** (`livermore.py`) - Volatility contraction
   - Bollinger band squeeze + volume surge
   - Jesse Livermore tape-reading methodology

**Strategy Registry:**
```python
# In main.py
STRATEGY_FACTORIES = {
    "dan_zanger_cup_handle": DanZangerCupHandleStrategy(),
    "can_slim": CanSlimStrategy(),
    "trend_following": TrendFollowingStrategy(),
    "livermore_breakout": LivermoreBreakoutStrategy(),
}
```

**Adding a New Strategy:**
1. Create `strategies/my_strategy.py` inheriting from `Strategy`
2. Implement `generate_signals()` and `required_columns()`
3. Add to `STRATEGY_FACTORIES` in `main.py`
4. Update tests in `tests/test_cli_main.py`
5. Document in README

### 3. Data Pipeline

**Enrichment Flow:**
```
Raw OHLCV data
  ↓
enrich_price_frame()
  ├→ 20-day average volume
  ├→ Volume change ratio
  ├→ 252-day relative strength (0-1 normalized)
  └→ 52-week high indicator
  ↓
load_fundamental_metrics()
  ├→ Check JSON cache: data/universe/fundamentals/{SYMBOL}.json
  ├→ Fallback to CSV: data/universe/fundamentals.csv
  └→ Fallback to Alpha Vantage API (if key set)
  ↓
Enriched DataFrame ready for strategy.generate_signals()
```

**Required Columns for Strategies:**
- `open`, `high`, `low`, `close`, `volume` (base OHLCV)
- `volume_20d_avg`, `volume_change` (enrichment)
- `relative_strength_252d`, `near_52wk_high` (enrichment)
- Optional: `earnings_growth`, `market_cap`, `pe_ratio` (fundamentals)

### 4. Backtesting Engine

**Location:** `backtesting/engine.py:BacktestingEngine`

**Workflow:**
```python
engine = BacktestingEngine(price_data, strategy, position_sizer)
result = engine.run()
# result.equity_curve: pd.Series (date-indexed)
# result.trades: List[Trade] (entry/exit logs)
# result.metrics: Dict (CAGR, Sharpe, drawdown)
```

**Simulation Logic:**
1. Generate signals from strategy
2. Size positions via `PositionSizer` (respects risk limits)
3. Simulate long-only trades:
   - Track cash, positions, equity
   - Apply transaction costs (0.1% default)
   - Record trade-level activity
4. Compute equity curve

**Key Constraints:**
- Long-only (no shorting)
- No intraday trading (close-to-close)
- Transaction costs on every fill
- Position sizing enforces max positions and sector limits

### 5. Risk Management

**Position Sizer:** `portfolio/position_sizer.py:PositionSizer`

**Enforcement:**
- Max open positions (default: 10)
- Individual stop loss (default: 8%)
- Portfolio stop loss (default: 15%)
- Sector concentration caps (e.g., biotech ≤35%)

**Health Monitor:** `portfolio/health.py:PortfolioHealthMonitor`

**Monitoring:**
- Drawdown detection (max intra-period decline)
- Sector concentration breaches
- Email alerts via SMTP when limits violated

### 6. Caching Strategy

**Price Cache:**
- Location: `data/cache/1d/{SYMBOL}.csv`
- TTL: 7 days (configurable)
- Provider: `data_providers/yahoo.py:YahooPriceProvider`

**Fundamentals Cache:**
- Location: `data/universe/fundamentals/{SYMBOL}.json`
- Source: Alpha Vantage API (requires `TS_ALPHA_VANTAGE_KEY`)
- Fallback: CSV at `data/universe/fundamentals.csv`

**Regime Cache:**
- In-memory with 900s TTL
- Avoids duplicate VIX/HYG/LQD/SPY API calls

**Config Cache:**
- In-memory, cleared with `--force-config-reload`

---

## CLI Commands Reference

**Entry Point:** `python main.py <command>`

### Global Flags
```bash
--settings PATH              # Use alternate user settings JSON
--defaults PATH              # Use alternate default settings JSON
--force-config-reload        # Bypass cached config
--verbose                    # Debug logging
```

### Commands

#### 1. `scan` - Universe Screening
```bash
python main.py scan [--seed-candidates PATH] [--symbols AAPL MSFT] [--limit 50] [--include-russell] [--email]
```
- Filters small-cap stocks by liquidity, float, spread, sector
- Persists to `data/universe/candidates.csv`
- Optional email dispatch

#### 2. `backtest` - Strategy Backtesting
```bash
python main.py backtest --symbol AAPL --strategies trend livermore [--start 2020-01-01] [--end 2024-01-01] [--output-dir reports/backtests/aapl]
```
- Runs historical simulation with transaction costs
- Generates performance metrics, attribution, equity curves
- Saves CSV reports

#### 3. `report` - Inspect Reports
```bash
python main.py report --backtest-dir reports/backtests/aapl
```
- Displays previously generated CSV reports

#### 4. `health` - Portfolio Health Check
```bash
python main.py health --equity portfolio/equity_curve.csv --positions portfolio/positions.csv [--email]
```
- Detects drawdowns and sector breaches
- Optional email alerts

#### 5. `notebook` - Analysis Notebook
```bash
python main.py notebook --dest notebooks/my_analysis.ipynb [--force]
```
- Copies Jupyter template for custom analysis

#### 6. `refresh-fundamentals` - Cache Fundamentals
```bash
python main.py refresh-fundamentals [--symbols AAPL MSFT] [--include-russell] [--include-sp500]
```
- Fetches Alpha Vantage data
- Writes JSON cache

#### 7. `schedule-fundamentals` - Automated Refresh
```bash
python main.py schedule-fundamentals [--run-once] [--force]
```
- Runs scheduled fundamentals refresh loop
- Use `--run-once` for cron/Task Scheduler

#### 8. `refresh-russell` - Update Russell 2000
```bash
python main.py refresh-russell
```
- Downloads latest Russell 2000 constituents

#### 9. `update-strategy-metrics` - Ingest Reliability Data
```bash
python main.py update-strategy-metrics --input data/strategy_metrics.json [--dry-run]
```
- Updates strategy weighting database

#### 10. `precompute-momentum` - Warm Momentum Cache
```bash
python main.py precompute-momentum [--timeframes day week month ytd] [--limit 200] [--skip-russell] [--skip-sp500]
```
- Pre-computes momentum leaderboards for faster API responses
- Uses batch price fetching and parallel processing
- Run overnight to ensure warm caches during market hours

---

## API Endpoints

**Start Server:**
```bash
uvicorn dashboard_api.app:app --reload
```

**Base URL:** `http://localhost:8000`

### Routes

#### Symbol Analysis
```
GET /api/symbols/{symbol}?start=2023-01-01&end=2024-01-01
```
Returns: price bars, strategy analysis, aggregated signal, fundamentals, macro overlay

#### Watchlist
```
GET /api/watchlist                    # List all
POST /api/watchlist                   # Create/update
DELETE /api/watchlist/{id}            # Remove
```

#### Momentum Leaderboards
```
GET /api/russell/momentum?timeframe=week&limit=50
GET /api/sp500/momentum?timeframe=week&limit=50
```

#### Strategy Metrics
```
GET /api/diagnostics/strategy-weights
```

---

## Development Guidelines

### Code Style

**Type Hints:**
- Use throughout (enables IDE support and mypy)
- `from __future__ import annotations` for forward references

**Dataclasses:**
- Prefer `@dataclass(frozen=True)` for immutable domain models
- Examples: `StrategySignal`, `SymbolSnapshot`, `BacktestResult`

**Error Handling:**
```python
try:
    # External API call
except AlphaVantageError as e:
    logger.warning("API error, falling back to cache: %s", e)
except Exception as e:
    logger.error("Unexpected error: %s", e)
    raise
```
- Distinguish expected failures (log + continue) vs. critical failures (log + raise)

**Logging:**
```python
logger = logging.getLogger("trading_system.module_name")
logger.info("Processing %d symbols", len(symbols))
logger.debug("Detailed trace: %s", debug_data)
```

### Testing

**Run Tests:**
```bash
# All tests
python -m pytest

# CLI tests only
python -m pytest tests/test_cli_main.py

# With coverage
python -m pytest --cov=trading_system
```

**Test Structure:**
- Unit tests for strategies, indicators, position sizer
- Integration tests for backtesting engine
- CLI regression tests for command parsing

**When Adding Features:**
1. Write tests first (TDD preferred)
2. Update `tests/test_cli_main.py` for CLI changes
3. Run full suite before committing

### Dependencies

**Core:**
- pandas, numpy (data manipulation)
- yfinance (market data)
- requests (API calls)

**API:**
- fastapi, uvicorn (web server)
- sqlmodel, pydantic (database, validation)

**Frontend:**
- React, Vite (build tooling)
- Tailwind CSS (styling)

**Testing:**
- pytest (test framework)

**Adding Dependencies:**
1. Add to `requirements.txt`
2. Document in README prerequisites
3. Add lazy import check in `main.py` if optional

---

## Common Tasks

### Adding a New Strategy

1. **Create strategy file:**
```python
# strategies/rsi_divergence.py
from strategies.base import Strategy, StrategySignal

class RsiDivergenceStrategy(Strategy):
    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close", "volume", "rsi"]

    def generate_signals(self, symbol: str, prices: pd.DataFrame) -> Iterable[StrategySignal]:
        # Implementation
        yield StrategySignal(
            symbol=symbol,
            date=current_date,
            strategy="rsi_divergence",
            signal_type=SignalType.BUY,
            confidence=0.85,
            metadata={"rsi": 32.5}
        )
```

2. **Register in `main.py`:**
```python
from strategies.rsi_divergence import RsiDivergenceStrategy

STRATEGY_FACTORIES = {
    # ... existing strategies
    "rsi_divergence": RsiDivergenceStrategy(),
}
```

3. **Add to config:**
```json
// config/default_settings.json
"strategy_weights": {
    // ... existing weights
    "rsi_divergence": 0.2  // Ensure all weights sum to 1.0
}
```

4. **Update tests:**
```python
# tests/test_cli_main.py
def test_rsi_divergence_strategy():
    assert "rsi_divergence" in STRATEGY_FACTORIES
```

5. **Document in README**

### Modifying Risk Limits

**Edit:** `config/settings.local.json` (gitignored) or `config/default_settings.json`

```json
{
  "risk_management": {
    "max_positions": 15,           // Increase max positions
    "individual_stop_pct": 0.10,   // Widen individual stop to 10%
    "portfolio_stop_pct": 0.20,    // Widen portfolio stop to 20%
    "sector_limits": {
      "biotech": 0.40,             // Increase biotech cap to 40%
      "tech": 0.35                 // Add tech cap at 35%
    }
  }
}
```

**Test changes:**
```bash
python main.py backtest --symbol AAPL --strategies trend --settings config/settings.local.json --verbose
```

### Debugging API Issues

**Enable debug logging:**
```bash
# In dashboard_api/app.py, set log level
import logging
logging.basicConfig(level=logging.DEBUG)

uvicorn dashboard_api.app:app --reload --log-level debug
```

**Check Alpha Vantage rate limits:**
- Free tier: 5 calls/minute, 500 calls/day
- Returns HTTP 429 when throttled
- Frontend displays retry message

**Inspect cache:**
```bash
# Check if fundamentals cached
ls data/universe/fundamentals/AAPL.json

# Check price cache
ls data/cache/1d/AAPL.csv
```

### Running Scheduled Automation

**Windows Task Scheduler:**
```powershell
schtasks /Create /SC WEEKLY /D SUN /ST 22:30 /TN "TradingSystemRefresh" /TR "cmd /c cd C:\projects\trading_system && .venv\Scripts\python.exe main.py schedule-fundamentals --run-once"
```

**Linux/macOS cron:**
```bash
30 22 * * 0 cd /path/to/trading_system && source .venv/bin/activate && python main.py schedule-fundamentals --run-once
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'yfinance'`
**Fix:** `pip install -r requirements.txt`

### Issue: Email alerts not working
**Check:**
1. SMTP credentials in `config/settings.local.json`
2. Firewall rules allowing SMTP ports
3. Test with: `python main.py health --equity test_equity.csv --email --verbose`

### Issue: Backtest returns empty reports
**Causes:**
- Strategies produced no signals
- Missing enrichment columns
- Data quality issues

**Debug:**
```bash
python main.py backtest --symbol AAPL --strategies trend --verbose
# Check logs for "Required columns missing" or "No signals generated"
```

### Issue: Dashboard shows stale data
**Fix:**
1. Clear price cache: `rm -rf data/cache/1d/*.csv`
2. Restart API with `--force-config-reload`
3. Refresh browser cache

### Issue: Alpha Vantage HTTP 429
**Cause:** Rate limit exceeded (5 calls/min on free tier)

**Fix:**
- Wait 60 seconds before retry
- Upgrade to premium tier
- Use cached data when available

---

## File Locations Reference

### Configuration
- `config/default_settings.json` - System defaults (versioned)
- `config/settings.local.json` - User overrides (gitignored)

### Data (gitignored)
- `data/cache/1d/{SYMBOL}.csv` - Price cache
- `data/universe/fundamentals/{SYMBOL}.json` - Fundamentals cache
- `data/universe/candidates.csv` - Screened universe
- `data/universe/russell_2000.csv` - Russell constituents
- `data/watchlist.db` - SQLite watchlist database
- `data/reports/backtests/` - Backtest outputs

### Documentation
- `README.md` - User guide (comprehensive)
- `CLI_USAGE.md` - Command reference
- `project_plan.md` - Feature roadmap
- `docs/cloud_deployment_plan.md` - PythonAnywhere deployment

### Tests
- `tests/test_cli_main.py` - CLI regression tests
- `tests/test_strategies.py` - Strategy unit tests
- `tests/test_backtesting.py` - Engine integration tests

---

## Best Practices

### When Modifying Code

1. **Read before changing:**
   - Use `Read` tool to understand current implementation
   - Check tests to understand expected behavior
   - Review config schema if changing settings

2. **Follow existing patterns:**
   - Use dataclasses for domain models
   - Add type hints throughout
   - Use frozen dataclasses for immutability
   - Follow module naming conventions

3. **Test changes:**
   - Run affected tests: `pytest tests/test_<module>.py`
   - Run full suite before committing
   - Add new tests for new features

4. **Update documentation:**
   - Update README for user-facing changes
   - Update this file for developer guidance
   - Add docstrings for public APIs

### When Adding Features

1. **Plan first:**
   - Identify affected modules
   - Check if existing abstractions fit
   - Design for extensibility

2. **Implement incrementally:**
   - Start with data models (dataclasses)
   - Add core logic
   - Wire into CLI/API
   - Add tests
   - Document

3. **Maintain backwards compatibility:**
   - Don't break existing CLI commands
   - Version API endpoints if changing contracts
   - Provide migration path for config changes

### When Debugging

1. **Use `--verbose` flag:**
   ```bash
   python main.py backtest --symbol AAPL --strategies trend --verbose
   ```

2. **Check logs systematically:**
   - Config loading
   - Data fetching (cache hit/miss)
   - Signal generation
   - Position sizing
   - Trade execution

3. **Isolate the problem:**
   - Test strategy in isolation
   - Verify data quality
   - Check config validation

4. **Use debugger:**
   ```python
   import pdb; pdb.set_trace()  # Add breakpoint
   ```

---

## Key Design Principles

1. **Modularity** - Each component works independently; composition at CLI level
2. **Testability** - Pure functions, dependency injection, mock-friendly
3. **Configuration over code** - Settings in JSON, not hardcoded
4. **Fail gracefully** - Meaningful errors, fallbacks, retries
5. **Cache aggressively** - Balance freshness with performance
6. **Type safety** - Type hints throughout, validate at boundaries
7. **Risk first** - Enforce limits before capital allocation
8. **Extensibility** - Plugin pattern for strategies, providers

---

## Quick Reference

### Start Development Environment
```bash
# Activate virtualenv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start API
uvicorn dashboard_api.app:app --reload

# Start frontend
cd dashboard_web && npm install && npm run dev
```

### Common Commands
```bash
# Screen universe
python main.py scan --limit 25

# Backtest single strategy
python main.py backtest --symbol AAPL --strategies trend --start 2020-01-01

# Check portfolio health
python main.py health --equity data/portfolio/equity.csv --positions data/portfolio/positions.csv

# Refresh fundamentals cache
python main.py refresh-fundamentals --include-russell

# Update strategy metrics
python main.py update-strategy-metrics --input data/metrics.json
```

### Environment Variables
```bash
TS_ALPHA_VANTAGE_KEY=your_key        # Alpha Vantage API key
TS_EMAIL_SMTP_HOST=smtp.gmail.com    # Email SMTP host
TS_EMAIL_SMTP_PORT=587               # Email SMTP port
TS_EMAIL_USERNAME=user@example.com   # Email username
TS_EMAIL_PASSWORD=app_password       # Email password
```

---

## Contact & Resources

- **Main Documentation:** [README.md](README.md)
- **CLI Reference:** [CLI_USAGE.md](CLI_USAGE.md)
- **Project Plan:** [project_plan.md](project_plan.md)
- **Deployment Guide:** [docs/cloud_deployment_plan.md](docs/cloud_deployment_plan.md)

---

**Last Updated:** 2026-01-18

This file should be updated whenever significant architectural changes are made to the codebase.
