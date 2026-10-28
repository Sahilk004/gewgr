export const fmtNum = (v: number | null | undefined, digits = 0): string =>
  v == null || Number.isNaN(v) ? "–" : v.toLocaleString("en-GB", { maximumFractionDigits: digits });

export const fmtMW = (v: number | null | undefined, digits = 0): string =>
  v == null || Number.isNaN(v) ? "–" : `${fmtNum(v, digits)} MW`;

export const fmtPct = (v: number | null | undefined, digits = 1): string =>
  v == null || Number.isNaN(v) ? "–" : `${v.toFixed(digits)}%`;

export const fmtSigned = (v: number | null | undefined): string =>
  v == null || Number.isNaN(v) ? "–" : `${v > 0 ? "+" : ""}${fmtNum(v)} MW`;

/** Format an ISO instant in London local time. */
export const londonTime = (iso: string, opts: Intl.DateTimeFormatOptions): string =>
  new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/London", ...opts }).format(new Date(iso));

export const describeAge = (hours: number): string => {
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
};
