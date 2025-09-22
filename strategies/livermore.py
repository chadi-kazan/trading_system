"""Livermore breakout strategy implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from strategies.base import SignalType, Strategy, StrategySignal


@dataclass(frozen=True)
class LivermoreParams:
    consolidation_window: int = 20
    max_range_percentage: float = 0.15
    breakout_threshold: float = 0.02
    volume_multiplier: float = 1.3
    min_bars: int = 40


class LivermoreBreakoutStrategy(Strategy):
    """Detects Livermore-style consolidation breakouts with volume confirmation."""

    name = "livermore_breakout"

    def __init__(self, params: LivermoreParams | None = None) -> None:
        self.params = params or LivermoreParams()

    def required_columns(self) -> List[str]:
        return ["close", "high", "low", "volume"]

    def generate_signals(self, symbol: str, prices: pd.DataFrame) -> List[StrategySignal]:
        if prices.empty:
            return []

        df = prices.sort_index().copy()
        missing = [col for col in self.required_columns() if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns for Livermore strategy: {missing}")

        if len(df) < max(self.params.min_bars, self.params.consolidation_window + 5):
            return []

        rolling_high = df["high"].rolling(self.params.consolidation_window)
        rolling_low = df["low"].rolling(self.params.consolidation_window)
        avg_volume = df["volume"].rolling(self.params.consolidation_window, min_periods=5).mean()

        signals: List[StrategySignal] = []
        prev_high = rolling_high.max().shift(1)
        prev_low = rolling_low.min().shift(1)

        for idx in range(self.params.consolidation_window, len(df)):
            current = df.iloc[idx]
            window_high = prev_high.iloc[idx]
            window_low = prev_low.iloc[idx]
            if np.isnan(window_high) or np.isnan(window_low) or window_high <= window_low:
                continue

            price_range = window_high - window_low
            if price_range <= 0:
                continue

            range_pct = price_range / window_low
            if range_pct > self.params.max_range_percentage:
                continue

            breakout_price = current["close"]
            if breakout_price < window_high * (1 + self.params.breakout_threshold):
                continue

            volume_avg = avg_volume.iloc[idx - 1] if idx > 0 else None
            if volume_avg is None or volume_avg <= 0:
                continue

            if current["volume"] < volume_avg * self.params.volume_multiplier:
                continue

            metadata = {
                "consolidation_high": float(window_high),
                "consolidation_low": float(window_low),
                "range_pct": float(range_pct),
                "breakout_price": float(breakout_price),
                "breakout_volume": float(current["volume"]),
                "avg_volume": float(volume_avg),
            }
            signals.append(
                StrategySignal(
                    symbol=symbol,
                    date=df.index[idx],
                    strategy=self.name,
                    signal_type=SignalType.BUY,
                    confidence=float(1 - min(1.0, range_pct / self.params.max_range_percentage)),
                    metadata=metadata,
                )
            )

        return signals


__all__ = ["LivermoreBreakoutStrategy", "LivermoreParams"]
