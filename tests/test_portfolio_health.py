from __future__ import annotations

import pandas as pd
import pytest

from portfolio.health import PortfolioHealthConfig, PortfolioHealthMonitor


def _equity_curve() -> pd.Series:
    data = [100, 120, 80, 130]
    dates = pd.date_range("2024-01-01", periods=len(data), freq="D")
    return pd.Series(data, index=dates)


def test_portfolio_health_report():
    config = PortfolioHealthConfig(
        sector_limits={"technology": 0.4, "energy": 0.3, "other": 0.3}
    )
    monitor = PortfolioHealthMonitor(config)
    positions = pd.DataFrame([
        {"symbol": "AAPL", "value": 40000, "sector": "technology"},
        {"symbol": "MSFT", "value": 35000, "sector": "technology"},
        {"symbol": "XOM", "value": 25000, "sector": "energy"},
    ])

    report = monitor.evaluate(_equity_curve(), positions)

    assert report.max_drawdown > 0
    assert report.drawdown_alerts  # alert generated for drop to 80
    assert any(b.sector == "technology" for b in report.sector_breaches)
    assert report.positions_count == len(positions)


def test_empty_equity_curve_raises():
    config = PortfolioHealthConfig(sector_limits={"other": 1.0})
    monitor = PortfolioHealthMonitor(config)

    with pytest.raises(ValueError):
        monitor.evaluate(pd.Series(dtype=float), pd.DataFrame())
