"""Metadata helpers for presenting strategy information in the dashboard."""

from __future__ import annotations

from typing import Dict, List

STRATEGY_METADATA: Dict[str, Dict[str, str]] = {
    "dan_zanger_cup_handle": {
        "label": "Dan Zanger Cup & Handle",
        "description": "Identifies cup-and-handle breakouts with volume confirmation to flag potential momentum entries.",
        "chart_type": "candlestick-pattern",
    },
    "can_slim": {
        "label": "CAN SLIM Score",
        "description": "Evaluates earnings, relative strength, price position, and volume thrust to produce a composite CAN SLIM score.",
        "chart_type": "factor-radar",
    },
    "trend_following": {
        "label": "EMA Trend Following",
        "description": "Tracks fast and slow EMAs with ATR risk bands to highlight trend continuation or reversals.",
        "chart_type": "line-ema",
    },
    "livermore_breakout": {
        "label": "Livermore Breakout",
        "description": "Looks for tight consolidations and volume-backed breakouts inspired by Livermore's tape reading.",
        "chart_type": "range-breakout",
    },
}

STRATEGY_ORDER: List[str] = [
    "dan_zanger_cup_handle",
    "can_slim",
    "trend_following",
    "livermore_breakout",
]


__all__ = ["STRATEGY_METADATA", "STRATEGY_ORDER"]
