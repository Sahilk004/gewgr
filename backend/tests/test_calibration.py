from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.core.calibration import add_calibration, apply_basis, calibration_report, fit_linear
from app.core.decision import decision_view
from app.core.evaluation import build_evaluation
from app.core.metrics import summarize
from app.synthetic import make_synthetic

WINDOW = (date(2026, 1, 1), date(2026, 1, 31))


def biased_data():
    """Forecasts that run 15% high plus 500 MW, like the proportional offset seen in real data."""
    actuals, forecasts = make_synthetic()
    forecasts["generation"] = forecasts["generation"] * 1.15 + 500
    return actuals, forecasts


def test_fit_linear_recovers_line():
    f = np.arange(10.0)
    slope, intercept = fit_linear(f, 2 * f + 5)
    assert slope == pytest.approx(2.0) and intercept == pytest.approx(5.0)


def test_fit_linear_rejects_constant_forecast():
    with pytest.raises(ValueError):
        fit_linear([1, 1, 1], [1, 2, 3])


def test_calibration_is_leave_one_day_out():
    rows = []
    for day, mult in [("2026-01-01", 2), ("2026-01-02", 2), ("2026-01-03", 100)]:
        for f in range(1, 41):
            rows.append({"delivery_date": day, "forecast": float(f), "actual": float(mult * f)})
    ev = add_calibration(pd.DataFrame(rows), min_obs=20)
    day3 = ev[ev["delivery_date"] == "2026-01-03"]
    # day 3 is calibrated from days 1-2 only (actual = 2 x forecast), ignoring its own 100x outcome
    assert day3["cal_forecast"].to_numpy() == pytest.approx(2 * day3["forecast"].to_numpy())


def test_days_without_enough_other_data_are_dropped():
    ev = pd.DataFrame({"delivery_date": ["a"] * 5, "forecast": np.arange(5.0), "actual": np.arange(5.0)})
    out = apply_basis(add_calibration(ev, min_obs=100), "calibrated")
    assert out.empty


def test_unknown_basis_rejected():
    with pytest.raises(ValueError):
        apply_basis(pd.DataFrame(), "nope")


def test_calibration_removes_proportional_offset():
    actuals, forecasts = biased_data()
    raw = build_evaluation(forecasts, actuals, WINDOW, "09:30", "hour_mean")
    cal = apply_basis(add_calibration(raw), "calibrated")
    r, c = summarize(raw), summarize(cal)
    assert r["bias"] > 1000
    assert abs(c["bias"]) < 0.2 * r["bias"]
    assert c["mae"] < r["mae"]


def test_report_shape():
    actuals, forecasts = biased_data()
    rep = calibration_report(build_evaluation(forecasts, actuals, WINDOW, "09:30", "hour_mean"))
    assert rep["offset_pct"] > 10 and 0.5 < rep["slope"] < 1.1
    assert rep["calibrated"]["mae"] < rep["raw"]["mae"]


def test_decision_view_calibrated_pulls_forecast_toward_actual():
    actuals, forecasts = biased_data()
    raw = build_evaluation(forecasts, actuals, WINDOW, "09:30", "hour_mean")
    cal = apply_basis(add_calibration(raw), "calibrated")
    d = date(2026, 1, 15)
    r = decision_view(forecasts, actuals, raw, d, "09:30", "hour_mean", 0.9)["rows"]
    c = decision_view(forecasts, actuals, cal, d, "09:30", "hour_mean", 0.9, basis="calibrated", raw_evaluation=raw)["rows"]
    assert (c["forecast"] - c["actual"]).abs().mean() < (r["forecast"] - r["actual"]).abs().mean()
