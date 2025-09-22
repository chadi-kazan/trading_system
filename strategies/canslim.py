"""CAN SLIM scoring strategy implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from strategies.base import SignalType, Strategy, StrategySignal


@dataclass(frozen=True)
class CanSlimParams:
    earnings_growth_threshold: float = 0.25
    relative_strength_threshold: float = 0.8
    near_high_threshold: float = 0.15
    volume_increase_threshold: float = 0.20
    min_score: float = 0.75

    weights: Dict[str, float] = None

    def __post_init__(self) -> None:
        if self.weights is None:
            object.__setattr__(self, "weights", {
                "earnings": 0.25,
                "relative_strength": 0.25,
                "price_near_high": 0.25,
                "volume_increase": 0.25,
            })
        if not np.isclose(sum(self.weights.values()), 1.0, atol=1e-6):
            raise ValueError("CAN SLIM weights must sum to 1.0")


class CanSlimStrategy(Strategy):
    """Scores stocks using CAN SLIM style factors."""

    name = "can_slim"

    def __init__(self, params: CanSlimParams | None = None) -> None:
        self.params = params or CanSlimParams()

    def required_columns(self) -> List[str]:
        return [
            "close",
            "volume",
            "earnings_growth",
            "relative_strength",
            "fifty_two_week_high",
            "average_volume",
            "volume_change",
        ]

    def generate_signals(self, symbol: str, prices: pd.DataFrame) -> List[StrategySignal]:
        if prices.empty:
            return []

        df = prices.sort_index().copy()
        required = self.required_columns()
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns for CAN SLIM strategy: {missing}")

        latest = df.iloc[-1]
        score_components = self._calculate_components(latest)
        total_score = sum(score_components.values())

        if total_score < self.params.min_score:
            return []

        metadata = {**score_components, "total_score": float(total_score)}
        signal = StrategySignal(
            symbol=symbol,
            date=df.index[-1],
            strategy=self.name,
            signal_type=SignalType.BUY,
            confidence=float(total_score),
            metadata=metadata,
        )
        return [signal]

    def _calculate_components(self, row: pd.Series) -> Dict[str, float]:
        weights = self.params.weights

        earnings_score = 0.0
        earnings_growth = row.get("earnings_growth")
        if pd.notna(earnings_growth) and earnings_growth >= self.params.earnings_growth_threshold:
            earnings_score = weights["earnings"]

        rs_score = 0.0
        rs = row.get("relative_strength")
        if pd.notna(rs):
            rs_score = weights["relative_strength"] * min(1.0, rs)

        price_score = 0.0
        high_price = row.get("fifty_two_week_high")
        close_price = row.get("close")
        if pd.notna(high_price) and high_price > 0 and pd.notna(close_price):
            distance = (high_price - close_price) / high_price
            if distance <= self.params.near_high_threshold:
                price_score = weights["price_near_high"] * (1 - (distance / self.params.near_high_threshold))

        volume_score = 0.0
        volume_change = row.get("volume_change")
        if pd.notna(volume_change) and volume_change >= self.params.volume_increase_threshold:
            volume_score = weights["volume_increase"] * min(1.0, volume_change / self.params.volume_increase_threshold)

        return {
            "earnings_score": float(earnings_score),
            "relative_strength_score": float(rs_score),
            "price_near_high_score": float(price_score),
            "volume_increase_score": float(volume_score),
        }


__all__ = ["CanSlimStrategy", "CanSlimParams"]
