"""Equity curve utilities for portfolio monitoring."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


def load_equity_curve(path: Path) -> pd.Series:
    """Load equity curve from CSV with `date` and `equity` columns."""

    df = pd.read_csv(path, parse_dates=["date"])
    if "equity" not in df.columns:
        raise ValueError("Equity curve must contain an 'equity' column")
    return pd.Series(df["equity"].values, index=df["date"])


def equity_curve_from_positions(positions: pd.DataFrame, cash: float = 0.0) -> pd.Series:
    """Construct equity curve from positions valued over time."""

    if positions.empty:
        return pd.Series([cash], index=[pd.Timestamp.utcnow()])

    if not {"date", "value"}.issubset(positions.columns):
        raise ValueError("Positions DataFrame must contain 'date' and 'value' columns")

    grouped = positions.groupby("date")["value"].sum().cumsum() + cash
    return grouped


__all__ = ["load_equity_curve", "equity_curve_from_positions"]
