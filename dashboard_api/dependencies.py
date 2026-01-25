"""Dependency providers for FastAPI routes."""

from __future__ import annotations

import logging
from functools import lru_cache

from .services import MomentumAnalyticsService, RussellMomentumService, SPMomentumService, SignalService

LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_signal_service() -> SignalService:
    return SignalService()


@lru_cache(maxsize=1)
def get_russell_momentum_service() -> RussellMomentumService:
    try:
        print(">>> Creating RussellMomentumService...")
        service = RussellMomentumService()
        print(">>> RussellMomentumService created successfully")
        return service
    except Exception as exc:
        import traceback
        print(f">>> FAILED to create RussellMomentumService: {exc}")
        traceback.print_exc()
        raise


@lru_cache(maxsize=1)
def get_sp_momentum_service() -> SPMomentumService:
    return SPMomentumService()


__all__ = ["get_signal_service", "get_russell_momentum_service", "get_sp_momentum_service", "get_momentum_analytics_service"]


@lru_cache(maxsize=1)
def get_momentum_analytics_service() -> MomentumAnalyticsService:
    return MomentumAnalyticsService(get_russell_momentum_service(), get_sp_momentum_service())

