from __future__ import annotations

import pandas as pd

from backtesting.engine import BacktestingEngine
from strategies.base import SignalType, Strategy, StrategySignal


class BuySellStrategy(Strategy):
    name = "dummy"

    def required_columns(self):
        return ["close", "volume"]

    def generate_signals(self, symbol: str, prices: pd.DataFrame):
        if len(prices.index) < 3:
            return []
        buy_date = prices.index[1]
        sell_date = prices.index[-1]
        return [
            StrategySignal(
                symbol=symbol,
                date=buy_date,
                strategy=self.name,
                signal_type=SignalType.BUY,
                confidence=0.5,
                metadata={"price": float(prices.loc[buy_date, "close"])}
            ),
            StrategySignal(
                symbol=symbol,
                date=sell_date,
                strategy=self.name,
                signal_type=SignalType.SELL,
                confidence=0.5,
                metadata={"price": float(prices.loc[sell_date, "close"])}
            ),
        ]


class HoldStrategy(Strategy):
    name = "hold"

    def required_columns(self):
        return ["close"]

    def generate_signals(self, symbol: str, prices: pd.DataFrame):
        return []


def test_backtesting_engine_simulates_trades():
    engine = BacktestingEngine(transaction_cost=0.0)
    data = pd.DataFrame(
        {
            "close": [100, 102, 105, 108, 110],
            "volume": [1000, 1100, 1200, 1300, 1400],
        },
        index=pd.date_range("2024-01-01", periods=5),
    )

    def half_sizer(signals, equity):
        buys = [s for s in signals if s.signal_type is SignalType.BUY]
        if not buys:
            return []
        price = buys[0].metadata.get("price", data.iloc[0]["close"])
        shares = int((equity / 2) // price)
        return [
            {
                "symbol": buys[0].symbol,
                "shares": shares,
                "entry_price": price,
                "allocation": shares * price,
            }
        ]

    result = engine.run(
        data,
        BuySellStrategy(),
        position_sizer=half_sizer,
        symbol="TEST",
    )

    assert result.equity_curve.index.equals(data.index)
    assert len(result.trades) == 2
    assert result.trades[0]["action"] == "BUY"
    assert result.trades[1]["action"] == "SELL"
    assert result.metrics["final"] > 100_000
    assert result.metrics["total_return"] > 0
    assert result.metrics["num_trades"] == 2


def test_backtesting_engine_handles_no_positions():
    engine = BacktestingEngine()
    data = pd.DataFrame(
        {
            "close": [100, 101, 102],
        },
        index=pd.date_range("2024-02-01", periods=3),
    )

    result = engine.run(
        data,
        HoldStrategy(),
        position_sizer=lambda signals, equity: [],
        symbol="TEST",
    )

    assert (result.equity_curve == 100_000).all()
    assert result.metrics["final"] == 100_000
    assert result.metrics["total_return"] == 0
    assert result.metrics["num_trades"] == 0
