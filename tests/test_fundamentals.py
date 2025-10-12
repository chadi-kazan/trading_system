from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_pipeline import fundamentals
from data_pipeline.fundamentals import load_fundamental_metrics
from analytics import compute_earnings_signal


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


def test_map_earnings_metrics_builds_scores():
    payload = {
        "quarterlyEarnings": [
            {"reportedEPS": "1.20", "estimatedEPS": "1.00"},
            {"reportedEPS": "1.05", "estimatedEPS": "0.98"},
            {"reportedEPS": "0.90", "estimatedEPS": "1.02"},
            {"reportedEPS": "0.85", "estimatedEPS": "0.80"},
        ]
    }
    metrics = fundamentals._map_earnings_metrics(payload)
    assert "earnings_surprise_avg" in metrics
    assert "earnings_positive_ratio" in metrics
    assert "earnings_signal_score" in metrics
    assert metrics["earnings_positive_ratio"] == pytest.approx(0.75)
    assert 0 <= metrics["earnings_signal_score"] <= 1


def test_compute_earnings_signal_from_metrics():
    fundamentals_payload = {
        "earnings_surprise_avg": 0.08,
        "earnings_positive_ratio": 0.75,
        "earnings_eps_trend": 0.12,
    }
    signal = compute_earnings_signal(fundamentals_payload)
    assert signal.score is not None
    assert signal.multiplier() > 0.5
    metadata = signal.to_metadata()
    assert metadata["confidence_multiplier"] == signal.multiplier()
