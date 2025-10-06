"""Utilities for ingesting strategy performance metrics into the strategy metrics database."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from sqlmodel import Session, select

from dashboard_api.strategy_metrics import (
    MarketRegime,
    Strategy,
    StrategyMetricHistory,
    StrategyRegimeSnapshot,
    engine,
    serialise_dict,
)

logger = logging.getLogger("strategy_metrics.refresh")


@dataclass(slots=True)
class MetricRecord:
    strategy_id: str
    regime_slug: str
    sample_size: int
    wins: int
    strategy_label: Optional[str] = None
    description: Optional[str] = None
    default_weight: Optional[float] = None
    regime_name: Optional[str] = None
    regime_description: Optional[str] = None
    detection_notes: Optional[str] = None
    avg_excess_return: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    reliability_weight: Optional[float] = None
    correlation_penalty: Optional[float] = None
    regime_fit: Optional[float] = None
    decay_lambda: Optional[float] = None
    last_sampled_at: Optional[datetime] = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "MetricRecord":
        data = payload.copy()
        last_sampled_at = data.get("last_sampled_at")
        if isinstance(last_sampled_at, str):
            try:
                data["last_sampled_at"] = datetime.fromisoformat(last_sampled_at)
            except ValueError:
                logger.warning("Could not parse last_sampled_at '%s' for strategy %s", last_sampled_at, data.get("strategy_id"))
                data["last_sampled_at"] = None
        extras = data.get("extras")
        if extras is None:
            data["extras"] = {}
        elif not isinstance(extras, dict):
            logger.warning("Extras payload for strategy %s is not a dict; ignoring", data.get("strategy_id"))
            data["extras"] = {}
        return cls(**data)

    @property
    def win_rate(self) -> Optional[float]:
        if self.sample_size <= 0:
            return None
        return self.wins / self.sample_size


def load_metric_records(path: Path) -> List[MetricRecord]:
    if not path.exists():
        raise FileNotFoundError(f"Metrics input file not found: {path}")
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("JSON metrics payload must be a list of objects")
        return [MetricRecord.from_mapping(item) for item in raw]
    raise ValueError("Unsupported metrics input format. Provide a JSON array of metric objects.")


def _upsert_record(record: MetricRecord, session: Session, observed_at: datetime) -> None:
    strategy_id = record.strategy_id.strip().lower()
    regime_slug = record.regime_slug.strip().lower()
    if not strategy_id or not regime_slug:
        raise ValueError("Strategy ID and regime slug must not be empty")

    strategy = session.get(Strategy, strategy_id)
    if strategy is None:
        strategy = Strategy(id=strategy_id, label=record.strategy_label or strategy_id.replace("_", " ").title())
        session.add(strategy)
    if record.strategy_label:
        strategy.label = record.strategy_label
    if record.description is not None:
        strategy.description = record.description
    if record.default_weight is not None:
        strategy.default_weight = record.default_weight
    strategy.updated_at = observed_at

    regime = session.get(MarketRegime, regime_slug)
    if regime is None:
        regime = MarketRegime(slug=regime_slug, name=record.regime_name or regime_slug.replace("_", " ").title())
        session.add(regime)
    if record.regime_name:
        regime.name = record.regime_name
    if record.regime_description is not None:
        regime.description = record.regime_description
    if record.detection_notes is not None:
        regime.detection_notes = record.detection_notes

    snapshot = session.exec(
        select(StrategyRegimeSnapshot).where(
            StrategyRegimeSnapshot.strategy_id == strategy_id,
            StrategyRegimeSnapshot.regime_slug == regime_slug,
        )
    ).one_or_none()

    extras_payload = serialise_dict(record.extras)
    win_rate = record.win_rate

    if snapshot is None:
        snapshot = StrategyRegimeSnapshot(
            strategy_id=strategy_id,
            regime_slug=regime_slug,
            sample_size=record.sample_size,
            wins=record.wins,
            win_rate=win_rate,
            avg_excess_return=record.avg_excess_return,
            volatility=record.volatility,
            max_drawdown=record.max_drawdown,
            decay_lambda=record.decay_lambda,
            reliability_weight=record.reliability_weight,
            correlation_penalty=record.correlation_penalty,
            regime_fit=record.regime_fit,
            extras=extras_payload,
            last_sampled_at=record.last_sampled_at,
            updated_at=observed_at,
        )
        session.add(snapshot)
    else:
        snapshot.sample_size = record.sample_size
        snapshot.wins = record.wins
        snapshot.win_rate = win_rate
        snapshot.avg_excess_return = record.avg_excess_return
        snapshot.volatility = record.volatility
        snapshot.max_drawdown = record.max_drawdown
        snapshot.decay_lambda = record.decay_lambda
        snapshot.reliability_weight = record.reliability_weight
        snapshot.correlation_penalty = record.correlation_penalty
        snapshot.regime_fit = record.regime_fit
        snapshot.extras = extras_payload
        snapshot.last_sampled_at = record.last_sampled_at
        snapshot.updated_at = observed_at

    history_entry = StrategyMetricHistory(
        strategy_id=strategy_id,
        regime_slug=regime_slug,
        observed_at=record.last_sampled_at or observed_at,
        reliability_weight=record.reliability_weight,
        avg_excess_return=record.avg_excess_return,
        volatility=record.volatility,
        max_drawdown=record.max_drawdown,
        win_rate=win_rate,
        sample_size=record.sample_size,
        correlation_penalty=record.correlation_penalty,
        regime_fit=record.regime_fit,
        decay_lambda=record.decay_lambda,
        extras=extras_payload,
    )
    session.add(history_entry)


def ingest_strategy_metrics(records: Sequence[MetricRecord], *, dry_run: bool = False) -> int:
    if not records:
        logger.info("No strategy metric records supplied; nothing to do")
        return 0

    processed = 0
    now = datetime.utcnow()
    with Session(engine) as session:
        for record in records:
            _upsert_record(record, session, observed_at=now)
            processed += 1
        if dry_run:
            session.rollback()
        else:
            session.commit()
    return processed


def load_and_ingest_metrics(path: Path, *, dry_run: bool = False) -> int:
    records = load_metric_records(path)
    return ingest_strategy_metrics(records, dry_run=dry_run)

