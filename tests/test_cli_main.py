from argparse import Namespace
from dataclasses import replace
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


def _prepare_schedule_config(tmp_path, *, enabled=True):
    config = _load_config()
    storage = replace(
        config.storage,
        price_cache_dir=tmp_path / "prices",
        universe_dir=tmp_path / "universe",
        signal_dir=tmp_path / "signals",
        portfolio_dir=tmp_path / "portfolio",
    )
    for directory in storage.__dict__.values():
        directory.mkdir(parents=True, exist_ok=True)

    schedule_cfg = replace(config.automation.fundamentals_refresh, enabled=enabled)
    automation_cfg = replace(config.automation, fundamentals_refresh=schedule_cfg)

    return replace(config, storage=storage, automation=automation_cfg)


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








def test_refresh_russell_cli(monkeypatch, tmp_path):
    parser = build_parser()
    dest = tmp_path / "russell.csv"
    args = parser.parse_args(["refresh-russell", "--url", "https://example.com/russell.csv", "--dest", str(dest)])

    class DummyStorage:
        universe_dir = tmp_path

    ctx = AppContext(manager=None, config=SimpleNamespace(data_sources=None, storage=DummyStorage()))

    captured = {}

    def fake_refresh(dest_path, url):
        captured["dest"] = dest_path
        captured["url"] = url
        dest_path.write_text("symbol\nABC\n")
        return 1

    monkeypatch.setattr('main.refresh_russell_file', fake_refresh)

    result = args.handler(args, ctx)

    assert result == 0
    assert captured["url"] == "https://example.com/russell.csv"
    assert captured["dest"] == dest
    assert dest.exists()
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

def test_schedule_fundamentals_cli(monkeypatch, tmp_path):
    parser = build_parser()
    args = parser.parse_args(["schedule-fundamentals", "--run-once", "--limit", "10", "--force"])

    config = _load_config()
    storage = replace(
        config.storage,
        price_cache_dir=tmp_path / "prices",
        universe_dir=tmp_path / "universe",
        signal_dir=tmp_path / "signals",
        portfolio_dir=tmp_path / "portfolio",
    )
    for directory in storage.__dict__.values():
        directory.mkdir(parents=True, exist_ok=True)
    config = replace(config, storage=storage)

    ctx = AppContext(manager=None, config=config)

    captured: dict[str, object] = {}

    def fake_run(config_arg, schedule_cfg, **kwargs):
        captured["config"] = config_arg
        captured["schedule"] = schedule_cfg
        captured["kwargs"] = kwargs

    monkeypatch.setattr('main.run_scheduled_refresh', fake_run)

    result = args.handler(args, ctx)

    assert result == 0
    assert captured["config"] is config
    assert captured["kwargs"]["run_once"] is True
    assert captured["kwargs"]["limit"] == 10
    assert captured["kwargs"]["max_iterations"] is None


def test_schedule_fundamentals_cli_requires_force(monkeypatch, tmp_path):
    parser = build_parser()
    args = parser.parse_args(["schedule-fundamentals"])

    config = _prepare_schedule_config(tmp_path, enabled=False)
    ctx = AppContext(manager=None, config=config)

    called = False

    def fake_run(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr('main.run_scheduled_refresh', fake_run)

    result = args.handler(args, ctx)

    assert result == 0
    assert called is False


def test_schedule_fundamentals_cli_conflicting_flags(monkeypatch, tmp_path):
    parser = build_parser()
    args = parser.parse_args(["schedule-fundamentals", "--include-russell", "--skip-russell", "--force"])

    ctx = AppContext(manager=None, config=_prepare_schedule_config(tmp_path))

    monkeypatch.setattr('main.run_scheduled_refresh', lambda *_, **__: (_ for _ in ()).throw(AssertionError("should not run")))

    result = args.handler(args, ctx)

    assert result == 1


def test_schedule_fundamentals_cli_validates_throttle(monkeypatch, tmp_path):
    parser = build_parser()
    args = parser.parse_args(["schedule-fundamentals", "--throttle", "-1", "--force"])

    ctx = AppContext(manager=None, config=_prepare_schedule_config(tmp_path))

    monkeypatch.setattr('main.run_scheduled_refresh', lambda *_, **__: (_ for _ in ()).throw(AssertionError("should not run")))

    result = args.handler(args, ctx)

    assert result == 1


def test_schedule_fundamentals_cli_validates_max_iterations(monkeypatch, tmp_path):
    parser = build_parser()
    args = parser.parse_args(["schedule-fundamentals", "--max-iterations", "0", "--force"])

    ctx = AppContext(manager=None, config=_prepare_schedule_config(tmp_path))

    monkeypatch.setattr('main.run_scheduled_refresh', lambda *_, **__: (_ for _ in ()).throw(AssertionError("should not run")))

    result = args.handler(args, ctx)

    assert result == 1


def test_schedule_fundamentals_cli_passes_max_iterations(monkeypatch, tmp_path):
    parser = build_parser()
    args = parser.parse_args(["schedule-fundamentals", "--max-iterations", "5", "--force"])

    ctx = AppContext(manager=None, config=_prepare_schedule_config(tmp_path))

    captured: dict[str, object] = {}

    def fake_run(config_arg, schedule_cfg, **kwargs):
        captured["config"] = config_arg
        captured["schedule"] = schedule_cfg
        captured["kwargs"] = kwargs

    monkeypatch.setattr('main.run_scheduled_refresh', fake_run)

    result = args.handler(args, ctx)

    assert result == 0
    assert captured["config"] is ctx.config
    assert captured["kwargs"]["max_iterations"] == 5
