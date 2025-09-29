"""Legacy monolithic entry point retained for backwards compatibility."""

from __future__ import annotations

import warnings
from typing import Optional, Sequence

from main import main as _cli_main

warnings.warn(
    "`trading_system_implementation.py` is deprecated. Use the modular CLI via `python main.py`.",
    DeprecationWarning,
    stacklevel=2,
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Delegate to the modern CLI entry point."""
    return _cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
