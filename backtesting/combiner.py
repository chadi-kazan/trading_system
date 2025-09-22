"""Combined strategy backtesting aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd

from backtesting.runner import StrategyBacktestReport


def combine_equity_curves(reports: Iterable[StrategyBacktestReport], weights: Dict[str, float] | None = None) -> pd.Series:
    curves = []
    wts = []
    for report in reports:
        equity = report.result.equity_curve
        if equity.empty:
            continue
        weight = weights.get(report.strategy_name, 1.0) if weights else 1.0
        curves.append(equity)
        wts.append(weight)

    if not curves:
        return pd.Series(dtype=float)

    aligned = pd.concat(curves, axis=1).fillna(method="ffill").fillna(method="bfill")
    weight_series = pd.Series(wts, index=aligned.columns)
    combined = aligned.mul(weight_series, axis=1).sum(axis=1) / weight_series.sum()
    return combined


def summarize_combined_metrics(reports: Iterable[StrategyBacktestReport]) -> Dict[str, float]:
    metrics: Dict[str, float] = {}
    for report in reports:
        for key, value in report.result.metrics.items():
            metrics.setdefault(key, 0.0)
            metrics[key] += value
    return metrics


__all__ = ["combine_equity_curves", "summarize_combined_metrics"]
