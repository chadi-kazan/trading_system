"""Abstract interfaces and helper utilities for market data providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class PriceRequest:
    """Parameters for fetching price history for a single ticker."""

    symbol: str
    start: date
    end: date
    interval: str = "1d"


@dataclass(frozen=True)
class PriceResult:
    """Returned data frame and metadata from a provider."""

    data: pd.DataFrame
    from_cache: bool
    cache_path: Path | None


class PriceProvider(Protocol):
    """Protocol describing required price data interface."""

    cache_dir: Path

    def get_price_history(self, request: PriceRequest) -> PriceResult:
        """Retrieve historical prices for the given request."""

