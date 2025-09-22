from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.dan_zanger import DanZangerCupHandleStrategy, DanZangerParams


def _make_price_series() -> pd.DataFrame:
    close_values: list[float] = []

    close_values.extend(np.linspace(90, 100, 20, endpoint=False))
    close_values.extend(np.linspace(100, 74, 20, endpoint=False))
    close_values.extend(np.linspace(74, 98, 25, endpoint=False))
    close_values.extend(np.linspace(98, 96, 10, endpoint=False))
    close_values.extend(np.linspace(96, 90, 5, endpoint=False))
    close_values.extend(np.linspace(90, 100, 5, endpoint=False))
    close_values.extend(np.linspace(100, 103, 4, endpoint=False))
    close_values.extend([105.5, 108.0])

    dates = pd.date_range("2024-01-01", periods=len(close_values), freq="D")
    close = pd.Series(close_values, index=dates)
    volume = pd.Series(150_000, index=dates)
    volume.iloc[-15:] = 200_000
    volume.iloc[-5:] = 420_000

    return pd.DataFrame({"close": close, "volume": volume})


def test_detects_cup_and_handle_breakout():
    data = _make_price_series()
    params = DanZangerParams(cup_lookback=80, handle_min=4, handle_max=10, volume_mean_window=10)
    strategy = DanZangerCupHandleStrategy(params=params)

    signals = strategy.generate_signals("TEST", data)

    assert signals, "Expected at least one breakout signal"
    breakout_signal = signals[-1]
    assert breakout_signal.signal_type.name == "BUY"
    assert breakout_signal.strategy == strategy.name
    assert breakout_signal.confidence > 0.5
    metadata = breakout_signal.metadata
    assert metadata["cup_depth"] >= strategy.params.cup_depth_min
    assert metadata["handle_pullback"] <= strategy.params.handle_pullback_max


def test_rejects_insufficient_depth():
    dates = pd.date_range("2024-01-01", periods=130, freq="D")
    close = pd.Series(np.linspace(100, 110, len(dates)), index=dates)
    volume = pd.Series(120_000, index=dates)
    data = pd.DataFrame({"close": close, "volume": volume})

    params = DanZangerParams(cup_lookback=80, handle_min=4, handle_max=10, volume_mean_window=10)
    strategy = DanZangerCupHandleStrategy(params=params)
    signals = strategy.generate_signals("TEST", data)

    assert not signals
