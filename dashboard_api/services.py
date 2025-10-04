"""Service layer that powers the dashboard API."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from data_pipeline import enrich_price_frame, load_fundamental_metrics
from data_pipeline.alpha_vantage_client import AlphaVantageClient, AlphaVantageError
from data_providers.base import PriceRequest
from data_providers.yahoo import YahooPriceProvider
from indicators.moving_average import ema
from indicators.volatility import average_true_range
from main import build_strategy_weight_map, instantiate_strategies
from strategies.aggregation import AggregationParams, SignalAggregator
from strategies.base import Strategy, StrategySignal
from strategies.trend_following import TrendFollowingStrategy
from trading_system.config_manager import TradingSystemConfig

from .config import get_config
from .metadata import STRATEGY_METADATA, STRATEGY_ORDER
from .schemas import (
    AggregatedSignalPayload,
    PriceBar,
    StrategyAnalysis,
    StrategyInfo,
    StrategySignalPayload,
    SymbolAnalysisResponse,
    SymbolSearchResult,
)

LOGGER = logging.getLogger(__name__)


class RateLimitError(RuntimeError):
    """Raised when a request is throttled to protect upstream providers."""


class SignalService:
    """High-level orchestration for symbol analysis and search."""

    def __init__(self, config: TradingSystemConfig | None = None) -> None:
        self.config = config or get_config()
        self.price_provider = YahooPriceProvider(
            cache_dir=self.config.storage.price_cache_dir,
            cache_ttl_days=self.config.data_sources.cache_days,
        )
        self._strategies: List[Strategy] = instantiate_strategies(None, self.config)
        self._strategy_map: Dict[str, Strategy] = {strategy.name: strategy for strategy in self._strategies}

        weights = build_strategy_weight_map(self.config)
        self.aggregator = SignalAggregator(
            AggregationParams(
                min_confidence=0.5,
                weighting=weights,
            )
        )

        api_key = self.config.data_sources.alpha_vantage_key
        self.alpha_client: Optional[AlphaVantageClient]
        if api_key:
            self.alpha_client = AlphaVantageClient(api_key)
        else:
            self.alpha_client = None

        self.analysis_cache_ttl_seconds: float = 300.0
        self.analysis_throttle_seconds: float = 10.0
        self.search_cache_ttl_seconds: float = 300.0
        self.search_throttle_seconds: float = 1.0
        self._analysis_cache: Dict[Tuple[str, str, str, str], Tuple[float, SymbolAnalysisResponse]] = {}
        self._analysis_last_fetch: Dict[Tuple[str, str, str, str], float] = {}
        self._search_cache: Dict[str, Tuple[float, List[SymbolSearchResult]]] = {}
        self._last_search_ts: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_strategies(self) -> List[StrategyInfo]:
        items: List[StrategyInfo] = []
        for name in STRATEGY_ORDER:
            meta = STRATEGY_METADATA.get(name, {})
            items.append(
                StrategyInfo(
                    name=name,
                    label=meta.get("label", name.replace("_", " ").title()),
                    description=meta.get("description", ""),
                    chart_type=meta.get("chart_type", "unknown"),
                )
            )
        return items

    def search_symbols(self, query: str, *, max_results: int = 10) -> List[SymbolSearchResult]:
        text = (query or "").strip()
        if not text:
            return []

        key = text.lower()
        now = time.time()
        cached = self._search_cache.get(key)
        if cached and now - cached[0] <= self.search_cache_ttl_seconds:
            LOGGER.debug("Serving cached search results for '%s'", text)
            return [result.model_copy() for result in cached[1]]

        items: List[Dict[str, Any]] = []
        if self.alpha_client is not None and now - self._last_search_ts >= self.search_throttle_seconds:
            self._last_search_ts = now
            try:
                items = self.alpha_client.search_symbols(text, max_results=max_results)
            except AlphaVantageError as exc:
                LOGGER.warning("Alpha Vantage search failed for '%s': %s", text, exc)
        elif self.alpha_client is None:
            LOGGER.debug("Alpha Vantage key unavailable; skipping external search for '%s'", text)
        else:
            LOGGER.debug("Throttling Alpha Vantage search for '%s'", text)

        if not items:
            from universe.candidates import load_seed_candidates

            candidates = load_seed_candidates()
            filtered = [symbol for symbol in candidates if text.upper() in symbol]
            items = [
                {
                    "symbol": symbol,
                    "name": symbol,
                    "type": "Equity",
                    "region": "Local",
                    "match_score": 0.0,
                }
                for symbol in filtered[:max_results]
            ]

        results = [SymbolSearchResult(**item) for item in items]
        self._search_cache[key] = (time.time(), results)
        return [result.model_copy() for result in results]

    def get_symbol_analysis(
        self,
        symbol: str,
        *,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> SymbolAnalysisResponse:
        cleaned_symbol = symbol.strip().upper()
        if not cleaned_symbol:
            raise ValueError("Symbol must not be empty")
        if start > end:
            raise ValueError("Start date must be on or before end date")

        cache_key = self._analysis_cache_key(cleaned_symbol, start, end, interval)
        cached = self._get_cached_analysis(cache_key)
        if cached is not None:
            LOGGER.debug("Serving cached analysis for %s", cleaned_symbol)
            return cached

        now = time.time()
        last_fetch = self._analysis_last_fetch.get(cache_key)
        if last_fetch and now - last_fetch < self.analysis_throttle_seconds:
            raise RateLimitError("Please wait before requesting another update for this symbol.")
        self._analysis_last_fetch[cache_key] = now

        price_request = PriceRequest(symbol=cleaned_symbol, start=start, end=end, interval=interval)
        price_result = self.price_provider.get_price_history(price_request)
        frame = price_result.data
        if frame.empty:
            raise ValueError(f"No price data was returned for {cleaned_symbol}")

        fundamentals: Dict[str, Any] = {}
        try:
            fundamentals = load_fundamental_metrics(
                cleaned_symbol,
                base_dir=self.config.storage.universe_dir,
                api_key=self.config.data_sources.alpha_vantage_key,
            )
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Fundamentals lookup failed for %s: %s", cleaned_symbol, exc)

        enriched = enrich_price_frame(cleaned_symbol, frame, fundamentals=fundamentals)
        enriched = self._ensure_additional_indicators(enriched)

        strategy_payloads: List[StrategyAnalysis] = []
        collected_signals: List[StrategySignal] = []

        for name in STRATEGY_ORDER:
            strategy = self._strategy_map.get(name)
            if strategy is None:
                LOGGER.debug("Strategy %s is not registered; skipping", name)
                continue
            try:
                signals = strategy.generate_signals(cleaned_symbol, enriched)
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.exception("Strategy %s failed for %s", name, cleaned_symbol)
                signals = []
            collected_signals.extend(signals)
            payload = self._build_strategy_analysis(strategy, signals)
            strategy_payloads.append(payload)

        aggregated_signals = [
            self._to_aggregated_payload(signal)
            for signal in self.aggregator.aggregate(collected_signals)
        ]

        prices = [self._to_price_bar(idx, row) for idx, row in enriched.iterrows()]

        analysis = SymbolAnalysisResponse(
            symbol=cleaned_symbol,
            start=start,
            end=end,
            interval=interval,
            price_bars=prices,
            strategies=strategy_payloads,
            aggregated_signals=aggregated_signals,
        )
        self._store_analysis(cache_key, analysis)
        return analysis

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_additional_indicators(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame

        enriched = frame.copy()
        trend = self._strategy_map.get("trend_following")
        if isinstance(trend, TrendFollowingStrategy):
            params = trend.params
            try:
                enriched["fast_ema"] = ema(enriched["close"], span=params.fast_span)
                enriched["slow_ema"] = ema(enriched["close"], span=params.slow_span)
                enriched["atr"] = average_true_range(
                    enriched["high"],
                    enriched["low"],
                    enriched["close"],
                    period=params.atr_period,
                )
            except KeyError:
                LOGGER.debug("Missing columns for EMA/ATR enrichment; skipping additional indicators")
        else:
            for column in ("fast_ema", "slow_ema", "atr"):
                if column not in enriched.columns:
                    enriched[column] = pd.NA
        return enriched

    def _build_strategy_analysis(
        self,
        strategy: Strategy,
        signals: Iterable[StrategySignal],
    ) -> StrategyAnalysis:
        meta = STRATEGY_METADATA.get(strategy.name, {})
        signal_payloads = [self._to_signal_payload(signal) for signal in signals]
        latest_metadata = signal_payloads[-1].metadata if signal_payloads else None

        extras: Dict[str, Any] = {}
        if strategy.name == "can_slim" and latest_metadata:
            extras["scores"] = latest_metadata
        elif strategy.name == "trend_following" and latest_metadata:
            extras["latest_stop_price"] = latest_metadata.get("stop_price")

        return StrategyAnalysis(
            name=strategy.name,
            label=meta.get("label", strategy.name.replace("_", " ").title()),
            description=meta.get("description", ""),
            chart_type=meta.get("chart_type", "unknown"),
            signals=signal_payloads,
            latest_metadata=latest_metadata,
            extras=extras,
        )

    @staticmethod
    def _to_signal_payload(signal: StrategySignal) -> StrategySignalPayload:
        return StrategySignalPayload(
            date=_ensure_datetime(signal.date),
            signal_type=signal.signal_type.name,
            confidence=float(signal.confidence),
            metadata=_normalise_metadata(signal.metadata),
        )

    @staticmethod
    def _to_aggregated_payload(signal: StrategySignal) -> AggregatedSignalPayload:
        return AggregatedSignalPayload(
            date=_ensure_datetime(signal.date),
            signal_type=signal.signal_type.name,
            confidence=float(signal.confidence),
            metadata=_normalise_metadata(signal.metadata),
        )

    def _analysis_cache_key(
        self,
        symbol: str,
        start: date,
        end: date,
        interval: str,
    ) -> Tuple[str, str, str, str]:
        return (symbol, start.isoformat(), end.isoformat(), interval)

    def _get_cached_analysis(self, key: Tuple[str, str, str, str]) -> Optional[SymbolAnalysisResponse]:
        entry = self._analysis_cache.get(key)
        if entry is None:
            return None
        timestamp, model = entry
        if time.time() - timestamp > self.analysis_cache_ttl_seconds:
            self._analysis_cache.pop(key, None)
            return None
        return model.model_copy()

    def _store_analysis(self, key: Tuple[str, str, str, str], analysis: SymbolAnalysisResponse) -> None:
        self._analysis_cache[key] = (time.time(), analysis)

    @staticmethod
    def _to_price_bar(index: Any, row: pd.Series) -> PriceBar:
        data = row.to_dict()
        return PriceBar(
            date=_ensure_datetime(index),
            open=_safe_float(data.get("open")),
            high=_safe_float(data.get("high")),
            low=_safe_float(data.get("low")),
            close=_safe_float(data.get("close")),
            adj_close=_safe_float(data.get("adj_close", data.get("close"))),
            volume=_safe_float(data.get("volume")),
            average_volume=_maybe_float(data.get("average_volume")),
            volume_change=_maybe_float(data.get("volume_change")),
            fifty_two_week_high=_maybe_float(data.get("fifty_two_week_high")),
            relative_strength=_maybe_float(data.get("relative_strength")),
            earnings_growth=_maybe_float(data.get("earnings_growth")),
            fast_ema=_maybe_float(data.get("fast_ema")),
            slow_ema=_maybe_float(data.get("slow_ema")),
            atr=_maybe_float(data.get("atr")),
        )


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.fromisoformat(str(value))


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _maybe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(result):
        return None
    return result


def _normalise_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    normalised: Dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, datetime):
            normalised[key] = value.isoformat()
        elif isinstance(value, date):
            normalised[key] = value.isoformat()
        elif hasattr(value, "isoformat"):
            try:
                normalised[key] = value.isoformat()
            except Exception:  # pragma: no cover - defensive
                normalised[key] = value
        elif isinstance(value, list):
            normalised[key] = [
                item.isoformat() if hasattr(item, "isoformat") else item
                for item in value
            ]
        else:
            normalised[key] = value
    return normalised


__all__ = ["SignalService", "RateLimitError"]


