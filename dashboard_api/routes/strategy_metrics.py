"""API routes for querying and updating strategy performance metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..strategy_metrics import (
    MarketRegime,
    Strategy,
    StrategyMetricHistory,
    StrategyRegimeSnapshot,
    deserialise_dict,
    get_session,
    serialise_dict,
)

router = APIRouter(prefix="/strategy-metrics", tags=["StrategyMetrics"])


class StrategyModel(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    default_weight: Optional[float] = None


class RegimeModel(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    detection_notes: Optional[str] = None


class StrategyMetricHistoryModel(BaseModel):
    observed_at: datetime
    reliability_weight: Optional[float] = None
    avg_excess_return: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    sample_size: Optional[int] = None
    correlation_penalty: Optional[float] = None
    regime_fit: Optional[float] = None
    decay_lambda: Optional[float] = None
    extras: Dict[str, Any] = Field(default_factory=dict)


class StrategyMetricSummary(BaseModel):
    strategy: StrategyModel
    regime: RegimeModel
    sample_size: int
    wins: int
    win_rate: Optional[float] = None
    avg_excess_return: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    decay_lambda: Optional[float] = None
    reliability_weight: Optional[float] = None
    correlation_penalty: Optional[float] = None
    regime_fit: Optional[float] = None
    last_sampled_at: Optional[datetime] = None
    updated_at: datetime
    extras: Dict[str, Any] = Field(default_factory=dict)
    history: List[StrategyMetricHistoryModel] = Field(default_factory=list)


class StrategyMetricUpsert(BaseModel):
    strategy_id: str = Field(..., description="Unique identifier for the strategy (e.g., dan_zanger_cup_handle)")
    strategy_label: Optional[str] = Field(None, description="Human label used in dashboards")
    description: Optional[str] = None
    default_weight: Optional[float] = Field(None, ge=0)
    regime_slug: str = Field(..., description="Machine-readable regime identifier (e.g., bull_trending)")
    regime_name: Optional[str] = None
    regime_description: Optional[str] = None
    detection_notes: Optional[str] = None
    sample_size: int = Field(..., ge=0)
    wins: int = Field(..., ge=0)
    avg_excess_return: Optional[float] = None
    volatility: Optional[float] = Field(None, ge=0)
    max_drawdown: Optional[float] = None
    reliability_weight: Optional[float] = Field(None, ge=0)
    correlation_penalty: Optional[float] = None
    regime_fit: Optional[float] = None
    decay_lambda: Optional[float] = Field(None, ge=0)
    last_sampled_at: Optional[datetime] = None
    extras: Optional[Dict[str, Any]] = None


def _fetch_strategies(session: Session, ids: Iterable[str]) -> Dict[str, Strategy]:
    if not ids:
        return {}
    statement = select(Strategy).where(Strategy.id.in_(list(ids)))
    return {strategy.id: strategy for strategy in session.exec(statement).all()}


def _fetch_regimes(session: Session, slugs: Iterable[str]) -> Dict[str, MarketRegime]:
    if not slugs:
        return {}
    statement = select(MarketRegime).where(MarketRegime.slug.in_(list(slugs)))
    return {regime.slug: regime for regime in session.exec(statement).all()}


def _build_history_models(rows: List[StrategyMetricHistory]) -> List[StrategyMetricHistoryModel]:
    return [
        StrategyMetricHistoryModel(
            observed_at=row.observed_at,
            reliability_weight=row.reliability_weight,
            avg_excess_return=row.avg_excess_return,
            volatility=row.volatility,
            max_drawdown=row.max_drawdown,
            win_rate=row.win_rate,
            sample_size=row.sample_size,
            correlation_penalty=row.correlation_penalty,
            regime_fit=row.regime_fit,
            decay_lambda=row.decay_lambda,
            extras=deserialise_dict(row.extras) or {},
        )
        for row in rows
    ]


@router.get("", response_model=List[StrategyMetricSummary])
def list_strategy_metrics(
    include_history: bool = Query(False, description="Include time-series history for each strategy/regime pair"),
    strategy_id: Optional[str] = Query(None, description="Filter by strategy identifier"),
    session: Session = Depends(get_session),
) -> List[StrategyMetricSummary]:
    statement = select(StrategyRegimeSnapshot)
    if strategy_id:
        statement = statement.where(StrategyRegimeSnapshot.strategy_id == strategy_id)

    snapshots = session.exec(statement).all()
    if not snapshots:
        return []

    strategy_map = _fetch_strategies(session, {snapshot.strategy_id for snapshot in snapshots})
    regime_map = _fetch_regimes(session, {snapshot.regime_slug for snapshot in snapshots})

    history_lookup: Dict[tuple[str, str], List[StrategyMetricHistoryModel]] = {}
    if include_history:
        for snapshot in snapshots:
            history_statement = (
                select(StrategyMetricHistory)
                .where(
                    StrategyMetricHistory.strategy_id == snapshot.strategy_id,
                    StrategyMetricHistory.regime_slug == snapshot.regime_slug,
                )
                .order_by(StrategyMetricHistory.observed_at.desc())
            )
            history_rows = session.exec(history_statement).all()
            history_lookup[(snapshot.strategy_id, snapshot.regime_slug)] = _build_history_models(history_rows)

    summaries: List[StrategyMetricSummary] = []
    for snapshot in snapshots:
        strategy = strategy_map.get(snapshot.strategy_id)
        regime = regime_map.get(snapshot.regime_slug)
        if strategy is None or regime is None:
            # Data integrity issue: skip rather than crashing.
            continue
        summaries.append(
            StrategyMetricSummary(
                strategy=StrategyModel(
                    id=strategy.id,
                    label=strategy.label,
                    description=strategy.description,
                    default_weight=strategy.default_weight,
                ),
                regime=RegimeModel(
                    slug=regime.slug,
                    name=regime.name,
                    description=regime.description,
                    detection_notes=regime.detection_notes,
                ),
                sample_size=snapshot.sample_size,
                wins=snapshot.wins,
                win_rate=snapshot.win_rate,
                avg_excess_return=snapshot.avg_excess_return,
                volatility=snapshot.volatility,
                max_drawdown=snapshot.max_drawdown,
                decay_lambda=snapshot.decay_lambda,
                reliability_weight=snapshot.reliability_weight,
                correlation_penalty=snapshot.correlation_penalty,
                regime_fit=snapshot.regime_fit,
                last_sampled_at=snapshot.last_sampled_at,
                updated_at=snapshot.updated_at,
                extras=deserialise_dict(snapshot.extras) or {},
                history=history_lookup.get((snapshot.strategy_id, snapshot.regime_slug), []),
            )
        )

    return summaries


@router.post("", response_model=List[StrategyMetricSummary], status_code=status.HTTP_201_CREATED)
def upsert_strategy_metrics(
    payload: List[StrategyMetricUpsert],
    session: Session = Depends(get_session),
) -> List[StrategyMetricSummary]:
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload must contain at least one entry")

    summaries: List[StrategyMetricSummary] = []
    now = datetime.utcnow()

    for item in payload:
        strategy_id = item.strategy_id.strip().lower()
        regime_slug = item.regime_slug.strip().lower()
        if not strategy_id or not regime_slug:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Strategy ID and regime slug must be provided")

        strategy = session.get(Strategy, strategy_id)
        if strategy is None:
            strategy = Strategy(id=strategy_id, label=item.strategy_label or strategy_id.replace("_", " ").title())
            session.add(strategy)
        if item.strategy_label:
            strategy.label = item.strategy_label
        if item.description is not None:
            strategy.description = item.description
        if item.default_weight is not None:
            strategy.default_weight = item.default_weight
        strategy.updated_at = now

        regime = session.get(MarketRegime, regime_slug)
        if regime is None:
            regime = MarketRegime(slug=regime_slug, name=item.regime_name or regime_slug.replace("_", " ").title())
            session.add(regime)
        if item.regime_name:
            regime.name = item.regime_name
        if item.regime_description is not None:
            regime.description = item.regime_description
        if item.detection_notes is not None:
            regime.detection_notes = item.detection_notes

        snapshot_statement = select(StrategyRegimeSnapshot).where(
            StrategyRegimeSnapshot.strategy_id == strategy_id,
            StrategyRegimeSnapshot.regime_slug == regime_slug,
        )
        snapshot = session.exec(snapshot_statement).one_or_none()

        win_rate = item.wins / item.sample_size if item.sample_size > 0 else None
        extras_serialised = serialise_dict(item.extras)

        if snapshot is None:
            snapshot = StrategyRegimeSnapshot(
                strategy_id=strategy_id,
                regime_slug=regime_slug,
                sample_size=item.sample_size,
                wins=item.wins,
                win_rate=win_rate,
                avg_excess_return=item.avg_excess_return,
                volatility=item.volatility,
                max_drawdown=item.max_drawdown,
                decay_lambda=item.decay_lambda,
                reliability_weight=item.reliability_weight,
                correlation_penalty=item.correlation_penalty,
                regime_fit=item.regime_fit,
                extras=extras_serialised,
                last_sampled_at=item.last_sampled_at,
                updated_at=now,
            )
            session.add(snapshot)
        else:
            snapshot.sample_size = item.sample_size
            snapshot.wins = item.wins
            snapshot.win_rate = win_rate
            snapshot.avg_excess_return = item.avg_excess_return
            snapshot.volatility = item.volatility
            snapshot.max_drawdown = item.max_drawdown
            snapshot.decay_lambda = item.decay_lambda
            snapshot.reliability_weight = item.reliability_weight
            snapshot.correlation_penalty = item.correlation_penalty
            snapshot.regime_fit = item.regime_fit
            snapshot.extras = extras_serialised
            snapshot.last_sampled_at = item.last_sampled_at
            snapshot.updated_at = now

        history_entry = StrategyMetricHistory(
            strategy_id=strategy_id,
            regime_slug=regime_slug,
            observed_at=item.last_sampled_at or now,
            reliability_weight=item.reliability_weight,
            avg_excess_return=item.avg_excess_return,
            volatility=item.volatility,
            max_drawdown=item.max_drawdown,
            win_rate=win_rate,
            sample_size=item.sample_size,
            correlation_penalty=item.correlation_penalty,
            regime_fit=item.regime_fit,
            decay_lambda=item.decay_lambda,
            extras=extras_serialised,
        )
        session.add(history_entry)

        summaries.append(
            StrategyMetricSummary(
                strategy=StrategyModel(
                    id=strategy.id,
                    label=strategy.label,
                    description=strategy.description,
                    default_weight=strategy.default_weight,
                ),
                regime=RegimeModel(
                    slug=regime.slug,
                    name=regime.name,
                    description=regime.description,
                    detection_notes=regime.detection_notes,
                ),
                sample_size=item.sample_size,
                wins=item.wins,
                win_rate=win_rate,
                avg_excess_return=item.avg_excess_return,
                volatility=item.volatility,
                max_drawdown=item.max_drawdown,
                decay_lambda=item.decay_lambda,
                reliability_weight=item.reliability_weight,
                correlation_penalty=item.correlation_penalty,
                regime_fit=item.regime_fit,
                last_sampled_at=item.last_sampled_at or now,
                updated_at=now,
                extras=item.extras or {},
                history=[],
            )
        )

    session.commit()

    return summaries
