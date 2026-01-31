"""Utilities for downloading Russell 2000 constituents."""

from __future__ import annotations

import csv
import logging
import re
from io import StringIO
from pathlib import Path
from typing import Iterable

import requests

LOGGER = logging.getLogger(__name__)

DEFAULT_RUSSELL_URL = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"


def download_russell_2000(url: str = DEFAULT_RUSSELL_URL) -> Iterable[str]:
    """Return an iterable of ticker symbols downloaded from *url*."""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    # Strip BOM if present and split into lines
    content = response.text.lstrip("\ufeff")
    lines = content.split("\n")

    # Find the header row (contains "Ticker" column)
    header_idx = None
    for idx, line in enumerate(lines):
        if "Ticker" in line and "Name" in line:
            header_idx = idx
            break

    if header_idx is None:
        LOGGER.warning("Could not find header row with 'Ticker' column")
        return

    # Parse CSV starting from header row
    csv_content = "\n".join(lines[header_idx:])
    reader = csv.DictReader(StringIO(csv_content))

    seen = set()
    # Pattern for valid US stock tickers: 1-5 uppercase letters, optionally followed by .A/.B (class shares)
    valid_ticker_pattern = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')

    for row in reader:
        symbol = (row.get("Ticker") or "").strip().upper()
        # Filter: non-empty, not "-", valid format, no duplicates
        if (symbol and
            symbol != "-" and
            valid_ticker_pattern.match(symbol) and
            symbol not in seen):
            seen.add(symbol)
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
