"""Alpha Vantage API client for fundamentals."""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

import time

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
        max_retries: int = 3,
        backoff_seconds: float = 5.0,
        rate_limit_sleep: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("Alpha Vantage API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.max_retries = max(1, max_retries)
        self.backoff_seconds = max(0.0, backoff_seconds)
        self.rate_limit_sleep = max(0.0, rate_limit_sleep)

    # ------------------------------------------------------------------
    def fetch_company_overview(self, symbol: str) -> Dict[str, Any]:
        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper(),
            "apikey": self.api_key,
        }

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                payload = response.json()
            except requests.HTTPError as exc:  # pragma: no cover - network/HTTP errors
                response = exc.response
                if response is not None and response.status_code == 429:
                    wait_seconds = self._retry_after_seconds(response.headers)
                    self._handle_rate_limit(symbol, attempt, wait_seconds, detail="HTTP 429 response")
                    last_exc = exc
                    continue

                last_exc = exc
                LOGGER.warning(
                    "Alpha Vantage HTTP error for %s (attempt %s/%s): %s",
                    symbol,
                    attempt,
                    self.max_retries,
                    exc,
                )
            except Exception as exc:  # pragma: no cover - network/JSON errors
                last_exc = exc
                LOGGER.warning(
                    "Alpha Vantage request failed for %s (attempt %s/%s): %s",
                    symbol,
                    attempt,
                    self.max_retries,
                    exc,
                )
            else:
                if not isinstance(payload, dict):
                    raise AlphaVantageError("Unexpected overview payload format")

                note = payload.get("Note")
                if note:
                    self._handle_rate_limit(symbol, attempt, None, detail=note)
                    last_exc = AlphaVantageError(note)
                    continue

                if payload.get("Information"):
                    raise AlphaVantageError(payload["Information"])  # pragma: no cover - upstream error
                if payload.get("Error Message"):
                    raise AlphaVantageError(payload["Error Message"])  # pragma: no cover - invalid symbol

                return payload

            if attempt < self.max_retries and self.backoff_seconds:
                self._sleep(self.backoff_seconds)

        if last_exc:
            raise AlphaVantageError(f"Failed to fetch overview for {symbol}") from last_exc
        raise AlphaVantageError(f"Failed to fetch overview for {symbol}")

    # ------------------------------------------------------------------
    def fetch_earnings(self, symbol: str) -> Dict[str, Any]:
        params = {
            "function": "EARNINGS",
            "symbol": symbol.upper(),
            "apikey": self.api_key,
        }

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                payload = response.json()
            except requests.HTTPError as exc:  # pragma: no cover - network/HTTP errors
                resp = exc.response
                if resp is not None and resp.status_code == 429:
                    wait_seconds = self._retry_after_seconds(resp.headers)
                    self._handle_rate_limit(symbol, attempt, wait_seconds, detail="HTTP 429 response")
                    last_exc = exc
                    continue
                last_exc = exc
                LOGGER.warning(
                    "Alpha Vantage HTTP error for earnings %s (attempt %s/%s): %s",
                    symbol,
                    attempt,
                    self.max_retries,
                    exc,
                )
            except Exception as exc:  # pragma: no cover - network/JSON errors
                last_exc = exc
                LOGGER.warning(
                    "Alpha Vantage earnings request failed for %s (attempt %s/%s): %s",
                    symbol,
                    attempt,
                    self.max_retries,
                    exc,
                )
            else:
                if not isinstance(payload, dict):
                    raise AlphaVantageError("Unexpected earnings payload format")

                note = payload.get("Note")
                if note:
                    self._handle_rate_limit(symbol, attempt, None, detail=note)
                    last_exc = AlphaVantageError(note)
                    continue

                if payload.get("Information"):
                    raise AlphaVantageError(payload["Information"])  # pragma: no cover
                if payload.get("Error Message"):
                    raise AlphaVantageError(payload["Error Message"])  # pragma: no cover

                return payload

            if attempt < self.max_retries and self.backoff_seconds:
                self._sleep(self.backoff_seconds)

        if last_exc:
            raise AlphaVantageError(f"Failed to fetch earnings for {symbol}") from last_exc
        raise AlphaVantageError(f"Failed to fetch earnings for {symbol}")

    # ------------------------------------------------------------------
    def search_symbols(
        self,
        keywords: str,
        *,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Return search matches for *keywords* using Alpha Vantage SYMBOL_SEARCH."""

        query = (keywords or "").strip()
        if not query:
            return []

        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query,
            "apikey": self.api_key,
        }

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                payload = response.json()
            except requests.HTTPError as exc:  # pragma: no cover - network/HTTP errors
                resp = exc.response
                if resp is not None and resp.status_code == 429:
                    wait_seconds = self._retry_after_seconds(resp.headers)
                    self._handle_rate_limit(query, attempt, wait_seconds, detail="HTTP 429 response")
                    last_exc = exc
                    continue

                last_exc = exc
                LOGGER.warning(
                    "Alpha Vantage HTTP error during symbol search '%s' (attempt %s/%s): %s",
                    query,
                    attempt,
                    self.max_retries,
                    exc,
                )
            except Exception as exc:  # pragma: no cover - network/JSON errors
                last_exc = exc
                LOGGER.warning(
                    "Alpha Vantage symbol search failed for '%s' (attempt %s/%s): %s",
                    query,
                    attempt,
                    self.max_retries,
                    exc,
                )
            else:
                if not isinstance(payload, dict):
                    raise AlphaVantageError("Unexpected symbol search payload format")

                note = payload.get("Note")
                if note:
                    self._handle_rate_limit(query, attempt, None, detail=note)
                    last_exc = AlphaVantageError(note)
                    continue

                matches = payload.get("bestMatches") or []
                normalised: list[dict[str, Any]] = []
                for match in matches:
                    symbol = (match.get("1. symbol") or "").strip()
                    if not symbol:
                        continue
                    try:
                        score = float(match.get("9. matchScore", 0) or 0)
                    except (TypeError, ValueError):  # pragma: no cover - bad score
                        score = 0.0
                    normalised.append(
                        {
                            "symbol": symbol,
                            "name": (match.get("2. name") or "").strip(),
                            "type": (match.get("3. type") or "").strip(),
                            "region": (match.get("4. region") or "").strip(),
                            "market_open": (match.get("5. marketOpen") or "").strip(),
                            "market_close": (match.get("6. marketClose") or "").strip(),
                            "timezone": (match.get("7. timezone") or "").strip(),
                            "currency": (match.get("8. currency") or "").strip(),
                            "match_score": score,
                        }
                    )

                if max_results > 0:
                    normalised = normalised[:max_results]
                return normalised

            if attempt < self.max_retries and self.backoff_seconds:
                self._sleep(self.backoff_seconds)

        if last_exc:
            raise AlphaVantageError(f"Failed to search symbols for '{query}'") from last_exc
        raise AlphaVantageError(f"Failed to search symbols for '{query}'")


    def _handle_rate_limit(
        self,
        symbol: str,
        attempt: int,
        wait_seconds: Optional[float],
        *,
        detail: str | None = None,
    ) -> None:
        wait = self.rate_limit_sleep
        if wait_seconds is not None:
            wait = max(wait, wait_seconds)

        message = detail or "Alpha Vantage rate limit reached"
        LOGGER.warning(
            "Alpha Vantage rate limit for %s (attempt %s/%s): %s; sleeping %.1f seconds",
            symbol,
            attempt,
            self.max_retries,
            message,
            wait,
        )
        self._sleep(wait)

    @staticmethod
    def _retry_after_seconds(headers: Mapping[str, str] | None) -> Optional[float]:
        if not headers:
            return None
        value = headers.get("Retry-After")
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:  # pragma: no cover - malformed header
            return None

    @staticmethod
    def _sleep(seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


__all__ = ["AlphaVantageClient", "AlphaVantageError"]



