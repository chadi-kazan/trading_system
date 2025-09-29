"""Backtesting engine with simple long-only simulation and basic metrics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

import pandas as pd

from portfolio.drawdown_monitor import calculate_drawdowns
from strategies.base import SignalType, Strategy, StrategySignal


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: List[Dict[str, float | str]]
    metrics: Dict[str, float]


class BacktestingEngine:
    """Runs strategy backtests over historical price data."""

    def __init__(self, transaction_cost: float = 0.001) -> None:
        if transaction_cost < 0:
            raise ValueError("transaction_cost must be non-negative")
        self.transaction_cost = transaction_cost

    def run(
        self,
        price_data: pd.DataFrame,
        strategy: Strategy,
        position_sizer: Callable[[Iterable[StrategySignal], float], List[Dict[str, float]]],
        initial_capital: float = 100_000,
        symbol: str = "ASSET",
    ) -> BacktestResult:
        if price_data.empty:
            raise ValueError("Price data cannot be empty")
        if initial_capital <= 0:
            raise ValueError("initial_capital must be positive")

        frame = price_data.sort_index().copy()
        frame.index = pd.to_datetime(frame.index)

        signals = list(strategy.generate_signals(symbol, frame))
        allocations = position_sizer(signals, float(initial_capital)) or []

        buy_signals = self._signals_by_symbol(signals, SignalType.BUY)
        sell_signals_by_date = self._signals_by_date(signals, SignalType.SELL, frame.index)

        pending_entries = self._prepare_entries(allocations, buy_signals, frame, symbol)
        entries_by_date: Dict[pd.Timestamp, List[dict]] = defaultdict(list)
        for entry in pending_entries:
            entries_by_date[entry["date"]].append(entry)

        cash = float(initial_capital)
        positions: Dict[str, dict] = {}
        trades: List[Dict[str, float | str]] = []
        equity_values: List[float] = []

        for current_date in frame.index:
            for entry in entries_by_date.pop(current_date, []):
                price = entry["price"]
                shares = entry["shares"]
                if shares <= 0:
                    continue
                max_affordable = int(cash // (price * (1 + self.transaction_cost)))
                if max_affordable <= 0:
                    continue
                if shares > max_affordable:
                    shares = max_affordable
                cost = shares * price
                fees = cost * self.transaction_cost
                cash -= cost + fees
                positions[entry["symbol"]] = {
                    "shares": shares,
                    "entry_price": price,
                    "entry_date": current_date,
                    "strategy": entry["strategy"],
                    "entry_fees": fees,
                }
                trades.append(
                    {
                        "action": "BUY",
                        "symbol": entry["symbol"],
                        "date": current_date.isoformat(),
                        "shares": float(shares),
                        "price": float(price),
                        "value": float(cost),
                        "fees": float(fees),
                        "strategy": entry["strategy"],
                    }
                )

            for sell_signal in sell_signals_by_date.get(current_date, []):
                symbol = sell_signal.symbol
                if symbol not in positions:
                    continue
                price = self._signal_price(sell_signal, frame, current_date, symbol)
                position = positions.pop(symbol)
                shares = position["shares"]
                proceeds = shares * price
                fees = proceeds * self.transaction_cost
                cash += proceeds - fees
                pnl = proceeds - fees - (shares * position["entry_price"]) - position["entry_fees"]
                trades.append(
                    {
                        "action": "SELL",
                        "symbol": symbol,
                        "date": current_date.isoformat(),
                        "shares": float(shares),
                        "price": float(price),
                        "value": float(proceeds),
                        "fees": float(fees),
                        "strategy": sell_signal.strategy,
                        "pnl": float(pnl),
                    }
                )

            equity = cash
            for sym, position in positions.items():
                price = self._get_close(frame, current_date, sym)
                equity += position["shares"] * price
            equity_values.append(float(equity))

        equity_curve = pd.Series(equity_values, index=frame.index)
        _, max_drawdown = calculate_drawdowns(equity_curve)
        final_equity = float(equity_curve.iloc[-1])
        total_return = (final_equity / initial_capital) - 1

        metrics = {
            "final": final_equity,
            "total_return": float(total_return),
            "max_drawdown": float(max_drawdown),
            "num_trades": len(trades),
        }

        trade_dicts: List[Dict[str, float | str]] = []
        for trade in trades:
            trade_dicts.append(dict(trade))

        return BacktestResult(equity_curve=equity_curve, trades=trade_dicts, metrics=metrics)

    def _signals_by_symbol(
        self,
        signals: Iterable[StrategySignal],
        signal_type: SignalType,
    ) -> Dict[str, List[StrategySignal]]:
        result: Dict[str, List[StrategySignal]] = defaultdict(list)
        for signal in signals:
            if signal.signal_type is signal_type:
                result[signal.symbol].append(signal)
        for symbol in result:
            result[symbol].sort(key=lambda s: pd.Timestamp(s.date))
        return result

    def _signals_by_date(
        self,
        signals: Iterable[StrategySignal],
        signal_type: SignalType,
        index: pd.Index,
    ) -> Dict[pd.Timestamp, List[StrategySignal]]:
        result: Dict[pd.Timestamp, List[StrategySignal]] = defaultdict(list)
        for signal in signals:
            if signal.signal_type is not signal_type:
                continue
            aligned = self._align_date(pd.Timestamp(signal.date), index)
            if aligned is None:
                continue
            result[aligned].append(signal)
        return result
    def _prepare_entries(
        self,
        allocations: Iterable[Dict[str, float]],
        buy_signals: Dict[str, List[StrategySignal]],
        frame: pd.DataFrame,
        fallback_symbol: str,
    ) -> List[dict]:
        entries: List[dict] = []
        for allocation in allocations:
            symbol = allocation.get("symbol") or fallback_symbol
            signals = buy_signals.get(symbol, [])
            if not signals:
                continue
            signal = signals.pop(0)
            target_date = pd.Timestamp(signal.date)
            aligned_date = self._align_date(target_date, frame.index)
            if aligned_date is None:
                continue
            price = float(
                allocation.get("entry_price")
                or self._signal_price(signal, frame, aligned_date, symbol)
            )
            if price <= 0:
                continue
            shares = allocation.get("shares")
            if shares is None:
                allocation_value = float(allocation.get("allocation", 0.0))
                shares = int(allocation_value // price) if allocation_value > 0 else 0
            shares = int(shares)
            if shares <= 0:
                continue
            entries.append(
                {
                    "symbol": symbol,
                    "shares": shares,
                    "price": price,
                    "date": aligned_date,
                    "strategy": signal.strategy,
                }
            )
        return entries

    @staticmethod
    def _align_date(target: pd.Timestamp, index: pd.Index) -> Optional[pd.Timestamp]:
        if target is pd.NaT or index.empty:
            return None
        if not index.is_monotonic_increasing:
            index = index.sort_values()
        pos = index.searchsorted(target)
        if pos >= len(index):
            return None
        return pd.Timestamp(index[pos])

    def _signal_price(
        self,
        signal: StrategySignal,
        frame: pd.DataFrame,
        date: pd.Timestamp,
        symbol: str,
    ) -> float:
        metadata = signal.metadata or {}
        for key in ("price", "entry_price", "close", "breakout_price"):
            value = metadata.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return float(self._get_close(frame, date, symbol))

    def _get_close(self, frame: pd.DataFrame, date: pd.Timestamp, symbol: str) -> float:
        if isinstance(frame.columns, pd.MultiIndex):
            for key in (
                (symbol, "close"),
                ("close", symbol),
            ):
                if key in frame.columns:
                    return float(frame.loc[date, key])
            close_cols = [col for col in frame.columns if col[-1] == "close"]
            if close_cols:
                return float(frame.loc[date, close_cols[0]])
        if "close" in frame.columns:
            return float(frame.loc[date, "close"])
        candidate = f"{symbol}_close"
        if candidate in frame.columns:
            return float(frame.loc[date, candidate])
        raise KeyError("Unable to locate close price in price_data")






