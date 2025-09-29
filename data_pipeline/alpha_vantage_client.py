"""Alpha Vantage API client for fundamentals."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

LOGGER = logging.getLogger(__name__)


class AlphaVantageError(RuntimeError):
    """Raised when the Alpha Vantage API returns an error payload."""


class AlphaVantageClient:
    """Thin wrapper around the Alpha Vantage REST API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://www.alphavantage.co/query",
        session: Optional[requests.Session] = None,
    ) -> None:
        if not api_key:
            raise ValueError("Alpha Vantage API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    # ------------------------------------------------------------------
    def fetch_company_overview(self, symbol: str) -> Dict[str, Any]:
        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper(),
            "apikey": self.api_key,
        }
        response = self.session.get(self.base_url, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, dict):
            raise AlphaVantageError("Unexpected overview payload format")
        if payload.get("Note"):
            LOGGER.warning("Alpha Vantage throttling notice: %s", payload["Note"])
        if payload.get("Information"):
            raise AlphaVantageError(payload["Information"])  # pragma: no cover - upstream error
        if payload.get("Error Message"):
            raise AlphaVantageError(payload["Error Message"])  # pragma: no cover - invalid symbol

        return payload


__all__ = ["AlphaVantageClient", "AlphaVantageError"]
