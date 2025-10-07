"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from .services import RussellMomentumService, SignalService


@lru_cache(maxsize=1)
def get_signal_service() -> SignalService:
    return SignalService()


@lru_cache(maxsize=1)
def get_russell_momentum_service() -> RussellMomentumService:
    return RussellMomentumService()


__all__ = ["get_signal_service", "get_russell_momentum_service"]
