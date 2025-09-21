"""Yahoo Finance market data provider implementation."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from .base import PriceRequest, PriceResult

LOGGER = logging.getLogger(__name__)


class YahooPriceProvider:
    """Retrieve historical price data from Yahoo Finance with on-disk caching."""

    def __init__(
        self,
        cache_dir: Path,
        cache_ttl_days: int = 7,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_days = cache_ttl_days
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_price_history(self, request: PriceRequest) -> PriceResult:
        """Return OHLCV data for the requested symbol and period."""
        self._validate_request(request)

        cache_path = self._cache_path(request.symbol, request.interval)
        if self._cache_satisfies(request, cache_path):
            data = self._load_cache(cache_path)
            filtered = self._filter_frame(data, request.start, request.end)
            return PriceResult(data=filtered, from_cache=True, cache_path=cache_path)

        data = self._download_with_retry(request)
        if data.empty:
            raise RuntimeError(f"No price data returned for {request.symbol}")

        standardised = self._prepare_frame(data, request.symbol)
        standardised.to_csv(cache_path, index=True, index_label="date")

        filtered = self._filter_frame(standardised, request.start, request.end)
        return PriceResult(data=filtered, from_cache=False, cache_path=cache_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_request(request: PriceRequest) -> None:
        if request.start > request.end:
            raise ValueError("Request start date must be before end date")

    def _cache_path(self, symbol: str, interval: str) -> Path:
        safe_symbol = symbol.upper().replace("/", "-")
        interval_dir = self.cache_dir / interval
        interval_dir.mkdir(parents=True, exist_ok=True)
        return interval_dir / f"{safe_symbol}.csv"

    def _cache_satisfies(self, request: PriceRequest, cache_path: Path) -> bool:
        if not cache_path.exists():
            return False

        if self.cache_ttl_days > 0:
            last_modified = datetime.fromtimestamp(cache_path.stat().st_mtime)
            if datetime.now() - last_modified > timedelta(days=self.cache_ttl_days):
                return False

        data = self._load_cache(cache_path)
        if data.empty:
            return False

        min_date = data.index.min().date()
        max_date = data.index.max().date()

        tolerance = timedelta(days=3 if request.interval.endswith("d") else 1)
        if min_date > request.start + tolerance:
            return False
        if max_date < request.end - tolerance:
            return False
        return True
    @staticmethod
    def _load_cache(cache_path: Path) -> pd.DataFrame:
        return pd.read_csv(cache_path, parse_dates=["date"], index_col="date")

    @staticmethod
    def _filter_frame(frame: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
        if frame.empty:
            return frame
        mask = (frame.index.date >= start) & (frame.index.date <= end)
        return frame.loc[mask]

    def _download_with_retry(self, request: PriceRequest) -> pd.DataFrame:
        delay = 1.0
        last_exception: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                end_inclusive = request.end + timedelta(days=1)
                data = yf.download(
                    request.symbol,
                    start=request.start.isoformat(),
                    end=end_inclusive.isoformat(),
                    interval=request.interval,
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
                if not isinstance(data, pd.DataFrame):
                    raise RuntimeError("Unexpected response type from yfinance")
                if data.empty:
                    LOGGER.warning("Attempt %s: empty data for %s", attempt, request.symbol)
                else:
                    return data
            except Exception as exc:  # yfinance raises broad exceptions
                last_exception = exc
                LOGGER.warning(
                    "Attempt %s failed for %s: %s", attempt, request.symbol, exc
                )
            time.sleep(delay)
            delay *= self.backoff_factor

        if last_exception:
            raise RuntimeError(f"Failed to download data for {request.symbol}") from last_exception
        raise RuntimeError(f"Failed to download data for {request.symbol}")

    @staticmethod
    def _prepare_frame(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        frame = raw.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            # Prefer selecting the requested symbol if multi-index contains tickers.
            try:
                frame = frame.xs(symbol, axis=1, level=-1)
            except (KeyError, TypeError):
                frame.columns = ["_".join(str(part) for part in col if part) for col in frame.columns.to_flat_index()]

        # Normalise column names to lowercase snake_case without ticker suffixes.
        normalised_columns = []
        suffix = f"_{symbol.lower()}"
        for col in frame.columns:
            col_str = str(col).lower().replace(" ", "_")
            if col_str.endswith(suffix):
                col_str = col_str[: -len(suffix)]
            normalised_columns.append(col_str)
        frame.columns = normalised_columns

        if "adj_close" not in frame.columns and "adjclose" in frame.columns:
            frame = frame.rename(columns={"adjclose": "adj_close"})

        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(frame.columns):
            raise RuntimeError("Downloaded data missing required OHLCV columns")

        if "adj_close" not in frame.columns:
            frame["adj_close"] = frame["close"]

        ordered = frame[["open", "high", "low", "close", "adj_close", "volume"]].copy()
        ordered.index.name = "date"
        return ordered.sort_index()


__all__ = ["YahooPriceProvider"]
