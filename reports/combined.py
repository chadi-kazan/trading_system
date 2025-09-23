"""Combined backtest reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from backtesting.runner import StrategyBacktestReport
from reports.performance import build_performance_report


def generate_combined_report(
    reports: Iterable[StrategyBacktestReport],
    output_path: Path | None = None,
) -> pd.DataFrame:
    df = build_performance_report(reports)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path)
    return df


__all__ = ["generate_combined_report"]
