"""Performance reporting utilities for backtest results."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd

from backtesting.runner import StrategyBacktestReport
from portfolio.drawdown_monitor import calculate_drawdowns


def compute_total_return(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    start = equity_curve.iloc[0]
    end = equity_curve.iloc[-1]
    if start == 0:
        return 0.0
    return float(end / start - 1)


def compute_cagr(equity_curve: pd.Series, periods_per_year: int = 252) -> float:
    if equity_curve.empty or len(equity_curve) < 2:
        return 0.0
    total_return = compute_total_return(equity_curve)
    years = len(equity_curve) / periods_per_year
    if years <= 0:
        return 0.0
    return float((1 + total_return) ** (1 / years) - 1)


def compute_sharpe(equity_curve: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    if equity_curve.empty or len(equity_curve) < 2:
        return 0.0
    returns = equity_curve.pct_change().dropna()
    if returns.empty or returns.std() == 0:
        return 0.0
    excess = returns - (risk_free_rate / periods_per_year)
    sharpe = math.sqrt(periods_per_year) * excess.mean() / excess.std()
    return float(sharpe)


def build_performance_report(
    reports: Iterable[StrategyBacktestReport],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> pd.DataFrame:
    rows = []
    index = []
    for report in reports:
        equity = report.result.equity_curve
        drawdowns, max_dd = calculate_drawdowns(equity)
        rows.append(
            {
                "final_equity": equity.iloc[-1] if not equity.empty else 0.0,
                "total_return": compute_total_return(equity),
                "cagr": compute_cagr(equity, periods_per_year),
                "max_drawdown": float(max_dd),
                "sharpe": compute_sharpe(equity, risk_free_rate, periods_per_year),
            }
        )
        index.append(report.strategy_name)

    if not rows:
        return pd.DataFrame(columns=["final_equity", "total_return", "cagr", "max_drawdown", "sharpe"])

    return pd.DataFrame(rows, index=index)


__all__ = [
    "compute_total_return",
    "compute_cagr",
    "compute_sharpe",
    "build_performance_report",
]
