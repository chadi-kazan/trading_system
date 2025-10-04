"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from .services import SignalService


@lru_cache(maxsize=1)
def get_signal_service() -> SignalService:
    return SignalService()


__all__ = ["get_signal_service"]
