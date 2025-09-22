from __future__ import annotations

import pandas as pd

from portfolio.sector_monitor import (
    calculate_sector_allocations,
    detect_sector_breaches,
)


def _positions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"symbol": "AAPL", "value": 40000, "sector": "technology"},
            {"symbol": "MSFT", "value": 35000, "sector": "technology"},
            {"symbol": "XOM", "value": 15000, "sector": "energy"},
            {"symbol": "AMZN", "value": 10000, "sector": "other"},
        ]
    )


def test_calculate_sector_allocations():
    limits = {"technology": 0.4, "energy": 0.3, "other": 0.3}
    allocations = calculate_sector_allocations(_positions(), limits)

    assert allocations
    tech_alloc = next(a for a in allocations if a.sector == "technology")
    assert abs(tech_alloc.allocation - 0.75) < 1e-6
    assert tech_alloc.limit == limits["technology"]


def test_detects_sector_breaches():
    limits = {"technology": 0.5, "energy": 0.2, "other": 0.3}
    breaches = detect_sector_breaches(_positions(), limits)

    assert len(breaches) == 1
    breach = breaches[0]
    assert breach.sector == "technology"
    assert abs(breach.allocation - 0.75) < 1e-6
    assert breach.limit == 0.5


def test_handles_empty_positions():
    limits = {"other": 1.0}
    empty = pd.DataFrame(columns=["symbol", "value", "sector"])
    allocations = calculate_sector_allocations(empty, limits)
    breaches = detect_sector_breaches(empty, limits)

    assert allocations == []
    assert breaches == []
