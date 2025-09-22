"""Moving average helpers."""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, span: int, adjust: bool = False) -> pd.Series:
    """Return the exponential moving average for the provided series."""

    if span <= 0:
        raise ValueError("EMA span must be positive")
    return series.ewm(span=span, adjust=adjust).mean()
