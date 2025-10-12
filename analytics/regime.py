"""Market regime detection utilities."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Optional

import pandas as pd

from data_providers.base import PriceRequest
from data_providers.yahoo import YahooPriceProvider


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _safe_pct_change(series: pd.Series, periods: int) -> float:
    if series.empty or len(series) <= periods:
        return 0.0
    recent = float(series.iloc[-1])
    past = float(series.iloc[-periods])
    if past == 0:
        return 0.0
    return (recent - past) / abs(past)


@dataclass(frozen=True)
class MarketRegimeSnapshot:
    """Represents the current macro regime assessment."""

    name: str
    score: float
    multiplier: float
    factors: Dict[str, float]
    updated_at: datetime
    notes: Optional[str] = None


class MarketRegimeAnalyzer:
    """Computes a lightweight macro overlay using liquid risk proxies."""

    def __init__(
        self,
        provider: YahooPriceProvider,
        *,
        cache_seconds: int = 900,
    ) -> None:
        self._provider = provider
        self._cache_seconds = cache_seconds
        self._cache: Optional[tuple[float, MarketRegimeSnapshot]] = None

    # ------------------------------------------------------------------
    def current(self) -> MarketRegimeSnapshot:
        """Return the latest cached regime snapshot (re-computing if stale)."""

        now = time.time()
        if self._cache is not None:
            timestamp, snapshot = self._cache
            if now - timestamp < self._cache_seconds:
                return snapshot

        snapshot = self._compute_snapshot()
        self._cache = (now, snapshot)
        return snapshot

    # ------------------------------------------------------------------
    def _compute_snapshot(self) -> MarketRegimeSnapshot:
        end_date = date.today()
        start_date = end_date - timedelta(days=120)

        try:
            vix_series = self._fetch_close("^VIX", start_date, end_date)
            hyg_series = self._fetch_close("HYG", start_date, end_date)
            lqd_series = self._fetch_close("LQD", start_date, end_date)
            spy_series = self._fetch_close("SPY", start_date, end_date)
        except Exception:
            return self._neutral_snapshot("Unable to retrieve macro series")

        if vix_series.empty or hyg_series.empty or lqd_series.empty or spy_series.empty:
            return self._neutral_snapshot("Macro series returned empty data")

        vix_value = float(vix_series.iloc[-1])
        hyg_last = float(hyg_series.iloc[-1])
        lqd_last = float(lqd_series.iloc[-1])
        spy_trend = _safe_pct_change(spy_series, 20)

        credit_ratio = hyg_last / lqd_last if lqd_last else 1.0

        vix_score = _clamp((35.0 - vix_value) / 35.0)
        credit_score = _clamp((credit_ratio - 0.94) / 0.06)
        trend_score = _clamp((spy_trend + 0.04) / 0.10)

        composite = _clamp(0.35 * trend_score + 0.35 * credit_score + 0.30 * vix_score)
        multiplier = round(0.55 + 0.45 * composite, 3)

        if composite >= 0.65:
            name = "risk_on"
            notes = "Equities trending, credit supportive, volatility subdued."
        elif composite >= 0.45:
            name = "neutral"
            notes = "Mixed macro posture; maintain risk but tighten selections."
        else:
            name = "risk_off"
            notes = "Defensive conditions detected; consider throttling exposure."

        factors = {
            "vix": round(vix_value, 2),
            "vix_score": round(vix_score, 3),
            "credit_ratio": round(credit_ratio, 3),
            "credit_score": round(credit_score, 3),
            "spy_20d_return": round(spy_trend, 3),
            "trend_score": round(trend_score, 3),
        }

        return MarketRegimeSnapshot(
            name=name,
            score=round(composite, 3),
            multiplier=multiplier,
            factors=factors,
            updated_at=datetime.utcnow(),
            notes=notes,
        )

    def _fetch_close(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> pd.Series:
        request = PriceRequest(symbol=symbol, start=start, end=end, interval="1d")
        result = self._provider.get_price_history(request)
        data = result.data
        if data.empty:
            return pd.Series(dtype=float)
        if "close" in data.columns:
            return data["close"]
        return data.squeeze()

    @staticmethod
    def _neutral_snapshot(reason: str) -> MarketRegimeSnapshot:
        return MarketRegimeSnapshot(
            name="neutral",
            score=0.5,
            multiplier=0.8,
            factors={},
            updated_at=datetime.utcnow(),
            notes=reason,
        )


__all__ = ["MarketRegimeAnalyzer", "MarketRegimeSnapshot"]
