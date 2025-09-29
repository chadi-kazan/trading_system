"""Fundamental metrics loading utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_json_fundamentals(path: Path) -> Dict[str, float]:
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}

    if isinstance(payload, dict):
        data = payload.get("data") if "data" in payload and isinstance(payload["data"], dict) else payload
        return {
            str(key).lower(): converted
            for key, value in data.items()
            if (converted := _to_float(value)) is not None
        }
    return {}


def _load_csv_fundamentals(path: Path, symbol: str) -> Dict[str, float]:
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return {}

    if frame.empty:
        return {}

    symbol_column = None
    for column in frame.columns:
        if str(column).lower() == "symbol":
            symbol_column = column
            break
    if symbol_column is None:
        return {}

    match = frame[frame[symbol_column].astype(str).str.upper() == symbol]
    if match.empty:
        return {}

    row = match.iloc[-1].to_dict()
    result: Dict[str, float] = {}
    for key, value in row.items():
        if str(key).lower() == "symbol":
            continue
        converted = _to_float(value)
        if converted is not None:
            result[str(key).lower()] = converted
    return result


def load_fundamental_metrics(symbol: str, base_dir: Path) -> Dict[str, float]:
    """Return normalized fundamental metrics for *symbol* from known cache locations."""

    cleaned_symbol = symbol.upper().strip()
    if not cleaned_symbol:
        return {}

    fundamentals_dir = base_dir / "fundamentals"
    if fundamentals_dir.is_dir():
        json_path = fundamentals_dir / f"{cleaned_symbol}.json"
        if json_path.exists():
            data = _load_json_fundamentals(json_path)
            if data:
                return data

    csv_path = base_dir / "fundamentals.csv"
    if csv_path.exists():
        data = _load_csv_fundamentals(csv_path, cleaned_symbol)
        if data:
            return data

    return {}


__all__ = ["load_fundamental_metrics"]
