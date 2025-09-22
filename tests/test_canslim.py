from __future__ import annotations

import pandas as pd

from strategies.canslim import CanSlimParams, CanSlimStrategy


def _make_row(**kwargs):
    base = {
        "close": 98.0,
        "volume": 1_200_000,
        "earnings_growth": 0.3,
        "relative_strength": 0.9,
        "fifty_two_week_high": 100.0,
        "average_volume": 900_000,
        "volume_change": 0.25,
    }
    base.update(kwargs)
    return pd.DataFrame([base], index=[pd.Timestamp("2024-05-01")])


def test_generates_signal_when_all_factors_pass():
    strategy = CanSlimStrategy()
    df = _make_row()

    signals = strategy.generate_signals("TST", df)

    assert len(signals) == 1
    signal = signals[0]
    assert signal.confidence >= strategy.params.min_score
    assert signal.metadata["earnings_score"] == strategy.params.weights["earnings"]


def test_filters_when_score_below_threshold():
    strategy = CanSlimStrategy()
    df = _make_row(earnings_growth=0.1, volume_change=0.05)

    signals = strategy.generate_signals("TST", df)

    assert signals == []


def test_raises_error_for_missing_columns():
    strategy = CanSlimStrategy()
    df = pd.DataFrame({"close": [100], "volume": [1_000_000]})

    try:
        strategy.generate_signals("TST", df)
    except ValueError as exc:
        assert "Missing required columns" in str(exc)
    else:
        assert False, "Expected error for missing columns"


def test_respects_custom_weights_and_threshold():
    params = CanSlimParams(min_score=0.6, weights={
        "earnings": 0.4,
        "relative_strength": 0.2,
        "price_near_high": 0.2,
        "volume_increase": 0.2,
    })
    strategy = CanSlimStrategy(params=params)
    df = _make_row(relative_strength=0.5)

    signals = strategy.generate_signals("TST", df)

    assert len(signals) == 1
    signal = signals[0]
    assert signal.confidence >= params.min_score

