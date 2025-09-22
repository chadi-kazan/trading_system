"""Signal aggregation utilities for combining multiple strategies."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List

from strategies.base import SignalType, StrategySignal


@dataclass
class AggregationParams:
    min_confidence: float = 0.5
    weighting: Dict[str, float] | None = None


class SignalAggregator:
    """Aggregates signals from multiple strategies into combined outputs."""

    def __init__(self, params: AggregationParams | None = None) -> None:
        self.params = params or AggregationParams()
        if self.params.weighting is None:
            self.params.weighting = {}

    def aggregate(self, signals: Iterable[StrategySignal]) -> List[StrategySignal]:
        grouped: Dict[str, Dict[str, list[StrategySignal]]] = defaultdict(lambda: defaultdict(list))
        for signal in signals:
            grouped[signal.symbol][signal.signal_type.name].append(signal)

        aggregated_signals: List[StrategySignal] = []
        for symbol, type_map in grouped.items():
            for signal_type, signal_list in type_map.items():
                combined = self._combine_signals(symbol, signal_type, signal_list)
                if combined is not None:
                    aggregated_signals.append(combined)

        return aggregated_signals

    def _combine_signals(
        self,
        symbol: str,
        signal_type: str,
        signal_list: List[StrategySignal],
    ) -> StrategySignal | None:
        total_weight = 0.0
        weighted_confidence = 0.0
        combined_metadata: Dict[str, list] = defaultdict(list)
        dates = []

        for signal in signal_list:
            weight = self.params.weighting.get(signal.strategy, 1.0)
            total_weight += weight
            weighted_confidence += weight * signal.confidence
            dates.append(signal.date)
            for key, value in signal.metadata.items():
                combined_metadata[key].append(value)

        if total_weight == 0:
            return None

        avg_confidence = weighted_confidence / total_weight
        if avg_confidence < self.params.min_confidence:
            return None

        flattened_metadata = {key: value for key, value in combined_metadata.items()}
        flattened_metadata["strategies"] = [s.strategy for s in signal_list]
        flattened_metadata["confidence_values"] = [s.confidence for s in signal_list]

        aggregated_signal = StrategySignal(
            symbol=symbol,
            date=max(dates),
            strategy="aggregated",
            signal_type=SignalType[signal_type],
            confidence=float(avg_confidence),
            metadata=flattened_metadata,
        )
        return aggregated_signal


__all__ = ["SignalAggregator", "AggregationParams"]
