export type Alignment = "hour_mean" | "hour_ending" | "point";

export type Basis = "raw" | "calibrated";

export interface Params {
  cutoff: string;
  alignment: Alignment;
  confidence: number;
  basis: Basis;
}

export interface Meta {
  source: string;
  fetched_at: string | null;
  delivery_start: string;
  delivery_end: string;
  default_cutoff: string;
  default_alignment: Alignment;
  n_actuals: number;
  n_forecasts: number;
  forecast_resolution_min: number;
}

export interface Summary {
  n: number;
  mae?: number;
  rmse?: number;
  bias?: number;
  nmae_pct?: number | null;
  p50_abs?: number;
  p90_abs?: number;
  p99_abs?: number;
  max_abs?: number;
  mean_actual?: number;
  mean_forecast?: number;
  overforecast_share?: number;
}

export interface GroupRow {
  n: number;
  mae: number;
  rmse: number;
  bias: number;
  p90_abs: number;
  [key: string]: string | number;
}

export interface DecisionRow {
  startTime: string;
  publishTime: string;
  forecast: number;
  actual: number | null;
  low?: number | null;
  high?: number | null;
}

export interface Decision {
  summary: {
    delivery_date: string;
    cutoff_utc: string;
    cutoff_local: string;
    n_points: number;
    band: { confidence: number; shortfall_mw: number; surplus_mw: number } | null;
    latest_publish_utc?: string;
    earliest_publish_utc?: string;
    min_age_h?: number;
    peak_mw?: number;
    trough_mw?: number;
    mean_mw?: number;
  };
  rows: DecisionRow[];
}

export interface SeriesRow {
  startTime: string;
  publishTime: string;
  forecast: number;
  actual: number;
  error: number;
}

export interface RiskBuffer {
  confidence: number;
  n: number;
  shortfall_mw?: number;
  surplus_mw?: number;
  by_hour?: { hour_of_day: number; n: number; shortfall_mw: number; surplus_mw: number }[];
  histogram?: { from: number; to: number; count: number }[];
}

export interface Calibration {
  n: number;
  slope?: number;
  intercept?: number;
  offset_pct?: number;
  raw?: Summary;
  calibrated?: Summary;
}
