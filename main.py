"""CLI entry point for the Small-Cap Growth Trading System."""

from __future__ import annotations

import argparse
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, Iterable, List, Optional, Sequence

import pandas as pd

from automation.emailer import EmailConfig as DispatcherEmailConfig, EmailDispatcher
from automation.fundamentals_refresh import (
    ValidationError as FundamentalsValidationError,
    run_scheduled_refresh,
)
from automation.strategy_metrics_refresh import load_and_ingest_metrics
from backtesting.combiner import combine_equity_curves
from backtesting.engine import BacktestingEngine
from backtesting.runner import StrategyBacktestRunner
from data_pipeline import enrich_price_frame, load_fundamental_metrics, refresh_fundamentals_cache
from data_providers.base import PriceRequest
from portfolio.equity_curve import load_equity_curve
from portfolio.health import PortfolioHealthConfig, PortfolioHealthMonitor
from portfolio.position_sizer import PositionSizer
from reports.attribution import compute_attribution
from reports.combined import generate_combined_report
from reports.performance import build_performance_report
from strategies.base import Strategy, StrategySignal
from strategies.canslim import CanSlimStrategy
from strategies.dan_zanger import DanZangerCupHandleStrategy
from strategies.livermore import LivermoreBreakoutStrategy
from strategies.trend_following import TrendFollowingStrategy
from trading_system.config_manager import (
    ConfigManager,
    TradingSystemConfig,
    EmailConfig as AppEmailConfig,
)
from universe.candidates import load_seed_candidates, RUSSELL_2000_PATH
from universe.russell import refresh_russell_file, DEFAULT_RUSSELL_URL

if TYPE_CHECKING:
    from data_providers.yahoo import YahooPriceProvider
    from universe.builder import UniverseBuilder

logger = logging.getLogger("trading_system.cli")

STRATEGY_FACTORIES: Dict[str, Callable[[TradingSystemConfig], Strategy]] = {
    DanZangerCupHandleStrategy.name: lambda _cfg: DanZangerCupHandleStrategy(),
    CanSlimStrategy.name: lambda _cfg: CanSlimStrategy(),
    TrendFollowingStrategy.name: lambda _cfg: TrendFollowingStrategy(),
    LivermoreBreakoutStrategy.name: lambda _cfg: LivermoreBreakoutStrategy(),
}

STRATEGY_ALIASES: Dict[str, str] = {key: key for key in STRATEGY_FACTORIES}
STRATEGY_ALIASES.update(
    {
        "dan_zanger": DanZangerCupHandleStrategy.name,
        "cup_handle": DanZangerCupHandleStrategy.name,
        "dan_zanger_cup_handle": DanZangerCupHandleStrategy.name,
        "canslim": CanSlimStrategy.name,
        "can_slim": CanSlimStrategy.name,
        "trend": TrendFollowingStrategy.name,
        "trend_following": TrendFollowingStrategy.name,
        "livermore": LivermoreBreakoutStrategy.name,
        "livermore_breakout": LivermoreBreakoutStrategy.name,
    }
)


@dataclass
class AppContext:
    manager: ConfigManager
    config: TradingSystemConfig


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def build_context(args: argparse.Namespace) -> AppContext:
    manager_kwargs: Dict[str, Path] = {}
    if args.defaults:
        manager_kwargs["default_path"] = Path(args.defaults)
    if args.settings:
        manager_kwargs["user_path"] = Path(args.settings)
    manager = ConfigManager(**manager_kwargs)
    config = manager.load(force_reload=args.force_config_reload)
    return AppContext(manager=manager, config=config)


def parse_iso_date(value: str) -> date:
    try:
        return datetime.fromisoformat(value).date()
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid ISO date '{value}'") from exc


def resolve_date_range(start: Optional[str], end: Optional[str], years: int = 3) -> tuple[date, date]:
    today = date.today()
    end_date = parse_iso_date(end) if end else today
    start_date = parse_iso_date(start) if start else end_date - timedelta(days=365 * years)
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date")
    return start_date, end_date






def load_price_frame_from_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Price file not found: {path}")
    frame = pd.read_csv(path)
    frame.columns = [str(column).lower() for column in frame.columns]
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date")
    frame = frame.sort_index()
    if frame.index.name is None:
        frame.index.name = "date"
    frame.attrs["symbol"] = path.stem.upper()
    frame.attrs["source_path"] = str(path)
    return frame

