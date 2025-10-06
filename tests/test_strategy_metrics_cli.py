from __future__ import annotations

import importlib
from datetime import datetime
from pathlib import Path

import pytest

try:
    from sqlmodel import Session, select
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    Session = None  # type: ignore[assignment]
    select = None  # type: ignore[assignment]

@pytest.mark.skipif(Session is None, reason="sqlmodel not installed")
def test_ingest_strategy_metrics(tmp_path, monkeypatch):
    db_path = tmp_path / "strategy_metrics.db"
    monkeypatch.setenv("STRATEGY_METRICS_DB_PATH", str(db_path))

    metrics_module = importlib.reload(importlib.import_module("dashboard_api.strategy_metrics"))
    automation = importlib.reload(importlib.import_module("automation.strategy_metrics_refresh"))

    record = automation.MetricRecord(
        strategy_id="trend_following",
        strategy_label="Trend Following",
        regime_slug="bull_trending",
        regime_name="Bull Trending",
        sample_size=40,
        wins=26,
        avg_excess_return=0.07,
        volatility=0.12,
        max_drawdown=0.15,
        reliability_weight=0.62,
        correlation_penalty=0.1,
        regime_fit=0.85,
        decay_lambda=0.2,
        last_sampled_at=datetime(2025, 10, 5, 12, 0, 0),
        extras={"notes": "Backtest window Q3"},
    )

    processed = automation.ingest_strategy_metrics([record], dry_run=False)
    assert processed == 1

    with Session(metrics_module.engine) as session:
        snapshot = session.exec(select(metrics_module.StrategyRegimeSnapshot)).one()
        assert snapshot.strategy_id == "trend_following"
        assert snapshot.sample_size == 40
        assert snapshot.wins == 26
        assert snapshot.reliability_weight == 0.62

        history_entries = session.exec(select(metrics_module.StrategyMetricHistory)).all()
        assert len(history_entries) == 1
        assert history_entries[0].strategy_id == "trend_following"
        assert history_entries[0].reliability_weight == 0.62

    # Ensure database file was created in the requested location
    assert db_path.exists()
