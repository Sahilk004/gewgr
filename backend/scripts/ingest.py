"""Download FUELHH (actual wind) and WINDFOR (wind forecasts) from Elexon BMRS into CSV snapshots.

Usage (from backend/):
    python -m scripts.ingest --start 2026-01-01 --end 2026-01-31

Forecasts are fetched from two days before `start` (decisions for Jan 1 are made on Dec 31)
until the day after `end`. Requests are chunked, retried with backoff and de-duplicated.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
CHUNK_DAYS = 7
log = logging.getLogger("ingest")


def get_json(session: requests.Session, endpoint: str, params: dict, retries: int = 4) -> list[dict]:
    url = f"{BASE_URL}/{endpoint}/stream"
    for attempt in range(retries):
        try:
            resp = session.get(url, params=params, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                raise ValueError(f"{endpoint}: expected a JSON list, got {type(data).__name__}")
            return data
        except (requests.RequestException, ValueError) as exc:
            wait = 2**attempt
            log.warning("%s failed (%s); retry %d/%d in %ds", endpoint, exc, attempt + 1, retries, wait)
            time.sleep(wait)
    raise RuntimeError(f"{endpoint} failed after {retries} attempts with params {params}")


def chunks(start: date, end: date, days: int = CHUNK_DAYS):
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=days - 1), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def fetch_actuals(session: requests.Session, start: date, end: date) -> pd.DataFrame:
    rows: list[dict] = []
    for a, b in chunks(start, end):
        data = get_json(session, "FUELHH", {"settlementDateFrom": a.isoformat(), "settlementDateTo": b.isoformat(), "fuelType": "WIND"})
        rows += [r for r in data if r.get("fuelType") == "WIND"]
        log.info("FUELHH %s..%s: %d rows", a, b, len(data))
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No FUELHH rows returned")
    df = df[["startTime", "generation"]].drop_duplicates("startTime", keep="last").sort_values("startTime")
    return df


def fetch_forecasts(session: requests.Session, pub_from: date, pub_to: date) -> pd.DataFrame:
    rows: list[dict] = []
    for a, b in chunks(pub_from, pub_to):
        params = {
            "publishDateTimeFrom": f"{a.isoformat()}T00:00:00Z",
            "publishDateTimeTo": f"{(b + timedelta(days=1)).isoformat()}T00:00:00Z",
        }
        data = get_json(session, "WINDFOR", params)
        rows += data
        log.info("WINDFOR %s..%s: %d rows", a, b, len(data))
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No WINDFOR rows returned")
    df = df[["startTime", "publishTime", "generation"]]
    return df.drop_duplicates(["startTime", "publishTime"], keep="last").sort_values(["startTime", "publishTime"])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 1))
    p.add_argument("--end", type=date.fromisoformat, default=date(2026, 1, 31))
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    args.out.mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        actuals = fetch_actuals(session, args.start, args.end + timedelta(days=0))
        forecasts = fetch_forecasts(session, args.start - timedelta(days=2), args.end)
    actuals.to_csv(args.out / "actuals.csv", index=False)
    forecasts.to_csv(args.out / "forecasts.csv", index=False)
    meta = {
        "source": "elexon", "datasets": ["FUELHH", "WINDFOR"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "delivery_start": args.start.isoformat(), "delivery_end": args.end.isoformat(),
        "n_actuals": len(actuals), "n_forecasts": len(forecasts),
    }
    (args.out / "meta.json").write_text(json.dumps(meta, indent=2))
    log.info("Done: %d actuals, %d forecasts -> %s", len(actuals), len(forecasts), args.out)


if __name__ == "__main__":
    main()
