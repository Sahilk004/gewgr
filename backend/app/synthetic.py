"""Synthetic data for tests and local demos ONLY. Never deploy this as real data."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def make_synthetic(start: date = date(2025, 12, 30), end: date = date(2026, 2, 1), seed: int = 7,
                   bias_mw: float = 0.0, noise_per_h: float = 60.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Half-hourly actuals and hourly forecasts (48h horizon) with horizon-growing noise."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, end, freq="30min", tz="UTC")
    walk = np.cumsum(rng.normal(0, 180, len(idx)))
    actual = np.clip(7000 + walk - np.convolve(walk, np.ones(200) / 200, mode="same") + 3000 * np.sin(np.arange(len(idx)) / 90) , 200, 20000)
    actuals = pd.DataFrame({"startTime": idx, "generation": actual})
    truth = actuals.set_index("startTime")["generation"]
    hourly_truth = (truth + truth.shift(-1)) / 2

    rows = []
    for pub in pd.date_range(start, end, freq="1h", tz="UTC"):
        for h in range(1, 49):
            t = pub + pd.Timedelta(hours=h)
            if t in hourly_truth.index and not np.isnan(hourly_truth[t]):
                noise = rng.normal(0, noise_per_h * h)
                rows.append((t, pub, max(0.0, hourly_truth[t] + bias_mw + noise)))
    forecasts = pd.DataFrame(rows, columns=["startTime", "publishTime", "generation"])
    return actuals, forecasts


def write_sample(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    actuals, forecasts = make_synthetic()
    actuals.to_csv(out_dir / "actuals.csv", index=False)
    forecasts.to_csv(out_dir / "forecasts.csv", index=False)
    meta = {"source": "synthetic", "fetched_at": datetime.now(timezone.utc).isoformat()}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
