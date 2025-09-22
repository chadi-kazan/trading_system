"""Dan Zanger cup-and-handle breakout strategy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from strategies.base import Strategy, StrategySignal, SignalType


@dataclass(frozen=True)
class DanZangerParams:
    cup_lookback: int = 120
    handle_min: int = 5
    handle_max: int = 15
    cup_depth_min: float = 0.12
    cup_depth_max: float = 0.35
    recovery_threshold: float = 0.85
    handle_pullback_min: float = 0.05
    handle_pullback_max: float = 0.15
    breakout_threshold: float = 0.02
    volume_multiplier: float = 1.5
    volume_mean_window: int = 20


class DanZangerCupHandleStrategy(Strategy):
    """Detects cup-and-handle breakouts following Dan Zanger guidelines."""

    name = "dan_zanger_cup_handle"

    def __init__(self, params: DanZangerParams | None = None) -> None:
        self.params = params or DanZangerParams()

    # ------------------------------------------------------------------
    def generate_signals(self, symbol: str, prices: pd.DataFrame) -> List[StrategySignal]:
        if prices.empty:
            return []

        df = prices.sort_index().copy()
        required = ["close", "volume"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns for Dan Zanger strategy: {missing}")

        df = df.dropna(subset=required)
        if len(df) < self.params.cup_lookback:
            return []

        rolling_volume = df["volume"].rolling(self.params.volume_mean_window, min_periods=5).mean()

        signals: List[StrategySignal] = []
        for idx in range(self.params.cup_lookback, len(df)):
            window = df.iloc[idx - self.params.cup_lookback : idx + 1]
            if len(window) < self.params.cup_lookback:
                continue

            breakout_row = window.iloc[-1]
            breakout_date = window.index[-1]

            handle_window = window.iloc[-(self.params.handle_max + 1) : -1]
            if len(handle_window) < self.params.handle_min:
                continue

            handle_high_price = handle_window["close"].max()
            handle_high_idx = handle_window["close"].idxmax()
            handle_low_price = handle_window["close"].min()
            if handle_high_price <= 0:
                continue

            handle_pullback = (handle_high_price - handle_low_price) / handle_high_price
            if not (self.params.handle_pullback_min <= handle_pullback <= self.params.handle_pullback_max):
                continue

            cup_window = window.loc[:handle_window.index[0]]
            if len(cup_window) < self.params.handle_min * 2:
                continue

            cup_bottom_idx = cup_window["close"].idxmin()
            cup_bottom_price = cup_window.loc[cup_bottom_idx, "close"]

            left_zone = cup_window.loc[:cup_bottom_idx]
            right_zone = window.loc[cup_bottom_idx:handle_high_idx]
            if left_zone.empty or right_zone.empty:
                continue

            left_peak_idx = left_zone["close"].idxmax()
            left_peak_price = left_zone.loc[left_peak_idx, "close"]
            right_peak_price = right_zone["close"].max()
            right_peak_idx = right_zone["close"].idxmax()

            if left_peak_price <= 0 or right_peak_price <= 0:
                continue

            cup_depth = (left_peak_price - cup_bottom_price) / left_peak_price
            if not (self.params.cup_depth_min <= cup_depth <= self.params.cup_depth_max):
                continue

            if left_peak_price == cup_bottom_price:
                continue

            recovery_ratio = (right_peak_price - cup_bottom_price) / (left_peak_price - cup_bottom_price)
            if recovery_ratio < self.params.recovery_threshold:
                continue

            breakout_price = breakout_row["close"]
            if breakout_price < right_peak_price * (1 + self.params.breakout_threshold):
                continue

            avg_volume = rolling_volume.iloc[idx - 1] if idx > 0 else None
            if avg_volume is None or avg_volume <= 0:
                continue

            if breakout_row["volume"] < avg_volume * self.params.volume_multiplier:
                continue

            confidence = min(1.0, max(0.0, 0.6 + (recovery_ratio - self.params.recovery_threshold)))
            metadata = {
                "left_peak": float(left_peak_price),
                "cup_bottom": float(cup_bottom_price),
                "right_peak": float(right_peak_price),
                "handle_pullback": float(handle_pullback),
                "cup_depth": float(cup_depth),
                "recovery_ratio": float(recovery_ratio),
                "breakout_price": float(breakout_price),
                "breakout_volume": float(breakout_row["volume"]),
                "avg_volume": float(avg_volume),
                "left_peak_date": left_peak_idx,
                "cup_bottom_date": cup_bottom_idx,
                "right_peak_date": right_peak_idx,
            }
            signals.append(
                StrategySignal(
                    symbol=symbol,
                    date=breakout_date,
                    strategy=self.name,
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    metadata=metadata,
                )
            )

        return signals

    def required_columns(self) -> List[str]:
        return ["close", "volume"]


__all__ = ["DanZangerCupHandleStrategy", "DanZangerParams"]
