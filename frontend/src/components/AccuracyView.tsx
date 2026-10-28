import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../api";
import { fmtMW, fmtNum, fmtPct, fmtSigned, londonTime } from "../format";
import { Calibration, GroupRow, Params, SeriesRow, Summary } from "../types";
import { Async, COLORS, Section, Strip } from "./ui";

const P = (p: Params) => ({ cutoff: p.cutoff, alignment: p.alignment, basis: p.basis });

export default function AccuracyView({ params }: { params: Params }) {
  const p = P(params);
  const summary = useApi<Summary>("/metrics", p);
  const series = useApi<{ rows: SeriesRow[] }>("/series", p);
  const byDay = useApi<{ rows: GroupRow[] }>("/metrics/by-day", p);
  const byHour = useApi<{ rows: GroupRow[] }>("/metrics/by-hour", p);
  const byLevel = useApi<{ rows: (GroupRow & { level: string; actual_min: number; actual_max: number })[] }>("/metrics/by-level", p);

  const cal = useApi<Calibration>("/calibration", { cutoff: params.cutoff, alignment: params.alignment });

  return (
    <>
      <Async q={cal}>
        {(c) =>
          c.raw && c.calibrated ? (
            <Section
              title="Forecast offset check"
              aside={`Compared with metered output, the published forecast runs ${fmtPct(c.offset_pct)} high over the month. A straight-line fit gives actual ≈ ${fmtNum(c.intercept)} MW + ${fmtNum(c.slope, 2)} × forecast. Each day is calibrated using only the other days.`}
            >
              <table>
                <thead><tr><th>Basis</th><th className="num">MAE</th><th className="num">RMSE</th><th className="num">Bias</th><th className="num">Worst 10%</th></tr></thead>
                <tbody>
                  {([["Raw forecast", c.raw], ["Calibrated forecast", c.calibrated]] as const).map(([name, m]) => (
                    <tr key={name} className={(name === "Raw forecast") === (params.basis === "raw") ? "current" : ""}>
                      <td>{name}</td><td className="num">{fmtMW(m.mae)}</td><td className="num">{fmtMW(m.rmse)}</td><td className="num">{fmtSigned(m.bias)}</td><td className="num">{fmtMW(m.p90_abs)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>
          ) : null
        }
      </Async>
      <Async q={summary}>
        {(m) => (
          <>
            <Strip
              stats={[
                { label: "Typical miss (MAE)", value: fmtMW(m.mae), hint: `${fmtPct(m.nmae_pct)} of average wind` },
                { label: "RMSE", value: fmtMW(m.rmse), hint: "penalises big misses" },
                { label: "Bias", value: fmtSigned(m.bias), hint: (m.bias ?? 0) > 0 ? "forecast too high on average" : "forecast too low on average" },
                { label: "Worst 10% of misses exceed", value: fmtMW(m.p90_abs) },
                { label: "Worst 1% exceed", value: fmtMW(m.p99_abs) },
              ]}
            />
            <p className="note">{fmtNum(m.n)} forecast intervals compared. Positive error means the forecast was above what was generated.</p>
          </>
        )}
      </Async>

      <Section title="Forecast at cutoff against actual output">
        <Async q={series}>
          {(s) => {
            const rows = s.rows.map((r) => ({ t: Date.parse(r.startTime), forecast: r.forecast, actual: r.actual }));
            return (
              <div className="chart">
                <ResponsiveContainer>
                  <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
                    <CartesianGrid stroke={COLORS.grid} vertical={false} />
                    <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={(t: number) => londonTime(new Date(t).toISOString(), { day: "numeric", month: "short" })} />
                    <YAxis domain={[0, (m: number) => Math.ceil(m / 4000) * 4000]} tickCount={6} tickFormatter={(v: number) => `${v / 1000}`} label={{ value: "GW", angle: -90, position: "insideLeft" }} />
                    <Tooltip labelFormatter={(t) => londonTime(new Date(Number(t)).toISOString(), { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} formatter={(v) => fmtMW(Number(v))} />
                    <Legend />
                    <Line dataKey="actual" name="Actual" stroke={COLORS.actual} dot={false} strokeWidth={1.5} isAnimationActive={false} />
                    <Line dataKey="forecast" name="Forecast at cutoff" stroke={COLORS.forecast} dot={false} strokeWidth={1.5} isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            );
          }}
        </Async>
      </Section>

      <Section title="Which days were hardest" aside="Mean error per delivery day. Bars above zero: forecast too high (supply shortfall risk). Below zero: forecast too low.">
        <Async q={byDay}>
          {(d) => (
            <div className="chart short">
              <ResponsiveContainer>
                <BarChart data={d.rows} margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
                  <CartesianGrid stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="delivery_date" tickFormatter={(s: string) => s.slice(8)} />
                  <YAxis />
                  <Tooltip formatter={(v) => fmtMW(Number(v))} />
                  <ReferenceLine y={0} stroke="var(--muted)" />
                  <Bar dataKey="bias" name="Bias" fill={COLORS.forecast} isAnimationActive={false} />
                  <Bar dataKey="mae" name="MAE" fill={COLORS.actual} isAnimationActive={false} />
                  <Legend />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Async>
      </Section>

      <Section title="Which hours of the day">
        <Async q={byHour}>
          {(d) => (
            <div className="chart short">
              <ResponsiveContainer>
                <BarChart data={d.rows} margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
                  <CartesianGrid stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="hour_of_day" tickFormatter={(h: number) => `${h}:00`} />
                  <YAxis />
                  <Tooltip formatter={(v) => fmtMW(Number(v))} labelFormatter={(h) => `${h}:00 London`} />
                  <ReferenceLine y={0} stroke="var(--muted)" />
                  <Bar dataKey="mae" name="MAE" fill={COLORS.actual} isAnimationActive={false} />
                  <Bar dataKey="bias" name="Bias" fill={COLORS.forecast} isAnimationActive={false} />
                  <Legend />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Async>
      </Section>

      <Section title="Windy against calm periods">
        <Async q={byLevel}>
          {(d) => (
            <table>
              <thead>
                <tr><th>Wind level</th><th>Actual output range</th><th className="num">MAE</th><th className="num">Bias</th><th className="num">Worst 10%</th></tr>
              </thead>
              <tbody>
                {d.rows.map((r) => (
                  <tr key={r.level}>
                    <td>{r.level}</td>
                    <td>{fmtNum(r.actual_min)} to {fmtMW(r.actual_max)}</td>
                    <td className="num">{fmtMW(r.mae)}</td>
                    <td className="num">{fmtSigned(r.bias)}</td>
                    <td className="num">{fmtMW(r.p90_abs)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Async>
      </Section>
    </>
  );
}
