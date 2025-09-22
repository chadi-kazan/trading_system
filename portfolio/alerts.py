"""Alerting utilities for portfolio monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from portfolio.drawdown_monitor import DrawdownEvent, detect_drawdown_events


@dataclass
class DrawdownAlertConfig:
    threshold: float = 0.15
    min_interval_days: int = 7


class DrawdownAlertManager:
    """Generates alerts based on drawdown events with throttling."""

    def __init__(self, config: DrawdownAlertConfig | None = None) -> None:
        self.config = config or DrawdownAlertConfig()
        self._last_alert_date: pd.Timestamp | None = None

    def process_equity_curve(self, equity_curve: pd.Series) -> List[DrawdownEvent]:
        events = detect_drawdown_events(equity_curve, self.config.threshold)
        alerts: List[DrawdownEvent] = []
        for event in events:
            if self._should_alert(event.trough_date):
                alerts.append(event)
                self._last_alert_date = event.trough_date
        return alerts

    def _should_alert(self, trough_date: pd.Timestamp) -> bool:
        if self._last_alert_date is None:
            return True
        delta = trough_date - self._last_alert_date
        return delta.days >= self.config.min_interval_days


__all__ = ["DrawdownAlertManager", "DrawdownAlertConfig"]
