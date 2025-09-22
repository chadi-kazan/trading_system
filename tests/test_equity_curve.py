from __future__ import annotations

from pathlib import Path

import pandas as pd

from portfolio.equity_curve import equity_curve_from_positions, load_equity_curve


def test_load_equity_curve(tmp_path: Path):
    data = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "equity": [100000, 101000, 99000]})
    path = tmp_path / "equity.csv"
    data.to_csv(path, index=False)

    series = load_equity_curve(path)
    assert list(series.values) == [100000, 101000, 99000]


def test_equity_curve_from_positions():
    positions = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=3),
        "value": [10000, 12000, 15000],
    })
    curve = equity_curve_from_positions(positions, cash=5000)

    assert list(curve.values) == [15000, 27000, 42000]


def test_equity_curve_from_empty_positions():
    curve = equity_curve_from_positions(pd.DataFrame(columns=["date", "value"]), cash=1000)
    assert curve.iloc[0] == 1000
