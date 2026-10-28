# GB wind forecast desk

A small web app for a day-ahead power buyer. It answers two questions for **January 2026**:

1. **What wind forecast did I actually have when I had to decide?** (the latest forecast published before the D-1 cutoff)
2. **How wrong are such forecasts, and how much buffer should I plan for?**

Data: Elexon BMRS `FUELHH` (actual wind) and `WINDFOR` (wind forecasts).

**Live app:** https://gewgr-5dox.vercel.app/

> **AI disclosure:** this project was built with assistance from Claude (Anthropic) for planning, code generation and review. All code was run, reviewed and understood by the author.

## Directory guide

```
backend/                FastAPI service + analysis (Python 3.12)
  app/core/selection.py    forecast-available-at-cutoff logic (the crux, pure functions)
  app/core/alignment.py    hourly forecast vs half-hourly actual alignment
  app/core/evaluation.py   joins forecast and actual, computes error
  app/core/metrics.py      MAE/RMSE/bias/quantiles, by hour/day/level/horizon, risk buffer
  app/core/decision.py     single-day decision view with leave-one-day-out band
  app/main.py              versioned API (/api/v1), validation, request logging
  app/data.py              loads CSV snapshots, caches evaluations
  scripts/ingest.py        downloads data from Elexon into backend/data/*.csv
  scripts/diagnose.py      sanity checks to run on real data
  scripts/make_sample_data.py   SYNTHETIC demo data (UI shows a warning banner)
  tests/                   pytest suite
frontend/               React + TypeScript + Vite + Recharts
api/index.py            Vercel serverless entrypoint
DECISIONS.md            assumptions and why
```

## Run it

### 1. Get the data (needs internet)
```bash
cd backend
pip install -r requirements.txt
python -m scripts.ingest --start 2026-01-01 --end 2026-01-31
python -m scripts.diagnose          # check resolution, alignment, bias vs lead time
```
Commit the generated `backend/data/*.csv` so the deployed app has no live dependency.
No internet or just exploring? `python -m scripts.make_sample_data` writes synthetic data.

### 2. Docker (everything)
```bash
docker compose up --build
# app: http://localhost:8080   API docs: http://localhost:8000/docs
```

### 3. Without Docker
```bash
cd backend && uvicorn app.main:app --reload          # http://localhost:8000
cd frontend && npm install && npm run dev            # http://localhost:5173
```

### Tests and checks
```bash
cd backend && pip install -r requirements-dev.txt && ruff check . && pytest
cd frontend && npm run typecheck && npm test
```
CI (`.github/workflows/ci.yml`) runs all of the above plus a Docker build.

## Deploy to Vercel
Import the repo; `vercel.json` builds the frontend and serves FastAPI from `api/index.py`
with the data snapshot bundled. Check the deployed URL in an incognito window.

## API (all under `/api/v1`)
`/health`, `/meta`, `/calibration`, `/decision/{date}`, `/series`, `/metrics`, `/metrics/by-day|by-hour|by-level|by-horizon|by-cutoff`, `/risk-buffer`.
Common query params: `cutoff=HH:MM`, `basis=raw|calibrated`, `alignment=hour_mean|hour_ending|point`, `confidence=0.5..0.99`.

## Limitations
One month of data is a small sample; the cutoff time and alignment are assumptions (see DECISIONS.md);
FUELHH wind may not match the forecast fleet exactly; wind only (no demand or other supply).