def load_price_data_for_backtest(args: argparse.Namespace, config: TradingSystemConfig) -> pd.DataFrame:
    if args.prices:
        csv_path = Path(args.prices)
        frame = load_price_frame_from_csv(csv_path)
        symbol = frame.attrs.get("symbol", csv_path.stem.upper())
        fundamentals = load_fundamental_metrics(symbol, config.storage.universe_dir, config.data_sources.alpha_vantage_key)
        return enrich_price_frame(symbol, frame, fundamentals=fundamentals)

    if args.symbol:
        try:
            from data_providers.yahoo import YahooPriceProvider
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency hint
            raise RuntimeError(
                "Yahoo Finance price downloads require the `yfinance` package. Install it via `pip install yfinance`."
            ) from exc

        start_date, end_date = resolve_date_range(args.start, args.end)
        provider = YahooPriceProvider(
            cache_dir=config.storage.price_cache_dir,
            cache_ttl_days=config.data_sources.cache_days,
        )
        symbol = args.symbol.upper()
        request = PriceRequest(
            symbol=symbol,
            start=start_date,
            end=end_date,
            interval=args.interval,
        )
        result = provider.get_price_history(request)
        data = result.data.copy()
        data.attrs["symbol"] = symbol
        data.attrs["source"] = "yahoo"
        data.attrs["interval"] = args.interval
        fundamentals = load_fundamental_metrics(symbol, config.storage.universe_dir, config.data_sources.alpha_vantage_key)
        return enrich_price_frame(symbol, data, fundamentals=fundamentals)

    raise ValueError("Either --prices or --symbol must be provided for backtesting")


    if args.symbol:
        try:
            from data_providers.yahoo import YahooPriceProvider
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency hint
            raise RuntimeError(
                "Yahoo Finance price downloads require the `yfinance` package. Install it via `pip install yfinance`."
            ) from exc

        start_date, end_date = resolve_date_range(args.start, args.end)
        provider = YahooPriceProvider(
            cache_dir=config.storage.price_cache_dir,
            cache_ttl_days=config.data_sources.cache_days,
        )
        symbol = args.symbol.upper()
        request = PriceRequest(
            symbol=symbol,
            start=start_date,
            end=end_date,
            interval=args.interval,
        )
        result = provider.get_price_history(request)
        data = result.data.copy()
        data.attrs["symbol"] = symbol
        data.attrs["source"] = "yahoo"
        data.attrs["interval"] = args.interval
        return enrich_price_frame(symbol, data)

    raise ValueError("Either --prices or --symbol must be provided for backtesting")

    if args.symbol:
        try:
            from data_providers.yahoo import YahooPriceProvider
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency hint
            raise RuntimeError(
                "Yahoo Finance price downloads require the `yfinance` package. Install it via `pip install yfinance`."
            ) from exc

        start_date, end_date = resolve_date_range(args.start, args.end)
        provider = YahooPriceProvider(
            cache_dir=config.storage.price_cache_dir,
            cache_ttl_days=config.data_sources.cache_days,
        )
        request = PriceRequest(
            symbol=args.symbol.upper(),
            start=start_date,
            end=end_date,
            interval=args.interval,
        )
        result = provider.get_price_history(request)
        return result.data

    raise ValueError("Either --prices or --symbol must be provided for backtesting")



def instantiate_strategies(
    selected: Optional[Sequence[str]],
    config: TradingSystemConfig,
) -> List[Strategy]:
    if selected:
        order: List[str] = []
        seen: set[str] = set()
        for name in selected:
            alias = STRATEGY_ALIASES.get(name.lower(), name.lower())
            if alias not in STRATEGY_FACTORIES:
                logger.warning("Unknown strategy '%s' - skipping", name)
                continue
            if alias in seen:
                continue
            order.append(alias)
            seen.add(alias)
    else:
        order = list(STRATEGY_FACTORIES.keys())

    instances: List[Strategy] = []
    for key in order:
        factory = STRATEGY_FACTORIES[key]
        try:
            instances.append(factory(config))
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialise strategy %s: %s", key, exc)
    return instances



def build_position_sizer(config: TradingSystemConfig):
    sizer = PositionSizer(config.risk_management)

    def size_positions(signals: Iterable[StrategySignal], equity: float) -> List[Dict[str, float]]:
        allocations = sizer.size_positions(signals, equity)
        return [asdict(allocation) for allocation in allocations]

    return size_positions



