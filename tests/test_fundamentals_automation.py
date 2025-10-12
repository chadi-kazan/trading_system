from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from automation import fundamentals_refresh as automation
from automation.fundamentals_refresh import (
    RefreshOutcome,
    ValidationError,
    calculate_next_run,
    refresh_once,
)
from trading_system.config_manager import ConfigManager, TradingSystemConfig


@pytest.fixture()
def automation_config(tmp_path) -> TradingSystemConfig:
    config = ConfigManager().load(force_reload=True)
    storage = replace(
        config.storage,
        price_cache_dir=tmp_path / "prices",
        universe_dir=tmp_path / "universe",
        signal_dir=tmp_path / "signals",
        portfolio_dir=tmp_path / "portfolio",
    )
    for directory in storage.__dict__.values():
        Path(directory).mkdir(parents=True, exist_ok=True)

    return replace(config, storage=storage)


def test_refresh_once_runs_validation_and_returns_outcome(automation_config):
    config = automation_config
    schedule = config.automation.fundamentals_refresh
    schedule = replace(
        schedule,
        validation=replace(
            schedule.validation,
            enabled=True,
            sample_size=2,
            min_universe_size=1,
            persist_snapshot=True,
            fail_on_breach=True,
        ),
    )

    class FakeBuilder:
        def __init__(self, cfg):
            self.config = cfg
            self._last_snapshot_path: Path | None = None

        def build_universe(self, symbols, persist=True):
            frame = pd.DataFrame({"symbol": ["AAA", "BBB"]})
            if persist:
                target = self.config.storage.universe_dir / "universe.csv"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("symbol\nAAA\nBBB\n", encoding="utf-8")
                self._last_snapshot_path = target
            else:
                self._last_snapshot_path = None
            return frame

        def last_snapshot_path(self):
            return self._last_snapshot_path

        def last_skipped_symbols(self):
            return ["MISS"]

        def collect_metadata_frame(self, symbols):
            return pd.DataFrame(
                {
                    "symbol": [sym for sym in symbols],
                    "name": [f"Name {sym}" for sym in symbols],
                    "sector": ["Tech"] * len(symbols),
                    "fetched_at": [datetime.utcnow().isoformat()] * len(symbols),
                }
            )

    outcome = refresh_once(
        config,
        schedule,
        seed_loader=lambda _path, extra_sources=None: ["AAA", "BBB", "CCC"],
        refresh_fn=lambda symbols, base_dir, api_key, throttle_seconds: len(symbols),
        builder_factory=lambda cfg: FakeBuilder(cfg),
    )

    assert outcome.refreshed == 3
    assert outcome.universe_size == 2
    assert outcome.snapshot_path is not None
    assert outcome.skipped_symbols == ["MISS"]
    metadata_file = config.storage.universe_dir / "sector_metadata.csv"
    assert metadata_file.exists()
    assert "symbol" in metadata_file.read_text()


def test_refresh_once_raises_validation_error_when_threshold_not_met(automation_config):
    config = automation_config
    schedule = config.automation.fundamentals_refresh
    schedule = replace(
        schedule,
        validation=replace(
            schedule.validation,
            enabled=True,
            min_universe_size=5,
            fail_on_breach=True,
        ),
    )

    class EmptyBuilder:
        def __init__(self, _cfg):
            self._last_snapshot_path = None

        def build_universe(self, symbols, persist=True):
            self._last_snapshot_path = None
            return pd.DataFrame(columns=["symbol"])

        def last_snapshot_path(self):
            return self._last_snapshot_path

        def last_skipped_symbols(self):
            return []

        def collect_metadata_frame(self, symbols):
            return pd.DataFrame(columns=["symbol", "name", "sector", "fetched_at"])

    with pytest.raises(ValidationError):
        refresh_once(
            config,
            schedule,
            seed_loader=lambda _path, extra_sources=None: ["AAA"],
            refresh_fn=lambda symbols, base_dir, api_key, throttle_seconds: len(symbols),
            builder_factory=lambda cfg: EmptyBuilder(cfg),
        )


def test_calculate_next_run_daily_and_weekly(automation_config):
    config = automation_config
    tz = ZoneInfo(config.automation.timezone)
    schedule = replace(config.automation.fundamentals_refresh, frequency="daily", time="10:00")

    now = datetime(2025, 1, 1, 12, 0, tzinfo=tz)
    next_run = calculate_next_run(now, schedule, config.automation.scan_day)
    assert next_run.date().isoformat() == "2025-01-02"
    assert next_run.time().hour == 10

    weekly_schedule = replace(schedule, frequency="weekly", day="monday")
    wednesday = datetime(2025, 1, 1, 9, 0, tzinfo=tz)  # Wednesday
    weekly_next = calculate_next_run(wednesday, weekly_schedule, config.automation.scan_day)
    assert weekly_next.weekday() == 0
    assert weekly_next > wednesday


def test_run_scheduled_refresh_run_once_delegates(monkeypatch, automation_config):
    config = automation_config
    schedule = config.automation.fundamentals_refresh

    calls: dict[str, object] = {}

    def fake_refresh(conf, sched, **kwargs):
        calls["config"] = conf
        calls["schedule"] = sched
        calls["kwargs"] = kwargs
        return RefreshOutcome(refreshed=1, universe_size=None, snapshot_path=None, skipped_symbols=[])

    monkeypatch.setattr(automation, "refresh_once", fake_refresh)

    automation.run_scheduled_refresh(
        config,
        schedule,
        run_once=True,
        limit=50,
    )

    assert calls["config"] is config
    assert calls["schedule"] == schedule
    assert calls["kwargs"]["limit"] == 50
    assert "include_sp500" in calls["kwargs"]
