"""Which forecast did the buyer actually have at decision time?

The crux of the product. A target half-hour has many forecast versions (one per
``publishTime``). A day-ahead buyer deciding at the cutoff on D-1 can only use
versions published at or before that cutoff, and uses the latest of those.
All functions are pure (no I/O) so they are easy to test.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

import pandas as pd

LONDON = "Europe/London"
REQUIRED_COLUMNS = {"startTime", "publishTime", "generation"}
_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def parse_hhmm(value: str) -> tuple[int, int]:
    m = _HHMM.match(value)
    if not m:
        raise ValueError(f"cutoff must be HH:MM in 24h format, got {value!r}")
    return int(m.group(1)), int(m.group(2))


def cutoff_for_delivery_date(
    delivery_date: date, cutoff: str = "09:30", days_before: int = 1, tz: str = LONDON
) -> pd.Timestamp:
    """Cutoff instant (UTC) for a delivery day: local HH:MM on ``days_before`` days earlier."""
    hour, minute = parse_hhmm(cutoff)
    d = delivery_date - timedelta(days=days_before)
    local = pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=hour, minute=minute, tz=tz)
    return local.tz_convert("UTC")


def _check_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"forecast frame is missing columns: {sorted(missing)}")


def with_cutoff(fc: pd.DataFrame, cutoff: str, days_before: int = 1, tz: str = LONDON) -> pd.DataFrame:
    """Add a ``cutoff`` column (UTC) to each forecast row, based on its delivery date."""
    _check_columns(fc)
    out = fc.copy()
    dates = out["startTime"].dt.tz_convert(tz).dt.date
    lookup = {d: cutoff_for_delivery_date(d, cutoff, days_before, tz) for d in dates.unique()}
    out["cutoff"] = pd.to_datetime(dates.map(lookup), utc=True)
    return out


def _latest_per_target(df: pd.DataFrame) -> pd.DataFrame:
    # Stable sort + keep="last": ties on publishTime resolve to the last input row.
    ordered = df.sort_values(["startTime", "publishTime"], kind="stable")
    return ordered.drop_duplicates("startTime", keep="last").reset_index(drop=True)


def select_latest_before_cutoff(
    fc: pd.DataFrame, cutoff: str = "09:30", days_before: int = 1, tz: str = LONDON
) -> pd.DataFrame:
    """One row per target: the latest forecast with publishTime <= cutoff (inclusive).

    Adds ``cutoff``, ``horizon_h`` (target - publish) and ``forecast_age_h`` (cutoff - publish).
    Targets with no eligible forecast are omitted.
    """
    df = with_cutoff(fc, cutoff, days_before, tz)
    chosen = _latest_per_target(df[df["publishTime"] <= df["cutoff"]])
    chosen["horizon_h"] = (chosen["startTime"] - chosen["publishTime"]).dt.total_seconds() / 3600
    chosen["forecast_age_h"] = (chosen["cutoff"] - chosen["publishTime"]).dt.total_seconds() / 3600
    return chosen


def select_by_min_horizon(fc: pd.DataFrame, min_horizon_h: float) -> pd.DataFrame:
    """One row per target: the latest forecast published at least ``min_horizon_h`` hours ahead."""
    _check_columns(fc)
    horizon = (fc["startTime"] - fc["publishTime"]).dt.total_seconds() / 3600
    chosen = _latest_per_target(fc[horizon >= min_horizon_h])
    chosen["horizon_h"] = (chosen["startTime"] - chosen["publishTime"]).dt.total_seconds() / 3600
    return chosen
