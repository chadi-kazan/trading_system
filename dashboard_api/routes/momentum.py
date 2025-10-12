"""Momentum analytics routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_momentum_analytics_service
from ..schemas import SectorScoreResponse
from ..services import MomentumAnalyticsService

router = APIRouter(prefix="/momentum", tags=["Momentum"])

TimeframeLiteral = Literal["day", "week", "month", "ytd"]


@router.get(
    "/sector-scores",
    response_model=SectorScoreResponse,
    summary="Sector strategy averages",
    response_description="Average strategy scores for the sector matching the supplied symbol.",
)
def get_sector_scores(
    symbol: str = Query(..., description="Ticker symbol to evaluate."),
    timeframe: TimeframeLiteral = Query("week", description="Performance window used to compute averages."),
    service: MomentumAnalyticsService = Depends(get_momentum_analytics_service),
) -> SectorScoreResponse:
    try:
        return service.get_sector_scores(symbol=symbol, timeframe=timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


__all__ = ["router"]
