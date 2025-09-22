"""Seed candidate loaders for the universe builder."""

from __future__ import annotations

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
]


def _normalise(symbols: Iterable[str]) -> List[str]:
    cleaned = []
    seen = set()
    for symbol in symbols:
        sym = symbol.strip().upper()
        if not sym or sym in seen:
            continue
        cleaned.append(sym)
        seen.add(sym)
    return cleaned


def load_seed_candidates(path: Path | None = None) -> List[str]:
    """Load candidate tickers from a text/CSV file or fallback defaults."""
    if path is None:
        path = Path("data/universe/seed_candidates.csv")

    if path.exists():
        content = path.read_text(encoding="utf-8")
        if "," in content:
            # treat as CSV and split on commas/newlines.
            raw = [part for chunk in content.splitlines() for part in chunk.split(",")]
        else:
            raw = content.splitlines()
        symbols = _normalise(raw)
        if symbols:
            return symbols
    return _normalise(DEFAULT_CANDIDATES)


__all__ = ["load_seed_candidates", "DEFAULT_CANDIDATES"]