def build_strategy_weight_map(config: TradingSystemConfig) -> Dict[str, float]:
    weights = config.strategy_weights.as_dict()
    return {
        DanZangerCupHandleStrategy.name: float(weights.get("zanger", 0.0)),
        CanSlimStrategy.name: float(weights.get("canslim", 0.0)),
        TrendFollowingStrategy.name: float(weights.get("trend_following", 0.0)),
        LivermoreBreakoutStrategy.name: float(weights.get("livermore", 0.0)),
    }



def build_email_dispatcher(config: TradingSystemConfig) -> EmailDispatcher:
    email_cfg: AppEmailConfig = config.email
    dispatcher_config = DispatcherEmailConfig(
        smtp_server=email_cfg.smtp_server,
        smtp_port=email_cfg.smtp_port,
        username=email_cfg.username,
        password=email_cfg.password,
        recipient=email_cfg.recipient,
        use_tls=email_cfg.use_tls,
    )
    return EmailDispatcher(dispatcher_config)



def send_backtest_email(config: TradingSystemConfig, performance_df: pd.DataFrame, attribution_df: pd.DataFrame) -> None:
    dispatcher = build_email_dispatcher(config)
    body_parts = ["Performance metrics:\n", performance_df.to_csv()]
    if not attribution_df.empty:
        body_parts.extend(["\nAttribution:\n", attribution_df.to_csv()])
    dispatcher.send_alert("Backtest Performance Summary", "".join(body_parts))



def send_scan_email(config: TradingSystemConfig, universe_df: pd.DataFrame) -> None:
    dispatcher = build_email_dispatcher(config)
    summary = universe_df.head(10)
    body = [f"Universe size: {len(universe_df)}"]
    if not summary.empty:
        columns = [col for col in ["symbol", "sector", "market_cap", "dollar_volume"] if col in summary.columns]
        body.append("\nTop screened symbols:\n")
        body.append(summary[columns].to_csv(index=False) if columns else summary.to_csv(index=False))
    dispatcher.send_alert("Universe Scan Results", "".join(body))



def send_health_email(config: TradingSystemConfig, report) -> None:
    dispatcher = build_email_dispatcher(config)
    lines = [f"Max drawdown: {report.max_drawdown:.2%}"]
    if report.drawdown_alerts:
        lines.append("\nDrawdown alerts:\n" + "\n".join(report.drawdown_alerts))
    if report.sector_breaches:
        breaches = [
            f"{breach.sector}: {breach.allocation:.2%} (limit {breach.limit:.2%})"
            for breach in report.sector_breaches
        ]
        lines.append("\nSector breaches:\n" + "\n".join(breaches))
    dispatcher.send_alert("Portfolio Health Alerts", "\n".join(lines))



def save_backtest_outputs(
    output_dir: Path,
    performance_df: pd.DataFrame,
    attribution_df: pd.DataFrame,
    combined_curve: pd.Series,
    combined_summary_df: pd.DataFrame,
) -> None:
    performance_dir = output_dir / "performance"
    combined_dir = output_dir / "combined"
    performance_dir.mkdir(parents=True, exist_ok=True)
    combined_dir.mkdir(parents=True, exist_ok=True)

    performance_path = performance_dir / "metrics.csv"
    performance_df.to_csv(performance_path)
    logger.info("Performance metrics saved to %s", performance_path)

    attribution_path = performance_dir / "attribution.csv"
    attribution_df.to_csv(attribution_path)
    logger.info("Attribution saved to %s", attribution_path)

    summary_path = combined_dir / "summary.csv"
    combined_summary_df.to_csv(summary_path)
    logger.info("Combined summary saved to %s", summary_path)

    curve_path = combined_dir / "equity_curve.csv"
    combined_curve.to_csv(curve_path, header=["equity"])
    logger.info("Combined equity curve saved to %s", curve_path)



