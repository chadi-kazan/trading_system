from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from data_providers.base import PriceRequest
from data_providers.yahoo import YahooPriceProvider


def _make_frame(start: date, periods: int) -> pd.DataFrame:
    rng = pd.date_range(start=start, periods=periods, freq="D", name="date")
    return pd.DataFrame(
        {
            "open": 1.0,
            "high": 1.1,
            "low": 0.9,
            "close": 1.0,
            "adj_close": 1.0,
            "volume": 1000,
        },
        index=rng,
    )


def test_get_price_history_reads_valid_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = YahooPriceProvider(cache_dir=tmp_path, cache_ttl_days=30)
    request = PriceRequest(symbol="TEST", start=date(2024, 1, 1), end=date(2024, 1, 5))

    cache_path = provider._cache_path(request.symbol, request.interval)  # type: ignore[attr-defined]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame = _make_frame(date(2023, 12, 20), periods=30)
    frame.to_csv(cache_path, index=True)

    called = {"value": False}

    def fake_download(self, req):  # pragma: no cover - should not run
        called["value"] = True
        return _make_frame(date(2024, 1, 1), periods=5)

    monkeypatch.setattr(YahooPriceProvider, "_download_with_retry", fake_download)

    result = provider.get_price_history(request)

    assert not called["value"]
    assert result.from_cache is True
    assert len(result.data) == 5


def test_get_price_history_refreshes_when_cache_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = YahooPriceProvider(cache_dir=tmp_path, cache_ttl_days=30)
    request = PriceRequest(symbol="TEST", start=date(2024, 1, 1), end=date(2024, 1, 15))

    cache_path = provider._cache_path(request.symbol, request.interval)  # type: ignore[attr-defined]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    stale_frame = _make_frame(date(2024, 1, 1), periods=3)
    stale_frame.to_csv(cache_path, index=True)

    def fake_download(self, req):
        fresh = _make_frame(date(2024, 1, 1), periods=20)
        return fresh

    monkeypatch.setattr(YahooPriceProvider, "_download_with_retry", fake_download)

    result = provider.get_price_history(request)

    assert result.from_cache is False
    assert len(result.data) == 15
    # cache rewritten with fresh data
    reloaded = pd.read_csv(cache_path, parse_dates=["date"], index_col="date")
    assert len(reloaded) == 20
