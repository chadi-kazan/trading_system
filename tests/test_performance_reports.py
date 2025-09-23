from __future__ import annotations

import pandas as pd

from backtesting.engine import BacktestResult
from backtesting.runner import StrategyBacktestReport
from reports.performance import build_performance_report, compute_cagr, compute_sharpe, compute_total_return


def _curve(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values)))


def _report(name: str, values: list[float]) -> StrategyBacktestReport:
    curve = _curve(values)
    result = BacktestResult(equity_curve=curve, trades=[], metrics={"final": values[-1]})
    return StrategyBacktestReport(strategy_name=name, result=result)


def test_performance_metrics():
    curve = _curve([100, 110, 121])
    total_return = compute_total_return(curve)
    assert abs(total_return - 0.21) < 1e-6

    cagr = compute_cagr(curve, periods_per_year=1)
    assert cagr > 0

    sharpe = compute_sharpe(curve, risk_free_rate=0.0, periods_per_year=1)
    assert sharpe >= 0


def test_build_performance_report():
    reports = [
        _report("strategy_a", [100, 110, 120]),
        _report("strategy_b", [100, 90, 80]),
    ]

    df = build_performance_report(reports, periods_per_year=1)
    assert df.shape[0] == 2
    assert "total_return" in df.columns
    assert df.loc["strategy_a", "total_return"] > 0
    assert df.loc["strategy_b", "total_return"] < 0
