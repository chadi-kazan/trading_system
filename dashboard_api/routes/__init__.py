from fastapi import APIRouter

from . import meta, strategy_metrics, symbols, watchlist

api_router = APIRouter(prefix="/api")
api_router.include_router(meta.router)
api_router.include_router(symbols.router)
api_router.include_router(watchlist.router)
api_router.include_router(strategy_metrics.router)

__all__ = ["api_router"]

