"""Sanity checks to run on real data BEFORE trusting the headline numbers.

Usage (from backend/):  python -m scripts.diagnose
Answers: what resolution/horizons does WINDFOR have, which actual-alignment fits best once the
level offset is removed, is the offset additive or proportional, and does it persist at short lead times?
"""
import numpy as np

from app.config import Settings
from app.core.alignment import MODES, infer_resolution_minutes
from app.core.evaluation import build_evaluation
from app.core.metrics import by_group, by_horizon, by_level
from app.data import DataStore


def main() -> None:
    s = DataStore(Settings.from_env())
    s.ensure_loaded()
    cfg, fc = s.settings, s.forecasts
    horizon = (fc["startTime"] - fc["publishTime"]).dt.total_seconds() / 3600
    print(f"source={s.meta.get('source')}  forecasts={len(fc):,}  actuals={len(s.actuals):,}")
    print(f"forecast resolution: {infer_resolution_minutes(fc['startTime'])} min")
    print(f"horizon hours: min={horizon.min():.1f} median={horizon.median():.1f} max={horizon.max():.1f}")
    print("publishTime minutes:", fc["publishTime"].dt.minute.value_counts().to_dict())
    neg = int((horizon < 0).sum())
    print(f"rows published AFTER their target time: {neg:,} ({neg / len(fc):.1%}); the cutoff rule never selects these")

    print("\n1) Alignment. 'centred MAE' removes the mean offset, so it compares timing fit rather than level:")
    for mode in MODES:
        e = build_evaluation(fc, s.actuals, s.window, cfg.default_cutoff, mode)["error"]
        print(f"  {mode:12s} n={len(e):4d}  MAE={e.abs().mean():8.1f}  bias={e.mean():8.1f}  centred MAE={(e - e.mean()).abs().mean():8.1f}")

    ev = build_evaluation(fc, s.actuals, s.window, cfg.default_cutoff, cfg.default_alignment)
    slope, intercept = np.polyfit(ev["actual"], ev["forecast"], 1)
    print("\n2) Additive or proportional offset? (using the default alignment)")
    print(f"  mean actual={ev['actual'].mean():,.0f} MW   mean forecast={ev['forecast'].mean():,.0f} MW")
    print(f"  forecast = {slope:.3f} x actual + {intercept:,.0f} MW   (correlation {ev[['forecast', 'actual']].corr().iloc[0, 1]:.3f})")
    print(f"  sum(forecast)/sum(actual) = {ev['forecast'].sum() / ev['actual'].sum():.3f}")
    for r in by_level(ev):
        print(f"  {r['level']:12s} actual {r['actual_min']:7,.0f}-{r['actual_max']:7,.0f} MW   bias={r['bias']:8.1f}   MAE={r['mae']:8.1f}")
    days = [r["bias"] for r in by_group(ev, "delivery_date")]
    print(f"  days with positive bias: {sum(b > 0 for b in days)}/{len(days)}   (daily bias range {min(days):,.0f} to {max(days):,.0f} MW)")

    print("\n3) Bias by lead time (a bias that persists at 1-3h is a definition gap, not forecast skill):")
    for row in by_horizon(fc, s.actuals, s.window, cfg.default_alignment, horizons=range(1, 49, 6)):
        print(f"  >= {row['horizon_h']:2d}h  MAE={row['mae']:8.1f}  bias={row['bias']:8.1f}  n={row['n']}")


if __name__ == "__main__":
    main()
