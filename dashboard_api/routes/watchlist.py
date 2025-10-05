"""Watchlist API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..watchlist import (
    WatchlistEntry,
    deserialise_scores,
    deserialise_signal,
    get_session,
    serialise_scores,
    serialise_signal,
)

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


class StrategyScoreModel(BaseModel):
    name: str
    label: str
    value: float = Field(ge=0)


class AggregatedSignalModel(BaseModel):
    date: str
    signal_type: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class WatchlistItem(BaseModel):
    id: str
    symbol: str
    status: str
    saved_at: datetime
    average_score: float
    final_scores: List[StrategyScoreModel]
    aggregated_signal: Optional[AggregatedSignalModel] = None


class WatchlistUpsert(BaseModel):
    symbol: str
    status: str
    final_scores: List[StrategyScoreModel]
    average_score: float
    aggregated_signal: Optional[AggregatedSignalModel] = None


@router.get("", response_model=List[WatchlistItem])
def list_watchlist(session: Session = Depends(get_session)) -> List[WatchlistItem]:
    statement = select(WatchlistEntry).order_by(WatchlistEntry.saved_at.desc())
    entries = session.exec(statement).all()
    return [
        WatchlistItem(
            id=entry.id,
            symbol=entry.symbol,
            status=entry.status,
            saved_at=entry.saved_at,
            average_score=entry.average_score,
            final_scores=deserialise_scores(entry.final_scores),
            aggregated_signal=deserialise_signal(entry.aggregated_signal),
        )
        for entry in entries
    ]


@router.post("", response_model=WatchlistItem, status_code=status.HTTP_201_CREATED)
def upsert_watchlist_item(payload: WatchlistUpsert, session: Session = Depends(get_session)) -> WatchlistItem:
    symbol = payload.symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol must not be empty")

    entry = session.get(WatchlistEntry, symbol)
    saved_at = datetime.utcnow()

    if entry is None:
        entry = WatchlistEntry(
            id=symbol,
            symbol=symbol,
            status=payload.status,
            saved_at=saved_at,
            average_score=payload.average_score,
            final_scores=serialise_scores([score.model_dump() for score in payload.final_scores]),
            aggregated_signal=serialise_signal(payload.aggregated_signal.model_dump() if payload.aggregated_signal else None),
        )
        session.add(entry)
    else:
        entry.status = payload.status
        entry.saved_at = saved_at
        entry.average_score = payload.average_score
        entry.final_scores = serialise_scores([score.model_dump() for score in payload.final_scores])
        entry.aggregated_signal = serialise_signal(payload.aggregated_signal.model_dump() if payload.aggregated_signal else None)

    session.commit()
    session.refresh(entry)

    return WatchlistItem(
        id=entry.id,
        symbol=entry.symbol,
        status=entry.status,
        saved_at=entry.saved_at,
        average_score=entry.average_score,
        final_scores=deserialise_scores(entry.final_scores),
        aggregated_signal=deserialise_signal(entry.aggregated_signal),
    )


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_item(symbol: str, session: Session = Depends(get_session)) -> None:
    entry = session.get(WatchlistEntry, symbol.upper())
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist entry not found")
    session.delete(entry)
    session.commit()
