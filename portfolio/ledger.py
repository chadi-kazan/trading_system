"""Paper trading ledger for simulated trades."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd


@dataclass
class Trade:
    symbol: str
    side: str
    quantity: int
    price: float
    timestamp: pd.Timestamp
    fees: float = 0.0


class PaperTradingLedger:
    """Manages paper trades and calculates unrealized/realized PnL."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else None
        columns = ["symbol", "side", "quantity", "price", "timestamp", "fees"]
        self.trades = pd.DataFrame(columns=columns)
        self.trades["timestamp"] = pd.to_datetime(self.trades["timestamp"])

        if self.path and self.path.exists():
            self.trades = pd.read_csv(self.path, parse_dates=["timestamp"])

    def record_trade(self, trade: Trade) -> None:
        entry = {
            "symbol": trade.symbol,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": trade.price,
            "timestamp": pd.Timestamp(trade.timestamp),
            "fees": trade.fees,
        }
        self.trades = pd.concat([self.trades, pd.DataFrame([entry])], ignore_index=True)
        if self.path:
            self.trades.to_csv(self.path, index=False)

    def positions(self) -> pd.DataFrame:
        if self.trades.empty:
            return pd.DataFrame(columns=["symbol", "quantity", "avg_price"])

        grouped = self.trades.groupby("symbol")
        qty = grouped.apply(self._net_quantity)
        avg_price = grouped.apply(self._avg_price)
        positions = pd.DataFrame({"quantity": qty, "avg_price": avg_price})
        positions = positions[positions["quantity"] != 0]
        positions.reset_index(inplace=True)
        return positions

    def realized_pnl(self) -> float:
        pnl = 0.0
        inventory: dict[str, List[tuple[int, float]]] = {}

        for _, row in self.trades.iterrows():
            symbol = row["symbol"]
            qty = int(row["quantity"])
            price = float(row["price"])
            side = row["side"].lower()
            fees = float(row.get("fees", 0.0))

            if side == "buy":
                inventory.setdefault(symbol, []).append((qty, price))
            elif side == "sell":
                remaining = qty
                lots = inventory.get(symbol, [])
                while remaining > 0 and lots:
                    lot_qty, lot_price = lots.pop(0)
                    matched = min(remaining, lot_qty)
                    pnl += (price - lot_price) * matched - fees
                    if lot_qty > matched:
                        lots.insert(0, (lot_qty - matched, lot_price))
                    remaining -= matched
                inventory[symbol] = lots

        return pnl

    def _net_quantity(self, trades: pd.DataFrame) -> int:
        buys = trades[trades["side"].str.lower() == "buy"]["quantity"].sum()
        sells = trades[trades["side"].str.lower() == "sell"]["quantity"].sum()
        return int(buys - sells)

    def _avg_price(self, trades: pd.DataFrame) -> float:
        buys = trades[trades["side"].str.lower() == "buy"]
        total_qty = buys["quantity"].sum()
        if total_qty == 0:
            return 0.0
        total_cost = (buys["quantity"] * buys["price"]).sum()
        return float(total_cost / total_qty)


__all__ = ["PaperTradingLedger", "Trade"]
