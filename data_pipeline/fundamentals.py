"""Fundamental metrics loading utilities."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

import pandas as pd

from .alpha_vantage_client import AlphaVantageClient, AlphaVantageError

LOGGER = logging.getLogger(__name__)


def _to_float(value: Any) -> float | None:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        is_percent = stripped.endswith("%")
        cleaned = stripped.rstrip("%").replace(",", "")
        try:
            numeric = float(cleaned)
        except ValueError:
            return None
        return numeric / 100.0 if is_percent else numeric
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
        fetched_at = payload.get("fetched_at")
        data = payload.get("data") if "data" in payload and isinstance(payload["data"], dict) else payload
        result = {
            str(key).lower(): converted
            for key, value in data.items()
            if (converted := _to_float(value)) is not None
        }
        if fetched_at:
            result["_fetched_at"] = str(fetched_at)
        return result
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

    pe_ratio = _to_float(payload.get("PERatio"))
    if pe_ratio is not None:
        metrics["pe_ratio"] = pe_ratio

    peg_ratio = _to_float(payload.get("PEGRatio"))
    if peg_ratio is not None:
        metrics["peg_ratio"] = peg_ratio

    eps = _to_float(payload.get("EPS"))
    if eps is not None:
        metrics["eps"] = eps

    ebitda = _to_float(payload.get("EBITDA"))
    if ebitda is not None:
        metrics["ebitda"] = ebitda

    dividend_yield = _to_float(payload.get("DividendYield"))
    if dividend_yield is not None:
        metrics["dividend_yield"] = dividend_yield

    revenue_ttm = _to_float(payload.get("RevenueTTM"))
    if revenue_ttm is not None:
        metrics["revenue_ttm"] = revenue_ttm

    profit_margin = _to_float(payload.get("ProfitMargin"))
    if profit_margin is not None:
        metrics["profit_margin"] = profit_margin

    operating_margin = _to_float(payload.get("OperatingMarginTTM"))
    if operating_margin is not None:
        metrics["operating_margin"] = operating_margin

    return_on_equity = _to_float(payload.get("ReturnOnEquityTTM"))
    if return_on_equity is not None:
        metrics["return_on_equity"] = return_on_equity

    debt_to_equity = _to_float(payload.get("DebtToEquityRatio"))
    if debt_to_equity is not None:
        metrics["debt_to_equity"] = debt_to_equity

    return metrics


def _map_earnings_metrics(payload: Dict[str, Any]) -> Dict[str, float]:
    quarterly = payload.get("quarterlyEarnings") or []
    if not isinstance(quarterly, Sequence):
        return {}

    surprises: list[float] = []
    beats = 0
    eps_values: list[float] = []

    for row in quarterly[:6]:
        if not isinstance(row, dict):
            continue
        reported = _to_float(row.get("reportedEPS"))
        estimated = _to_float(row.get("estimatedEPS"))
        if reported is None:
            continue
        eps_values.append(reported)
        if estimated is None or estimated == 0:
            continue
        surprise = (reported - estimated) / abs(estimated)
        surprises.append(surprise)
        if reported > estimated:
            beats += 1

    metrics: Dict[str, float] = {}
    if surprises:
        avg_surprise = sum(surprises) / len(surprises)
        metrics["earnings_surprise_avg"] = avg_surprise
        metrics["earnings_positive_ratio"] = beats / len(surprises)

    if len(eps_values) >= 2:
        latest = eps_values[0]
        prior = eps_values[1]
        if prior != 0:
            metrics["earnings_eps_trend"] = (latest - prior) / abs(prior)

    if metrics:
        components = []
        if "earnings_positive_ratio" in metrics:
            components.append(metrics["earnings_positive_ratio"])
        if "earnings_surprise_avg" in metrics:
            components.append(max(0.0, min(1.0, 0.5 + metrics["earnings_surprise_avg"] / 0.25)))
        if "earnings_eps_trend" in metrics:
            components.append(max(0.0, min(1.0, 0.5 + metrics["earnings_eps_trend"] / 0.25)))
        if components:
            metrics["earnings_signal_score"] = sum(components) / len(components)

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
            LOGGER.warning("Invalid Alpha Vantage configuration provided")
            return {}
        try:
            overview = av_client.fetch_company_overview(cleaned_symbol)
        except (AlphaVantageError, Exception) as exc:  # pragma: no cover - network faults
            LOGGER.warning("Alpha Vantage overview fetch failed for %s: %s", cleaned_symbol, exc)
        else:
            mapped = _map_alpha_overview(overview)
            earnings_metrics: Dict[str, float] = {}
            try:
                earnings_payload = av_client.fetch_earnings(cleaned_symbol)
            except (AlphaVantageError, Exception) as exc:  # pragma: no cover - network faults
                LOGGER.debug("Alpha Vantage earnings fetch failed for %s: %s", cleaned_symbol, exc)
            else:
                earnings_metrics = _map_earnings_metrics(earnings_payload)

            if mapped or earnings_metrics:
                result: Dict[str, float] = {}
                result.update(mapped)
                result.update(earnings_metrics)
                result["_fetched_at"] = datetime.utcnow().isoformat()
                return result

    return {}


def refresh_fundamentals_cache(
    symbols: Iterable[str],
    base_dir: Path,
    api_key: str,
    *,
    client: Optional[AlphaVantageClient] = None,
    throttle_seconds: float = 12.0,
) -> int:
    """Fetch fundamentals for *symbols* and write JSON cache files.

    Returns the number of successfully cached symbols.
    """

    cleaned = []
    seen: set[str] = set()
    for symbol in symbols:
        if not symbol:
            continue
        sym = symbol.upper().strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        cleaned.append(sym)

    if not cleaned:
        return 0

    if not api_key:
        raise ValueError("Alpha Vantage API key is required to refresh fundamentals")

    fundamentals_dir = base_dir / "fundamentals"
    fundamentals_dir.mkdir(parents=True, exist_ok=True)

    av_client = client or AlphaVantageClient(api_key)
    refreshed = 0
    for idx, symbol in enumerate(cleaned):
        try:
            overview = av_client.fetch_company_overview(symbol)
        except (AlphaVantageError, Exception) as exc:  # pragma: no cover - network faults
            LOGGER.warning("Skipping %s due to Alpha Vantage error: %s", symbol, exc)
            continue

        mapped = _map_alpha_overview(overview)
        try:
            earnings_payload = av_client.fetch_earnings(symbol)
        except (AlphaVantageError, Exception) as exc:  # pragma: no cover - network faults
            LOGGER.debug("Earnings fetch failed for %s: %s", symbol, exc)
            earnings_metrics = {}
        else:
            earnings_metrics = _map_earnings_metrics(earnings_payload)

        if earnings_metrics:
            mapped.update(earnings_metrics)
        if not mapped:
            LOGGER.info("Alpha Vantage returned no usable metrics for %s", symbol)
            continue

        payload = {
            "source": "alpha_vantage",
            "fetched_at": datetime.utcnow().isoformat(),
            "data": mapped,
        }
        target = fundamentals_dir / f"{symbol}.json"
        try:
            target.write_text(json.dumps(payload), encoding="utf-8")
        except OSError as exc:  # pragma: no cover - filesystem failure
            LOGGER.error("Failed to write fundamentals cache for %s: %s", symbol, exc)
            continue

        refreshed += 1
        if throttle_seconds > 0 and idx < len(cleaned) - 1:
            time.sleep(throttle_seconds)

    return refreshed


__all__ = ["load_fundamental_metrics", "refresh_fundamentals_cache"]
