"""Service layer that powers the dashboard API."""

from __future__ import annotations

import copy
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from analytics import (
    MarketRegimeAnalyzer,
    MarketRegimeSnapshot,
    EarningsSignal,
    compute_earnings_signal,
)
from data_pipeline import enrich_price_frame, load_fundamental_metrics
from data_pipeline.alpha_vantage_client import AlphaVantageClient, AlphaVantageError
from data_providers.base import PriceRequest
from data_providers.yahoo import BatchPriceResult, YahooPriceProvider
from indicators.moving_average import ema
from indicators.volatility import average_true_range
from strategies.aggregation import AggregationParams, SignalAggregator
from strategies.base import Strategy, StrategySignal
from strategies.trend_following import TrendFollowingStrategy
from trading_system.config_manager import TradingSystemConfig
from universe.candidates import load_russell_2000_candidates, load_sp500_candidates

if TYPE_CHECKING:
    from main import build_strategy_weight_map, instantiate_strategies

from .config import get_config
from .metadata import STRATEGY_METADATA, STRATEGY_ORDER
from .schemas import (
    AggregatedSignalPayload,
    MomentumEntry,
    MomentumResponse,
    SectorScoreResponse,
    SectorStrategyScore,
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
        from main import build_strategy_weight_map, instantiate_strategies

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
        self._regime_analyzer = MarketRegimeAnalyzer(self.price_provider)

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
                    investment_bounds=meta.get("investment_bounds"),
                    score_guidance=meta.get("score_guidance"),
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
        enriched = _ensure_additional_indicators(self._strategy_map, enriched)

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

        macro_snapshot = self._regime_analyzer.current()
        earnings_signal = compute_earnings_signal(fundamentals)

        aggregated_raw = list(self.aggregator.aggregate(collected_signals))
        adjusted_signals = [
            self._apply_overlays(signal, macro_snapshot, earnings_signal)
            for signal in aggregated_raw
        ]

        aggregated_signals = [
            self._to_aggregated_payload(signal)
            for signal in adjusted_signals
        ]

        prices = [self._to_price_bar(idx, row) for idx, row in enriched.iterrows()]
        latest_price_value = prices[-1].close if prices else None
        fundamentals_snapshot = self._build_fundamentals_payload(fundamentals, latest_price_value)

        analysis = SymbolAnalysisResponse(
            symbol=cleaned_symbol,
            start=start,
            end=end,
            interval=interval,
            price_bars=prices,
            strategies=strategy_payloads,
            aggregated_signals=aggregated_signals,
            macro_overlay=self._build_macro_payload(macro_snapshot),
            earnings_quality=self._build_earnings_payload(earnings_signal),
            fundamentals=fundamentals_snapshot,
        )
        self._store_analysis(cache_key, analysis)
        return analysis

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
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
            investment_bounds=meta.get("investment_bounds"),
            score_guidance=meta.get("score_guidance"),
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

    def _apply_overlays(
        self,
        signal: StrategySignal,
        macro: MarketRegimeSnapshot,
        earnings: EarningsSignal,
    ) -> StrategySignal:
        metadata = copy.deepcopy(signal.metadata)
        macro_metadata = {
            "regime": macro.name,
            "score": macro.score,
            "multiplier": macro.multiplier,
            "factors": macro.factors,
            "notes": macro.notes,
            "updated_at": macro.updated_at.isoformat(),
        }
        earnings_metadata = earnings.to_metadata()

        macro_multiplier = macro.multiplier
        earnings_multiplier = earnings.multiplier()
        final_confidence = signal.confidence * macro_multiplier * earnings_multiplier

        metadata["macro_overlay"] = macro_metadata
        metadata["earnings_quality"] = earnings_metadata
        metadata["confidence_components"] = {
            "base_confidence": signal.confidence,
            "macro_multiplier": macro_multiplier,
            "earnings_multiplier": earnings_multiplier,
            "final_confidence": final_confidence,
        }

        return StrategySignal(
            symbol=signal.symbol,
            date=signal.date,
            strategy=signal.strategy,
            signal_type=signal.signal_type,
            confidence=float(final_confidence),
            metadata=metadata,
        )

    @staticmethod
    def _build_macro_payload(snapshot: MarketRegimeSnapshot) -> Dict[str, Any]:
        return {
            "regime": snapshot.name,
            "score": snapshot.score,
            "multiplier": snapshot.multiplier,
            "factors": snapshot.factors,
            "notes": snapshot.notes,
            "updated_at": snapshot.updated_at.isoformat(),
        }

    @staticmethod
    def _build_earnings_payload(signal: EarningsSignal) -> Dict[str, Any] | None:
        payload = signal.to_metadata()
        if all(value is None for key, value in payload.items() if key != "confidence_multiplier"):
            return None
        payload["multiplier"] = payload.pop("confidence_multiplier")
        return payload

    def _build_fundamentals_payload(
        self,
        fundamentals: Dict[str, Any],
        latest_price: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        if not fundamentals and latest_price is None:
            return None

        def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
            return max(minimum, min(maximum, value))

        metrics: List[Dict[str, Any]] = []
        score_components: List[float] = []
        fetched_at = fundamentals.get("_fetched_at")

        def add_metric(
            key: str,
            label: str,
            ideal: str,
            raw_value: Any,
            formatter=None,
            interpreter=None,
        ) -> None:
            numeric: Optional[float] = None
            display = "—"
            interpretation = None
            if raw_value is not None:
                try:
                    numeric = float(raw_value)
                except (TypeError, ValueError):
                    numeric = None
                if numeric is not None:
                    try:
                        display = formatter(numeric) if formatter else f"{numeric:.3f}"
                    except Exception:  # pragma: no cover - defensive
                        display = f"{numeric:.3f}"
                    interpretation = interpreter(numeric) if interpreter else None
                else:
                    display = str(raw_value)
            metrics.append(
                {
                    "key": key,
                    "label": label,
                    "value": numeric,
                    "display": display,
                    "ideal": ideal,
                    "interpretation": interpretation,
                }
            )

        if latest_price is not None:
            add_metric(
                "price",
                "Price",
                "Confirm trend vs 50/200 day averages",
                latest_price,
                self._format_currency_value,
                lambda _: "Latest closing price.",
            )

        market_cap = fundamentals.get("market_cap")
        add_metric(
            "market_cap",
            "Market Cap",
            "> $100M (liquidity threshold)",
            market_cap,
            self._format_large_currency,
            lambda value: "Mega-cap scale." if value and value >= 1e11 else "Within small/mid-cap focus.",
        )

        pe_ratio = fundamentals.get("pe_ratio")
        add_metric(
            "pe_ratio",
            "P/E Ratio",
            "10-25 for growth names",
            pe_ratio,
            lambda v: f"{v:.1f}",
            lambda v: "Growth-aligned valuation." if v and v <= 25 else ("Rich multiple; confirm thesis." if v and v <= 50 else "Extremely rich valuation."),
        )
        if pe_ratio is not None and pe_ratio > 0:
            score_components.append(clamp((40.0 - float(pe_ratio)) / 30.0))

        peg_ratio = fundamentals.get("peg_ratio")
        add_metric(
            "peg_ratio",
            "PEG Ratio",
            "≤ 1.5 indicates reasonable price for growth",
            peg_ratio,
            lambda v: f"{v:.2f}",
            lambda v: "Growth priced fairly." if v and v <= 1.5 else ("Monitor valuation premium." if v and v <= 2.5 else "High growth premium."),
        )

        eps = fundamentals.get("eps")
        add_metric(
            "eps",
            "EPS (TTM)",
            "Positive and expanding",
            eps,
            lambda v: f"{v:.2f}",
            lambda v: "Positive earnings base." if v and v > 0 else "Negative EPS; evaluate turnaround evidence.",
        )

        ebitda = fundamentals.get("ebitda")
        add_metric(
            "ebitda",
            "EBITDA (TTM)",
            "Growing year over year",
            ebitda,
            self._format_large_currency,
            lambda v: "Healthy operating cash flow." if v and v > 0 else "Negative EBITDA; monitor liquidity.",
        )

        revenue = fundamentals.get("revenue_ttm")
        add_metric(
            "revenue_ttm",
            "Revenue (TTM)",
            "Consistent expansion",
            revenue,
            self._format_large_currency,
            lambda v: "Meaningful revenue base." if v and v > 0 else "Limited revenue data.",
        )

        dividend_yield = fundamentals.get("dividend_yield")
        add_metric(
            "dividend_yield",
            "Dividend Yield",
            "0% - 4% (higher for income)",
            dividend_yield,
            lambda v: self._format_percentage_value(v, 1),
            lambda v: "Income support in play." if v and v >= 0.02 else "Growth-oriented, low yield.",
        )
        if dividend_yield is not None:
            score_components.append(clamp(float(dividend_yield) / 0.04))

        profit_margin = fundamentals.get("profit_margin")
        add_metric(
            "profit_margin",
            "Profit Margin",
            "> 10% for quality names",
            profit_margin,
            lambda v: self._format_percentage_value(v, 1),
            lambda v: "Robust profitability." if v and v >= 0.12 else ("Moderate margin." if v and v >= 0.05 else "Thin or negative margin."),
        )
        if profit_margin is not None:
            score_components.append(clamp((float(profit_margin) + 0.05) / 0.25))

        operating_margin = fundamentals.get("operating_margin")
        add_metric(
            "operating_margin",
            "Operating Margin",
            "> 12% sustained",
            operating_margin,
            lambda v: self._format_percentage_value(v, 1),
            lambda v: "Efficient operations." if v and v >= 0.12 else ("Monitor efficiency trends." if v and v >= 0.05 else "Operating pressure present."),
        )

        roe = fundamentals.get("return_on_equity")
        add_metric(
            "return_on_equity",
            "Return on Equity",
            "> 15% indicates quality",
            roe,
            lambda v: self._format_percentage_value(v, 1),
            lambda v: "Excellent capital returns." if v and v >= 0.15 else ("Acceptable ROE." if v and v >= 0.08 else "Subpar ROE; investigate drivers."),
        )
        if roe is not None:
            score_components.append(clamp(float(roe) / 0.25))

        debt_to_equity = fundamentals.get("debt_to_equity")
        add_metric(
            "debt_to_equity",
            "Debt/Equity",
            "≤ 1.0 for flexibility",
            debt_to_equity,
            lambda v: f"{v:.2f}",
            lambda v: "Low leverage." if v and v <= 0.6 else ("Moderate leverage." if v and v <= 1.2 else "High leverage; monitor balance sheet."),
        )
        if debt_to_equity is not None:
            score_components.append(clamp((1.5 - float(debt_to_equity)) / 1.5))

        earnings_growth = fundamentals.get("earnings_growth")
        add_metric(
            "earnings_growth",
            "Earnings Growth YoY",
            "> 15% for growth focus",
            earnings_growth,
            lambda v: self._format_percentage_value(v, 1),
            lambda v: "Strong growth momentum." if v and v >= 0.15 else ("Mixed growth." if v and v >= 0.0 else "Earnings contraction."),
        )
        if earnings_growth is not None:
            score_components.append(clamp((float(earnings_growth) + 0.20) / 0.6))

        score: Optional[float] = None
        if score_components:
            score = sum(score_components) / len(score_components)

        snapshot: Dict[str, Any] = {
            "metrics": metrics,
            "notes": "Score blends valuation, profitability, growth, and yield markers.",
        }
        if score is not None:
            snapshot["score"] = round(float(score), 3)

        parsed_timestamp = self._parse_datetime_safe(fetched_at)
        if parsed_timestamp is not None:
            snapshot["updated_at"] = parsed_timestamp

        return snapshot

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

    @staticmethod
    def _format_currency_value(value: float) -> str:
        return f"${value:,.2f}"

    @staticmethod
    def _format_large_currency(value: float) -> str:
        if value is None:
            return "—"
        abs_value = abs(value)
        if abs_value >= 1_000_000_000_000:
            return f"${value / 1_000_000_000_000:.2f}T"
        if abs_value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if abs_value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if abs_value >= 1_000:
            return f"${value / 1_000:.2f}K"
        return f"${value:,.0f}"

    @staticmethod
    def _format_percentage_value(value: float, digits: int = 1) -> str:
        return f"{value * 100:.{digits}f}%"

    @staticmethod
    def _parse_datetime_safe(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except Exception:  # pragma: no cover - defensive
            return None


class BaseMomentumService:
    """Base implementation for computing index momentum leaderboards."""

    MAX_LIMIT = 200
    CACHE_TTL_SECONDS = 300.0
    TIMEFRAME_CONFIG: Dict[str, Dict[str, Any]] = {
        "day": {"window_days": 10, "reference_days": 1},
        "week": {"window_days": 28, "reference_days": 5},
        "month": {"window_days": 90, "reference_days": 21},
        "ytd": {"window_days": 400, "reference_days": None},
    }

    def __init__(
        self,
        *,
        baseline_symbol: str,
        symbol_loader: Callable[[], List[str]],
        metadata_sources: Sequence[Path],
        config: TradingSystemConfig | None = None,
    ) -> None:
        from main import build_strategy_weight_map, instantiate_strategies

        self.config = config or get_config()
        self.baseline_symbol = baseline_symbol
        self._symbol_loader = symbol_loader
        self._metadata_sources = list(metadata_sources)
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
        self._regime_analyzer = MarketRegimeAnalyzer(self.price_provider)

        self._symbols: Optional[List[str]] = None
        self._metadata: Optional[Dict[str, Dict[str, Optional[str]]]] = None
        self._cache: Dict[Tuple[str, int], Tuple[float, MomentumResponse]] = {}
        self._entries_cache: Dict[str, Tuple[float, List[MomentumEntry], int, int]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_momentum(self, timeframe: str, *, limit: int = 50) -> MomentumResponse:
        tf = (timeframe or "").strip().lower()
        if tf not in self.TIMEFRAME_CONFIG:
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Choose from day, week, month, ytd.")

        capped_limit = max(1, min(int(limit), self.MAX_LIMIT))
        cache_key = (tf, capped_limit)
        now = time.time()

        cached = self._cache.get(cache_key)
        if cached and now - cached[0] <= self.CACHE_TTL_SECONDS:
            return cached[1].model_copy(deep=True)

        entries, universe_size, skipped = self._gather_entries(tf)
        if not entries:
            raise RuntimeError("Failed to compute momentum for any symbols")

        sorted_entries = sorted(entries, key=lambda item: item.change_percent, reverse=True)
        top_gainers = sorted_entries[:capped_limit]

        losers_sorted = sorted(entries, key=lambda item: item.change_percent)
        negative_losers = [entry for entry in losers_sorted if entry.change_percent < 0]
        if negative_losers:
            top_losers = negative_losers[:capped_limit]
        else:
            top_losers = losers_sorted[:capped_limit]

        baseline_entry = next((entry for entry in entries if entry.symbol == self.baseline_symbol), None)

        response = MomentumResponse(
            timeframe=tf,
            generated_at=datetime.utcnow(),
            universe_size=universe_size,
            evaluated_symbols=len(entries),
            skipped_symbols=skipped,
            baseline_symbol=self.baseline_symbol if baseline_entry else None,
            baseline_change_percent=baseline_entry.change_percent if baseline_entry else None,
            baseline_last_price=baseline_entry.last_price if baseline_entry else None,
            top_gainers=top_gainers,
            top_losers=top_losers,
        )

        self._cache[cache_key] = (now, response)
        return response.model_copy(deep=True)

    def get_entries(self, timeframe: str = "week") -> List[MomentumEntry]:
        entries, _, _ = self._gather_entries((timeframe or "").strip().lower())
        return [entry.model_copy(deep=True) for entry in entries]

    def _gather_entries(self, timeframe: str) -> Tuple[List[MomentumEntry], int, int]:
        tf = (timeframe or "").strip().lower()
        if tf not in self.TIMEFRAME_CONFIG:
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Choose from day, week, month, ytd.")

        now = time.time()
        cached = self._entries_cache.get(tf)
        if cached and now - cached[0] <= self.CACHE_TTL_SECONDS:
            _, cached_entries, universe_size, skipped = cached
            return ([entry.model_copy(deep=True) for entry in cached_entries], universe_size, skipped)

        symbols = self._load_symbols()
        if not symbols:
            return [], 0, 0

        end_date = date.today()
        start_date = self._compute_start_date(end_date, tf)

        # Use optimized batch fetching and parallel processing
        entries, skipped = self._gather_entries_parallel(symbols, start_date, end_date, tf)

        cache_entries = [entry.model_copy(deep=True) for entry in entries]
        self._entries_cache[tf] = (now, cache_entries, len(symbols), skipped)
        return entries, len(symbols), skipped

    def _gather_entries_parallel(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        timeframe: str,
        max_workers: int = 8,
    ) -> Tuple[List[MomentumEntry], int]:
        """Gather momentum entries using batch price fetching and parallel processing."""
        entries: List[MomentumEntry] = []
        skipped = 0

        # Step 1: Batch fetch all price data at once
        LOGGER.info("Batch fetching prices for %d symbols", len(symbols))
        batch_result = self.price_provider.get_batch_price_history(
            symbols=symbols,
            start=start_date,
            end=end_date,
            interval="1d",
        )
        LOGGER.info(
            "Batch fetch complete: %d from cache, %d fetched, %d failed",
            batch_result.from_cache_count,
            batch_result.fetched_count,
            len(batch_result.failed),
        )

        # Track failed symbols
        skipped += len(batch_result.failed)

        # Pre-compute macro regime once (shared across all symbols)
        macro_snapshot = self._regime_analyzer.current()

        # Step 2: Process symbols in parallel using ThreadPoolExecutor
        symbols_with_data = list(batch_result.results.keys())

        def process_symbol(symbol: str) -> Optional[MomentumEntry]:
            """Process a single symbol using pre-fetched price data."""
            try:
                price_result = batch_result.results.get(symbol)
                if price_result is None or price_result.data.empty:
                    return None
                return self._evaluate_symbol_with_data(
                    symbol, price_result.data, start_date, end_date, timeframe, macro_snapshot
                )
            except Exception as exc:
                LOGGER.debug("Failed to process %s: %s", symbol, exc)
                return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(process_symbol, symbol): symbol
                for symbol in symbols_with_data
            }

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    entry = future.result()
                    if entry is not None:
                        entries.append(entry)
                    else:
                        skipped += 1
                except Exception as exc:
                    LOGGER.debug("Exception processing %s: %s", symbol, exc)
                    skipped += 1

        return entries, skipped

    def _evaluate_symbol_with_data(
        self,
        symbol: str,
        frame: pd.DataFrame,
        start_date: date,
        end_date: date,
        timeframe: str,
        macro_snapshot: MarketRegimeSnapshot,
    ) -> Optional[MomentumEntry]:
        """Evaluate a symbol using pre-fetched price data and pre-computed macro snapshot."""
        if frame.empty or "close" not in frame.columns:
            return None

        reference_price = self._select_reference_price(frame, timeframe)
        if reference_price is None or reference_price <= 0:
            return None

        enriched, fundamentals = self._prepare_enriched_frame(symbol, frame)
        strategy_scores, final_score, overlays = self._score_symbol_with_macro(
            symbol, enriched, fundamentals, macro_snapshot
        )

        latest_row = frame.iloc[-1]
        last_close = _safe_float(latest_row.get("close"))
        change_absolute = last_close - reference_price
        change_percent = (change_absolute / reference_price) * 100.0 if reference_price else 0.0

        volume = latest_row.get("volume")
        volume_value = _maybe_float(volume)
        average_volume = None
        relative_volume = None
        if "volume" in frame.columns:
            average_volume = _maybe_float(frame["volume"].tail(20).mean())
            if average_volume and average_volume > 0 and volume_value is not None:
                relative_volume = volume_value / average_volume

        metadata = self._load_metadata().get(symbol, {})

        return MomentumEntry(
            symbol=symbol,
            name=metadata.get("name") or symbol,
            sector=metadata.get("sector"),
            last_price=last_close,
            change_absolute=change_absolute,
            change_percent=change_percent,
            reference_price=reference_price,
            updated_at=_ensure_datetime(frame.index[-1]),
            volume=volume_value,
            average_volume=average_volume,
            relative_volume=relative_volume,
            data_points=len(frame.index),
            strategy_scores=strategy_scores,
            final_score=final_score,
            overlays=overlays,
        )

    def _score_symbol_with_macro(
        self,
        symbol: str,
        enriched: pd.DataFrame,
        fundamentals: Dict[str, Any],
        macro_snapshot: MarketRegimeSnapshot,
    ) -> Tuple[Dict[str, float], Optional[float], Dict[str, Optional[float]]]:
        """Score symbol using pre-computed macro snapshot to avoid redundant API calls."""
        scores: Dict[str, float] = {}
        collected: List[StrategySignal] = []

        for name in STRATEGY_ORDER:
            strategy = self._strategy_map.get(name)
            if strategy is None:
                continue
            try:
                signals = strategy.generate_signals(symbol, enriched)
            except Exception as exc:
                LOGGER.debug("Strategy %s failed for %s: %s", name, symbol, exc)
                signals = []
            if signals:
                latest_signal = signals[-1]
                scores[name] = float(latest_signal.confidence)
                collected.extend(signals)
            else:
                scores[name] = 0.0

        aggregated = list(self.aggregator.aggregate(collected))
        earnings_signal = compute_earnings_signal(fundamentals)
        overlays = {
            "macro_multiplier": macro_snapshot.multiplier,
            "earnings_multiplier": earnings_signal.multiplier(),
            "macro_score": macro_snapshot.score,
            "earnings_score": earnings_signal.score if earnings_signal.score is not None else None,
        }

        if not aggregated:
            return scores, None, overlays

        base_confidence = float(aggregated[-1].confidence)
        final_score = base_confidence * overlays["macro_multiplier"] * overlays["earnings_multiplier"]
        return scores, final_score, overlays

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_symbols(self) -> List[str]:
        if self._symbols is None:
            symbols = self._symbol_loader()
            self._symbols = [symbol.strip().upper() for symbol in symbols if symbol]
        return self._symbols

    def _load_metadata(self) -> Dict[str, Dict[str, Optional[str]]]:
        if self._metadata is not None:
            return self._metadata

        metadata: Dict[str, Dict[str, Optional[str]]] = {}
        for path in self._metadata_sources:
            if not path.exists():
                continue
            try:
                frame = pd.read_csv(path)
            except Exception:
                continue
            if "symbol" not in frame.columns:
                continue
            for _, row in frame.iterrows():
                symbol = str(row.get("symbol") or "").strip().upper()
                if not symbol:
                    continue
                name = str(row.get("name") or "").strip() or None
                sector = str(row.get("sector") or "").strip() or None
                metadata[symbol] = {
                    "name": name,
                    "sector": sector,
                }
        self._metadata = metadata
        return metadata

    def _compute_start_date(self, end_date: date, timeframe: str) -> date:
        config = self.TIMEFRAME_CONFIG[timeframe]
        if timeframe == "ytd":
            return date(end_date.year, 1, 1)
        window_days = max(int(config["window_days"]), 1)
        return end_date - timedelta(days=window_days)

    def _evaluate_symbol(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        timeframe: str,
    ) -> Optional[MomentumEntry]:
        try:
            result = self.price_provider.get_price_history(
                PriceRequest(symbol=symbol, start=start_date, end=end_date, interval="1d")
            )
        except Exception as exc:
            LOGGER.debug("Price download failed for %s: %s", symbol, exc)
            return None

        frame = result.data
        if frame.empty or "close" not in frame.columns:
            return None

        reference_price = self._select_reference_price(frame, timeframe)
        if reference_price is None or reference_price <= 0:
            return None

        enriched, fundamentals = self._prepare_enriched_frame(symbol, frame)
        strategy_scores, final_score, overlays = self._score_symbol(symbol, enriched, fundamentals)

        latest_row = frame.iloc[-1]
        last_close = _safe_float(latest_row.get("close"))
        change_absolute = last_close - reference_price
        change_percent = (change_absolute / reference_price) * 100.0 if reference_price else 0.0

        volume = latest_row.get("volume")
        volume_value = _maybe_float(volume)
        average_volume = None
        relative_volume = None
        if "volume" in frame.columns:
            average_volume = _maybe_float(frame["volume"].tail(20).mean())
            if average_volume and average_volume > 0 and volume_value is not None:
                relative_volume = volume_value / average_volume

        metadata = self._load_metadata().get(symbol, {})

        return MomentumEntry(
            symbol=symbol,
            name=metadata.get("name") or symbol,
            sector=metadata.get("sector"),
            last_price=last_close,
            change_absolute=change_absolute,
            change_percent=change_percent,
            reference_price=reference_price,
            updated_at=_ensure_datetime(frame.index[-1]),
            volume=volume_value,
            average_volume=average_volume,
            relative_volume=relative_volume,
            data_points=len(frame.index),
            strategy_scores=strategy_scores,
            final_score=final_score,
            overlays=overlays,
        )

    def _prepare_enriched_frame(self, symbol: str, frame: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        fundamentals: Dict[str, Any] = {}
        try:
            fundamentals = load_fundamental_metrics(
                symbol,
                base_dir=self.config.storage.universe_dir,
                api_key=self.config.data_sources.alpha_vantage_key,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.debug("Fundamentals lookup failed for %s: %s", symbol, exc)

        enriched = enrich_price_frame(symbol, frame, fundamentals=fundamentals)
        return _ensure_additional_indicators(self._strategy_map, enriched), fundamentals

    def _score_symbol(
        self,
        symbol: str,
        enriched: pd.DataFrame,
        fundamentals: Dict[str, Any],
    ) -> Tuple[Dict[str, float], Optional[float], Dict[str, Optional[float]]]:
        scores: Dict[str, float] = {}
        collected: List[StrategySignal] = []

        for name in STRATEGY_ORDER:
            strategy = self._strategy_map.get(name)
            if strategy is None:
                continue
            try:
                signals = strategy.generate_signals(symbol, enriched)
            except Exception as exc:  # pragma: no cover - defensive logging
                LOGGER.debug("Strategy %s failed for %s: %s", name, symbol, exc)
                signals = []
            if signals:
                latest_signal = signals[-1]
                scores[name] = float(latest_signal.confidence)
                collected.extend(signals)
            else:
                scores[name] = 0.0

        aggregated = list(self.aggregator.aggregate(collected))
        macro_snapshot = self._regime_analyzer.current()
        earnings_signal = compute_earnings_signal(fundamentals)
        overlays = {
            "macro_multiplier": macro_snapshot.multiplier,
            "earnings_multiplier": earnings_signal.multiplier(),
            "macro_score": macro_snapshot.score,
            "earnings_score": earnings_signal.score if earnings_signal.score is not None else None,
        }

        if not aggregated:
            return scores, None, overlays

        base_confidence = float(aggregated[-1].confidence)
        final_score = base_confidence * overlays["macro_multiplier"] * overlays["earnings_multiplier"]
        return scores, final_score, overlays

    def _select_reference_price(self, frame: pd.DataFrame, timeframe: str) -> Optional[float]:
        if frame.empty:
            return None

        config = self.TIMEFRAME_CONFIG[timeframe]
        last_index = frame.index[-1]

        if timeframe == "day":
            if len(frame.index) < 2:
                return None
            return _safe_float(frame.iloc[-2].get("close"))

        if timeframe == "week":
            target = last_index - timedelta(days=7)
            subset = frame.loc[frame.index <= target]
        elif timeframe == "month":
            target = last_index - timedelta(days=31)
            subset = frame.loc[frame.index <= target]
        elif timeframe == "ytd":
            year_start = datetime(last_index.year, 1, 1)
            subset = frame.loc[frame.index >= year_start]
            if not subset.empty:
                return _safe_float(subset.iloc[0].get("close"))
            subset = frame
        else:
            reference_days = config.get("reference_days")
            if not reference_days:
                return None
            target = last_index - timedelta(days=int(reference_days))
            subset = frame.loc[frame.index <= target]

        if subset.empty:
            if len(frame.index) < 2:
                return None
            subset = frame.iloc[[0]]
        return _safe_float(subset.iloc[-1].get("close"))


class RussellMomentumService(BaseMomentumService):
    """Momentum metrics for Russell 2000 constituents."""

    def __init__(self, config: TradingSystemConfig | None = None) -> None:
        config_obj = config or get_config()
        universe_dir = config_obj.storage.universe_dir
        super().__init__(
            baseline_symbol="IWM",
            symbol_loader=load_russell_2000_candidates,
            metadata_sources=[
                universe_dir / "seed_candidates.csv",
                universe_dir / "yahoo_small_caps.csv",
                universe_dir / "russell_2000.csv",
                universe_dir / "sector_metadata.csv",
            ],
            config=config_obj,
        )


class SPMomentumService(BaseMomentumService):
    """Momentum metrics for S&P 500 constituents."""

    def __init__(self, config: TradingSystemConfig | None = None) -> None:
        config_obj = config or get_config()
        universe_dir = config_obj.storage.universe_dir
        super().__init__(
            baseline_symbol="SPY",
            symbol_loader=load_sp500_candidates,
            metadata_sources=[
                universe_dir / "seed_candidates.csv",
                universe_dir / "sp500.csv",
                universe_dir / "sector_metadata.csv",
            ],
            config=config_obj,
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


def _ensure_additional_indicators(strategy_map: Dict[str, Strategy], frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    enriched = frame.copy()
    trend = strategy_map.get("trend_following")
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



class MomentumAnalyticsService:
    """Higher-level momentum analytics helpers (sector averages, etc.)."""

    def __init__(self, russell_service: RussellMomentumService, sp_service: SPMomentumService) -> None:
        self._services: List[Tuple[str, BaseMomentumService]] = [
            ("russell", russell_service),
            ("sp500", sp_service),
        ]

    def get_sector_scores(self, symbol: str, timeframe: str = "week") -> SectorScoreResponse:
        symbol_clean = (symbol or "").strip().upper()
        if not symbol_clean:
            raise ValueError("Symbol must not be empty")

        target_sector: Optional[str] = None
        target_universe: Optional[str] = None
        symbol_entry: Optional[MomentumEntry] = None
        universe_cache: Dict[str, List[MomentumEntry]] = {}

        for universe, service in self._services:
            try:
                entries = service.get_entries(timeframe)
            except ValueError:
                continue
            universe_cache[universe] = entries
            match = next((entry for entry in entries if entry.symbol.upper() == symbol_clean), None)
            if match and symbol_entry is None:
                symbol_entry = match
                target_sector = match.sector
                target_universe = universe

        if symbol_entry is None:
            raise ValueError("Symbol not found in tracked universes")

        if not target_sector:
            return SectorScoreResponse(
                symbol=symbol_clean,
                sector=None,
                universe=target_universe,
                timeframe=timeframe,
                sample_size=0,
                strategy_scores=[],
            )

        primary_entries = [
            entry
            for entry in universe_cache.get(target_universe or "", [])
            if entry.sector == target_sector
        ]

        if not primary_entries:
            return SectorScoreResponse(
                symbol=symbol_clean,
                sector=target_sector,
                universe=target_universe,
                timeframe=timeframe,
                sample_size=0,
                strategy_scores=[],
            )

        aggregated: Dict[str, List[float]] = {}
        for entry in primary_entries:
            for strategy_name, score in entry.strategy_scores.items():
                aggregated.setdefault(strategy_name, []).append(score)

        strategy_scores = [
            SectorStrategyScore(
                strategy=name,
                average_score=sum(values) / len(values),
                sample_size=len(values),
            )
            for name, values in aggregated.items()
            if values
        ]

        return SectorScoreResponse(
            symbol=symbol_clean,
            sector=target_sector,
            universe=target_universe,
            timeframe=timeframe,
            sample_size=len(primary_entries),
            strategy_scores=strategy_scores,
        )


__all__ = ["SignalService", "RussellMomentumService", "SPMomentumService", "MomentumAnalyticsService", "RateLimitError"]

