from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.trend_following import TrendFollowingParams, TrendFollowingStrategy


def _make_trend_data() -> pd.DataFrame:
    down_trend = np.linspace(110, 90, 80, endpoint=False)
    up_trend = np.linspace(90, 130, 120, endpoint=False)
    reversal = np.linspace(130, 95, 60)
    closes = np.concatenate([down_trend, up_trend, reversal])
    dates = pd.date_range("2024-01-01", periods=len(closes), freq="D")
    highs = closes + 1.5
    lows = closes - 1.5
    return pd.DataFrame({
        "close": closes,
        "high": highs,
        "low": lows,
    }, index=dates)


def test_generates_buy_and_sell_signals():
    data = _make_trend_data()
    params = TrendFollowingParams(fast_span=5, slow_span=20, atr_period=10, min_bars=40)
    strategy = TrendFollowingStrategy(params=params)

    signals = strategy.generate_signals("TST", data)

    assert signals, "Expected crossover signals"
    buy_signals = [s for s in signals if s.signal_type.name == "BUY"]
    sell_signals = [s for s in signals if s.signal_type.name == "SELL"]
    assert buy_signals, "Expected at least one buy signal"
    assert sell_signals, "Expected at least one sell signal"
    assert buy_signals[0].date < sell_signals[-1].date


def test_missing_columns_raise():
    strategy = TrendFollowingStrategy()
    df = pd.DataFrame({"close": [1, 2, 3]})
    try:
        strategy.generate_signals("TST", df)
    except ValueError as exc:
        assert "Missing required columns" in str(exc)
    else:
        assert False, "Expected ValueError for missing columns"
