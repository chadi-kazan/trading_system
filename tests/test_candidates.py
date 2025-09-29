from __future__ import annotations

from pathlib import Path

from universe import candidates
from universe.candidates import (
    DEFAULT_CANDIDATES,
    load_russell_2000_candidates,
    load_seed_candidates,
)


def test_loads_from_csv(tmp_path: Path) -> None:
    data = "symbol,name\nplug,Plug Power\nsofi,SoFi\nplug,Duplicate\n#comment,Ignored\n"
    file_path = tmp_path / "candidates.csv"
    file_path.write_text(data, encoding="utf-8")

    symbols = load_seed_candidates(file_path)

    assert symbols == ["PLUG", "SOFI"]


def test_falls_back_to_default_when_file_missing(tmp_path: Path) -> None:
    file_path = tmp_path / "missing.csv"

    symbols = load_seed_candidates(file_path)

    assert symbols == DEFAULT_CANDIDATES


def test_handles_plain_text_list(tmp_path: Path) -> None:
    data = "PLUG\nNVAX\n"
    file_path = tmp_path / "list.txt"
    file_path.write_text(data, encoding="utf-8")

    symbols = load_seed_candidates(file_path)

    assert symbols == ["PLUG", "NVAX"]


def test_extra_sources_are_combined(tmp_path: Path) -> None:
    extra_path = tmp_path / "extra.csv"
    extra_path.write_text("symbol\nIWM\nIWN\n", encoding="utf-8")

    symbols = load_seed_candidates(extra_sources=[extra_path])

    assert "IWM" in symbols
    assert "IWN" in symbols


def test_load_russell_2000_candidates_uses_configured_path(tmp_path: Path) -> None:
    original_path = candidates.RUSSELL_2000_PATH
    try:
        override = tmp_path / "russell_2000.csv"
        override.write_text("symbol\nABC\nXYZ\n", encoding="utf-8")
        candidates.RUSSELL_2000_PATH = override

        symbols = load_russell_2000_candidates()

        assert symbols == ["ABC", "XYZ"]
    finally:
        candidates.RUSSELL_2000_PATH = original_path
