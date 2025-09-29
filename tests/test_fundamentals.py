from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_pipeline import fundamentals
from data_pipeline.fundamentals import load_fundamental_metrics


def test_load_fundamental_metrics_from_json(tmp_path: Path):
    fundamentals_dir = tmp_path / "fundamentals"
    fundamentals_dir.mkdir(parents=True, exist_ok=True)
    (fundamentals_dir / "TEST.json").write_text('{"data": {"earnings_growth": "0.25", "relative_strength": 0.9}}')

    metrics = load_fundamental_metrics("test", tmp_path)
    assert metrics == {"earnings_growth": 0.25, "relative_strength": 0.9}


def test_load_fundamental_metrics_from_csv(tmp_path: Path):
    df = pd.DataFrame(
        {
            "symbol": ["ABC", "XYZ"],
            "earnings_growth": [0.1, 0.2],
            "relative_strength": [0.3, 0.4],
        }
    )
    df.to_csv(tmp_path / "fundamentals.csv", index=False)

    metrics = load_fundamental_metrics("xyz", tmp_path)
    assert metrics == {"earnings_growth": 0.2, "relative_strength": 0.4}


def test_load_fundamental_metrics_alpha_vantage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class DummyClient:
        def __init__(self, api_key: str) -> None:  # pragma: no cover - simple init
            self.api_key = api_key

        def fetch_company_overview(self, symbol: str):
            return {
                "QuarterlyEarningsGrowthYOY": "0.35",
                "52WeekHigh": "120",
                "52WeekLow": "80",
                "50DayMovingAverage": "100",
                "MarketCapitalization": "123456789",
            }

    monkeypatch.setattr(fundamentals, "AlphaVantageClient", DummyClient)

    metrics = load_fundamental_metrics("abc", tmp_path, api_key="demo")

    assert metrics["earnings_growth"] == 0.35
    assert metrics["relative_strength"] == pytest.approx(0.5)
    assert metrics["market_cap"] == 123456789.0
