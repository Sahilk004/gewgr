import { CartesianGrid, Legend, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../api";
import { fmtMW, fmtSigned } from "../format";
import { Params } from "../types";
import { Async, COLORS, Section } from "./ui";

interface HRow { horizon_h: number; mae: number; rmse: number; bias: number; n: number }
interface CRow { cutoff: string; n: number; mae: number; rmse: number; bias: number }

export default function HorizonView({ params }: { params: Params }) {
  const q = useApi<{ rows: HRow[] }>("/metrics/by-horizon", { alignment: params.alignment });
  const sweep = useApi<{ rows: CRow[] }>("/metrics/by-cutoff", { alignment: params.alignment, basis: params.basis });
  const [h, m] = params.cutoff.split(":").map(Number);
  const cutoffH = h + m / 60;
  // Delivery hours 00:00..23:59 on D are (24 - cutoff) .. (48 - cutoff) hours after a forecast published at the cutoff.
  const from = 24 - cutoffH;
  const to = 48 - cutoffH;

  return (
    <>
      <Section title="Accuracy against how far ahead the forecast was made" aside="Raw published forecasts. Each point uses the latest forecast published at least that many hours before the target. The shaded zone is the lead time a day-ahead buyer works with at the chosen cutoff.">
        <Async q={q}>
          {(d) => (
            <div className="chart tall">
              <ResponsiveContainer>
                <LineChart data={d.rows} margin={{ top: 8, right: 12, bottom: 16, left: 8 }}>
                  <CartesianGrid stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="horizon_h" type="number" domain={[1, 48]} label={{ value: "Hours between publication and target", position: "insideBottom", offset: -8 }} />
                  <YAxis tickFormatter={(v: number) => `${v}`} />
                  <Tooltip formatter={(v) => fmtMW(Number(v))} labelFormatter={(x) => `${x} h ahead`} />
                  <Legend verticalAlign="top" />
                  <ReferenceArea x1={Math.max(1, from)} x2={Math.min(48, to)} fill={COLORS.forecast} fillOpacity={0.08} />
                  <Line dataKey="mae" name="MAE" stroke={COLORS.actual} strokeWidth={2.5} dot={false} isAnimationActive={false} />
                  <Line dataKey="rmse" name="RMSE" stroke={COLORS.forecast} strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line dataKey="bias" name="Bias" stroke={COLORS.shortfall} strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Async>
      </Section>

      <Section title="Does the exact cutoff matter?" aside="Same analysis, moving the decision time. Each row is a different cutoff on the day before delivery (London time).">
        <Async q={sweep}>
          {(d) => (
            <table>
              <thead><tr><th>Cutoff</th><th className="num">Intervals</th><th className="num">MAE</th><th className="num">RMSE</th><th className="num">Bias</th></tr></thead>
              <tbody>
                {d.rows.map((r) => (
                  <tr key={r.cutoff} className={r.cutoff === params.cutoff ? "current" : ""}>
                    <td>{r.cutoff}</td><td className="num">{r.n}</td><td className="num">{fmtMW(r.mae)}</td><td className="num">{fmtMW(r.rmse)}</td><td className="num">{fmtSigned(r.bias)}</td>
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
