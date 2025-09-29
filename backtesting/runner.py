"""Strategy backtest orchestration utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd

from backtesting.engine import BacktestResult, BacktestingEngine
from strategies.base import Strategy


@dataclass
class StrategyBacktestReport:
    strategy_name: str
    result: BacktestResult


class StrategyBacktestRunner:
    """Runs individual backtests for multiple strategies."""

    def __init__(self, engine: BacktestingEngine | None = None) -> None:
        self.engine = engine or BacktestingEngine()

    def run_strategies(
        self,
        price_data: pd.DataFrame,
        strategies: Iterable[Strategy],
        position_sizer,
        initial_capital: float = 100_000,
        symbol: str = "ASSET",
    ) -> List[StrategyBacktestReport]:
        reports: List[StrategyBacktestReport] = []
        for strategy in strategies:
            result = self.engine.run(
                price_data=price_data,
                strategy=strategy,
                position_sizer=position_sizer,
                initial_capital=initial_capital,
                symbol=symbol,
            )
            reports.append(StrategyBacktestReport(strategy.name, result))
        return reports

    @staticmethod
    def summarize_reports(reports: Iterable[StrategyBacktestReport]) -> Dict[str, float]:
        summary: Dict[str, float] = {}
        for report in reports:
            summary[report.strategy_name] = float(report.result.metrics.get("final", 0.0))
        return summary


__all__ = ["StrategyBacktestRunner", "StrategyBacktestReport"]
