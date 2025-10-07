from __future__ import annotations

from datetime import datetime, timezone
import sys
import types

if "main" not in sys.modules:
    stub_main = types.ModuleType("main")

    def _build_strategy_weight_map(_config):
        return {}

    def _instantiate_strategies(*_args, **_kwargs):
        return []

    stub_main.build_strategy_weight_map = _build_strategy_weight_map
    stub_main.instantiate_strategies = _instantiate_strategies
    sys.modules["main"] = stub_main

from fastapi.testclient import TestClient

from dashboard_api.app import app
from dashboard_api.dependencies import get_russell_momentum_service
from dashboard_api.schemas import RussellMomentumEntry, RussellMomentumResponse


class DummyRussellService:
    def get_momentum(self, timeframe: str, limit: int = 50) -> RussellMomentumResponse:
        now = datetime.now(timezone.utc)
        return RussellMomentumResponse(
            timeframe=timeframe,
            generated_at=now,
            universe_size=2000,
            evaluated_symbols=2,
            skipped_symbols=0,
            baseline_symbol="IWM",
            baseline_change_percent=1.23,
            baseline_last_price=202.45,
            top_gainers=[
                RussellMomentumEntry(
                    symbol="ABC",
                    name="ABC Corp",
                    sector="Technology",
                    last_price=12.34,
                    change_absolute=1.11,
                    change_percent=9.88,
                    reference_price=11.23,
                    updated_at=now,
                    volume=1_200_000,
                    average_volume=1_000_000,
                    relative_volume=1.2,
                    data_points=25,
                )
            ],
            top_losers=[
                RussellMomentumEntry(
                    symbol="XYZ",
                    name="XYZ Industries",
                    sector="Industrials",
                    last_price=8.5,
                    change_absolute=-1.0,
                    change_percent=-10.53,
                    reference_price=9.5,
                    updated_at=now,
                    volume=950_000,
                    average_volume=1_100_000,
                    relative_volume=0.86,
                    data_points=25,
                )
            ],
        )


class FailingRussellService:
    def get_momentum(self, timeframe: str, limit: int = 50) -> RussellMomentumResponse:
        raise RuntimeError("service offline")


def test_russell_momentum_endpoint_returns_payload() -> None:
    app.dependency_overrides[get_russell_momentum_service] = lambda: DummyRussellService()
    client = TestClient(app)

    response = client.get("/api/russell/momentum?timeframe=week&limit=5")

    app.dependency_overrides.pop(get_russell_momentum_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["timeframe"] == "week"
    assert data["baseline_symbol"] == "IWM"
    assert len(data["top_gainers"]) == 1
    assert len(data["top_losers"]) == 1
    assert data["top_gainers"][0]["symbol"] == "ABC"
    assert data["top_losers"][0]["symbol"] == "XYZ"


def test_russell_momentum_endpoint_handles_service_error() -> None:
    app.dependency_overrides[get_russell_momentum_service] = lambda: FailingRussellService()
    client = TestClient(app)

    response = client.get("/api/russell/momentum?timeframe=month")

    app.dependency_overrides.pop(get_russell_momentum_service, None)

    assert response.status_code == 503
    assert "service offline" in response.json()["detail"]
