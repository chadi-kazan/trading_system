"""Drawdown monitoring utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import pandas as pd


@dataclass
class DrawdownEvent:
    peak_date: pd.Timestamp
    trough_date: pd.Timestamp
    peak_value: float
    trough_value: float
    drawdown_pct: float


def calculate_drawdowns(equity_curve: pd.Series) -> Tuple[pd.Series, float]:
    """Return drawdown series and maximum drawdown percentage."""

    if equity_curve.empty:
        return pd.Series(dtype=float), 0.0

    running_max = equity_curve.cummax()
    drawdowns = (equity_curve - running_max) / running_max
    max_drawdown = drawdowns.min() if not drawdowns.empty else 0.0
    return drawdowns, float(abs(max_drawdown))


def detect_drawdown_events(equity_curve: pd.Series, threshold: float) -> Iterable[DrawdownEvent]:
    drawdowns, _ = calculate_drawdowns(equity_curve)
    if drawdowns.empty:
        return []

    events: list[DrawdownEvent] = []
    in_drawdown = False
    peak_date = trough_date = None
    peak_value = trough_value = None

    for date, value in equity_curve.items():
        if not in_drawdown:
            peak_value = value
            peak_date = date
            trough_value = value
            trough_date = date
            in_drawdown = True
            continue

        if value >= peak_value:
            peak_value = value
            peak_date = date
            trough_value = value
            trough_date = date
            continue

        if value < trough_value:
            trough_value = value
            trough_date = date

        current_drawdown = 1 - (trough_value / peak_value)
        if current_drawdown >= threshold:
            events.append(
                DrawdownEvent(
                    peak_date=peak_date,
                    trough_date=trough_date,
                    peak_value=float(peak_value),
                    trough_value=float(trough_value),
                    drawdown_pct=float(current_drawdown),
                )
            )
            in_drawdown = False

    return events
