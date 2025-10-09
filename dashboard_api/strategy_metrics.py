"""Database models and helpers for strategy performance metrics and weighting."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Session, SQLModel, create_engine


DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("STRATEGY_METRICS_DB_PATH", DATA_DIR / "strategy_metrics.db"))

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)

_TABLE_NAMES = ("strategy", "marketregime", "strategyregimesnapshot", "strategymetrichistory")
for _table_name in _TABLE_NAMES:
    table = SQLModel.metadata.tables.get(_table_name)
    if table is not None:
        SQLModel.metadata.remove(table)


class Strategy(SQLModel, table=True):
    """Reference metadata for a trading strategy."""

    id: str = Field(primary_key=True, index=True)
    label: str
    description: Optional[str] = None
    default_weight: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketRegime(SQLModel, table=True):
    """Describes a detected market regime (e.g., bull_trending, high_vol_range)."""

    slug: str = Field(primary_key=True, index=True)
    name: str
    description: Optional[str] = None
    detection_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyRegimeSnapshot(SQLModel, table=True):
    """Latest rolling metrics for a strategy within a specific market regime."""

    __table_args__ = (UniqueConstraint("strategy_id", "regime_slug", name="uq_strategy_regime"),)

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    strategy_id: str = Field(index=True, foreign_key="strategy.id")
    regime_slug: str = Field(index=True, foreign_key="marketregime.slug")
    sample_size: int = 0
    wins: int = 0
    win_rate: Optional[float] = None
    avg_excess_return: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    decay_lambda: Optional[float] = None
    reliability_weight: Optional[float] = None
    correlation_penalty: Optional[float] = None
    regime_fit: Optional[float] = None
    extras: Optional[str] = None
    last_sampled_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyMetricHistory(SQLModel, table=True):
    """Historical snapshot of strategy metrics for trend analysis and charting."""

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    strategy_id: str = Field(index=True, foreign_key="strategy.id")
    regime_slug: str = Field(index=True, foreign_key="marketregime.slug")
    observed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    reliability_weight: Optional[float] = None
    avg_excess_return: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    sample_size: Optional[int] = None
    correlation_penalty: Optional[float] = None
    regime_fit: Optional[float] = None
    decay_lambda: Optional[float] = None
    extras: Optional[str] = None


def init_db() -> None:
    """Create tables if they do not yet exist."""

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterable[Session]:
    """Yield a database session for dependency injection."""

    with Session(engine) as session:
        yield session


def serialise_dict(payload: Optional[dict]) -> Optional[str]:
    if not payload:
        return None
    return json.dumps(payload, separators=(",", ":"))


def deserialise_dict(payload: Optional[str]) -> Optional[dict]:
    if not payload:
        return None
    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        return None
    return None


init_db()

__all__ = [
    "Strategy",
    "MarketRegime",
    "StrategyRegimeSnapshot",
    "StrategyMetricHistory",
    "engine",
    "get_session",
    "serialise_dict",
    "deserialise_dict",
]
