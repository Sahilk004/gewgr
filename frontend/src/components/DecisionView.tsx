import { useState } from "react";
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../api";
import { describeAge, fmtMW, londonTime } from "../format";
import { Decision, Meta, Params } from "../types";
import { Async, COLORS, Section, Strip } from "./ui";

const clock = (iso: string) => londonTime(iso, { hour: "2-digit", minute: "2-digit" });
const day = (iso: string) => londonTime(iso, { weekday: "short", day: "numeric", month: "short" });

export default function DecisionView({ params, meta }: { params: Params; meta: Meta }) {
  const [date, setDate] = useState("2026-01-15");
  const q = useApi<Decision>(`/decision/${date}`, params as unknown as Record<string, string | number>);

  return (
    <>
      <label className="inline">
        Delivery day
        <input type="date" value={date} min={meta.delivery_start} max={meta.delivery_end} onChange={(e) => e.target.value && setDate(e.target.value)} />
      </label>
      <Async q={q}>
        {(d) => {
          const s = d.summary;
          const rows = d.rows.map((r) => ({
            t: Date.parse(r.startTime),
            forecast: r.forecast,
            actual: r.actual,
            band: r.low != null && r.high != null ? [r.low, r.high] : null,
          }));
          return (
            <>
              <h2 className="lede">
                {s.latest_publish_utc ? (
                  <>
                    For delivery on {day(`${s.delivery_date}T12:00:00Z`)}, the buyer decides by {s.cutoff_local.slice(11)} on{" "}
                    {day(s.cutoff_utc)}. The latest forecast they had was published at {clock(s.latest_publish_utc)}, {(s.min_age_h ?? 0) < 1 / 60 ? "exactly at the cutoff" : `${describeAge(s.min_age_h ?? 0)} before the cutoff`}.
                  </>
                ) : (
                  "No forecast was published before the cutoff for this day."
                )}
              </h2>
              <Strip
                stats={[
                  { label: "Peak forecast", value: fmtMW(s.peak_mw) },
                  { label: "Lowest forecast", value: fmtMW(s.trough_mw) },
                  { label: "Average forecast", value: fmtMW(s.mean_mw) },
                  { label: "Plan for less wind by", value: fmtMW(s.band?.shortfall_mw), hint: `${Math.round(params.confidence * 100)}% of days`, tone: "short" },
                  { label: "Plan for more wind by", value: fmtMW(s.band?.surplus_mw), hint: `${Math.round(params.confidence * 100)}% of days`, tone: "surplus" },
                ]}
              />
              <Section title="Forecast known at the cutoff" aside="The shaded band comes from forecast errors on the other days in the month, so it uses nothing the buyer could not have known. The actual line is hindsight.">
                <div className="chart tall">
                  <ResponsiveContainer>
                    <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
                      <CartesianGrid stroke={COLORS.grid} vertical={false} />
                      <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={(t: number) => clock(new Date(t).toISOString())} />
                      <YAxis domain={[0, (m: number) => Math.ceil(m / 4000) * 4000]} tickCount={6} tickFormatter={(v: number) => `${v / 1000}`} label={{ value: "GW", angle: -90, position: "insideLeft" }} />
                      <Tooltip labelFormatter={(t) => clock(new Date(Number(t)).toISOString())} formatter={(v) => (Array.isArray(v) ? `${fmtMW(Number(v[0]))} to ${fmtMW(Number(v[1]))}` : fmtMW(Number(v)))} />
                      <Legend />
                      <Area dataKey="band" name="Likely range" stroke="none" fill={COLORS.band} fillOpacity={0.14} isAnimationActive={false} />
                      <Line dataKey="forecast" name="Forecast at cutoff" stroke={COLORS.forecast} strokeWidth={2.5} dot={false} isAnimationActive={false} />
                      <Line dataKey="actual" name="Actual (hindsight)" stroke={COLORS.actual} strokeWidth={2} strokeDasharray="5 4" dot={false} connectNulls isAnimationActive={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </Section>
            </>
          );
        }}
      </Async>
    </>
  );
}
