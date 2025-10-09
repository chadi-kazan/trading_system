"""Metadata helpers for presenting strategy information in the dashboard."""

from __future__ import annotations

from typing import Dict, List

STRATEGY_METADATA: Dict[str, Dict[str, str]] = {
    "dan_zanger_cup_handle": {
        "label": "Dan Zanger Cup & Handle",
        "description": "Identifies cup-and-handle breakouts with volume confirmation to flag potential momentum entries.",
        "chart_type": "candlestick-pattern",
        "investment_bounds": "Optimal when confidence ≥ 0.60, breakout closes above the handle high, and volume ≥ 130% of average.",
        "score_guidance": "0-49%: base still forming; 50-69%: watch for breakout confirmation; 70-100%: actionable breakout with power.",
    },
    "can_slim": {
        "label": "CAN SLIM Score",
        "description": "Evaluates earnings, relative strength, price position, and volume thrust to produce a composite CAN SLIM score.",
        "chart_type": "factor-radar",
        "investment_bounds": "Optimal when composite score ≥ 0.80 with relative strength ≥ 0.75 and earnings momentum accelerating.",
        "score_guidance": "0-59%: fundamentals not aligned; 60-79%: improving story; 80-100%: leadership-grade growth profile.",
    },
    "trend_following": {
        "label": "EMA Trend Following",
        "description": "Tracks fast and slow EMAs with ATR risk bands to highlight trend continuation or reversals.",
        "chart_type": "line-ema",
        "investment_bounds": "Optimal when confidence ≥ 0.55, price stays above the slow EMA, and ATR stop is rising.",
        "score_guidance": "0-49%: trend deteriorating; 50-74%: trend stabilising; 75-100%: trend in strong alignment.",
    },
    "livermore_breakout": {
        "label": "Livermore Breakout",
        "description": "Looks for tight consolidations and volume-backed breakouts inspired by Livermore's tape reading.",
        "chart_type": "range-breakout",
        "investment_bounds": "Optimal when confidence ≥ 0.58, base range ≤ 12%, and breakout volume ≥ 150% of the 50-day average.",
        "score_guidance": "0-54%: base still loose; 55-74%: setup forming; 75-100%: high-tension breakout ready to run.",
    },
}

STRATEGY_ORDER: List[str] = [
    "dan_zanger_cup_handle",
    "can_slim",
    "trend_following",
    "livermore_breakout",
]


__all__ = ["STRATEGY_METADATA", "STRATEGY_ORDER"]
