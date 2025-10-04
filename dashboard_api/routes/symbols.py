"""Symbol-centric endpoints for the dashboard API."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_signal_service
from ..schemas import SearchResponse, SymbolAnalysisResponse
from ..services import SignalService

router = APIRouter(tags=["Symbols"])


@router.get("/search", response_model=SearchResponse)
def search_symbols(
    q: str = Query(..., description="Symbol or keyword to search"),
    service: SignalService = Depends(get_signal_service),
) -> SearchResponse:
    results = service.search_symbols(q)
    return SearchResponse(query=q, results=results)


@router.get("/symbols/{symbol}", response_model=SymbolAnalysisResponse)
def get_symbol_analysis(
    symbol: str,
    start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("1d", description="Yahoo Finance interval (e.g. 1d, 1wk)"),
    service: SignalService = Depends(get_signal_service),
) -> SymbolAnalysisResponse:
    resolved_end = end or date.today()
    resolved_start = start or (resolved_end - timedelta(days=365 * 3))

    try:
        return service.get_symbol_analysis(
            symbol,
            start=resolved_start,
            end=resolved_end,
            interval=interval,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to analyse symbol") from exc
