"""Quick manual smoke test for the Yahoo price provider."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_providers.base import PriceRequest
from data_providers.yahoo import YahooPriceProvider


def run() -> None:
    cache_dir = Path("data/prices/cache")
    provider = YahooPriceProvider(cache_dir=cache_dir, cache_ttl_days=7)
    end = date.today()
    start = end - timedelta(days=30)

    for symbol in ["AAPL", "MSFT"]:
        request = PriceRequest(symbol=symbol, start=start, end=end)
        result = provider.get_price_history(request)
        frame = result.data
        print(
            f"{symbol}: {len(frame)} rows, from_cache={result.from_cache}, "
            f"first={frame.index.min().date() if not frame.empty else 'NA'}, "
            f"last={frame.index.max().date() if not frame.empty else 'NA'}"
        )


if __name__ == "__main__":
    run()
