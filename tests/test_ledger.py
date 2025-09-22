from __future__ import annotations

from pathlib import Path

import pandas as pd

from portfolio.ledger import PaperTradingLedger, Trade


def test_record_and_persist_trades(tmp_path: Path):
    ledger_path = tmp_path / "ledger.csv"
    ledger = PaperTradingLedger(path=ledger_path)

    trade = Trade(symbol="AAPL", side="buy", quantity=10, price=100, timestamp=pd.Timestamp("2024-01-01"))
    ledger.record_trade(trade)

    assert ledger_path.exists()
    reloaded = PaperTradingLedger(path=ledger_path)
    assert len(reloaded.trades) == 1


def test_positions_and_realized_pnl():
    ledger = PaperTradingLedger()
    ledger.record_trade(Trade("AAPL", "buy", 10, 100, pd.Timestamp("2024-01-01")))
    ledger.record_trade(Trade("AAPL", "buy", 5, 110, pd.Timestamp("2024-01-02")))
    ledger.record_trade(Trade("AAPL", "sell", 8, 120, pd.Timestamp("2024-01-03")))

    positions = ledger.positions()
    assert len(positions) == 1
    pos = positions.iloc[0]
    assert pos["symbol"] == "AAPL"
    assert pos["quantity"] == 7
    assert abs(pos["avg_price"] - 103.3333) < 1e-3

    pnl = ledger.realized_pnl()
    assert pnl > 0


def test_empty_ledger_returns_zero_metrics():
    ledger = PaperTradingLedger()
    assert ledger.positions().empty
    assert ledger.realized_pnl() == 0.0
