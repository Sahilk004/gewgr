import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../api";
import { fmtMW } from "../format";
import { Params, RiskBuffer } from "../types";
import { Async, COLORS, Section, Strip } from "./ui";

export default function RiskView({ params }: { params: Params }) {
  const q = useApi<RiskBuffer>("/risk-buffer", params as unknown as Record<string, string | number>);
  const pct = Math.round(params.confidence * 100);

  return (
    <Async q={q}>
      {(r) => {
        if (!r.by_hour || !r.histogram) return <p className="note">Not enough matched data for a risk buffer.</p>;
        const hours = r.by_hour.map((h) => ({ hour: h.hour_of_day, shortfall: h.shortfall_mw, surplus: -h.surplus_mw }));
        const hist = r.histogram.map((b) => ({ mid: Math.round((b.from + b.to) / 2), count: b.count, positive: (b.from + b.to) / 2 > 0 }));
        return (
          <>
            <h2 className="lede">
              To be covered on {pct}% of intervals, plan for up to {fmtMW(r.shortfall_mw)} less wind than forecast, or {fmtMW(r.surplus_mw)} more.
            </h2>
            <Strip
              stats={[
                { label: "Shortfall buffer", value: fmtMW(r.shortfall_mw), hint: "wind below forecast: line up other supply", tone: "short" },
                { label: "Surplus buffer", value: fmtMW(r.surplus_mw), hint: "wind above forecast: avoid over-buying", tone: "surplus" },
                { label: "Intervals used", value: String(r.n) },
              ]}
            />
            <Section title="How the miss is spread" aside="Forecast minus actual, in GW. Right of zero: the forecast was too high.">
              <div className="chart short">
                <ResponsiveContainer>
                  <BarChart data={hist} margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
                    <CartesianGrid stroke={COLORS.grid} vertical={false} />
                    <XAxis dataKey="mid" tickFormatter={(m: number) => (m / 1000).toFixed(1)} minTickGap={24} />
                    <YAxis />
                    <Tooltip labelFormatter={(m) => `around ${m} MW`} />
                    <Bar dataKey="count" name="Intervals" fill={COLORS.forecast} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Section>
            <Section title="Buffer by hour of day" aside="Each hour is estimated from about one month of days, so read hour-to-hour differences with care.">
              <div className="chart short">
                <ResponsiveContainer>
                  <BarChart data={hours} stackOffset="sign" margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
                    <CartesianGrid stroke={COLORS.grid} vertical={false} />
                    <XAxis dataKey="hour" tickFormatter={(h: number) => `${h}:00`} />
                    <YAxis />
                    <Tooltip formatter={(v) => fmtMW(Math.abs(Number(v)))} />
                    <ReferenceLine y={0} stroke="var(--muted)" />
                    <Bar dataKey="shortfall" name="Shortfall" stackId="a" fill={COLORS.shortfall} isAnimationActive={false} />
                    <Bar dataKey="surplus" name="Surplus" stackId="a" fill={COLORS.surplus} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Section>
          </>
        );
      }}
    </Async>
  );
}
