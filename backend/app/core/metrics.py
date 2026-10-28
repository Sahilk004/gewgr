"""Accuracy metrics and risk buffers. Pure functions over the evaluation frame."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .alignment import align_actuals, infer_resolution_minutes
from .evaluation import Window, restrict_to_window
from .selection import select_by_min_horizon

MIN_OBS_FOR_BAND = 30


def _num(x: Any) -> float | None:
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else x


def summarize(df: pd.DataFrame) -> dict[str, Any]:
    """Headline metrics. error = forecast - actual (MW)."""
    if df.empty:
        return {"n": 0}
    e, ae = df["error"], df["abs_error"]
    mean_actual = float(df["actual"].mean())
    mae = float(ae.mean())
    return {
        "n": int(len(df)),
        "mae": _num(mae),
        "rmse": _num(np.sqrt((e**2).mean())),
        "bias": _num(e.mean()),
        # Normalised MAE (% of mean actual output). Preferred over MAPE: wind output can be near zero.
        "nmae_pct": _num(mae / mean_actual * 100) if mean_actual > 0 else None,
        "p50_abs": _num(ae.quantile(0.5)),
        "p90_abs": _num(ae.quantile(0.9)),
        "p99_abs": _num(ae.quantile(0.99)),
        "max_abs": _num(ae.max()),
        "mean_actual": _num(mean_actual),
        "mean_forecast": _num(df["forecast"].mean()),
        "overforecast_share": _num((e > 0).mean()),
    }


def _short(g: pd.DataFrame) -> dict[str, Any]:
    s = summarize(g)
    return {k: s.get(k) for k in ("n", "mae", "rmse", "bias", "p90_abs")}


def by_group(df: pd.DataFrame, key: str) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return [{key: k, **_short(g)} for k, g in df.groupby(key, sort=True)]


def by_level(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Error split by actual wind output tercile (low / medium / high wind)."""
    if len(df) < 3:
        return []
    labels = ["Low wind", "Medium wind", "High wind"]
    bucket = pd.qcut(df["actual"].rank(method="first"), 3, labels=labels)
    rows = []
    for label in labels:
        g = df[bucket == label]
        rows.append({
            "level": label,
            "actual_min": _num(g["actual"].min()),
            "actual_max": _num(g["actual"].max()),
            **_short(g),
        })
    return rows


def by_horizon(
    forecasts: pd.DataFrame, actuals: pd.DataFrame, window: Window, alignment: str,
    horizons: range = range(1, 49),
) -> list[dict[str, Any]]:
    """Accuracy of 'the latest forecast published at least h hours before the target'."""
    fc = restrict_to_window(forecasts, *window)
    resolution = infer_resolution_minutes(forecasts["startTime"])
    rows = []
    for h in horizons:
        chosen = select_by_min_horizon(fc, h)
        if chosen.empty:
            continue
        targets = pd.DatetimeIndex(chosen["startTime"])
        actual = align_actuals(actuals, targets, alignment, resolution).to_numpy()
        err = (chosen["generation"].to_numpy() - actual)
        err = err[~np.isnan(err)]
        if err.size == 0:
            continue
        rows.append({
            "horizon_h": h, "n": int(err.size), "mae": _num(np.abs(err).mean()),
            "rmse": _num(np.sqrt((err**2).mean())), "bias": _num(err.mean()),
        })
    return rows


def error_quantiles(errors: pd.Series, confidence: float) -> tuple[float, float] | None:
    """(upper, lower) error quantiles at `confidence` and `1 - confidence`."""
    if len(errors) < MIN_OBS_FOR_BAND:
        return None
    return float(errors.quantile(confidence)), float(errors.quantile(1 - confidence))


def risk_buffer(df: pd.DataFrame, confidence: float = 0.9, bins: int = 20) -> dict[str, Any]:
    """Extra MW to plan for so the forecast error is covered `confidence` of the time.

    shortfall_mw: wind below forecast (error > 0) -> buyer needs more from other sources.
    surplus_mw:   wind above forecast (error < 0) -> buyer has bought more than needed.
    """
    if df.empty:
        return {"confidence": confidence, "n": 0}
    e = df["error"]
    shortfall = max(0.0, float(e.quantile(confidence)))
    surplus = max(0.0, -float(e.quantile(1 - confidence)))
    by_hour = []
    for hour, g in df.groupby("hour_of_day", sort=True):
        by_hour.append({
            "hour_of_day": int(hour), "n": int(len(g)),
            "shortfall_mw": max(0.0, float(g["error"].quantile(confidence))),
            "surplus_mw": max(0.0, -float(g["error"].quantile(1 - confidence))),
        })
    counts, edges = np.histogram(e.to_numpy(), bins=bins)
    hist = [{"from": float(edges[i]), "to": float(edges[i + 1]), "count": int(counts[i])} for i in range(len(counts))]
    return {
        "confidence": confidence, "n": int(len(e)),
        "shortfall_mw": shortfall, "surplus_mw": surplus,
        "by_hour": by_hour, "histogram": hist,
    }
