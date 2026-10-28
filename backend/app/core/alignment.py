"""Put half-hourly actuals and (possibly hourly) forecasts on the same footing."""
from __future__ import annotations

import pandas as pd

MODES = ("hour_mean", "hour_ending", "point")


def infer_resolution_minutes(starts: pd.Series) -> int:
    """30 if any forecast target falls on :30, else 60."""
    return 30 if (starts.dt.minute == 30).any() else 60


def align_actuals(
    actuals: pd.DataFrame, targets: pd.DatetimeIndex, mode: str = "hour_mean", resolution_min: int = 60
) -> pd.Series:
    """Actual wind (MW) corresponding to each forecast target.

    mode:
      hour_mean   - forecast at T describes the hour starting T: mean of actuals at T and T+30m
      hour_ending - forecast at T describes the hour ending T: mean of actuals at T-60m and T-30m
      point       - compare with the single half-hour actual starting at T
    Missing halves give NaN (never a silently partial average).
    For half-hourly forecasts every mode reduces to ``point``.
    """
    if mode not in MODES:
        raise ValueError(f"alignment must be one of {MODES}, got {mode!r}")
    a = actuals.drop_duplicates("startTime", keep="last").set_index("startTime")["generation"].astype(float)
    if mode == "point" or resolution_min <= 30:
        return pd.Series(a.reindex(targets).to_numpy(), index=targets)
    offsets = (0, 30) if mode == "hour_mean" else (-60, -30)
    parts = [a.reindex(targets + pd.Timedelta(minutes=m)).to_numpy() for m in offsets]
    return pd.Series((parts[0] + parts[1]) / 2, index=targets)
