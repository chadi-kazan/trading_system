"""Ad-hoc smoke test for the universe builder."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.config_manager import ConfigManager
from universe.builder import UniverseBuilder


def run() -> None:
    config = ConfigManager().load()
    builder = UniverseBuilder(config)
    from universe.candidates import load_seed_candidates
    tickers = load_seed_candidates()[:50]
    universe = builder.build_universe(tickers, as_of=date.today(), persist=False)
    print(f"Selected {len(universe)} symbols from {len(tickers)} candidates")
    skipped = builder.last_skipped_symbols()
    if skipped:
        sample = ', '.join(skipped[:10])
        if len(skipped) > 10:
            sample += ', ...'
        print(f"Skipped {len(skipped)} symbols due to missing fundamentals or fetch errors: {sample}")
    if not universe.empty:
        print(universe[["symbol", "market_cap", "dollar_volume", "sector"]].head().to_string(index=False))
    else:
        print("No symbols passed the screening criteria.")


if __name__ == "__main__":
    run()