def handle_scan(args: argparse.Namespace, ctx: AppContext) -> int:
    try:
        from universe.builder import UniverseBuilder
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency hint
        raise RuntimeError(
            "Universe scanning requires the `yfinance` package. Install it via `pip install yfinance`."
        ) from exc

    candidates: List[str]
    if args.symbols:
        candidates = [symbol.strip().upper() for symbol in args.symbols if symbol]
    else:
        seed_path = Path(args.seed_candidates) if args.seed_candidates else None
        extra_sources: list[Path] = []
        if args.include_russell:
            extra_sources.append(RUSSELL_2000_PATH)

        candidates = load_seed_candidates(seed_path, extra_sources=extra_sources)

    if args.limit and args.limit > 0:
        candidates = candidates[: args.limit]

    builder = UniverseBuilder(ctx.config)
    try:
        universe_df = builder.build_universe(candidates, persist=not args.no_persist)
    except Exception as exc:
        logger.exception("Universe scan failed: %s", exc)
        return 1

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        universe_df.to_csv(output_path, index=False)
        logger.info("Universe snapshot written to %s", output_path)

    print(f"Screened {len(candidates)} candidates -> {len(universe_df)} passing filters")
    if not universe_df.empty:
        preview = universe_df.head(args.preview_rows)
        print("\nPreview:\n", preview)
        skipped = builder.last_skipped_symbols()
        if skipped:
            print(f"Skipped {len(skipped)} symbols due to data issues: {', '.join(skipped[:10])}")

    if args.email and not universe_df.empty:
        send_scan_email(ctx.config, universe_df)

    return 0



def handle_backtest(args: argparse.Namespace, ctx: AppContext) -> int:
    try:
        price_data = load_price_data_for_backtest(args, ctx.config)
    except Exception as exc:
        logger.error("Failed to load price data: %s", exc)
        return 1

    strategies = instantiate_strategies(args.strategies, ctx.config)
    if not strategies:
        logger.error("No valid strategies requested for backtest")
        return 1

    runner = StrategyBacktestRunner(BacktestingEngine())
    position_sizer = build_position_sizer(ctx.config)

    inferred_symbol = price_data.attrs.get("symbol") if hasattr(price_data, "attrs") else None
    active_symbol = (args.symbol.upper() if args.symbol else None) or inferred_symbol or "ASSET"

    try:
        reports = runner.run_strategies(
            price_data=price_data,
            strategies=strategies,
            position_sizer=position_sizer,
            initial_capital=args.capital,
            symbol=active_symbol,
        )
    except Exception as exc:
        logger.exception("Backtest execution failed: %s", exc)
        return 1

    if not reports:
        logger.error("Backtest produced no results")
        return 1

    weights = build_strategy_weight_map(ctx.config)
    performance_df = build_performance_report(reports)

    combined_output_path: Optional[Path] = None
    if args.output_dir:
        combined_output_path = Path(args.output_dir) / "combined" / "summary.csv"

    combined_summary_df = generate_combined_report(reports, combined_output_path)
    attribution_df = compute_attribution(reports, weights)
    combined_curve = combine_equity_curves(reports, weights)

    if args.output_dir:
        save_backtest_outputs(
            Path(args.output_dir),
            performance_df,
            attribution_df,
            combined_curve,
            combined_summary_df,
        )

    print("\nPerformance metrics:\n", performance_df.round(4))
    if not attribution_df.empty:
        print("\nAttribution:\n", attribution_df.round(4))
    if not combined_curve.empty:
        print("\nCombined equity curve preview:\n", combined_curve.head())

    if args.email:
        send_backtest_email(ctx.config, performance_df, attribution_df)

    return 0



def handle_report(args: argparse.Namespace, ctx: AppContext) -> int:
    if not any([args.performance, args.attribution, args.equity]):
        logger.error("Provide at least one report path using --performance, --attribution, or --equity")
        return 1

    if args.performance:
        path = Path(args.performance)
        if not path.exists():
            logger.error("Performance file %s does not exist", path)
        else:
            df = pd.read_csv(path, index_col=0)
            print("Performance report:\n", df)

    if args.attribution:
        path = Path(args.attribution)
        if not path.exists():
            logger.error("Attribution file %s does not exist", path)
        else:
            df = pd.read_csv(path, index_col=0)
            print("\nAttribution report:\n", df)

    if args.equity:
        path = Path(args.equity)
        if not path.exists():
            logger.error("Equity curve file %s does not exist", path)
        else:
            df = pd.read_csv(path, index_col=0)
            series = df.iloc[:, 0]
            print("\nEquity curve tail:\n", series.tail())

    return 0



