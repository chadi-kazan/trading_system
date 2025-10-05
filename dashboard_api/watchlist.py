"""Database models and helpers for the dashboard watchlist."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "watchlist.db"

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)


class WatchlistEntry(SQLModel, table=True):
    """SQLite persisted watchlist entry."""

    id: str = Field(primary_key=True, index=True)
    symbol: str
    status: str
    saved_at: datetime
    average_score: float
    final_scores: str
    aggregated_signal: Optional[str] = None


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterable[Session]:
    with Session(engine) as session:
        yield session


def serialise_scores(final_scores: list[dict]) -> str:
    return json.dumps(final_scores, separators=(",", ":"))


def deserialise_scores(payload: str | None) -> list[dict]:
    if not payload:
        return []
    try:
        data = json.loads(payload)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def serialise_signal(signal: Optional[dict]) -> Optional[str]:
    if signal is None:
        return None
    return json.dumps(signal, separators=(",", ":"))


def deserialise_signal(payload: str | None) -> Optional[dict]:
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
