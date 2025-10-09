"""API routes exposing S&P 500 momentum snapshots."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_sp_momentum_service
from ..schemas import MomentumResponse
from ..services import SPMomentumService

router = APIRouter(prefix="/sp500", tags=["SP500"])

TimeframeLiteral = Literal["day", "week", "month", "ytd"]


@router.get(
    "/momentum",
    response_model=MomentumResponse,
    summary="S&P 500 momentum leaderboard",
    response_description="Top gainers and laggards within the S&P 500 for the requested timeframe.",
)
def get_sp500_momentum(
    timeframe: TimeframeLiteral = Query(
        "week",
        description="Performance window to evaluate (day, week, month, ytd).",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of symbols to include per leaderboard section.",
    ),
    service: SPMomentumService = Depends(get_sp_momentum_service),
) -> MomentumResponse:
    """Return S&P 500 momentum data for dashboards."""
    try:
        return service.get_momentum(timeframe=timeframe, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error") from exc


__all__ = ["router"]
