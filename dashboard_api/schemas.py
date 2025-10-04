"""Pydantic schemas powering the dashboard API responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime


class StrategyInfo(BaseModel):
    name: str
    label: str
    description: str
    chart_type: str


class StrategySignalPayload(BaseModel):
    date: datetime
    signal_type: str
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StrategyAnalysis(BaseModel):
    name: str
    label: str
    description: str
    chart_type: str
    signals: List[StrategySignalPayload] = Field(default_factory=list)
    latest_metadata: Optional[Dict[str, Any]] = None
    extras: Dict[str, Any] = Field(default_factory=dict)


class AggregatedSignalPayload(BaseModel):
    date: datetime
    signal_type: str
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PriceBar(BaseModel):
    date: datetime
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float
    average_volume: Optional[float] = None
    volume_change: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    relative_strength: Optional[float] = None
    earnings_growth: Optional[float] = None
    fast_ema: Optional[float] = None
    slow_ema: Optional[float] = None
    atr: Optional[float] = None


class SymbolAnalysisResponse(BaseModel):
    symbol: str
    start: date
    end: date
    interval: str
    price_bars: List[PriceBar]
    strategies: List[StrategyAnalysis]
    aggregated_signals: List[AggregatedSignalPayload] = Field(default_factory=list)


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    type: str
    region: str
    market_open: Optional[str] = None
    market_close: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    match_score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    results: List[SymbolSearchResult]


__all__ = [
    "AggregatedSignalPayload",
    "HealthResponse",
    "PriceBar",
    "SearchResponse",
    "StrategyAnalysis",
    "StrategyInfo",
    "StrategySignalPayload",
    "SymbolAnalysisResponse",
    "SymbolSearchResult",
]
