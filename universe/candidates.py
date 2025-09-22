"""Seed candidate loaders for the universe builder."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterable, List

DEFAULT_CANDIDATES = [
    "PLUG",
    "NVAX",
    "SOFI",
    "RUN",
    "ARRY",
    "BLDP",
    "ENPH",
    "SEDG",
    "BE",
    "FSLR",
    "INSM",
    "ARDX",
    "CRBU",
    "KRYS",
    "VERV",
    "STEM",
    "NOVA",
    "EVGO",
    "IONQ",
    "AEHR",
    "ONTO",
    "AMPL",
    "SWAV",
    "AKRO",
    "EXAI",
    "AVNS",
    "ENVX",
    "CLSK",
    "DNMR",
    "ALLO",
]

DEFAULT_PATH = Path("data/universe/seed_candidates.csv")


def _normalise(symbols: Iterable[str]) -> List[str]:
    cleaned: List[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        sym = symbol.strip().upper()
        if not sym or sym.startswith("#"):
            continue
        if sym in seen:
            continue
        cleaned.append(sym)
        seen.add(sym)
    return cleaned


def _load_symbols_from_file(path: Path) -> List[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return []

    if not text.strip():
        return []

    buffer = io.StringIO(text)
    reader = csv.DictReader(buffer)
    if reader.fieldnames and any(
        field and field.strip().lower() == "symbol" for field in reader.fieldnames
    ):
        values = [row.get("symbol", "") for row in reader]
        symbols = _normalise(values)
        if symbols:
            return symbols

    buffer.seek(0)
    reader_generic = csv.reader(buffer)
    flattened: list[str] = []
    for row in reader_generic:
        flattened.extend(row)
    return _normalise(flattened)


def load_seed_candidates(path: Path | None = None) -> List[str]:
    """Load candidate tickers from a file or fall back to defaults."""
    target_path = path or DEFAULT_PATH
    symbols = _load_symbols_from_file(target_path)
    if symbols:
        return symbols
    return _normalise(DEFAULT_CANDIDATES)


__all__ = ["load_seed_candidates", "DEFAULT_CANDIDATES", "DEFAULT_PATH"]
