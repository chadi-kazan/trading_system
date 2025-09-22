"""EMA crossover trend-following strategy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from indicators.moving_average import ema
from indicators.volatility import average_true_range
from strategies.base import SignalType, Strategy, StrategySignal


@dataclass(frozen=True)
class TrendFollowingParams:
    fast_span: int = 10
    slow_span: int = 30
    atr_period: int = 14
    atr_multiplier: float = 2.0
    min_bars: int = 60


class TrendFollowingStrategy(Strategy):
    """Generates signals from EMA crossovers with ATR-based stops."""

    name = "trend_following"

    def __init__(self, params: TrendFollowingParams | None = None) -> None:
        self.params = params or TrendFollowingParams()

    def required_columns(self) -> List[str]:
        return ["close", "high", "low"]

    def generate_signals(self, symbol: str, prices: pd.DataFrame) -> List[StrategySignal]:
        if prices.empty:
            return []

        df = prices.sort_index().copy()
        missing = [col for col in self.required_columns() if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns for trend following strategy: {missing}")

        if len(df) < max(self.params.min_bars, self.params.slow_span + self.params.atr_period):
            return []

        df["fast_ema"] = ema(df["close"], span=self.params.fast_span)
        df["slow_ema"] = ema(df["close"], span=self.params.slow_span)
        df["atr"] = average_true_range(df["high"], df["low"], df["close"], period=self.params.atr_period)

        signals: List[StrategySignal] = []
        prev_fast = df["fast_ema"].shift(1)
        prev_slow = df["slow_ema"].shift(1)

        crossover_up = (df["fast_ema"] > df["slow_ema"]) & (prev_fast <= prev_slow)
        crossover_down = (df["fast_ema"] < df["slow_ema"]) & (prev_fast >= prev_slow)

        for idx, row in df.iterrows():
            atr_value = row["atr"]
            if np.isnan(row["fast_ema"]) or np.isnan(row["slow_ema"]) or np.isnan(atr_value):
                continue

            if crossover_up.loc[idx] and row["close"] > row["fast_ema"]:
                stop_price = row["close"] - self.params.atr_multiplier * atr_value
                confidence = min(1.0, max(0.0, (row["fast_ema"] - row["slow_ema"]) / row["slow_ema"] * 5))
                metadata = {
                    "fast_ema": float(row["fast_ema"]),
                    "slow_ema": float(row["slow_ema"]),
                    "atr": float(atr_value),
                    "stop_price": float(stop_price),
                }
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        date=idx,
                        strategy=self.name,
                        signal_type=SignalType.BUY,
                        confidence=float(confidence),
                        metadata=metadata,
                    )
                )
            elif crossover_down.loc[idx]:
                confidence = min(1.0, max(0.0, (row["slow_ema"] - row["fast_ema"]) / row["slow_ema"] * 5))
                metadata = {
                    "fast_ema": float(row["fast_ema"]),
                    "slow_ema": float(row["slow_ema"]),
                }
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        date=idx,
                        strategy=self.name,
                        signal_type=SignalType.SELL,
                        confidence=float(confidence),
                        metadata=metadata,
                    )
                )

        return signals


__all__ = ["TrendFollowingStrategy", "TrendFollowingParams"]
