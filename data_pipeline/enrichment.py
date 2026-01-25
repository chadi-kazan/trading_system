"""Utilities for enriching raw price data with derived features."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


DEFAULT_VOLUME_WINDOW = 20
DEFAULT_STRENGTH_WINDOW = 252


def enrich_price_frame(
    symbol: str,
    frame: pd.DataFrame,
    volume_window: int = DEFAULT_VOLUME_WINDOW,
    strength_window: int = DEFAULT_STRENGTH_WINDOW,
    fundamentals: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """Return a copy of *frame* with additional columns required by strategies."""

    if frame.empty:
        enriched = frame.copy()
        enriched.attrs.update(frame.attrs)
        enriched.attrs["symbol"] = symbol
        enriched.attrs["enriched"] = True
        if fundamentals:
            enriched.attrs["fundamentals"] = True
        return enriched

    data = frame.copy().sort_index()

    if "volume" in data.columns:
        avg_volume = data["volume"].rolling(volume_window, min_periods=1).mean()
        data["average_volume"] = avg_volume
        ratio = data["volume"] / avg_volume.replace(0, pd.NA) - 1
        ratio = ratio.replace([np.inf, -np.inf], np.nan)
        data["volume_change"] = ratio.fillna(0)

    if "close" in data.columns:
        rolling_high = data["close"].rolling(strength_window, min_periods=1).max()
        rolling_low = data["close"].rolling(strength_window, min_periods=1).min()
        data["fifty_two_week_high"] = rolling_high
        price_range = (rolling_high - rolling_low).replace(0, pd.NA)
        relative_strength = (data["close"] - rolling_low) / price_range
        data["relative_strength"] = relative_strength.clip(lower=0, upper=1).fillna(0)
        earnings_proxy = data["close"].pct_change(strength_window)
        data["earnings_growth"] = earnings_proxy.fillna(0)

    if fundamentals:
        overrides_applied = False
        for raw_key, raw_value in fundamentals.items():
            key = str(raw_key).lower()
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            data[key] = value
            overrides_applied = True
        if overrides_applied:
            data.attrs["fundamentals"] = True

    data.attrs.update(frame.attrs)
    data.attrs["symbol"] = symbol
    data.attrs["enriched"] = True
    return data


__all__ = ["enrich_price_frame"]
