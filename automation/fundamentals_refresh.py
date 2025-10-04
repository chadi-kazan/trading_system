"""Automation helpers for scheduling fundamental cache refreshes."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path
from typing import Callable, Optional, Sequence

from zoneinfo import ZoneInfo

from data_pipeline import refresh_fundamentals_cache
from trading_system.config_manager import (
    FundamentalsRefreshAutomationConfig,
    FundamentalsValidationConfig,
    TradingSystemConfig,
)
from universe.builder import UniverseBuilder
from universe.candidates import RUSSELL_2000_PATH, load_seed_candidates

LOGGER = logging.getLogger(__name__)

WEEKDAY_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(slots=True)
class RefreshOutcome:
    """Aggregated results from a fundamentals refresh cycle."""

    refreshed: int
    universe_size: Optional[int]
    snapshot_path: Path | None
    skipped_symbols: list[str]


class ValidationError(RuntimeError):
    """Raised when universe validation requirements are not satisfied."""


_TimeProvider = Callable[[ZoneInfo], datetime]
_SleepFunction = Callable[[float], None]


def _parse_time(value: str) -> dt_time:
    for pattern in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(value, pattern)
            return dt_time(hour=parsed.hour, minute=parsed.minute, second=parsed.second)
        except ValueError:
            continue
    raise ValueError(f"Invalid time format '{value}'. Expected HH:MM or HH:MM:SS")


def _resolve_timezone(name: str | None) -> ZoneInfo:
    tz_name = (name or "UTC").strip() or "UTC"
    return ZoneInfo(tz_name)


def calculate_next_run(
    now: datetime,
    schedule: FundamentalsRefreshAutomationConfig,
    default_day: str | None,
) -> datetime:
    """Return the next scheduled run timestamp in the same timezone as *now*."""

    if now.tzinfo is None:
        raise ValueError("'now' must be timezone aware")

    target_time = _parse_time(schedule.time)
    frequency = schedule.frequency.lower()

    if frequency == "daily":
        candidate = now.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=target_time.second,
            microsecond=0,
        )
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if frequency == "weekly":
        day_name = (schedule.day or default_day or "").strip().lower()
        if not day_name:
            raise ValueError("Weekly schedules require a day name")
        if day_name not in WEEKDAY_TO_INDEX:
            raise ValueError(f"Invalid weekday '{day_name}'")

        candidate = now.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=target_time.second,
            microsecond=0,
        )
        days_ahead = (WEEKDAY_TO_INDEX[day_name] - now.weekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate

    raise ValueError(f"Unsupported frequency '{schedule.frequency}'")


def refresh_once(
    config: TradingSystemConfig,
    schedule: FundamentalsRefreshAutomationConfig,
    *,
    seed_path: Path | None = None,
    symbols: Sequence[str] | None = None,
    include_russell: Optional[bool] = None,
    limit: Optional[int] = None,
    throttle: Optional[float] = None,
    seed_loader: Callable[[Path | None, Sequence[Path]], list[str]] = load_seed_candidates,
    refresh_fn: Callable[..., int] = refresh_fundamentals_cache,
    builder_factory: Callable[[TradingSystemConfig], UniverseBuilder] = UniverseBuilder,
) -> RefreshOutcome:
    """Run a single fundamentals refresh cycle and optional validation."""

    api_key = config.data_sources.alpha_vantage_key
    if not api_key:
        raise ValueError("Alpha Vantage API key is required to refresh fundamentals")

    include_russell = schedule.include_russell if include_russell is None else include_russell
    limit = schedule.limit if limit is None else limit
    throttle_seconds = schedule.throttle if throttle is None else throttle

    base_symbols: list[str]
    if symbols is not None:
        base_symbols = [sym.strip().upper() for sym in symbols if sym]
    else:
        extras: list[Path] = []
        if include_russell:
            extras.append(RUSSELL_2000_PATH)
        base_symbols = seed_loader(seed_path, extra_sources=extras)

    if limit is not None and limit > 0:
        base_symbols = base_symbols[:limit]

    refreshed = refresh_fn(
        symbols=base_symbols,
        base_dir=config.storage.universe_dir,
        api_key=api_key,
        throttle_seconds=throttle_seconds,
    )

    validation_cfg: FundamentalsValidationConfig = schedule.validation
    universe_size: Optional[int] = None
    snapshot_path: Path | None = None
    skipped: list[str] = []

    if validation_cfg.enabled:
        validation_symbols = list(base_symbols)
        if validation_cfg.sample_size is not None and validation_cfg.sample_size > 0:
            validation_symbols = validation_symbols[: validation_cfg.sample_size]

        if not validation_symbols:
            if validation_cfg.fail_on_breach:
                raise ValidationError("No symbols available for validation")
            LOGGER.warning("Validation skipped because no symbols were available")
        else:
            builder = builder_factory(config)
            frame = builder.build_universe(
                validation_symbols,
                persist=validation_cfg.persist_snapshot,
            )
            universe_size = len(frame)
            snapshot_path = builder.last_snapshot_path()
            skipped = builder.last_skipped_symbols()

            if (
                validation_cfg.fail_on_breach
                and validation_cfg.min_universe_size > 0
                and (universe_size or 0) < validation_cfg.min_universe_size
            ):
                raise ValidationError(
                    f"Universe validation size {universe_size or 0} fell below minimum {validation_cfg.min_universe_size}"
                )

    return RefreshOutcome(
        refreshed=refreshed,
        universe_size=universe_size,
        snapshot_path=snapshot_path,
        skipped_symbols=skipped,
    )


def run_scheduled_refresh(
    config: TradingSystemConfig,
    schedule: FundamentalsRefreshAutomationConfig,
    *,
    run_once: bool = False,
    max_iterations: Optional[int] = None,
    seed_path: Path | None = None,
    include_russell: Optional[bool] = None,
    limit: Optional[int] = None,
    throttle: Optional[float] = None,
    sleep_fn: _SleepFunction = time.sleep,
    now_fn: _TimeProvider | None = None,
) -> None:
    """Execute the fundamentals refresh job according to the provided schedule."""

    timezone = _resolve_timezone(config.automation.timezone)
    default_day = config.automation.scan_day

    def _run_job(allow_raise: bool) -> None:
        try:
            outcome = refresh_once(
                config,
                schedule,
                seed_path=seed_path,
                include_russell=include_russell,
                limit=limit,
                throttle=throttle,
            )
            LOGGER.info("Cached fundamentals for %s symbols", outcome.refreshed)
            if outcome.universe_size is not None:
                LOGGER.info(
                    "Universe validation produced %s symbols%s",
                    outcome.universe_size,
                    f"; snapshot stored at {outcome.snapshot_path}" if outcome.snapshot_path else "",
                )
            if outcome.skipped_symbols:
                LOGGER.info("Universe validation skipped %s symbols", len(outcome.skipped_symbols))
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Fundamentals refresh job failed")
            if allow_raise:
                raise

    if run_once:
        _run_job(allow_raise=True)
        return

    iterations = 0
    while True:
        tz_now = now_fn(timezone) if now_fn else datetime.now(timezone)
        next_run = calculate_next_run(tz_now, schedule, default_day)
        wait_seconds = max(0.0, (next_run - tz_now).total_seconds())
        LOGGER.info("Next fundamentals refresh scheduled for %s (%s)", next_run.isoformat(), timezone.key)
        if wait_seconds:
            sleep_fn(wait_seconds)
        _run_job(allow_raise=False)
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break


__all__ = [
    "RefreshOutcome",
    "ValidationError",
    "calculate_next_run",
    "refresh_once",
    "run_scheduled_refresh",
]
