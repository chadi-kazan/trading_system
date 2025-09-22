"""Backtesting engine skeleton with transaction costs.""" 
 
from __future__ import annotations 
 
from dataclasses import dataclass 
from typing import Callable, Dict, Iterable, List 
 
import pandas as pd 
 
from strategies.base import Strategy, StrategySignal 
 
 
@dataclass 
class BacktestResult: 
    equity_curve: pd.Series 
    trades: List[Dict[str, float]] 
    metrics: Dict[str, float] 
 
 
class BacktestingEngine: 
    """Runs strategy backtests over historical price data.""" 
 
    def __init__(self, transaction_cost: float = 0.001) -> None: 
        self.transaction_cost = transaction_cost 
 
    def run( 
        self, 
        price_data: pd.DataFrame, 
        strategy: Strategy, 
        position_sizer: Callable[[Iterable[StrategySignal], float], List[Dict[str, float]]], 
        initial_capital: float = 100_000, 
    ) -> BacktestResult: 
        signals = self._generate_signals(price_data, strategy) 
        # Placeholder: positions sizing and order execution would go here. 
        equity_curve = pd.Series([initial_capital], index=[price_data.index[0]]) 
        return BacktestResult(equity_curve=equity_curve, trades=[], metrics={"final": initial_capital}) 
 
    def _generate_signals(self, price_data: pd.DataFrame, strategy: Strategy) -> List[StrategySignal]: 
        signals = strategy.generate_signals("TEST", price_data) 
        return signals 
 
 
__all__ = ["BacktestingEngine", "BacktestResult"] 
