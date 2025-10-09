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
from dashboard_api.dependencies import get_russell_momentum_service, get_sp_momentum_service
from dashboard_api.schemas import MomentumEntry, MomentumResponse


class DummyRussellService:
    def get_momentum(self, timeframe: str, limit: int = 50) -> MomentumResponse:
        now = datetime.now(timezone.utc)
        return MomentumResponse(
            timeframe=timeframe,
            generated_at=now,
            universe_size=2000,
            evaluated_symbols=2,
            skipped_symbols=0,
            baseline_symbol="IWM",
            baseline_change_percent=1.23,
            baseline_last_price=202.45,
            top_gainers=[
                MomentumEntry(
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
                    strategy_scores={"dan_zanger_cup_handle": 0.6, "can_slim": 0.72},
                    final_score=0.65,
                )
            ],
            top_losers=[
                MomentumEntry(
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
                    strategy_scores={"dan_zanger_cup_handle": 0.2, "can_slim": 0.4},
                    final_score=0.35,
                )
            ],
        )


class FailingRussellService:
    def get_momentum(self, timeframe: str, limit: int = 50) -> MomentumResponse:
        raise RuntimeError("service offline")


class DummySPService:
    def get_momentum(self, timeframe: str, limit: int = 50) -> MomentumResponse:
        now = datetime.now(timezone.utc)
        return MomentumResponse(
            timeframe=timeframe,
            generated_at=now,
            universe_size=500,
            evaluated_symbols=1,
            skipped_symbols=0,
            baseline_symbol="SPY",
            baseline_change_percent=0.87,
            baseline_last_price=428.12,
            top_gainers=[
                MomentumEntry(
                    symbol="MSFT",
                    name="Microsoft Corporation",
                    sector="Technology",
                    last_price=320.12,
                    change_absolute=5.6,
                    change_percent=1.78,
                    reference_price=314.52,
                    updated_at=now,
                    volume=2_100_000,
                    average_volume=1_900_000,
                    relative_volume=1.11,
                    data_points=30,
                    strategy_scores={"can_slim": 0.81, "trend_following": 0.75},
                    final_score=0.79,
                )
            ],
            top_losers=[],
        )


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


def test_sp500_momentum_endpoint_returns_payload() -> None:
    app.dependency_overrides[get_sp_momentum_service] = lambda: DummySPService()
    client = TestClient(app)

    response = client.get("/api/sp500/momentum?timeframe=day&limit=50")

    app.dependency_overrides.pop(get_sp_momentum_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["baseline_symbol"] == "SPY"
    assert data["top_gainers"][0]["symbol"] == "MSFT"
