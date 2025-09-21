"""Universe builder that screens small-cap growth equities using Yahoo Finance data."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd
import yfinance as yf

from trading_system.config_manager import TradingSystemConfig, UniverseCriteriaConfig

LOGGER = logging.getLogger(__name__)


@dataclass
class SymbolSnapshot:
    """Lightweight container for per-symbol fundamentals required by the screen."""

    symbol: str
    name: str | None
    sector: str | None
    exchange: str | None
    market_cap: float | None
    last_price: float | None
    average_volume: float | None
    dollar_volume: float | None
    float_shares: float | None
    bid_ask_spread: float | None
    fetched_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "exchange": self.exchange,
            "market_cap": self.market_cap,
            "last_price": self.last_price,
            "average_volume": self.average_volume,
            "dollar_volume": self.dollar_volume,
            "float_shares": self.float_shares,
            "bid_ask_spread": self.bid_ask_spread,
            "fetched_at": self.fetched_at.isoformat(),
        }


class UniverseBuilder:
    """Constructs a screened trading universe from Yahoo Finance fundamentals."""

    def __init__(
        self,
        config: TradingSystemConfig,
        cache_dir: Path | None = None,
        cache_ttl_days: int | None = None,
    ) -> None:
        self.config = config
        self.criteria: UniverseCriteriaConfig = config.universe_criteria
        self.cache_dir = cache_dir or (config.storage.universe_dir / "fundamentals_cache")
        self.cache_ttl_days = cache_ttl_days if cache_ttl_days is not None else config.data_sources.cache_days
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.universe_dir = config.storage.universe_dir
        self.universe_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build_universe(
        self,
        symbols: Iterable[str],
        as_of: date | None = None,
        persist: bool = True,
    ) -> pd.DataFrame:
        """Fetch fundamentals, apply screening filters, and return qualifying symbols."""

        as_of = as_of or date.today()
        snapshots: List[SymbolSnapshot] = []
        for raw_symbol in symbols:
            symbol = raw_symbol.strip().upper()
            if not symbol:
                continue
            try:
                snapshot = self._get_snapshot(symbol)
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.warning("Skipping %s due to fetch error: %s", symbol, exc)
                continue
            if snapshot is None:
                continue
            snapshots.append(snapshot)

        frame = pd.DataFrame(snapshot.to_dict() for snapshot in snapshots)
        if frame.empty:
            LOGGER.warning("No valid symbols found for universe build")
            return frame

        screened = self._apply_filters(frame)
        screened = screened.sort_values("market_cap", ascending=True).reset_index(drop=True)
        screened["as_of"] = pd.Timestamp(as_of)

        if persist and not screened.empty:
            filename = self._universe_filename(as_of)
            screened.to_csv(filename, index=False)
            LOGGER.info("Universe snapshot saved to %s", filename)

        return screened

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _universe_filename(self, as_of: date) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return self.universe_dir / f"universe_{as_of.isoformat()}_{timestamp}.csv"

    def _get_snapshot(self, symbol: str) -> SymbolSnapshot | None:
        cached = self._read_cache(symbol)
        if cached is not None:
            return cached

        snapshot = self._fetch_symbol_data(symbol)
        if snapshot is not None:
            self._write_cache(snapshot)
        return snapshot

    def _fetch_symbol_data(self, symbol: str) -> SymbolSnapshot | None:
        ticker = yf.Ticker(symbol)
        try:
            fast_info = ticker.fast_info
            fast_dict = dict(fast_info) if fast_info is not None else {}
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.debug("fast_info unavailable for %s: %s", symbol, exc)
            fast_dict = {}

        try:
            info = ticker.get_info()
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.debug("info unavailable for %s: %s", symbol, exc)
            info = {}

        market_cap = self._first_available(
            fast_dict.get("market_cap"),
            info.get("marketCap"),
        )
        last_price = self._first_available(
            fast_dict.get("last_price"),
            fast_dict.get("regular_market_price"),
            info.get("regularMarketPrice"),
        )
        average_volume = self._first_available(
            fast_dict.get("ten_day_average_volume"),
            fast_dict.get("fifty_two_week_average_volume"),
            info.get("averageDailyVolume3Month"),
            info.get("averageVolume"),
        )
        float_shares = self._first_available(
            fast_dict.get("shares_float"),
            info.get("floatShares"),
        )
        bid = self._first_available(fast_dict.get("bid"), info.get("bid"))
        ask = self._first_available(fast_dict.get("ask"), info.get("ask"))
        spread = None
        if bid and ask and bid > 0 and ask > 0:
            mid = (bid + ask) / 2
            if mid > 0:
                spread = (ask - bid) / mid

        if average_volume and last_price:
            dollar_volume = average_volume * last_price
        else:
            dollar_volume = None

        if market_cap is None or dollar_volume is None:
            return None

        snapshot = SymbolSnapshot(
            symbol=symbol,
            name=info.get("shortName") or info.get("longName"),
            sector=info.get("sector"),
            exchange=info.get("exchange") or info.get("fullExchangeName"),
            market_cap=float(market_cap) if market_cap is not None else None,
            last_price=float(last_price) if last_price is not None else None,
            average_volume=float(average_volume) if average_volume is not None else None,
            dollar_volume=float(dollar_volume) if dollar_volume is not None else None,
            float_shares=float(float_shares) if float_shares is not None else None,
            bid_ask_spread=float(spread) if spread is not None else None,
            fetched_at=datetime.utcnow(),
        )
        return snapshot

    def _apply_filters(self, frame: pd.DataFrame) -> pd.DataFrame:
        criteria = self.criteria
        filtered = frame.dropna(subset=["market_cap", "dollar_volume"])

        filtered = filtered[
            (filtered["market_cap"] >= criteria.market_cap_min)
            & (filtered["market_cap"] <= criteria.market_cap_max)
        ]

        filtered = filtered[filtered["dollar_volume"] >= criteria.min_daily_volume]

        if criteria.min_float > 0:
            filtered = filtered[filtered["float_shares"].fillna(0) >= criteria.min_float]

        if criteria.max_spread > 0:
            filtered = filtered[filtered["bid_ask_spread"].fillna(0) <= criteria.max_spread]

        if criteria.target_sectors:
            allowed = {sector.lower() for sector in criteria.target_sectors}
            filtered = filtered[
                filtered["sector"].fillna("none").str.lower().isin(allowed)
            ]

        if criteria.exchange_whitelist:
            allowed_exchanges = {exchange.lower() for exchange in criteria.exchange_whitelist}
            filtered = filtered[
                filtered["exchange"].fillna("none").str.lower().isin(allowed_exchanges)
            ]

        return filtered

    def _read_cache(self, symbol: str) -> SymbolSnapshot | None:
        path = self.cache_dir / f"{symbol}.json"
        if not path.exists():
            return None

        if self.cache_ttl_days > 0:
            last_modified = datetime.fromtimestamp(path.stat().st_mtime)
            if datetime.utcnow() - last_modified > timedelta(days=self.cache_ttl_days):
                return None

        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            return None

        data = payload.get("data")
        fetched_at = payload.get("fetched_at")
        if not data or not fetched_at:
            return None

        return SymbolSnapshot(
            symbol=data.get("symbol", symbol),
            name=data.get("name"),
            sector=data.get("sector"),
            exchange=data.get("exchange"),
            market_cap=data.get("market_cap"),
            last_price=data.get("last_price"),
            average_volume=data.get("average_volume"),
            dollar_volume=data.get("dollar_volume"),
            float_shares=data.get("float_shares"),
            bid_ask_spread=data.get("bid_ask_spread"),
            fetched_at=datetime.fromisoformat(fetched_at),
        )

    def _write_cache(self, snapshot: SymbolSnapshot) -> None:
        path = self.cache_dir / f"{snapshot.symbol}.json"
        payload = {
            "fetched_at": snapshot.fetched_at.isoformat(),
            "data": snapshot.to_dict(),
        }
        path.write_text(json.dumps(payload))

    @staticmethod
    def _first_available(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None


__all__ = ["UniverseBuilder"]
