from datetime import date

import pandas as pd
import pytest

from app.core.selection import cutoff_for_delivery_date, parse_hhmm, select_by_min_horizon, select_latest_before_cutoff


def fc(rows):
    return pd.DataFrame(
        [(pd.Timestamp(t, tz="UTC"), pd.Timestamp(p, tz="UTC"), g) for t, p, g in rows],
        columns=["startTime", "publishTime", "generation"],
    )


TARGET = "2026-01-15 12:00"


def test_picks_latest_forecast_before_cutoff():
    df = fc([(TARGET, "2026-01-13 20:00", 100), (TARGET, "2026-01-14 08:00", 200), (TARGET, "2026-01-14 09:00", 300)])
    out = select_latest_before_cutoff(df, "09:30")
    assert out["generation"].tolist() == [300]


def test_never_uses_forecast_published_after_cutoff():
    df = fc([(TARGET, "2026-01-14 09:00", 300), (TARGET, "2026-01-14 10:00", 999), (TARGET, "2026-01-15 06:00", 888)])
    out = select_latest_before_cutoff(df, "09:30")
    assert out["generation"].tolist() == [300]


def test_cutoff_is_inclusive():
    df = fc([(TARGET, "2026-01-14 09:30", 500), (TARGET, "2026-01-14 09:31", 600)])
    assert select_latest_before_cutoff(df, "09:30")["generation"].tolist() == [500]


def test_target_without_eligible_forecast_is_omitted():
    df = fc([(TARGET, "2026-01-14 11:00", 1)])
    assert select_latest_before_cutoff(df, "09:30").empty


def test_cutoff_respects_london_dst():
    # July: London is UTC+1, so 09:30 local == 08:30 UTC. A 08:45 UTC publish is AFTER the cutoff.
    assert cutoff_for_delivery_date(date(2026, 7, 15), "09:30") == pd.Timestamp("2026-07-14 08:30", tz="UTC")
    df = fc([("2026-07-15 12:00", "2026-07-14 08:00", 1), ("2026-07-15 12:00", "2026-07-14 08:45", 2)])
    assert select_latest_before_cutoff(df, "09:30")["generation"].tolist() == [1]


def test_age_and_horizon_columns():
    df = fc([(TARGET, "2026-01-14 09:00", 300)])
    row = select_latest_before_cutoff(df, "09:30").iloc[0]
    assert row["forecast_age_h"] == pytest.approx(0.5)
    assert row["horizon_h"] == pytest.approx(27.0)


def test_each_target_resolved_independently():
    df = fc([("2026-01-15 12:00", "2026-01-14 09:00", 1), ("2026-01-16 12:00", "2026-01-15 09:00", 2),
             ("2026-01-16 12:00", "2026-01-15 11:00", 3)])
    out = select_latest_before_cutoff(df, "09:30").sort_values("startTime")
    assert out["generation"].tolist() == [1, 2]


def test_missing_columns_raise():
    with pytest.raises(ValueError):
        select_latest_before_cutoff(pd.DataFrame({"startTime": []}), "09:30")


@pytest.mark.parametrize("bad", ["9:30", "24:00", "09:60", "abc", ""])
def test_bad_cutoff_rejected(bad):
    with pytest.raises(ValueError):
        parse_hhmm(bad)


def test_min_horizon_selection():
    df = fc([(TARGET, "2026-01-15 06:00", 1), (TARGET, "2026-01-15 10:00", 2), (TARGET, "2026-01-15 11:30", 3)])
    assert select_by_min_horizon(df, 2)["generation"].tolist() == [2]
    assert select_by_min_horizon(df, 7)["generation"].tolist() == []