def handle_health(args: argparse.Namespace, ctx: AppContext) -> int:
    equity_path = Path(args.equity) if args.equity else ctx.config.storage.portfolio_dir / "equity_curve.csv"
    positions_path = Path(args.positions) if args.positions else ctx.config.storage.portfolio_dir / "positions.csv"

    if not equity_path.exists():
        logger.error("Equity curve file not found: %s", equity_path)
        return 1
    if not positions_path.exists():
        logger.error("Positions file not found: %s", positions_path)
        return 1

    equity_curve = load_equity_curve(equity_path)
    positions_df = pd.read_csv(positions_path)

    monitor = PortfolioHealthMonitor(
        PortfolioHealthConfig(sector_limits=ctx.config.risk_management.sector_limits)
    )
    try:
        report = monitor.evaluate(equity_curve, positions_df)
    except Exception as exc:
        logger.error("Failed to evaluate portfolio health: %s", exc)
        return 1

    print(f"Max drawdown: {report.max_drawdown:.2%}")
    if report.drawdown_alerts:
        print("\nAlerts:")
        for alert in report.drawdown_alerts:
            print(f"- {alert}")
    if report.sector_breaches:
        print("\nSector breaches:")
        for breach in report.sector_breaches:
            print(f"- {breach.sector}: {breach.allocation:.2%} (limit {breach.limit:.2%})")

    if args.email and (report.drawdown_alerts or report.sector_breaches):
        send_health_email(ctx.config, report)

    return 0



def handle_notebook(args: argparse.Namespace, _ctx: AppContext) -> int:
    template_path = Path(args.template)
    dest_path = Path(args.dest)

    if not template_path.exists():
        logger.error("Template notebook not found: %s", template_path)
        return 1
    if dest_path.exists() and not args.force:
        logger.error("Destination %s already exists. Use --force to overwrite.", dest_path)
        return 1

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, dest_path)
    print(f"Notebook copied to {dest_path}")
    return 0



def handle_refresh_fundamentals(args: argparse.Namespace, ctx: AppContext) -> int:
    api_key = ctx.config.data_sources.alpha_vantage_key
    if not api_key:
        logger.error("Alpha Vantage API key not configured; set data_sources.alpha_vantage_key or TS_ALPHA_VANTAGE_KEY.")
        return 1

    seed_path = Path(args.seed_candidates) if args.seed_candidates else None
    extra_sources: list[Path] = []
    if args.include_russell:
        extra_sources.append(RUSSELL_2000_PATH)

    symbols = load_seed_candidates(seed_path, extra_sources=extra_sources)

    if args.symbols:
        manual = [sym.strip().upper() for sym in args.symbols if sym]
        symbols = list(dict.fromkeys(manual + symbols))

    if args.limit and args.limit > 0:
        symbols = symbols[: args.limit]

    refreshed = refresh_fundamentals_cache(
        symbols=symbols,
        base_dir=ctx.config.storage.universe_dir,
        api_key=api_key,
        throttle_seconds=args.throttle,
    )
    print(f"Cached fundamentals for {refreshed} symbols")
    return 0

def handle_schedule_fundamentals(args: argparse.Namespace, ctx: AppContext) -> int:
    schedule_cfg = ctx.config.automation.fundamentals_refresh
    if not schedule_cfg.enabled and not args.force:
        logger.info("Fundamentals refresh automation is disabled in configuration; use --force to run anyway.")
        return 0

    if args.include_russell and args.skip_russell:
        logger.error("Cannot specify both --include-russell and --skip-russell.")
        return 1

    include_russell = schedule_cfg.include_russell
    if args.include_russell:
        include_russell = True
    if args.skip_russell:
        include_russell = False

    if getattr(args, "include_sp500", False) and getattr(args, "skip_sp500", False):
        logger.error("Cannot specify both --include-sp500 and --skip-sp500.")
        return 1

    include_sp500 = getattr(schedule_cfg, "include_sp500", False)
    if getattr(args, "include_sp500", False):
        include_sp500 = True
    if getattr(args, "skip_sp500", False):
        include_sp500 = False

    if args.throttle is not None and args.throttle < 0:
        logger.error("Throttle must be non-negative")
        return 1

    limit = args.limit if args.limit and args.limit > 0 else None

    if args.max_iterations is not None and args.max_iterations <= 0:
        logger.error("max-iterations must be greater than zero")
        return 1

    seed_path = Path(args.seed_candidates) if args.seed_candidates else None

    try:
        run_scheduled_refresh(
            ctx.config,
            schedule_cfg,
            run_once=args.run_once,
            max_iterations=args.max_iterations,
            seed_path=seed_path,
            include_russell=include_russell,
            include_sp500=include_sp500,
            limit=limit,
            throttle=args.throttle,
        )
    except FundamentalsValidationError as exc:
        logger.error("Fundamentals validation failed: %s", exc)
        return 1
    except ValueError as exc:
        logger.error(str(exc))
        return 1
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unexpected error while running fundamentals scheduler: %s", exc)
        return 1

    return 0


