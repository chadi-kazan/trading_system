from argparse import Namespace
from types import SimpleNamespace
import json
import pandas as pd

from main import (
    STRATEGY_FACTORIES,
    build_parser,
    build_strategy_weight_map,
    instantiate_strategies,
    load_price_frame_from_csv,
    load_price_data_for_backtest,
    AppContext,
)
from trading_system.config_manager import ConfigManager


def _load_config():
    return ConfigManager().load(force_reload=True)


def test_instantiate_strategies_defaults_cover_all():
    config = _load_config()
    strategies = instantiate_strategies(None, config)
    assert {strategy.name for strategy in strategies} == set(STRATEGY_FACTORIES.keys())


def test_instantiate_strategies_accepts_aliases():
    config = _load_config()
    strategies = instantiate_strategies(["dan_zanger", "trend"], config)
    names = [strategy.name for strategy in strategies]
    assert names == [
        next(iter(STRATEGY_FACTORIES)),
        "trend_following",
    ]


def test_build_strategy_weight_map_returns_all_keys():
    config = _load_config()
    weights = build_strategy_weight_map(config)
    assert set(weights.keys()) == set(STRATEGY_FACTORIES.keys())


def test_load_price_frame_from_csv_normalises_columns(tmp_path):
    path = tmp_path / "prices.csv"
    pd.DataFrame(
        {
            "Date": ["2024-01-02", "2024-01-01"],
            "Close": [10.0, 11.0],
            "Volume": [100, 200],
        }
    ).to_csv(path, index=False)

    frame = load_price_frame_from_csv(path)

    assert frame.index.name == "date"
    assert list(frame.columns) == ["close", "volume"]
    assert list(frame.index) == sorted(frame.index)


def test_build_parser_attaches_handlers():
    parser = build_parser()
    args = parser.parse_args(["backtest", "--symbol", "AAPL"])
    assert args.command == "backtest"
    assert hasattr(args, "handler")


def test_scan_parser_supports_russell_flag():
    parser = build_parser()
    args = parser.parse_args(["scan", "--include-russell"])
    assert args.include_russell is True
    assert hasattr(args, "handler")





def test_handle_refresh_fundamentals(monkeypatch, tmp_path):
    parser = build_parser()
    args = parser.parse_args(["refresh-fundamentals", "--throttle", "0"])

    class DummyStorage:
        universe_dir = tmp_path

    class DummyDataSources:
        alpha_vantage_key = "demo"

    ctx = AppContext(manager=None, config=SimpleNamespace(data_sources=DummyDataSources(), storage=DummyStorage()))

    monkeypatch.setattr('main.load_seed_candidates', lambda seed_path, extra_sources=None: ['ABC'])

    captured = {}

    def fake_refresh(symbols, base_dir, api_key, throttle_seconds):
        captured["symbols"] = symbols
        captured["base_dir"] = base_dir
        captured["api_key"] = api_key
        captured["throttle"] = throttle_seconds
        return len(symbols)

    monkeypatch.setattr('main.refresh_fundamentals_cache', fake_refresh)

    result = args.handler(args, ctx)

    assert result == 0
    assert captured["symbols"] == ['ABC']
    assert captured["base_dir"] == tmp_path
    assert captured["api_key"] == 'demo'
    assert captured["throttle"] == 0.0
def test_load_price_data_for_backtest_enriches_csv(tmp_path):
    config = _load_config()
    path = tmp_path / "prices.csv"
    pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10, freq="D"),
        "close": [100 + i for i in range(10)],
        "volume": [1_000 + 10 * i for i in range(10)],
    }).to_csv(path, index=False)

    fundamentals_dir = config.storage.universe_dir / "fundamentals"
    dir_existed = fundamentals_dir.exists()
    fundamentals_dir.mkdir(parents=True, exist_ok=True)
    fundamentals_path = fundamentals_dir / "PRICES.json"

    try:
        fundamentals_path.write_text(json.dumps({"earnings_growth": 0.5, "relative_strength": 0.95}))
        args = Namespace(prices=path, symbol=None, start=None, end=None, interval="1d")
        frame = load_price_data_for_backtest(args, config)

        expected_columns = {
            "average_volume",
            "volume_change",
            "fifty_two_week_high",
            "relative_strength",
            "earnings_growth",
        }
        assert expected_columns.issubset(frame.columns)
        assert frame.attrs.get("enriched") is True
        assert frame.attrs.get("fundamentals") is True
        assert frame["earnings_growth"].iloc[-1] == 0.5
        assert frame["relative_strength"].iloc[-1] == 0.95
    finally:
        if fundamentals_path.exists():
            fundamentals_path.unlink()
        if not dir_existed and fundamentals_dir.exists():
            try:
                fundamentals_dir.rmdir()
            except OSError:
                pass

    assert frame.attrs.get("symbol") == path.stem.upper()
