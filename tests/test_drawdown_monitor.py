from __future__ import annotations

import pandas as pd

from portfolio.drawdown_monitor import calculate_drawdowns, detect_drawdown_events


def _equity_curve() -> pd.Series:
    data = [100, 105, 110, 90, 92, 130, 120, 140]
    dates = pd.date_range("2024-01-01", periods=len(data), freq="D")
    return pd.Series(data, index=dates)


def test_calculate_drawdowns_and_max():
    curve = _equity_curve()
    drawdowns, max_dd = calculate_drawdowns(curve)

    assert len(drawdowns) == len(curve)
    assert abs(max_dd - 0.181818) < 1e-5  # (90/110)
    assert drawdowns.iloc[3] < 0  # drawdown at the trough


def test_detect_drawdown_events():
    curve = _equity_curve()
    events = list(detect_drawdown_events(curve, threshold=0.15))

    assert events, "Expected drawdown event"
    event = events[0]
    assert event.peak_value == 110
    assert event.trough_value == 90
    assert abs(event.drawdown_pct - 0.181818) < 1e-5


def test_empty_series_returns_no_events():
    curve = pd.Series(dtype=float)
    drawdowns, max_dd = calculate_drawdowns(curve)
    assert drawdowns.empty and max_dd == 0
    events = list(detect_drawdown_events(curve, threshold=0.1))
    assert events == []
