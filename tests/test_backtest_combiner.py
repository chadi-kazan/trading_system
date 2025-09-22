from __future__ import annotations

import pandas as pd

from backtesting.combiner import combine_equity_curves, summarize_combined_metrics
from backtesting.engine import BacktestResult
from backtesting.runner import StrategyBacktestReport


def _report(name: str, values: list[float]) -> StrategyBacktestReport:
    curve = pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values)))
    metrics = {"final": values[-1]}
    result = BacktestResult(equity_curve=curve, trades=[], metrics=metrics)
    return StrategyBacktestReport(strategy_name=name, result=result)


def test_combine_equity_curves_with_weights():
    reports = [
        _report("A", [100, 105, 110]),
        _report("B", [100, 102, 103]),
    ]
    combined = combine_equity_curves(reports, weights={"A": 2.0, "B": 1.0})

    assert len(combined) == 3
    assert combined.iloc[-1] > combined.iloc[0]


def test_summarize_combined_metrics():
    reports = [
        _report("A", [100, 110]),
        _report("B", [100, 90]),
    ]
    summary = summarize_combined_metrics(reports)

    assert summary["final"] == 200
