"""Metadata endpoints for the dashboard API."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends

from ..dependencies import get_signal_service
from ..schemas import HealthResponse, StrategyInfo
from ..services import SignalService

router = APIRouter(tags=["Meta"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", timestamp=datetime.utcnow())


@router.get("/strategies", response_model=List[StrategyInfo])
def list_strategies(service: SignalService = Depends(get_signal_service)) -> List[StrategyInfo]:
    return service.list_strategies()
