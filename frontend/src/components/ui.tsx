import { ReactNode } from "react";
import { UseQueryResult } from "@tanstack/react-query";

export function Async<T>({ q, children }: { q: UseQueryResult<T>; children: (data: T) => ReactNode }) {
  if (q.isPending) return <p className="note" aria-busy="true">Loading…</p>;
  if (q.isError) return <p className="error" role="alert">{(q.error as Error).message}</p>;
  return <>{children(q.data)}</>;
}

export interface Stat {
  label: string;
  value: string;
  hint?: string;
  tone?: "short" | "surplus";
}

/** A ruled strip of figures rather than a row of cards. */
export function Strip({ stats }: { stats: Stat[] }) {
  return (
    <dl className="strip">
      {stats.map((s) => (
        <div key={s.label} className={s.tone ? `stat ${s.tone}` : "stat"}>
          <dt>{s.label}</dt>
          <dd>{s.value}</dd>
          {s.hint && <small>{s.hint}</small>}
        </div>
      ))}
    </dl>
  );
}

export function Section({ title, children, aside }: { title: string; children: ReactNode; aside?: string }) {
  return (
    <section className="block">
      <h2>{title}</h2>
      {aside && <p className="note">{aside}</p>}
      {children}
    </section>
  );
}

export const COLORS = {
  forecast: "var(--teal)",
  actual: "var(--amber)",
  shortfall: "var(--short)",
  surplus: "var(--surplus)",
  grid: "var(--rule)",
  band: "var(--teal)",
};
