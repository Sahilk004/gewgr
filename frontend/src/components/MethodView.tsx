import { fmtNum, londonTime } from "../format";
import { Meta, Params } from "../types";

export default function MethodView({ meta, params }: { meta: Meta; params: Params }) {
  return (
    <article className="prose">
      <h2>How the numbers are made</h2>
      <p>
        For each delivery interval in January 2026 we find every wind forecast published for it, discard any published after the
        decision cutoff ({params.cutoff} London time on the day before), and keep the most recent of the rest. That is the forecast a
        day-ahead buyer actually had. It is compared with the metered wind output once the day has happened.
      </p>
      <h2>Forecast offset and calibration</h2>
      <p>
        The published forecast runs well above metered wind output, and the gap is already present for forecasts made an hour ahead,
        so it is a systematic difference between the two series rather than weather forecasting skill. It is larger in windier periods.
        The <b>calibrated</b> basis applies a straight-line correction fitted on all other days. It is a practical fix for planning, not an
        explanation: possible causes include wind that is curtailed after the forecast is made, or the two series covering different wind farms.
      </p>
      <h2>Definitions</h2>
      <ul>
        <li><b>Error</b> is forecast minus actual. Positive means the forecast was too high.</li>
        <li><b>MAE</b> is the average size of the miss. <b>RMSE</b> weights large misses more. <b>Bias</b> is the average signed error.</li>
        <li><b>Normalised MAE</b> expresses MAE as a share of average actual output. We avoid percentage error per interval because wind can fall close to zero.</li>
        <li><b>Risk buffer</b> is an empirical quantile of past errors, not a statistical guarantee.</li>
      </ul>
      <h2>Assumptions and limits</h2>
      <ul>
        <li>The cutoff is an assumption you can change; GB day-ahead auctions close between about 09:20 and 09:50 London time.</li>
        <li>Forecasts are {meta.forecast_resolution_min}-minute resolution while actuals are half-hourly. Alignment is set to <code>{params.alignment}</code>: hourly forecasts are compared with the average of the matching half-hours.</li>
        <li>Actuals come from the FUELHH wind series and may not cover exactly the same wind farms as the forecast, which can show up as bias.</li>
        <li>One month of data is a small sample. Buffers will move as more days are added.</li>
        <li>This analysis covers wind only. Demand and other generation are not modelled.</li>
      </ul>
      <h2>Data</h2>
      <p>
        Source: <code>{meta.source}</code>{meta.fetched_at ? `, fetched ${londonTime(meta.fetched_at, { day: "numeric", month: "short", year: "numeric" })}` : ""}.
        {" "}{fmtNum(meta.n_actuals)} actual readings and {fmtNum(meta.n_forecasts)} forecast versions, covering {meta.delivery_start} to {meta.delivery_end}.
      </p>
    </article>
  );
}
