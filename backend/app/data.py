"""Loads the committed CSV snapshots and caches evaluation frames per (cutoff, alignment)."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pandas as pd

from .config import Settings
from .core.calibration import BASES, add_calibration, apply_basis
from .core.evaluation import build_evaluation


class DataNotFound(RuntimeError):
    pass


def _read(path: Path, time_cols: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise DataNotFound(f"{path.name} not found in {path.parent}. Run `python -m scripts.ingest` first.")
    df = pd.read_csv(path)
    for c in time_cols:
        df[c] = pd.to_datetime(df[c], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    return df.dropna(subset=["generation", *time_cols])


class DataStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.Lock()
        self._loaded = False
        self._cache: dict[tuple[str, str, str], pd.DataFrame] = {}
        self.actuals = pd.DataFrame()
        self.forecasts = pd.DataFrame()
        self.meta: dict[str, Any] = {}

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            d = self.settings.data_dir
            self.actuals = _read(d / "actuals.csv", ["startTime"]).drop_duplicates("startTime", keep="last")
            self.forecasts = _read(d / "forecasts.csv", ["startTime", "publishTime"]).drop_duplicates(
                ["startTime", "publishTime"], keep="last")
            meta_path = d / "meta.json"
            self.meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"source": "unknown"}
            self._loaded = True

    @property
    def window(self):
        return (self.settings.delivery_start, self.settings.delivery_end)

    def evaluation(self, cutoff: str, alignment: str, basis: str = "raw") -> pd.DataFrame:
        if basis not in BASES:
            raise ValueError(f"basis must be one of {BASES}, got {basis!r}")
        self.ensure_loaded()
        key = (cutoff, alignment, basis)
        if key not in self._cache:
            if basis == "raw":
                self._cache[key] = build_evaluation(
                    self.forecasts, self.actuals, self.window, cutoff, alignment, self.settings.days_before)
            else:
                self._cache[key] = apply_basis(add_calibration(self.evaluation(cutoff, alignment, "raw")), basis)
        return self._cache[key]
