from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_pipeline import fundamentals
from data_pipeline.fundamentals import load_fundamental_metrics


def test_load_fundamental_metrics_from_json(tmp_path: Path):
    fundamentals_dir = tmp_path / "fundamentals"
    fundamentals_dir.mkdir(parents=True, exist_ok=True)
    (fundamentals_dir / "TEST.json").write_text('{"data": {"earnings_growth": "0.25", "relative_strength": 0.9}}')

    metrics = load_fundamental_metrics("test", tmp_path)
    assert metrics == {"earnings_growth": 0.25, "relative_strength": 0.9}


def test_load_fundamental_metrics_from_csv(tmp_path: Path):
    df = pd.DataFrame(
        {
            "symbol": ["ABC", "XYZ"],
            "earnings_growth": [0.1, 0.2],
            "relative_strength": [0.3, 0.4],
        }
    )
    df.to_csv(tmp_path / "fundamentals.csv", index=False)

    metrics = load_fundamental_metrics("xyz", tmp_path)
    assert metrics == {"earnings_growth": 0.2, "relative_strength": 0.4}


def test_load_fundamental_metrics_alpha_vantage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class DummyClient:
        def __init__(self, api_key: str) -> None:  # pragma: no cover - simple init
            self.api_key = api_key

        def fetch_company_overview(self, symbol: str):
            return {
                "QuarterlyEarningsGrowthYOY": "0.35",
                "52WeekHigh": "120",
                "52WeekLow": "80",
                "50DayMovingAverage": "100",
                "MarketCapitalization": "123456789",
            }

    monkeypatch.setattr(fundamentals, "AlphaVantageClient", DummyClient)

    metrics = load_fundamental_metrics("abc", tmp_path, api_key="demo")

    assert metrics["earnings_growth"] == 0.35
    assert metrics["relative_strength"] == pytest.approx(0.5)
    assert metrics["market_cap"] == 123456789.0


def test_alpha_vantage_client_retries(monkeypatch):
    from data_pipeline.alpha_vantage_client import AlphaVantageClient

    class DummyResponse:
        def __init__(self, payload, status=200):
            self._payload = payload
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError('http error')

        def json(self):
            return self._payload

    class DummySession:
        def __init__(self):
            self.calls = 0

        def get(self, url, params, timeout):
            self.calls += 1
            if self.calls == 1:
                return DummyResponse({'Note': 'Please slow down'})
            return DummyResponse({'QuarterlyEarningsGrowthYOY': '0.2'})

    sleeps: list[float] = []
    monkeypatch.setattr('time.sleep', lambda seconds: sleeps.append(seconds))

    client = AlphaVantageClient('demo', session=DummySession(), max_retries=2, backoff_seconds=0, rate_limit_sleep=0.5)
    data = client.fetch_company_overview('ABC')

    assert data['QuarterlyEarningsGrowthYOY'] == '0.2'
    assert sleeps and pytest.approx(sleeps[0], rel=1e-6) == 0.5

def test_alpha_vantage_client_handles_http_rate_limit(monkeypatch):
    import requests
    from data_pipeline.alpha_vantage_client import AlphaVantageClient

    sleeps: list[float] = []
    monkeypatch.setattr('time.sleep', lambda seconds: sleeps.append(seconds))

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict[str, str] | None = None, headers: dict[str, str] | None = None):
            self.status_code = status_code
            self._payload = payload or {}
            self.headers = headers or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError('rate limited')
                error.response = self
                raise error

        def json(self):
            return self._payload

    class DummySession:
        def __init__(self):
            self.calls = 0

        def get(self, url, params, timeout):  # pragma: no cover - simple shim
            self.calls += 1
            if self.calls == 1:
                return DummyResponse(429, headers={'Retry-After': '2'})
            return DummyResponse(200, payload={'QuarterlyEarningsGrowthYOY': '0.3'})

    client = AlphaVantageClient('demo', session=DummySession(), max_retries=2, backoff_seconds=0, rate_limit_sleep=1)
    data = client.fetch_company_overview('ABC')

    assert data['QuarterlyEarningsGrowthYOY'] == '0.3'
    assert sleeps and pytest.approx(sleeps[0], rel=1e-6) == 2.0
