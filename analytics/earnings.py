"""Earnings quality and surprise analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class EarningsSignal:
    """Summarises earnings quality and surprise momentum for a symbol."""

    score: Optional[float]
    surprise_average: Optional[float]
    positive_ratio: Optional[float]
    eps_trend: Optional[float]

    def multiplier(self) -> float:
        """Return a [0.5, 1] style multiplier for confidence adjustment."""
        if self.score is None:
            return 1.0
        return round(0.55 + 0.45 * _clamp(self.score, 0.0, 1.0), 3)

    def to_metadata(self) -> Dict[str, Optional[float]]:
        return {
            "score": None if self.score is None else round(float(self.score), 3),
            "surprise_average": None if self.surprise_average is None else round(float(self.surprise_average), 3),
            "positive_ratio": None if self.positive_ratio is None else round(float(self.positive_ratio), 3),
            "eps_trend": None if self.eps_trend is None else round(float(self.eps_trend), 3),
            "confidence_multiplier": self.multiplier(),
        }


def compute_earnings_signal(fundamentals: Dict[str, float]) -> EarningsSignal:
    """Derive an earnings signal snapshot from cached fundamental metrics."""

    if not fundamentals:
        return EarningsSignal(score=None, surprise_average=None, positive_ratio=None, eps_trend=None)

    surprise_avg = fundamentals.get("earnings_surprise_avg")
    positive_ratio = fundamentals.get("earnings_positive_ratio")
    eps_trend = fundamentals.get("earnings_eps_trend")
    preset_score = fundamentals.get("earnings_signal_score")

    components = []
    if positive_ratio is not None:
        components.append(_clamp(float(positive_ratio)))
    if surprise_avg is not None:
        components.append(_clamp(0.5 + float(surprise_avg) / 0.25))
    if eps_trend is not None:
        components.append(_clamp(0.5 + float(eps_trend) / 0.25))

    composite = None
    if components:
        composite = sum(components) / len(components)
    if preset_score is not None:
        # blend cached score with derived components if available
        if composite is None:
            composite = float(preset_score)
        else:
            composite = (composite + float(preset_score)) / 2

    return EarningsSignal(
        score=None if composite is None else _clamp(float(composite)),
        surprise_average=None if surprise_avg is None else float(surprise_avg),
        positive_ratio=None if positive_ratio is None else _clamp(float(positive_ratio)),
        eps_trend=None if eps_trend is None else float(eps_trend),
    )


__all__ = ["EarningsSignal", "compute_earnings_signal"]