def handle_refresh_russell(args: argparse.Namespace, ctx: AppContext) -> int:
    url = args.url or DEFAULT_RUSSELL_URL
    dest = args.dest or (ctx.config.storage.universe_dir / "russell_2000.csv")

    try:
        count = refresh_russell_file(dest, url=url)
    except Exception as exc:  # pragma: no cover - network faults
        logger.error("Failed to refresh Russell 2000 list: %s", exc)
        return 1

    print(f"Saved {count} Russell symbols to {dest}")
    return 0



def handle_refresh_datasets(args: argparse.Namespace, ctx: AppContext) -> int:
    api_key = ctx.config.data_sources.alpha_vantage_key
    if not api_key:
        logger.error("Alpha Vantage API key not configured; set data_sources.alpha_vantage_key or TS_ALPHA_VANTAGE_KEY.")
        return 1

    status = 0
    if not args.skip_russell:
        url = args.russell_url or DEFAULT_RUSSELL_URL
        dest = args.russell_dest or (ctx.config.storage.universe_dir / 'russell_2000.csv')
        try:
            count = refresh_russell_file(dest, url=url)
            logger.info("Refreshed Russell 2000 list (%s symbols)", count)
        except Exception as exc:  # pragma: no cover - network faults
            logger.error("Failed to refresh Russell 2000 list: %s", exc)
            status = 1

    seed_path = Path(args.seed_candidates) if args.seed_candidates else None
    extra_sources: list[Path] = []
    include_russell = args.include_russell or (not args.skip_russell)
    if include_russell:
        extra_sources.append(RUSSELL_2000_PATH)

    symbols = load_seed_candidates(seed_path, extra_sources=extra_sources)
    if args.symbols:
        manual = [sym.strip().upper() for sym in args.symbols if sym]
        symbols = list(dict.fromkeys(manual + symbols))

    if args.limit and args.limit > 0:
        symbols = symbols[: args.limit]

    refreshed = refresh_fundamentals_cache(
        symbols=symbols,
        base_dir=ctx.config.storage.universe_dir,
        api_key=api_key,
        throttle_seconds=args.throttle,
    )
    print(f"Cached fundamentals for {refreshed} symbols")
    return status


def handle_update_strategy_metrics(args: argparse.Namespace, ctx: AppContext) -> int:
    if not args.input:
        logger.error("--input path is required")
        return 1
    input_path = Path(args.input)
    try:
        processed = load_and_ingest_metrics(input_path, dry_run=args.dry_run)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to ingest strategy metrics from %s: %s", input_path, exc)
        return 1
    suffix = " (dry run)" if args.dry_run else ""
    logger.info("Ingested %d strategy metric record(s)%s", processed, suffix)
    return 0


