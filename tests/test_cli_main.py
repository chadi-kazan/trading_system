from argparse import Namespace
import pandas as pd

from main import (
    STRATEGY_FACTORIES,
    build_parser,
    build_strategy_weight_map,
    instantiate_strategies,
    load_price_frame_from_csv,
    load_price_data_for_backtest,
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


def test_load_price_data_for_backtest_enriches_csv(tmp_path):
    config = _load_config()
    path = tmp_path / "prices.csv"
    pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10, freq="D"),
        "close": [100 + i for i in range(10)],
        "volume": [1_000 + 10 * i for i in range(10)],
    }).to_csv(path, index=False)

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
    assert frame.attrs.get("symbol") == path.stem.upper()
