import { useQuery, UseQueryResult } from "@tanstack/react-query";

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export async function getJson<T>(path: string, params: Record<string, string | number> = {}): Promise<T> {
  const qs = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep default message */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function useApi<T>(path: string, params: Record<string, string | number> = {}): UseQueryResult<T> {
  return useQuery<T>({ queryKey: [path, params], queryFn: () => getJson<T>(path, params) });
}
