"""FastAPI application. All routes are versioned under /api/v1.

NOTE: no `from __future__ import annotations` here. FastAPI must resolve the `Store`
dependency alias defined inside create_app(), which string annotations would hide.
"""
import json
import logging
import time
import uuid
from datetime import date
from typing import Annotated, Any, Literal

import pandas as pd
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import __version__
from .config import Settings
from .core import metrics
from .core.calibration import calibration_report
from .core.decision import decision_view
from .core.evaluation import restrict_to_window  # noqa: F401  (re-exported for tests)
from .data import DataNotFound, DataStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wind-api")

CutoffQ = Annotated[str, Query(pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="Local (London) HH:MM on D-1")]
AlignQ = Annotated[Literal["hour_mean", "hour_ending", "point"], Query()]
ConfQ = Annotated[float, Query(ge=0.5, le=0.99)]
BasisQ = Annotated[Literal["raw", "calibrated"], Query(description="raw forecast, or linearly calibrated to metered output")]
SWEEP_CUTOFFS = ["06:00", "08:00", "09:00", "09:20", "09:30", "09:50", "10:00", "11:00", "12:00"]


class Health(BaseModel):
    status: str
    version: str


class Meta(BaseModel):
    source: str
    fetched_at: str | None = None
    delivery_start: date
    delivery_end: date
    default_cutoff: str
    default_alignment: str
    n_actuals: int
    n_forecasts: int
    forecast_resolution_min: int


def _json(df: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = DataStore(settings)
    app = FastAPI(title="GB wind forecast accuracy API", version=__version__)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET"], allow_headers=["*"])

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        rid = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        log.info("rid=%s %s %s -> %s in %.0fms", rid, request.method, request.url.path,
                 response.status_code, (time.perf_counter() - start) * 1000)
        return response

    @app.exception_handler(DataNotFound)
    async def data_missing(_: Request, exc: DataNotFound):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def bad_value(_: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def get_store() -> DataStore:
        store.ensure_loaded()
        return store

    Store = Annotated[DataStore, Depends(get_store)]
    r = APIRouter(prefix="/api/v1")

    @r.get("/health", response_model=Health)
    def health() -> Health:
        return Health(status="ok", version=__version__)

    @r.get("/meta", response_model=Meta)
    def meta(s: Store) -> Meta:
        from .core.alignment import infer_resolution_minutes
        return Meta(
            source=str(s.meta.get("source", "unknown")), fetched_at=s.meta.get("fetched_at"),
            delivery_start=settings.delivery_start, delivery_end=settings.delivery_end,
            default_cutoff=settings.default_cutoff, default_alignment=settings.default_alignment,
            n_actuals=len(s.actuals), n_forecasts=len(s.forecasts),
            forecast_resolution_min=infer_resolution_minutes(s.forecasts["startTime"]),
        )

    @r.get("/decision/{delivery_date}")
    def decision(delivery_date: date, s: Store, cutoff: CutoffQ = settings.default_cutoff,
                 alignment: AlignQ = settings.default_alignment, basis: BasisQ = "raw", confidence: ConfQ = 0.9):
        if not (settings.delivery_start <= delivery_date <= settings.delivery_end):
            raise HTTPException(404, f"delivery_date must be within {settings.delivery_start}..{settings.delivery_end}")
        ev = s.evaluation(cutoff, alignment, basis)
        raw_ev = s.evaluation(cutoff, alignment, "raw")
        out = decision_view(s.forecasts, s.actuals, ev, delivery_date, cutoff, alignment, confidence,
                            settings.days_before, basis, raw_ev)
        return {"summary": out["summary"], "rows": _json(out["rows"])}

    @r.get("/series")
    def series(s: Store, cutoff: CutoffQ = settings.default_cutoff, alignment: AlignQ = settings.default_alignment, basis: BasisQ = "raw"):
        ev = s.evaluation(cutoff, alignment, basis)
        cols = ["startTime", "publishTime", "forecast", "actual", "error"]
        return {"rows": _json(ev[cols])}

    @r.get("/metrics")
    def metrics_summary(s: Store, cutoff: CutoffQ = settings.default_cutoff, alignment: AlignQ = settings.default_alignment, basis: BasisQ = "raw"):
        return metrics.summarize(s.evaluation(cutoff, alignment, basis))

    @r.get("/metrics/by-day")
    def metrics_by_day(s: Store, cutoff: CutoffQ = settings.default_cutoff, alignment: AlignQ = settings.default_alignment, basis: BasisQ = "raw"):
        return {"rows": metrics.by_group(s.evaluation(cutoff, alignment, basis), "delivery_date")}

    @r.get("/metrics/by-hour")
    def metrics_by_hour(s: Store, cutoff: CutoffQ = settings.default_cutoff, alignment: AlignQ = settings.default_alignment, basis: BasisQ = "raw"):
        return {"rows": metrics.by_group(s.evaluation(cutoff, alignment, basis), "hour_of_day")}

    @r.get("/metrics/by-level")
    def metrics_by_level(s: Store, cutoff: CutoffQ = settings.default_cutoff, alignment: AlignQ = settings.default_alignment, basis: BasisQ = "raw"):
        return {"rows": metrics.by_level(s.evaluation(cutoff, alignment, basis))}

    @r.get("/metrics/by-horizon")
    def metrics_by_horizon(s: Store, alignment: AlignQ = settings.default_alignment):
        return {"rows": metrics.by_horizon(s.forecasts, s.actuals, s.window, alignment)}

    @r.get("/metrics/by-cutoff")
    def metrics_by_cutoff(s: Store, alignment: AlignQ = settings.default_alignment, basis: BasisQ = "raw"):
        rows = []
        for c in SWEEP_CUTOFFS:
            m = metrics.summarize(s.evaluation(c, alignment, basis))
            rows.append({"cutoff": c, **{k: m.get(k) for k in ("n", "mae", "rmse", "bias")}})
        return {"rows": rows}

    @r.get("/calibration")
    def calibration(s: Store, cutoff: CutoffQ = settings.default_cutoff, alignment: AlignQ = settings.default_alignment):
        return calibration_report(s.evaluation(cutoff, alignment, "raw"))

    @r.get("/risk-buffer")
    def risk_buffer(s: Store, cutoff: CutoffQ = settings.default_cutoff, alignment: AlignQ = settings.default_alignment, basis: BasisQ = "raw",
                    confidence: ConfQ = 0.9):
        return metrics.risk_buffer(s.evaluation(cutoff, alignment, basis), confidence)

    app.include_router(r)
    return app


app = create_app()
