from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.livermore import LivermoreBreakoutStrategy, LivermoreParams


def _make_data() -> pd.DataFrame:
    base = np.linspace(50, 54, 60, endpoint=False)
    consolidation = 55 + np.sin(np.linspace(0, 2 * np.pi, 25)) * 0.2
    breakout = np.linspace(56.8, 62, 30)
    closes = np.concatenate([base, consolidation, breakout])
    highs = closes + 0.4
    lows = closes - 0.4
    volumes = np.concatenate([
        np.full(60, 100_000),
        np.full(25, 110_000),
        np.full(30, 190_000)
    ])
    dates = pd.date_range("2024-01-01", periods=len(closes), freq="D")
    return pd.DataFrame({
        "close": closes,
        "high": highs,
        "low": lows,
        "volume": volumes,
    }, index=dates)


def test_generates_breakout_signal():
    data = _make_data()
    params = LivermoreParams(consolidation_window=20, max_range_percentage=0.05, breakout_threshold=0.02, volume_multiplier=1.3, min_bars=40)
    strategy = LivermoreBreakoutStrategy(params=params)

    signals = strategy.generate_signals("TST", data)

    assert signals, "Expected breakout signal"
    signal = signals[-1]
    assert signal.signal_type.name == "BUY"
    assert signal.metadata["range_pct"] <= params.max_range_percentage
    assert signal.metadata["breakout_volume"] >= signal.metadata["avg_volume"] * params.volume_multiplier


def test_missing_columns_raise():
    strategy = LivermoreBreakoutStrategy()
    df = pd.DataFrame({"close": [1, 2, 3]})
    try:
        strategy.generate_signals("TST", df)
    except ValueError as exc:
        assert "Missing required columns" in str(exc)
    else:
        assert False, "Expected ValueError for missing columns"
