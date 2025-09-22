"""Position sizing engine respecting risk and sector limits."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Dict, Iterable, List, Optional

from strategies.base import SignalType, StrategySignal
from trading_system.config_manager import RiskManagementConfig


@dataclass
class PositionAllocation:
    symbol: str
    shares: int
    allocation: float
    confidence: float
    sector: str
    entry_price: float
    stop_price: float


class PositionSizer:
    """Allocates capital to signals based on configured risk limits."""

    def __init__(self, risk_config: RiskManagementConfig) -> None:
        self.risk_config = risk_config

    def size_positions(
        self,
        signals: Iterable[StrategySignal],
        account_equity: float,
        sector_map: Optional[Dict[str, str]] = None,
    ) -> List[PositionAllocation]:
        if account_equity <= 0:
            return []

        sector_map = sector_map or {}
        max_positions = max(1, self.risk_config.max_positions)
        base_allocation = account_equity / max_positions

        allocations: List[PositionAllocation] = []
        sector_allocated: Dict[str, float] = {key: 0.0 for key in self.risk_config.sector_limits}
        total_positions = 0

        sorted_signals = sorted(
            (s for s in signals if s.signal_type == SignalType.BUY),
            key=lambda s: s.confidence,
            reverse=True,
        )

        for signal in sorted_signals:
            if total_positions >= max_positions:
                break

            price = self._extract_price(signal)
            if price is None or price <= 0:
                continue

            sector = sector_map.get(signal.symbol, "other").lower()
            sector_limit = self._get_sector_limit(sector)
            current_sector_allocation = sector_allocated.get(sector, 0.0)
            remaining_sector_capacity = account_equity * sector_limit - current_sector_allocation
            if remaining_sector_capacity <= 0:
                continue

            allocation_budget = min(base_allocation, remaining_sector_capacity)
            shares = floor(allocation_budget / price)
            if shares <= 0:
                continue

            allocation_value = shares * price
            stop_price = price * (1 - self.risk_config.individual_stop)

            allocations.append(
                PositionAllocation(
                    symbol=signal.symbol,
                    shares=shares,
                    allocation=allocation_value,
                    confidence=float(signal.confidence),
                    sector=sector,
                    entry_price=price,
                    stop_price=stop_price,
                )
            )
            total_positions += 1
            sector_allocated[sector] = current_sector_allocation + allocation_value

        return allocations

    def _get_sector_limit(self, sector: str) -> float:
        limits = self.risk_config.sector_limits
        if sector in limits:
            return limits[sector]
        return limits.get("other", 1.0)

    @staticmethod
    def _extract_price(signal: StrategySignal) -> Optional[float]:
        metadata = signal.metadata or {}
        for key in ("entry_price", "breakout_price", "price", "close"):
            value = metadata.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None


__all__ = ["PositionSizer", "PositionAllocation"]

