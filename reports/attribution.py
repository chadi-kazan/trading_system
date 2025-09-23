"""Performance attribution utilities."""

from __future__ import annotations

from typing import Dict, Iterable

import pandas as pd

from backtesting.runner import StrategyBacktestReport
from reports.performance import compute_total_return


def compute_attribution(
    reports: Iterable[StrategyBacktestReport],
    weights: Dict[str, float] | None = None,
) -> pd.DataFrame:
    rows = []
    total_weight = 0.0
    weighted_return = 0.0

    for report in reports:
        equity = report.result.equity_curve
        if equity.empty:
            continue
        ret = compute_total_return(equity)
        weight = weights.get(report.strategy_name, 1.0) if weights else 1.0
        rows.append({
            "strategy": report.strategy_name,
            "return": ret,
            "weight": weight,
            "weighted_return": ret * weight,
        })
        total_weight += weight
        weighted_return += ret * weight

    if not rows or total_weight == 0:
        return pd.DataFrame(columns=["return", "weight", "contribution"])

    df = pd.DataFrame(rows).set_index("strategy")
    df["contribution"] = df["weighted_return"] / total_weight
    df.drop(columns=["weighted_return"], inplace=True)
    df["weight"] = df["weight"] / total_weight
    df["return"] = df["return"].astype(float)
    df["contribution"] = df["contribution"].astype(float)
    return df


__all__ = ["compute_attribution"]
