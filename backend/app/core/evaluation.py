"""Join the forecast the buyer had with what actually happened."""
from __future__ import annotations

from datetime import date

import pandas as pd

from .alignment import align_actuals, infer_resolution_minutes
from .selection import LONDON, select_latest_before_cutoff

Window = tuple[date, date]


def restrict_to_window(df: pd.DataFrame, start: date, end: date, col: str = "startTime") -> pd.DataFrame:
    d = df[col].dt.tz_convert(LONDON).dt.date
    return df[(d >= start) & (d <= end)]


def attach_actuals(chosen: pd.DataFrame, actuals: pd.DataFrame, alignment: str, resolution: int) -> pd.DataFrame:
    out = chosen.copy()
    targets = pd.DatetimeIndex(out["startTime"])
    out["actual"] = align_actuals(actuals, targets, alignment, resolution).to_numpy()
    return out


def build_evaluation(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    window: Window,
    cutoff: str = "09:30",
    alignment: str = "hour_mean",
    days_before: int = 1,
) -> pd.DataFrame:
    """One row per delivery target with forecast-at-cutoff, actual and error.

    error = forecast - actual. Positive => forecast too high => buyer under-buys (shortfall risk).
    """
    resolution = infer_resolution_minutes(forecasts["startTime"])
    chosen = select_latest_before_cutoff(restrict_to_window(forecasts, *window), cutoff, days_before)
    chosen = attach_actuals(chosen, actuals, alignment, resolution)
    chosen = chosen.dropna(subset=["actual"]).rename(columns={"generation": "forecast"})
    chosen["error"] = chosen["forecast"] - chosen["actual"]
    chosen["abs_error"] = chosen["error"].abs()
    local = chosen["startTime"].dt.tz_convert(LONDON)
    chosen["delivery_date"] = local.dt.strftime("%Y-%m-%d")
    chosen["hour_of_day"] = local.dt.hour
    return chosen.reset_index(drop=True)
