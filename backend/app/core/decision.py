"""The decision view: what the buyer saw for one delivery day, with an uncertainty band."""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .alignment import infer_resolution_minutes
from .evaluation import attach_actuals, restrict_to_window
from .calibration import MIN_CAL_OBS, fit_linear
from .metrics import _num, error_quantiles
from .selection import LONDON, cutoff_for_delivery_date, select_latest_before_cutoff


def decision_view(
    forecasts: pd.DataFrame, actuals: pd.DataFrame, evaluation: pd.DataFrame, delivery_date: date,
    cutoff: str, alignment: str, confidence: float, days_before: int = 1,
    basis: str = "raw", raw_evaluation: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Forecast available at the cutoff for `delivery_date`, plus a band from *other* days' errors.

    The band excludes the delivery day itself (leave-one-day-out) so it never uses information
    the buyer would not have had. Actuals are shown only as hindsight.
    """
    resolution = infer_resolution_minutes(forecasts["startTime"])
    day = restrict_to_window(forecasts, delivery_date, delivery_date)
    chosen = select_latest_before_cutoff(day, cutoff, days_before)
    chosen = attach_actuals(chosen, actuals, alignment, resolution).rename(columns={"generation": "forecast"})

    if basis == "calibrated":
        # Calibrate this day's forecast with a fit on the other days only.
        raw = raw_evaluation if raw_evaluation is not None else evaluation
        raw_others = raw[raw["delivery_date"] != delivery_date.isoformat()]
        if len(raw_others) >= MIN_CAL_OBS:
            slope, intercept = fit_linear(raw_others["forecast"], raw_others["actual"])
            chosen["forecast"] = (intercept + slope * chosen["forecast"]).clip(lower=0)

    others = evaluation[evaluation["delivery_date"] != delivery_date.isoformat()]
    q = error_quantiles(others["error"], confidence) if not others.empty else None
    if q is not None:
        # actual = forecast - error. Low case uses the upper error quantile, high case the lower.
        chosen["low"] = (chosen["forecast"] - q[0]).clip(lower=0)
        chosen["high"] = chosen["forecast"] - q[1]

    cutoff_utc = cutoff_for_delivery_date(delivery_date, cutoff, days_before)
    summary: dict[str, Any] = {
        "delivery_date": delivery_date.isoformat(),
        "cutoff_utc": cutoff_utc.isoformat(),
        "cutoff_local": cutoff_utc.tz_convert(LONDON).strftime("%Y-%m-%d %H:%M"),
        "basis": basis,
        "n_points": int(len(chosen)),
        "band": None if q is None else {"confidence": confidence, "shortfall_mw": max(0.0, q[0]), "surplus_mw": max(0.0, -q[1])},
    }
    if not chosen.empty:
        summary.update({
            "latest_publish_utc": chosen["publishTime"].max().isoformat(),
            "earliest_publish_utc": chosen["publishTime"].min().isoformat(),
            "min_age_h": _num(chosen["forecast_age_h"].min()),
            "peak_mw": _num(chosen["forecast"].max()),
            "trough_mw": _num(chosen["forecast"].min()),
            "mean_mw": _num(chosen["forecast"].mean()),
        })
    cols = [c for c in ["startTime", "publishTime", "forecast", "actual", "low", "high"] if c in chosen.columns]
    return {"summary": summary, "rows": chosen[cols]}
