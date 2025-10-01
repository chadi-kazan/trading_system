from __future__ import annotations

from pathlib import Path

import pytest

from universe.russell import DEFAULT_RUSSELL_URL, download_russell_2000, refresh_russell_file


class DummyResponse:
    def __init__(self, text: str, status: int = 200) -> None:
        self.text = text
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_download_russell_2000_parses_symbol_column(monkeypatch):
    sample_csv = "symbol,name\nIWM,Russell ETF\nIWN,Another\n"

    def fake_get(url, timeout):  # pragma: no cover - simple stub
        assert url == DEFAULT_RUSSELL_URL
        return DummyResponse(sample_csv)

    monkeypatch.setattr('requests.get', fake_get)

    symbols = list(download_russell_2000())
    assert symbols == ["IWM", "IWN"]


def test_refresh_russell_file_writes_unique(monkeypatch, tmp_path: Path):
    dest = tmp_path / "russell.csv"

    def fake_get(url, timeout):  # pragma: no cover - simple stub
        return DummyResponse("symbol\nIWM\nIWM\nIWN\n")

    monkeypatch.setattr('requests.get', fake_get)

    count = refresh_russell_file(dest)
    assert count == 2
    assert dest.read_text() == "symbol\nIWM\nIWN\n"


def test_refresh_russell_file_handles_errors(monkeypatch, tmp_path: Path):
    dest = tmp_path / "russell.csv"

    def fake_get(url, timeout):  # pragma: no cover - simple stub
        return DummyResponse("", status=500)

    monkeypatch.setattr('requests.get', fake_get)

    with pytest.raises(RuntimeError):
        refresh_russell_file(dest)
