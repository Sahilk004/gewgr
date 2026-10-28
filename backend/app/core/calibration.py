"""Linear calibration of the forecast against metered output: actual ~ intercept + slope * forecast.

Each delivery day is calibrated with a fit on *all other days* (leave-one-day-out), so a day's own
outcome never leaks into its calibrated forecast. In production this would be fitted on trailing history.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .metrics import summarize

MIN_CAL_OBS = 100
BASES = ("raw", "calibrated")


def fit_linear(forecast, actual) -> tuple[float, float]:
    f, a = np.asarray(forecast, dtype=float), np.asarray(actual, dtype=float)
    if f.size < 2 or np.ptp(f) == 0:
        raise ValueError("need at least two distinct forecast values to calibrate")
    slope, intercept = np.polyfit(f, a, 1)
    return float(slope), float(intercept)


def add_calibration(ev: pd.DataFrame, min_obs: int = MIN_CAL_OBS) -> pd.DataFrame:
    """Add ``cal_forecast`` (leave-one-day-out). Days with too little other-day data get NaN."""
    out = ev.reset_index(drop=True).copy()
    f, a = out["forecast"].to_numpy(float), out["actual"].to_numpy(float)
    cal = np.full(len(out), np.nan)
    for _, idx in out.groupby("delivery_date").indices.items():
        keep = np.ones(len(out), dtype=bool)
        keep[idx] = False
        if keep.sum() < min_obs:
            continue
        slope, intercept = fit_linear(f[keep], a[keep])
        cal[idx] = np.maximum(0.0, intercept + slope * f[idx])
    out["cal_forecast"] = cal
    return out


def apply_basis(ev: pd.DataFrame, basis: str) -> pd.DataFrame:
    """Return the frame with forecast/error expressed on the chosen basis."""
    if basis == "raw":
        return ev
    if basis != "calibrated":
        raise ValueError(f"basis must be one of {BASES}, got {basis!r}")
    out = ev.dropna(subset=["cal_forecast"]).copy()
    out["raw_forecast"] = out["forecast"]
    out["forecast"] = out["cal_forecast"]
    out["error"] = out["forecast"] - out["actual"]
    out["abs_error"] = out["error"].abs()
    return out.reset_index(drop=True)


def calibration_report(raw_ev: pd.DataFrame) -> dict[str, Any]:
    """Offset diagnosis: full-sample fit, plus raw vs leave-one-day-out calibrated accuracy."""
    if len(raw_ev) < MIN_CAL_OBS:
        return {"n": int(len(raw_ev))}
    slope, intercept = fit_linear(raw_ev["forecast"], raw_ev["actual"])
    calibrated = apply_basis(add_calibration(raw_ev), "calibrated")
    raw_same_rows = raw_ev.loc[raw_ev["startTime"].isin(calibrated["startTime"])]
    return {
        "n": int(len(raw_ev)), "slope": slope, "intercept": intercept,
        "offset_pct": float(raw_ev["forecast"].sum() / raw_ev["actual"].sum() * 100 - 100),
        "raw": summarize(raw_same_rows), "calibrated": summarize(calibrated),
    }
