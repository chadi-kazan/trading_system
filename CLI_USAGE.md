# Trading System CLI Usage

Run the entry point with `python main.py <command>` using the options below. All commands share the global flags:

- `--settings PATH` � override the user settings JSON (defaults to `config/settings.local.json`).
- `--defaults PATH` � use an alternate defaults file instead of `config/default_settings.json`.
- `--force-config-reload` � bypass the cached configuration and reload from disk.
- `--verbose` � enable debug logging for additional diagnostics.

## Commands

### scan
Screen candidate symbols and persist the filtered universe.

```
python main.py scan [--seed-candidates CSV] [--symbols TICKER ...] [--limit N]
                    [--preview-rows N] [--output CSV] [--no-persist] [--email]
```

- Provide explicit tickers with `--symbols` or a CSV via `--seed-candidates`.
- Use `--include-russell` to merge the bundled Russell 2000 list (`data/universe/russell_2000.csv`) with your seeds.
- Results are saved under the configured storage directory unless `--no-persist` is supplied.
- `--email` sends the first ten passing symbols using the configured SMTP settings.

### backtest
Run the modular strategies through the backtesting engine and produce reports.

```
python main.py backtest [--prices CSV | --symbol TICKER] [--start YYYY-MM-DD]
                        [--end YYYY-MM-DD] [--interval 1d] [--capital AMOUNT]
                        [--strategies NAME ...] [--output-dir DIR] [--email]
```

- Use `--prices` for a local OHLCV file or `--symbol` to fetch via Yahoo Finance.
- The CLI enriches price data on the fly (relative strength, 52-week highs, volume trends) so CAN SLIM and other strategies have the columns they expect.
- Provide an Alpha Vantage API key via config (`data_sources.alpha_vantage_key`) to fetch fundamentals when local caches are empty.
- The backtesting engine sizes positions using `risk_management` settings and simulates trades with transaction costs to produce realistic equity curves.
- `--strategies` accepts any combination of `dan_zanger`, `canslim`, `trend`, `livermore` (aliases resolved automatically).
- If `data/universe/fundamentals/` or `fundamentals.csv` exists, those values override derived enrichment metrics during backtests.
- When `--output-dir` is provided, performance metrics are written to `DIR/performance/` and combined results to `DIR/combined/`.
- `--email` sends performance and attribution tables using the configured email dispatcher.

### report
Inspect previously generated CSV outputs.

```
python main.py report [--performance CSV] [--attribution CSV] [--equity CSV]
```

Pass one or more paths saved by the backtest command to print the metrics to stdout.

### health
Evaluate portfolio drawdowns and sector concentration using stored equity and position files.

```
python main.py health [--equity CSV] [--positions CSV] [--email]
```

Defaults resolve to the configured `storage.portfolio_dir`. Email summaries are sent when alerts are present and `--email` is set.

### notebook
Copy the bundled analysis notebook to a working location.

```
python main.py notebook [--template PATH] [--dest PATH] [--force]
```

Use `--force` to overwrite an existing destination file.

### refresh-fundamentals
Download fundamentals for a batch of symbols and update the local cache.

```
python main.py refresh-fundamentals [--symbols TICKER ...] [--seed-candidates CSV]
                                      [--include-russell] [--limit N] [--throttle SECONDS]
```

- Requires `data_sources.alpha_vantage_key` (or `TS_ALPHA_VANTAGE_KEY`).
- Defaults to the configured seed list and can merge Russell constituents with `--include-russell`.
- Writes JSON files under `storage.universe_dir/fundamentals/` for downstream enrichment.

### refresh-russell
Download and store the Russell 2000 constituents.

```
python main.py refresh-russell [--url URL] [--dest CSV]
```

- Defaults to the packaged GitHub dataset and writes to `data/universe/russell_2000.csv`.
- Combine with `refresh-fundamentals` or the scheduler for end-to-end automation.

### schedule-fundamentals
Run the scheduled fundamentals refresh loop defined in `automation.fundamentals_refresh`.

```
python main.py schedule-fundamentals [--run-once] [--max-iterations N]
                                     [--seed-candidates CSV]
                                     [--include-russell | --skip-russell]
                                     [--limit N] [--throttle SECONDS] [--force]
```

- The command loops until interrupted, respecting the configured frequency, time, day, and validation thresholds.
- Use `--run-once` when an external scheduler (cron/Task Scheduler) invokes the command and you want it to exit after one cycle.
- `--force` overrides a disabled automation toggle in config for ad-hoc runs.
- `--max-iterations` limits the number of refresh cycles when running interactively.

### precompute-momentum
Pre-compute momentum leaderboards for Russell 2000 and S&P 500 to warm the API cache.

```
python main.py precompute-momentum [--timeframes day week month ytd]
                                   [--limit N] [--skip-russell] [--skip-sp500]
```

- Fetches price data in batch and computes strategy scores for all symbols.
- Results are cached in memory (5-minute TTL) for faster API responses.
- Use `--timeframes` to compute specific periods (default: all four).
- `--limit` controls the maximum symbols per leaderboard (default: 200).
- `--skip-russell` or `--skip-sp500` to exclude an index from computation.
- Run overnight via cron/Task Scheduler to ensure warm caches during market hours.

**Example scheduled task (Windows):**
```powershell
schtasks /Create /SC DAILY /ST 06:00 /TN "PrecomputeMomentum" /TR "cmd /c cd C:\projects\trading_system && .venv\Scripts\python.exe main.py precompute-momentum"
```

**Example cron job (Linux/macOS):**
```bash
0 6 * * * cd /path/to/trading_system && source .venv/bin/activate && python main.py precompute-momentum
```
