from __future__ import annotations

import datetime as dt

from strategies.aggregation import AggregationParams, SignalAggregator
from strategies.base import SignalType, StrategySignal


def _signal(symbol: str, strategy: str, signal_type: SignalType, confidence: float, date: dt.datetime) -> StrategySignal:
    return StrategySignal(
        symbol=symbol,
        date=date,
        strategy=strategy,
        signal_type=signal_type,
        confidence=confidence,
        metadata={"source": strategy},
    )


def test_aggregation_combines_confidence_and_metadata():
    aggregator = SignalAggregator()
    date = dt.datetime(2024, 1, 2)
    signals = [
        _signal("AAPL", "dan_zanger_cup_handle", SignalType.BUY, 0.8, date),
        _signal("AAPL", "can_slim", SignalType.BUY, 0.7, date),
    ]

    aggregated = aggregator.aggregate(signals)

    assert len(aggregated) == 1
    agg_signal = aggregated[0]
    assert agg_signal.symbol == "AAPL"
    assert agg_signal.signal_type == SignalType.BUY
    assert agg_signal.confidence >= aggregator.params.min_confidence
    assert agg_signal.metadata["strategies"] == ["dan_zanger_cup_handle", "can_slim"]


def test_respects_threshold_and_weighting():
    params = AggregationParams(min_confidence=0.6, weighting={
        "trend_following": 2.0,
        "can_slim": 0.5,
    })
    aggregator = SignalAggregator(params=params)
    date = dt.datetime(2024, 1, 3)
    signals = [
        _signal("MSFT", "trend_following", SignalType.BUY, 0.55, date),
        _signal("MSFT", "can_slim", SignalType.BUY, 0.5, date),
    ]

    aggregated = aggregator.aggregate(signals)
    assert aggregated == []


def test_filters_signals_below_threshold():
    aggregator = SignalAggregator(AggregationParams(min_confidence=0.9))
    date = dt.datetime(2024, 1, 4)
    signals = [
        _signal("TSLA", "trend_following", SignalType.BUY, 0.5, date),
        _signal("TSLA", "dan_zanger_cup_handle", SignalType.BUY, 0.6, date),
    ]

    aggregated = aggregator.aggregate(signals)
    assert aggregated == []


def test_handles_multiple_symbol_types():
    aggregator = SignalAggregator()
    date = dt.datetime(2024, 1, 5)
    signals = [
        _signal("AAPL", "trend_following", SignalType.BUY, 0.7, date),
        _signal("AAPL", "trend_following", SignalType.SELL, 0.8, date),
        _signal("MSFT", "can_slim", SignalType.BUY, 0.9, date),
    ]

    aggregated = aggregator.aggregate(signals)
    assert len(aggregated) == 3
    types = {sig.signal_type.name for sig in aggregated if sig.symbol == "AAPL"}
    assert types == {"BUY", "SELL"}
