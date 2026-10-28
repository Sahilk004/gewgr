from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.core.alignment import align_actuals, infer_resolution_minutes
from app.core.decision import decision_view
from app.core.evaluation import build_evaluation
from app.core.metrics import by_group, by_horizon, by_level, risk_buffer, summarize
from app.synthetic import make_synthetic

WINDOW = (date(2026, 1, 1), date(2026, 1, 31))


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_align_hour_mean_and_modes():
    act = pd.DataFrame({"startTime": [ts("2026-01-15 11:30"), ts("2026-01-15 12:00"), ts("2026-01-15 12:30")],
                        "generation": [10.0, 20.0, 40.0]})
    t = pd.DatetimeIndex([ts("2026-01-15 12:00")])
    assert align_actuals(act, t, "hour_mean", 60).iloc[0] == 30.0
    assert align_actuals(act, t, "point", 60).iloc[0] == 20.0
    # hour ending at 12:00 needs 11:00 which is missing -> NaN, not a partial average
    assert np.isnan(align_actuals(act, t, "hour_ending", 60).iloc[0])
    with pytest.raises(ValueError):
        align_actuals(act, t, "nope", 60)


def test_resolution_inference():
    s = pd.Series(pd.to_datetime(["2026-01-01 00:00", "2026-01-01 01:00"], utc=True))
    assert infer_resolution_minutes(s) == 60
    s2 = pd.Series(pd.to_datetime(["2026-01-01 00:00", "2026-01-01 00:30"], utc=True))
    assert infer_resolution_minutes(s2) == 30


def test_summarize_hand_computed():
    df = pd.DataFrame({"forecast": [110.0, 80.0, 130.0], "actual": [100.0, 100.0, 100.0]})
    df["error"] = df["forecast"] - df["actual"]  # 10, -20, 30
    df["abs_error"] = df["error"].abs()
    m = summarize(df)
    assert m["n"] == 3
    assert m["mae"] == pytest.approx(20.0)
    assert m["bias"] == pytest.approx(20 / 3)
    assert m["rmse"] == pytest.approx(np.sqrt((100 + 400 + 900) / 3))
    assert m["nmae_pct"] == pytest.approx(20.0)
    assert m["overforecast_share"] == pytest.approx(2 / 3)


def test_summarize_empty():
    assert summarize(pd.DataFrame()) == {"n": 0}


def test_risk_buffer_directional():
    errs = np.concatenate([np.full(90, 10.0), np.full(10, 100.0)])  # over-forecast tail only
    df = pd.DataFrame({"error": errs, "hour_of_day": 0})
    rb = risk_buffer(df, 0.95)
    assert rb["shortfall_mw"] == pytest.approx(100.0)
    assert rb["surplus_mw"] == 0.0
    assert sum(b["count"] for b in rb["histogram"]) == 100


def test_end_to_end_cutoff_matters_and_bias_detected():
    actuals, forecasts = make_synthetic(bias_mw=500.0)
    ev = build_evaluation(forecasts, actuals, WINDOW, "09:30", "hour_mean")
    assert len(ev) == 31 * 24
    assert (ev["publishTime"] <= ev["cutoff"]).all()
    assert summarize(ev)["bias"] > 300  # injected +500 MW bias is visible (clipping at 0 shaves a little)
    # Deciding later (closer to delivery) must not make things worse on average
    late = build_evaluation(forecasts, actuals, WINDOW, "23:00", "hour_mean")
    assert summarize(late)["mae"] < summarize(ev)["mae"]


def test_error_grows_with_horizon():
    actuals, forecasts = make_synthetic()
    rows = by_horizon(forecasts, actuals, WINDOW, "hour_mean", horizons=range(1, 49, 12))
    maes = [r["mae"] for r in rows]
    assert maes == sorted(maes)


def test_groupings_and_decision_view():
    actuals, forecasts = make_synthetic()
    ev = build_evaluation(forecasts, actuals, WINDOW, "09:30", "hour_mean")
    assert len(by_group(ev, "hour_of_day")) == 24
    assert [r["level"] for r in by_level(ev)] == ["Low wind", "Medium wind", "High wind"]
    out = decision_view(forecasts, actuals, ev, date(2026, 1, 15), "09:30", "hour_mean", 0.9)
    rows, summ = out["rows"], out["summary"]
    assert summ["n_points"] == 24 and summ["cutoff_local"] == "2026-01-14 09:30"
    assert (rows["publishTime"] <= pd.Timestamp("2026-01-14 09:30", tz="UTC")).all()
    assert (rows["low"] <= rows["forecast"]).all() and (rows["high"] >= rows["forecast"]).all()
