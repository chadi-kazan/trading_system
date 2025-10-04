from fastapi import APIRouter

from . import meta, symbols

api_router = APIRouter(prefix="/api")
api_router.include_router(meta.router)
api_router.include_router(symbols.router)

__all__ = ["api_router"]