def handle_precompute_momentum(args: argparse.Namespace, ctx: AppContext) -> int:
    """Pre-compute momentum data for Russell 2000 and/or S&P 500 and cache it."""
    import json
    from datetime import datetime

    from dashboard_api.services import RussellMomentumService, SPMomentumService

    timeframes = args.timeframes or ["day", "week", "month", "ytd"]
    cache_dir = ctx.config.storage.universe_dir / "momentum_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    if not args.skip_russell:
        logger.info("Pre-computing Russell 2000 momentum data...")
        try:
            russell_service = RussellMomentumService(ctx.config)
            for tf in timeframes:
                logger.info("  Computing Russell momentum for timeframe: %s", tf)
                start_time = time.time()
                response = russell_service.get_momentum(timeframe=tf, limit=args.limit or 200)
                elapsed = time.time() - start_time
                logger.info("    Completed in %.2f seconds (%d symbols)", elapsed, response.evaluated_symbols)
                results[f"russell_{tf}"] = {
                    "timeframe": tf,
                    "evaluated_symbols": response.evaluated_symbols,
                    "skipped_symbols": response.skipped_symbols,
                    "computed_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.error("Failed to compute Russell momentum: %s", exc)
            if not args.skip_sp500:
                logger.info("Continuing with S&P 500...")
            else:
                return 1

    if not args.skip_sp500:
        logger.info("Pre-computing S&P 500 momentum data...")
        try:
            sp_service = SPMomentumService(ctx.config)
            for tf in timeframes:
                logger.info("  Computing S&P 500 momentum for timeframe: %s", tf)
                start_time = time.time()
                response = sp_service.get_momentum(timeframe=tf, limit=args.limit or 200)
                elapsed = time.time() - start_time
                logger.info("    Completed in %.2f seconds (%d symbols)", elapsed, response.evaluated_symbols)
                results[f"sp500_{tf}"] = {
                    "timeframe": tf,
                    "evaluated_symbols": response.evaluated_symbols,
                    "skipped_symbols": response.skipped_symbols,
                    "computed_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.error("Failed to compute S&P 500 momentum: %s", exc)
            return 1

    # Write summary to cache directory
    summary_path = cache_dir / "precompute_summary.json"
    summary = {
        "last_run": datetime.utcnow().isoformat(),
        "results": results,
    }
    summary_path.write_text(json.dumps(summary, indent=2))
    logger.info("Pre-computation complete. Summary written to %s", summary_path)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Small-Cap Growth Trading System CLI")
    parser.add_argument("--settings", type=Path, help="Path to user settings override JSON")
    parser.add_argument("--defaults", type=Path, help="Path to alternate default settings JSON")
    parser.add_argument("--force-config-reload", action="store_true", help="Reload configuration from disk")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan", help="Run the universe screening pipeline")
    scan.add_argument("--seed-candidates", type=Path, help="CSV of candidate symbols to seed the scan")
    scan.add_argument("--symbols", nargs="+", help="Explicit symbols to scan")
    scan.add_argument("--limit", type=int, help="Limit number of symbols to evaluate")
    scan.add_argument("--preview-rows", type=int, default=5, help="Rows to show in CLI preview")
    scan.add_argument("--include-russell", action="store_true", help="Include Russell 2000 constituents in the candidate seed list")
    scan.add_argument("--output", type=Path, help="Optional CSV path for scan results")
    scan.add_argument("--no-persist", action="store_true", help="Skip persisting to configured storage directory")
    scan.add_argument("--email", action="store_true", help="Email summary using configured dispatcher")
    scan.set_defaults(handler=handle_scan)

    backtest = subparsers.add_parser("backtest", help="Run strategy backtests")
    backtest.add_argument("--prices", type=Path, help="CSV file containing price history with a date column")
    backtest.add_argument("--symbol", help="Ticker symbol to fetch via Yahoo Finance")
    backtest.add_argument("--start", help="Backtest start date (YYYY-MM-DD)")
    backtest.add_argument("--end", help="Backtest end date (YYYY-MM-DD)")
    backtest.add_argument("--interval", default="1d", help="Price interval for Yahoo downloads")
    backtest.add_argument("--capital", type=float, default=100_000.0, help="Initial capital for the backtest")
    backtest.add_argument("--strategies", nargs="+", help="Strategies to include (default: all registered)")
    backtest.add_argument("--output-dir", type=Path, help="Directory for writing reports")
    backtest.add_argument("--email", action="store_true", help="Email performance summary after completion")
    backtest.set_defaults(handler=handle_backtest)

    report = subparsers.add_parser("report", help="Inspect previously generated reports")
    report.add_argument("--performance", type=Path, help="Path to performance metrics CSV")
    report.add_argument("--attribution", type=Path, help="Path to attribution CSV")
    report.add_argument("--equity", type=Path, help="Path to combined equity curve CSV")
    report.set_defaults(handler=handle_report)

    health = subparsers.add_parser("health", help="Evaluate portfolio health and alerts")
    health.add_argument("--equity", type=Path, help="Equity curve CSV path")
    health.add_argument("--positions", type=Path, help="Positions CSV path")
    health.add_argument("--email", action="store_true", help="Email alerts when thresholds are breached")
    health.set_defaults(handler=handle_health)

    notebook = subparsers.add_parser("notebook", help="Manage analysis notebook templates")
    notebook.add_argument("--template", type=Path, default=Path("notebooks/backtest_analysis_template.ipynb"), help="Source template path")
    notebook.add_argument("--dest", type=Path, default=Path("notebooks/trading_dashboard.ipynb"), help="Destination path for the notebook")
    notebook.add_argument("--force", action="store_true", help="Overwrite destination if it exists")
    notebook.set_defaults(handler=handle_notebook)

    refresh = subparsers.add_parser("refresh-fundamentals", help="Refresh cached fundamentals via Alpha Vantage")
    refresh.add_argument("--symbols", nargs="+", help="Explicit symbols to refresh")
    refresh.add_argument("--seed-candidates", type=Path, help="CSV of candidate symbols to seed the refresh")
    refresh.add_argument("--include-russell", action="store_true", help="Include Russell 2000 constituents when refreshing")
    refresh.add_argument("--limit", type=int, help="Limit number of symbols to refresh")
    refresh.add_argument("--throttle", type=float, default=12.0, help="Seconds to wait between Alpha Vantage requests (default: 12)")
    refresh.set_defaults(handler=handle_refresh_fundamentals)


    russell = subparsers.add_parser("refresh-russell", help="Download the latest Russell 2000 constituents")
    russell.add_argument("--url", help="Optional source URL for the Russell 2000 CSV")
    russell.add_argument("--dest", type=Path, help="Destination CSV path (default: storage.universe_dir/'russell_2000.csv')")
    russell.set_defaults(handler=handle_refresh_russell)


    datasets = subparsers.add_parser("refresh-datasets", help="Refresh Russell constituents and fundamentals cache")
    datasets.add_argument("--symbols", nargs="+", help="Explicit symbols to refresh for fundamentals")
    datasets.add_argument("--seed-candidates", type=Path, help="CSV of candidate symbols to seed the refresh")
    datasets.add_argument("--include-russell", action="store_true", help="Include Russell 2000 constituents when refreshing fundamentals")
    datasets.add_argument("--limit", type=int, help="Limit number of symbols to refresh")
    datasets.add_argument("--throttle", type=float, default=12.0, help="Seconds to wait between Alpha Vantage requests (default: 12)")
    datasets.add_argument("--russell-url", help="Alternate source URL for the Russell 2000 CSV")
    datasets.add_argument("--russell-dest", type=Path, help="Destination CSV path (default: storage.universe_dir/'russell_2000.csv')")
    datasets.add_argument("--skip-russell", action="store_true", help="Skip downloading the Russell 2000 list")
    datasets.set_defaults(handler=handle_refresh_datasets)

    metrics = subparsers.add_parser("update-strategy-metrics", help="Upsert strategy reliability metrics from a JSON payload")
    metrics.add_argument("--input", type=Path, required=True, help="Path to a JSON array of strategy metric records")
    metrics.add_argument("--dry-run", action="store_true", help="Validate records without committing changes")
    metrics.set_defaults(handler=handle_update_strategy_metrics)

    schedule = subparsers.add_parser("schedule-fundamentals", help="Run scheduled fundamentals refresh automation")
    schedule.add_argument("--seed-candidates", type=Path, help="Optional seed candidates CSV override")
    schedule.add_argument("--include-russell", action="store_true", help="Include Russell 2000 constituents for refresh regardless of config")
    schedule.add_argument("--skip-russell", action="store_true", help="Exclude Russell 2000 constituents even if enabled in config")
    schedule.add_argument("--include-sp500", action="store_true", help="Include S&P 500 constituents for refresh regardless of config")
    schedule.add_argument("--skip-sp500", action="store_true", help="Exclude S&P 500 constituents even if enabled in config")
    schedule.add_argument("--limit", type=int, help="Override the maximum number of symbols refreshed per cycle")
    schedule.add_argument("--throttle", type=float, help="Override the Alpha Vantage throttle (seconds)")
    schedule.add_argument("--run-once", action="store_true", help="Run a single refresh cycle immediately and exit")
    schedule.add_argument("--max-iterations", type=int, help="Limit the number of scheduled cycles before exiting")
    schedule.add_argument("--force", action="store_true", help="Run even if automation is disabled in the configuration")
    schedule.set_defaults(handler=handle_schedule_fundamentals)

    precompute = subparsers.add_parser("precompute-momentum", help="Pre-compute momentum data for faster API responses")
    precompute.add_argument("--timeframes", nargs="+", choices=["day", "week", "month", "ytd"], help="Timeframes to compute (default: all)")
    precompute.add_argument("--limit", type=int, default=200, help="Maximum symbols per leaderboard (default: 200)")
    precompute.add_argument("--skip-russell", action="store_true", help="Skip Russell 2000 momentum computation")
    precompute.add_argument("--skip-sp500", action="store_true", help="Skip S&P 500 momentum computation")
    precompute.set_defaults(handler=handle_precompute_momentum)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.verbose)
    ctx = build_context(args)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    return args.handler(args, ctx)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())











