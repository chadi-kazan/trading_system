"""Service layer that powers the dashboard API."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from data_pipeline import enrich_price_frame, load_fundamental_metrics
from data_pipeline.alpha_vantage_client import AlphaVantageClient, AlphaVantageError
from data_providers.base import PriceRequest
from data_providers.yahoo import YahooPriceProvider
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

        self._symbols: Optional[List[str]] = None
        self._metadata: Optional[Dict[str, Dict[str, Optional[str]]]] = None
        self._cache: Dict[Tuple[str, int], Tuple[float, MomentumResponse]] = {}

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

        symbols = self._load_symbols()
        if not symbols:
            raise RuntimeError("No symbols available for analysis")

        end_date = date.today()
        start_date = self._compute_start_date(end_date, tf)

        entries: List[MomentumEntry] = []
        skipped = 0

        for symbol in symbols:
            entry = self._evaluate_symbol(symbol, start_date, end_date, tf)
            if entry is None:
                skipped += 1
                continue
            entries.append(entry)

        if not entries:
            raise RuntimeError("Failed to compute momentum for any symbols")

        entries.sort(key=lambda item: item.change_percent, reverse=True)
        top_gainers = entries[:capped_limit]

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
            universe_size=len(symbols),
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

        enriched = self._prepare_enriched_frame(symbol, frame)
        strategy_scores, final_score = self._score_symbol(symbol, enriched)

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
        )

    def _prepare_enriched_frame(self, symbol: str, frame: pd.DataFrame) -> pd.DataFrame:
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
        return _ensure_additional_indicators(self._strategy_map, enriched)

    def _score_symbol(self, symbol: str, enriched: pd.DataFrame) -> Tuple[Dict[str, float], Optional[float]]:
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
        final_score = float(aggregated[-1].confidence) if aggregated else None
        return scores, final_score

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


__all__ = ["SignalService", "RussellMomentumService", "SPMomentumService", "RateLimitError"]


