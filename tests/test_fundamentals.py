from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_pipeline.fundamentals import load_fundamental_metrics


def test_load_fundamental_metrics_from_json(tmp_path: Path):
    fundamentals_dir = tmp_path / "fundamentals"
    fundamentals_dir.mkdir(parents=True, exist_ok=True)
    (fundamentals_dir / "TEST.json").write_text('{"data": {"earnings_growth": "0.25", "relative_strength": 0.9}}')

    metrics = load_fundamental_metrics("test", tmp_path)
    assert metrics == {"earnings_growth": 0.25, "relative_strength": 0.9}


def test_load_fundamental_metrics_from_csv(tmp_path: Path):
    df = pd.DataFrame(
        {
            "symbol": ["ABC", "XYZ"],
            "earnings_growth": [0.1, 0.2],
            "relative_strength": [0.3, 0.4],
        }
    )
    df.to_csv(tmp_path / "fundamentals.csv", index=False)

    metrics = load_fundamental_metrics("xyz", tmp_path)
    assert metrics == {"earnings_growth": 0.2, "relative_strength": 0.4}
