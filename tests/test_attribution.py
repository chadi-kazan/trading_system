from __future__ import annotations

import pandas as pd

from backtesting.engine import BacktestResult
from backtesting.runner import StrategyBacktestReport
from reports.attribution import compute_attribution


def _report(name: str, values: list[float]) -> StrategyBacktestReport:
    curve = pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values)))
    result = BacktestResult(curve, [], {"final": values[-1]})
    return StrategyBacktestReport(name, result)


def test_compute_attribution_with_weights():
    reports = [
        _report("A", [100, 120]),
        _report("B", [100, 80])
    ]
    df = compute_attribution(reports, weights={"A": 2.0, "B": 1.0})

    assert "contribution" in df.columns
    assert df.loc["A", "weight"] > df.loc["B", "weight"]
    assert df.loc["A", "contribution"] > df.loc["B", "contribution"]


def test_compute_attribution_handles_empty_reports():
    df = compute_attribution([])
    assert df.empty
