from __future__ import annotations

import pandas as pd

from portfolio.alerts import DrawdownAlertConfig, DrawdownAlertManager


def _equity_curve() -> pd.Series:
    data = [100, 110, 95, 105, 80, 120, 75, 125]
    dates = pd.date_range("2024-01-01", periods=len(data), freq="D")
    return pd.Series(data, index=dates)


def test_drawdown_alerts_trigger_and_throttle():
    manager = DrawdownAlertManager(DrawdownAlertConfig(threshold=0.15, min_interval_days=3))
    curve = _equity_curve()

    alerts1 = manager.process_equity_curve(curve)
    assert alerts1

    extended_curve = pd.concat([curve, pd.Series([90, 130], index=pd.date_range("2024-01-08", periods=2, freq="D"))])
    alerts2 = manager.process_equity_curve(extended_curve)
    assert alerts2  # new drawdown after cooldown

    extended_curve2 = pd.concat([extended_curve, pd.Series([70, 130], index=pd.date_range("2024-01-11", periods=2, freq="D"))])
    alerts3 = manager.process_equity_curve(extended_curve2)
    assert alerts3
