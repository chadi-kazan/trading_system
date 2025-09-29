# Trading System CLI Usage

Run the entry point with `python main.py <command>` using the options below. All commands share the global flags:

- `--settings PATH` – override the user settings JSON (defaults to `config/settings.local.json`).
- `--defaults PATH` – use an alternate defaults file instead of `config/default_settings.json`.
- `--force-config-reload` – bypass the cached configuration and reload from disk.
- `--verbose` – enable debug logging for additional diagnostics.

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

