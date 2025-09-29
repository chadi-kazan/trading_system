from __future__ import annotations

import pandas as pd

from backtesting.engine import BacktestingEngine
from backtesting.runner import StrategyBacktestRunner
from strategies.base import SignalType, Strategy, StrategySignal


class DummyStrategy(Strategy):
    def __init__(self, name: str, confidence: float) -> None:
        self.name = name
        self.confidence = confidence

    def required_columns(self):
        return ["close", "volume"]

    def generate_signals(self, symbol: str, prices: pd.DataFrame):
        return [
            StrategySignal(
                symbol=symbol,
                date=prices.index[-1],
                strategy=self.name,
                signal_type=SignalType.BUY,
                confidence=self.confidence,
                metadata={"price": float(prices.iloc[-1]["close"])}
            )
        ]


def test_backtest_runner_summarizes_results():
    data = pd.DataFrame({
        "close": [100, 102, 104],
        "volume": [1000, 1100, 1200],
    }, index=pd.date_range("2024-01-01", periods=3))

    def dummy_sizer(signals, equity):
        return []

    engine = BacktestingEngine()
    runner = StrategyBacktestRunner(engine)

    strategies = [
        DummyStrategy("strategy_a", 0.5),
        DummyStrategy("strategy_b", 0.7),
    ]

    reports = runner.run_strategies(data, strategies, position_sizer=dummy_sizer, symbol="TEST")
    summary = runner.summarize_reports(reports)

    assert len(reports) == 2
    assert summary["strategy_a"] == 100_000
    assert summary["strategy_b"] == 100_000

