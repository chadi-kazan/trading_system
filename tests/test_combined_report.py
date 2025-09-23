from __future__ import annotations

from pathlib import Path

import pandas as pd

from backtesting.engine import BacktestResult
from backtesting.runner import StrategyBacktestReport
from reports.combined import generate_combined_report


def _report(name: str, values: list[float]) -> StrategyBacktestReport:
    curve = pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values)))
    metrics = {"final": values[-1]}
    return StrategyBacktestReport(name, BacktestResult(curve, [], metrics))


def test_generate_combined_report(tmp_path: Path):
    reports = [
        _report("A", [100, 110, 120]),
        _report("B", [100, 95, 90]),
    ]
    output = tmp_path / "combined.csv"
    df = generate_combined_report(reports, output)

    assert df.shape[0] == 2
    assert output.exists()
    reloaded = pd.read_csv(output, index_col=0)
    assert reloaded.loc["A", "final_equity"] == 120
