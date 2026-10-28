import { useState } from "react";
import { useApi } from "./api";
import AccuracyView from "./components/AccuracyView";
import DecisionView from "./components/DecisionView";
import HorizonView from "./components/HorizonView";
import MethodView from "./components/MethodView";
import RiskView from "./components/RiskView";
import { Async } from "./components/ui";
import { Alignment, Basis, Meta, Params } from "./types";

const TABS = [
  { id: "decision", label: "Decision day" },
  { id: "accuracy", label: "Accuracy" },
  { id: "horizon", label: "Lead time" },
  { id: "risk", label: "Risk buffer" },
  { id: "method", label: "Method" },
] as const;
type TabId = (typeof TABS)[number]["id"];

const CUTOFFS = ["06:00", "08:00", "09:00", "09:20", "09:30", "09:50", "10:00", "11:00", "12:00"];
const ALIGN: { value: Alignment; label: string }[] = [
  { value: "hour_mean", label: "Hour starting at T" },
  { value: "hour_ending", label: "Hour ending at T" },
  { value: "point", label: "Single half-hour" },
];

export default function App() {
  const metaQ = useApi<Meta>("/meta");
  const [tab, setTab] = useState<TabId>("decision");
  const [overrides, setOverrides] = useState<Partial<Params>>({});

  return (
    <Async q={metaQ}>
      {(meta) => {
        const params: Params = {
          cutoff: overrides.cutoff ?? meta.default_cutoff,
          alignment: overrides.alignment ?? meta.default_alignment,
          confidence: overrides.confidence ?? 0.9,
          basis: overrides.basis ?? "raw",
        };
        return (
          <div className="shell">
            <aside className="rail">
              <h1>Wind forecast desk</h1>
              <p className="sub">GB day-ahead purchasing, January 2026</p>

              <label>
                Decision cutoff (day before, London)
                <select value={params.cutoff} onChange={(e) => setOverrides({ ...overrides, cutoff: e.target.value })}>
                  {[...new Set([...CUTOFFS, meta.default_cutoff])].sort().map((c) => <option key={c}>{c}</option>)}
                </select>
              </label>
              <label>
                Compare actuals as
                <select value={params.alignment} onChange={(e) => setOverrides({ ...overrides, alignment: e.target.value as Alignment })}>
                  {ALIGN.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
                </select>
              </label>
              <label>
                Forecast basis
                <select value={params.basis} onChange={(e) => setOverrides({ ...overrides, basis: e.target.value as Basis })}>
                  <option value="raw">Raw (as published)</option>
                  <option value="calibrated">Calibrated to metered wind</option>
                </select>
              </label>
              <label>
                Cover {Math.round(params.confidence * 100)}% of cases
                <input type="range" min={0.5} max={0.99} step={0.01} value={params.confidence} onChange={(e) => setOverrides({ ...overrides, confidence: Number(e.target.value) })} />
              </label>
            </aside>

            <main>
              {meta.source === "synthetic" && (
                <p className="banner" role="status">Synthetic demo data. These numbers are not real. Run the ingestion script to load Elexon data.</p>
              )}
              <nav aria-label="Views">
                {TABS.map((t) => (
                  <button key={t.id} aria-current={tab === t.id ? "page" : undefined} onClick={() => setTab(t.id)}>{t.label}</button>
                ))}
              </nav>
              {tab === "decision" && <DecisionView params={params} meta={meta} />}
              {tab === "accuracy" && <AccuracyView params={params} />}
              {tab === "horizon" && <HorizonView params={params} />}
              {tab === "risk" && <RiskView params={params} />}
              {tab === "method" && <MethodView params={params} meta={meta} />}
            </main>
          </div>
        );
      }}
    </Async>
  );
}
