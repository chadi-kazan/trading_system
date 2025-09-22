from __future__ import annotations

from pathlib import Path

from universe.candidates import DEFAULT_CANDIDATES, load_seed_candidates


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
