"""High level portfolio health monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from portfolio.alerts import DrawdownAlertConfig, DrawdownAlertManager
from portfolio.drawdown_monitor import calculate_drawdowns
from portfolio.sector_monitor import SectorBreach, detect_sector_breaches


@dataclass
class PortfolioHealthConfig:
    sector_limits: Dict[str, float]
    drawdown_alert: DrawdownAlertConfig = field(default_factory=DrawdownAlertConfig)


@dataclass
class PortfolioHealthReport:
    max_drawdown: float
    drawdown_alerts: List[str]
    sector_breaches: List[SectorBreach]
    positions_count: int


class PortfolioHealthMonitor:
    """Aggregates portfolio monitoring signals into a concise report."""

    def __init__(self, config: PortfolioHealthConfig) -> None:
        self.config = config
        self.alert_manager = DrawdownAlertManager(config.drawdown_alert)

    def evaluate(self, equity_curve: pd.Series, positions: pd.DataFrame) -> PortfolioHealthReport:
        if equity_curve.empty:
            raise ValueError("Equity curve cannot be empty")

        drawdowns, max_dd = calculate_drawdowns(equity_curve)
        alerts = self.alert_manager.process_equity_curve(equity_curve)
        breaches = detect_sector_breaches(positions, self.config.sector_limits)

        alert_messages = [
            f"Drawdown {event.drawdown_pct:.2%} from {event.peak_date.date()} to {event.trough_date.date()}"
            for event in alerts
        ]

        return PortfolioHealthReport(
            max_drawdown=float(max_dd),
            drawdown_alerts=alert_messages,
            sector_breaches=breaches,
            positions_count=len(positions) if not positions.empty else 0,
        )


__all__ = ["PortfolioHealthMonitor", "PortfolioHealthConfig", "PortfolioHealthReport"]
