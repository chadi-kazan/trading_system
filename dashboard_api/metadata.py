"""Metadata helpers for presenting strategy information in the dashboard."""

from __future__ import annotations

from typing import Dict, List

STRATEGY_METADATA: Dict[str, Dict[str, str]] = {
    "dan_zanger_cup_handle": {
        "label": "Dan Zanger Cup & Handle",
        "description": "Identifies cup-and-handle breakouts with volume confirmation to flag potential momentum entries.",
        "chart_type": "candlestick-pattern",
        "investment_bounds": "Confidence ≥ 0.60 with breakout closing above handle high and volume > 1.3× average.",
    },
    "can_slim": {
        "label": "CAN SLIM Score",
        "description": "Evaluates earnings, relative strength, price position, and volume thrust to produce a composite CAN SLIM score.",
        "chart_type": "factor-radar",
        "investment_bounds": "Composite score ≥ 0.80 with RS score ≥ 0.75 and earnings momentum accelerating.",
    },
    "trend_following": {
        "label": "EMA Trend Following",
        "description": "Tracks fast and slow EMAs with ATR risk bands to highlight trend continuation or reversals.",
        "chart_type": "line-ema",
        "investment_bounds": "Confidence ≥ 0.55 while price > slow EMA and ATR stop rising for two sessions.",
    },
    "livermore_breakout": {
        "label": "Livermore Breakout",
        "description": "Looks for tight consolidations and volume-backed breakouts inspired by Livermore's tape reading.",
        "chart_type": "range-breakout",
        "investment_bounds": "Confidence ≥ 0.58 with base range ≤ 12% and breakout volume ≥ 1.5× 50-day average.",
    },
}

STRATEGY_ORDER: List[str] = [
    "dan_zanger_cup_handle",
    "can_slim",
    "trend_following",
    "livermore_breakout",
]


__all__ = ["STRATEGY_METADATA", "STRATEGY_ORDER"]
