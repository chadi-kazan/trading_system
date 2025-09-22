from __future__ import annotations

import datetime as dt

from portfolio.position_sizer import PositionSizer
from strategies.base import SignalType, StrategySignal
from trading_system.config_manager import RiskManagementConfig


def _signal(symbol: str, confidence: float, price: float, date: dt.datetime) -> StrategySignal:
    return StrategySignal(
        symbol=symbol,
        date=date,
        strategy="test_strategy",
        signal_type=SignalType.BUY,
        confidence=confidence,
        metadata={"entry_price": price},
    )


def test_sizes_positions_respecting_limits():
    risk = RiskManagementConfig(
        max_positions=4,
        individual_stop=0.08,
        portfolio_stop=0.2,
        sector_limits={
            "technology": 0.4,
            "energy": 0.3,
            "other": 0.3,
        },
    )
    sizer = PositionSizer(risk)
    date = dt.datetime(2024, 1, 1)
    signals = [
        _signal("AAPL", 0.9, 100.0, date),
        _signal("MSFT", 0.85, 95.0, date),
        _signal("XOM", 0.8, 50.0, date),
        _signal("TSLA", 0.75, 200.0, date),
        _signal("AMZN", 0.7, 120.0, date),
    ]
    sector_map = {
        "AAPL": "technology",
        "MSFT": "technology",
        "XOM": "energy",
        "TSLA": "technology",
        "AMZN": "other",
    }

    allocations = sizer.size_positions(signals, account_equity=100_000, sector_map=sector_map)

    assert len(allocations) == 4
    # Ensure highest confidence selected first
    assert allocations[0].symbol == "AAPL"
    # Ensure sector allocation does not exceed limit (80k tech limit -> 40k per base)
    tech_alloc = sum(p.allocation for p in allocations if p.sector == "technology")
    assert tech_alloc <= 100_000 * risk.sector_limits["technology"] + 1e-6


def test_skips_when_price_missing_or_sector_limit_hit():
    risk = RiskManagementConfig(
        max_positions=3,
        individual_stop=0.08,
        portfolio_stop=0.2,
        sector_limits={
            "energy": 0.25,
            "other": 0.75,
        },
    )
    sizer = PositionSizer(risk)
    date = dt.datetime(2024, 1, 2)
    signals = [
        StrategySignal(
            symbol="BAD",
            date=date,
            strategy="test",
            signal_type=SignalType.BUY,
            confidence=0.9,
            metadata={},
        ),
        _signal("XOM", 0.85, 40.0, date),
        _signal("CVX", 0.8, 38.0, date),
        _signal("NEE", 0.75, 70.0, date),
    ]
    sector_map = {
        "XOM": "energy",
        "CVX": "energy",
        "NEE": "energy",
    }

    allocations = sizer.size_positions(signals, account_equity=60_000, sector_map=sector_map)

    # Only first energy allocation should be included due to sector cap 0.25
    assert [p.symbol for p in allocations] == ["XOM"]


def test_zero_equity_returns_empty():
    risk = RiskManagementConfig(
        max_positions=5,
        individual_stop=0.08,
        portfolio_stop=0.2,
        sector_limits={"other": 1.0},
    )
    sizer = PositionSizer(risk)

    allocations = sizer.size_positions([_signal("AAPL", 0.9, 100, dt.datetime.utcnow())], account_equity=0)
    assert allocations == []
