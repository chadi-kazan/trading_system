"""Volatility-related indicator helpers."""

from __future__ import annotations

import pandas as pd


def average_true_range(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Compute the Average True Range (ATR)."""

    if period <= 0:
        raise ValueError("ATR period must be positive")

    previous_close = closes.shift(1)
    true_range = pd.concat(
        [
            highs - lows,
            (highs - previous_close).abs(),
            (lows - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.rolling(window=period, min_periods=period).mean()
