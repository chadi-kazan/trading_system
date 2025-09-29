from __future__ import annotations

import numpy as np
import pandas as pd

from data_pipeline.enrichment import enrich_price_frame


def test_enrich_price_frame_adds_expected_columns():
    dates = pd.date_range("2023-01-01", periods=300)
    close = pd.Series(np.linspace(50, 150, 300), index=dates)
    volume = pd.Series(np.linspace(1_000, 5_000, 300), index=dates)
    frame = pd.DataFrame({"close": close, "volume": volume})

    enriched = enrich_price_frame("TEST", frame)

    expected_columns = {
        "average_volume",
        "volume_change",
        "fifty_two_week_high",
        "relative_strength",
        "earnings_growth",
    }
    assert expected_columns.issubset(enriched.columns)
    assert enriched.attrs["symbol"] == "TEST"
    assert enriched.attrs["enriched"] is True

    assert np.isclose(enriched.loc[dates[0], "average_volume"], volume.iloc[0])
    assert 0 <= enriched.loc[dates[-1], "relative_strength"] <= 1

    lookback = 252
    expected_growth = close.pct_change(lookback).iloc[-1]
    assert np.isclose(enriched.loc[dates[-1], "earnings_growth"], expected_growth, atol=1e-6)



def test_enrich_price_frame_applies_fundamentals():
    dates = pd.date_range("2024-01-01", periods=5)
    frame = pd.DataFrame({"close": [10, 11, 12, 13, 14], "volume": [1000, 1010, 1020, 1030, 1040]}, index=dates)
    fundamentals = {"earnings_growth": 0.42, "relative_strength": 0.9}
    enriched = enrich_price_frame("TEST", frame, fundamentals=fundamentals)
    assert enriched["earnings_growth"].iloc[-1] == 0.42
    assert enriched["relative_strength"].iloc[-1] == 0.9
    assert enriched.attrs.get("fundamentals") is True
def test_enrich_price_frame_handles_empty_frames():
    frame = pd.DataFrame(columns=["close", "volume"])
    enriched = enrich_price_frame("EMPTY", frame)
    assert enriched.empty
    assert enriched.attrs["symbol"] == "EMPTY"
    assert enriched.attrs["enriched"] is True
