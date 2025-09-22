"""Sector concentration monitoring utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd


@dataclass
class SectorAllocation:
    sector: str
    allocation: float
    limit: float


@dataclass
class SectorBreach:
    sector: str
    allocation: float
    limit: float


def calculate_sector_allocations(
    positions: pd.DataFrame,
    sector_limits: Dict[str, float],
) -> List[SectorAllocation]:
    """Calculate allocation per sector from positions DataFrame."""

    if positions.empty:
        return []

    sector_alloc = (
        positions.groupby("sector")["value"].sum().reset_index()
    )
    total_equity = positions["value"].sum()
    allocations = []
    for _, row in sector_alloc.iterrows():
        sector = row["sector"].lower()
        limit = sector_limits.get(sector, sector_limits.get("other", 1.0))
        allocations.append(
            SectorAllocation(
                sector=sector,
                allocation=float(row["value"] / total_equity),
                limit=float(limit),
            )
        )
    return allocations


def detect_sector_breaches(
    positions: pd.DataFrame,
    sector_limits: Dict[str, float],
    tolerance: float = 0.0,
) -> List[SectorBreach]:
    """Return list of sectors exceeding their allocation limits."""

    allocations = calculate_sector_allocations(positions, sector_limits)
    breaches = []
    for alloc in allocations:
        if alloc.allocation > alloc.limit + tolerance:
            breaches.append(
                SectorBreach(
                    sector=alloc.sector,
                    allocation=alloc.allocation,
                    limit=alloc.limit,
                )
            )
    return breaches


__all__ = [
    "calculate_sector_allocations",
    "detect_sector_breaches",
    "SectorBreach",
    "SectorAllocation",
]
