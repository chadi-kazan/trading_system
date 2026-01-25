"""API routes exposing Russell 2000 momentum snapshots."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_russell_momentum_service
from ..schemas import MomentumResponse
from ..services import RussellMomentumService

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/russell", tags=["Russell"])

TimeframeLiteral = Literal["day", "week", "month", "ytd"]


@router.get(
    "/momentum",
    response_model=MomentumResponse,
    summary="Russell 2000 momentum leaderboard",
    response_description="Top gainers and laggards within the Russell 2000 for the requested timeframe.",
)
def get_russell_momentum(
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
    service: RussellMomentumService = Depends(get_russell_momentum_service),
) -> MomentumResponse:
    """Return Russell 2000 momentum data for dashboards."""
    try:
        print(f">>> get_russell_momentum called: timeframe={timeframe}, limit={limit}")
        result = service.get_momentum(timeframe=timeframe, limit=limit)
        print(">>> get_russell_momentum completed successfully")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        import traceback
        print(f">>> UNEXPECTED ERROR in get_russell_momentum: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error") from exc


__all__ = ["router"]
