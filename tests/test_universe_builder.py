from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from trading_system.config_manager import ConfigManager, TradingSystemConfig
from universe.builder import SymbolSnapshot, UniverseBuilder


class DummyTicker:
    def __init__(self, symbol: str, data_map: dict[str, dict[str, dict[str, float | str | None]]]):
        self.symbol = symbol
        self._data_map = data_map

    @property
    def fast_info(self) -> dict[str, float | str | None]:
        return self._data_map[self.symbol]["fast"]

    def get_info(self) -> dict[str, float | str | None]:
        return self._data_map[self.symbol]["info"]


@pytest.fixture()
def config_with_tmp_storage() -> TradingSystemConfig:
    config = ConfigManager().load(force_reload=True)
    with TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        storage = replace(
            config.storage,
            price_cache_dir=base / "prices",
            universe_dir=base / "universe",
            signal_dir=base / "signals",
            portfolio_dir=base / "portfolio",
        )
        yield replace(config, storage=storage)


def test_builder_filters_symbols(config_with_tmp_storage):
    config = config_with_tmp_storage

    data_map = {
        "GOOD": {
            "fast": {
                "market_cap": 1_200_000_000,
                "last_price": 12.0,
                "ten_day_average_volume": 150_000,
                "shares_float": 20_000_000,
                "bid": 11.9,
                "ask": 12.1,
            },
            "info": {
                "sector": "Technology",
                "exchange": "NASDAQ",
                "shortName": "Good Tech",
            },
        },
        "SMALL": {
            "fast": {
                "market_cap": 10_000_000,
                "last_price": 4.0,
                "ten_day_average_volume": 50_000,
                "shares_float": 5_000_000,
                "bid": 3.9,
                "ask": 4.1,
            },
            "info": {
                "sector": "Technology",
                "exchange": "NASDAQ",
                "shortName": "Small Co",
            },
        },
    }

    def factory(symbol: str) -> DummyTicker:
        if symbol not in data_map:
            raise KeyError(symbol)
        return DummyTicker(symbol, data_map)

    builder = UniverseBuilder(
        config,
        cache_dir=config.storage.universe_dir / "cache",
        cache_ttl_days=0,
        ticker_factory=factory,
    )

    result = builder.build_universe(["GOOD", "SMALL"], persist=False)

    assert builder.last_snapshot_path() is None
    assert list(result["symbol"]) == ["GOOD"]
    row = result.iloc[0]
    assert pytest.approx(row["market_cap"], rel=1e-6) == 1_200_000_000
    assert row["sector"] == "Technology"


def test_builder_uses_cache_round_trip(config_with_tmp_storage):
    config = config_with_tmp_storage
    cache_dir = config.storage.universe_dir / "cache"

    snapshot = SymbolSnapshot(
        symbol="CACHE",
        name="Cached Corp",
        sector="Energy",
        exchange="NYSE",
        market_cap=800_000_000,
        last_price=20.0,
        average_volume=80_000,
        dollar_volume=1_600_000,
        float_shares=15_000_000,
        bid_ask_spread=0.02,
        fetched_at=datetime.utcnow(),
    )

    cache_dir.mkdir(parents=True, exist_ok=True)
    builder = UniverseBuilder(
        config,
        cache_dir=cache_dir,
        cache_ttl_days=10,
        ticker_factory=lambda symbol: None,
    )

    builder._write_cache(snapshot)  # type: ignore[attr-defined]
    result = builder.build_universe(["CACHE"], persist=False)

    assert builder.last_snapshot_path() is None
    assert list(result["symbol"]) == ["CACHE"]


def test_builder_records_skipped_symbols(config_with_tmp_storage):
    config = config_with_tmp_storage

    data_map = {
        "GOOD": {
            "fast": {
                "market_cap": 200_000_000,
                "last_price": 15.0,
                "ten_day_average_volume": 200_000,
                "shares_float": 25_000_000,
                "bid": 14.9,
                "ask": 15.1,
            },
            "info": {
                "sector": "Technology",
                "exchange": "NASDAQ",
                "shortName": "Good Co",
            },
        },
        "MISS": {
            "fast": {
                "market_cap": None,
                "last_price": None,
                "ten_day_average_volume": None,
                "shares_float": None,
                "bid": None,
                "ask": None,
            },
            "info": {},
        },
    }

    def factory(symbol: str):
        return DummyTicker(symbol, data_map)

    builder = UniverseBuilder(
        config,
        cache_dir=config.storage.universe_dir / "cache",
        cache_ttl_days=0,
        ticker_factory=factory,
    )

    result = builder.build_universe(["GOOD", "MISS"], persist=False)

    assert builder.last_snapshot_path() is None
    assert list(result["symbol"]) == ["GOOD"]
    assert builder.last_skipped_symbols() == ["MISS"]

def test_builder_tracks_snapshot_path(config_with_tmp_storage):
    config = config_with_tmp_storage

    data_map = {
        "GOOD": {
            "fast": {
                "market_cap": 1_200_000_000,
                "last_price": 12.0,
                "ten_day_average_volume": 150_000,
                "shares_float": 20_000_000,
                "bid": 11.9,
                "ask": 12.1,
            },
            "info": {
                "sector": "Technology",
                "exchange": "NASDAQ",
                "shortName": "Good Tech",
            },
        }
    }

    def factory(symbol: str) -> DummyTicker:
        if symbol not in data_map:
            raise KeyError(symbol)
        return DummyTicker(symbol, data_map)

    builder = UniverseBuilder(
        config,
        cache_dir=config.storage.universe_dir / "cache",
        cache_ttl_days=0,
        ticker_factory=factory,
    )

    result = builder.build_universe(["GOOD"], persist=True)

    snapshot_path = builder.last_snapshot_path()
    assert snapshot_path is not None
    assert snapshot_path.exists()
    assert "GOOD" in snapshot_path.read_text()
    assert list(result["symbol"]) == ["GOOD"]
