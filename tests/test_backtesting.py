from __future__ import annotations

import pandas as pd

from backtesting.engine import BacktestingEngine
from strategies.base import Strategy, StrategySignal, SignalType


class DummyStrategy(Strategy):
    name = "dummy"

    def required_columns(self):
        return ["close", "volume"]

    def generate_signals(self, symbol: str, prices: pd.DataFrame):
        if prices.empty:
            return []
        return [
            StrategySignal(
                symbol=symbol,
                date=prices.index[-1],
                strategy=self.name,
                signal_type=SignalType.BUY,
                confidence=0.5,
                metadata={"price": float(prices.iloc[-1]["close"])}
            )
        ]


def test_backtesting_engine_runs():
    engine = BacktestingEngine()
    data = pd.DataFrame({
        "close": [100, 102, 104],
        "volume": [1000, 1100, 1050]
    }, index=pd.date_range("2024-01-01", periods=3))

    result = engine.run(
        data,
        DummyStrategy(),
        position_sizer=lambda signals, equity: []
    )

    assert not result.equity_curve.empty
    assert result.metrics["final"] == 100_000
