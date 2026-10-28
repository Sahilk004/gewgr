# Decisions and assumptions

| # | Decision | Why | Revisit if |
|---|----------|-----|-----------|
| 1 | Decision cutoff defaults to **09:20 London time on D-1** (earliest auction close), user-adjustable | GB day-ahead auctions close roughly 09:20-09:50; verify against the exchange rules. Forecasts are published at :30, so a 09:30 cutoff would sit exactly on a publication and flip with a 09:20 vs 09:50 close. MAE moves under 1% between 06:00 and 11:00 cutoffs. | The client trades on a specific auction |
| 2 | Cutoff is **inclusive** (`publishTime <= cutoff`) and evaluated in **Europe/London**, then converted to UTC | Matches how a trader reads "by 09:30". Tested across DST | - |
| 3 | Forecast used = **latest `publishTime` at or before cutoff** for each target | Using the newest forecast of any age leaks information the buyer did not have | - |
| 4 | If WINDFOR is hourly and FUELHH half-hourly, compare with the **mean of the two matching half-hours** (`hour_mean`) | Same footing, uses all actuals. `hour_ending` and `point` are selectable; `python -m scripts.diagnose` shows which fits best on real data | Diagnose shows another alignment fits clearly better |
| 5 | Error = forecast - actual. Positive = forecast too high = **shortfall risk** | One convention everywhere, stated in the UI | - |
| 6 | Report MAE, RMSE, bias, nMAE, P50/P90/P99 absolute error. **No MAPE** | Wind output can approach zero | - |
| 7 | Risk buffer = empirical error quantiles, estimated on **other days only** in the decision view | Avoids using the delivery day's own error | More data available: fit per hour or per wind regime |
| 8 | Data committed as CSV snapshots, no live Elexon calls at runtime | Deterministic demo, no outage or rate-limit risk | Productionising: scheduled ingestion into a DB |
| 9 | FUELHH wind may not cover the same fleet as WINDFOR | Persistent bias even at short lead times indicates a definition gap, not forecast skill | - |
| 10 | Real-data diagnosis (Jan 2026): forecast mean 13.4 GW vs metered 11.6 GW; +1.6 GW bias already at 1h lead; correlation 0.93; offset grows with wind level; 28/31 days positive | The offset is a series mismatch, not forecast skill. Cause is a hypothesis (curtailment or fleet scope), not confirmed | Elexon/NESO confirm the scope of WINDFOR vs FUELHH |
| 11 | Offer a **calibrated** basis: actual ~ a + b x forecast, fitted **leave-one-day-out** | A single mean bias does not fit (offset varies with wind). Leave-one-day-out stops a day's own outcome leaking into its forecast | Production: fit on trailing history only |
| 12 | Alignment stays `hour_mean` | After removing the offset all three modes give the same error (centred MAE ~1,460 MW) | - |
| 13 | ~20% of WINDFOR rows are published after their target time. They are never eligible because the cutoff is on D-1 | Data hygiene note | - |
