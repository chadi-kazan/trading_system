"""Fundamental metrics loading utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .alpha_vantage_client import AlphaVantageClient, AlphaVantageError

LOGGER = logging.getLogger(__name__)


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


def _map_alpha_overview(payload: Dict[str, Any]) -> Dict[str, float]:
    metrics: Dict[str, float] = {}

    earnings_growth = _to_float(payload.get("QuarterlyEarningsGrowthYOY"))
    if earnings_growth is not None:
        metrics["earnings_growth"] = earnings_growth

    fifty_two_high = _to_float(payload.get("52WeekHigh"))
    fifty_two_low = _to_float(payload.get("52WeekLow"))
    moving_avg = _to_float(
        payload.get("50DayMovingAverage")
        or payload.get("200DayMovingAverage")
        or payload.get("AnalystTargetPrice")
    )
    if (
        fifty_two_high is not None
        and fifty_two_low is not None
        and moving_avg is not None
        and fifty_two_high > fifty_two_low
    ):
        relative_strength = (moving_avg - fifty_two_low) / (fifty_two_high - fifty_two_low)
        metrics["relative_strength"] = float(max(0.0, min(1.0, relative_strength)))

    market_cap = _to_float(payload.get("MarketCapitalization"))
    if market_cap is not None:
        metrics["market_cap"] = market_cap

    return metrics


def load_fundamental_metrics(
    symbol: str,
    base_dir: Path,
    api_key: Optional[str] = None,
    client: Optional[AlphaVantageClient] = None,
) -> Dict[str, float]:
    """Return normalized fundamental metrics for *symbol* from cache or Alpha Vantage."""

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

    if api_key:
        try:
            av_client = client or AlphaVantageClient(api_key)
        except ValueError:
            return {}
        try:
            overview = av_client.fetch_company_overview(cleaned_symbol)
        except (AlphaVantageError, Exception) as exc:  # pragma: no cover - network faults
            LOGGER.warning("Alpha Vantage overview fetch failed for %s: %s", cleaned_symbol, exc)
        else:
            mapped = _map_alpha_overview(overview)
            if mapped:
                return mapped

    return {}


__all__ = ["load_fundamental_metrics"]
