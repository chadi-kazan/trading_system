"""Utilities for downloading Russell 2000 constituents."""

from __future__ import annotations

import csv
import logging
from io import StringIO
from pathlib import Path
from typing import Iterable

import requests

LOGGER = logging.getLogger(__name__)

DEFAULT_RUSSELL_URL = "https://raw.githubusercontent.com/datasets/russell-2000/master/data/russell-2000.csv"


def download_russell_2000(url: str = DEFAULT_RUSSELL_URL) -> Iterable[str]:
    """Return an iterable of ticker symbols downloaded from *url*."""

    response = requests.get(url, timeout=15)
    response.raise_for_status()
    content = response.text

    reader = csv.DictReader(StringIO(content))
    if reader.fieldnames and any(h and h.lower() == "symbol" for h in reader.fieldnames):
        for row in reader:
            symbol = (row.get("symbol") or "").strip().upper()
            if symbol:
                yield symbol
    else:
        reader_generic = csv.reader(StringIO(content))
        for row in reader_generic:
            for cell in row:
                symbol = cell.strip().upper()
                if symbol:
                    yield symbol


def refresh_russell_file(dest: Path, url: str = DEFAULT_RUSSELL_URL) -> int:
    """Download Russell symbols from *url* and write them to *dest*.

    Returns the number of tickers written.
    """

    symbols = list(dict.fromkeys(download_russell_2000(url)))
    if not symbols:
        LOGGER.warning("Russell download returned no symbols")
        return 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("symbol\n" + "\n".join(symbols) + "\n", encoding="utf-8")
    LOGGER.info("Saved %s Russell 2000 symbols to %s", len(symbols), dest)
    return len(symbols)


__all__ = ["download_russell_2000", "refresh_russell_file", "DEFAULT_RUSSELL_URL"]
